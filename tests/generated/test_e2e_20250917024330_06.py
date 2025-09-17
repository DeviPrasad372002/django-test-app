import importlib.util, pytest
if importlib.util.find_spec('django') is None:
    pytest.skip('django not installed; skipping module', allow_module_level=True)

import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

try:
    import pytest
    import jwt
    import datetime
    from django.conf import settings
    from django.utils import timezone
    from conduit.apps.authentication.models import User
except ImportError:
    import pytest
    pytest.skip("Django or project imports unavailable", allow_module_level=True)

def test_usermanager_create_user_and_superuser_and_jwt_token():
    
    # Arrange
    username = "testuser"
    email = "testuser@example.com"
    password = "s3cureP@ssw0rd"

    # Act
    user = User.objects.create_user(username=username, email=email, password=password)

    # Assert
    assert isinstance(user, User)
    assert user.username == username
    assert user.email == email
    assert user.check_password(password) is True

    # token property should be a JWT that decodes to this user's id
    token = user.token
    assert isinstance(token, (str, bytes))
    # jwt.decode in pyjwt >=2 returns dict; ensure correct algorithm used
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    # Expect the token to include the user's id under a common key (id)
    assert decoded.get("id") == user.pk

    # name helpers should return sensible string values
    full = user.get_full_name()
    short = user.get_short_name()
    assert isinstance(full, str)
    assert isinstance(short, str)
    # Common implementations use the username as both full and short name
    assert full == username
    assert short == username

    # create_superuser creates elevated account flags
    superuser = User.objects.create_superuser(username="admin", email="admin@example.com", password="adminpw")
    assert isinstance(superuser, User)
    assert superuser.is_superuser is True
    assert superuser.is_staff is True

def test_timestampedmodel_updates_updated_at_on_save(monkeypatch):
    
    # Arrange
    base_time = datetime.datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    later_time = base_time + datetime.timedelta(seconds=42)

    # Force timezone.now to return base_time for creation
    monkeypatch.setattr(timezone, "now", lambda: base_time)

    user = User.objects.create_user(username="timeuser", email="time@example.com", password="pw")

    # Ensure updated_at and created_at are set to base_time initially
    assert getattr(user, "created_at", None) is not None
    assert getattr(user, "updated_at", None) is not None
    assert user.created_at == base_time
    assert user.updated_at == base_time

    # Act: advance time and save an update
    monkeypatch.setattr(timezone, "now", lambda: later_time)
    user.username = "timeuser2"
    user.save()

    # Refresh from DB and Assert updated_at changed to later_time
    refreshed = User.objects.get(pk=user.pk)
    assert refreshed.username == "timeuser2"
    assert refreshed.updated_at == later_time
    assert refreshed.updated_at > refreshed.created_at
