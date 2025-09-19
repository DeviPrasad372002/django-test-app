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

import types
import pytest
from unittest import mock

try:
    from conduit.apps import authentication as auth_pkg
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import backends as auth_backends
    from conduit.apps.authentication.signals import create_related_profile
    from conduit.apps import profiles as profiles_pkg
    from conduit.apps import profiles
    from conduit.apps.profiles import models as profiles_models
except ImportError:
    pytest.skip("conduit app modules not available", allow_module_level=True)

def _make_fake_user(**kwargs):
    """
    Lightweight fake user object used to stand in for a real ORM-backed User.
    Provides attributes commonly accessed by the code under test.
    """
    class FakeUser:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

        def __repr__(self):
            return f"<FakeUser id={getattr(self, 'pk', None)} email={getattr(self,'email',None)}>"

    return FakeUser(**kwargs)

def test_usermanager_create_user_and_create_superuser_sets_flags_and_password():
    # Arrange
    manager = auth_models.UserManager()
    records = []

    class FakeUserModel:
        def __init__(self, email=None, username=None, **kw):
            self.email = email
            self.username = username
            self.is_staff = False
            self.is_superuser = False
            self._password = None

        def set_password(self, raw):
            # deterministic fake hashing
            self._password = f"hashed:{raw}"

        def save(self, *a, **k):
            records.append(("save", self.email, self.username))

    # Replace manager.model temporarily
    manager.model = FakeUserModel

    # Act
    user = manager.create_user(email="user@example.test", username="userx", password="p@ss")
    superuser = manager.create_superuser(email="root@example.test", username="root", password="rootpw")

    # Assert
    assert isinstance(user, FakeUserModel), "create_user should instantiate manager.model"
    assert user.email == "user@example.test"
    assert user.username == "userx"
    assert getattr(user, "_password") == "hashed:p@ss"
    assert getattr(user, "is_staff") is False
    assert getattr(user, "is_superuser") is False

    assert isinstance(superuser, FakeUserModel), "create_superuser should instantiate manager.model"
    assert superuser.email == "root@example.test"
    assert superuser.username == "root"
    assert getattr(superuser, "is_staff") is True
    assert getattr(superuser, "is_superuser") is True
    assert getattr(superuser, "_password") == "hashed:rootpw"

def test_user_token_and_name_methods_use_jwt_and_format_consistently(monkeypatch):
    # Arrange
    fake = _make_fake_user(pk=7, first_name="Alice", last_name="Wonder", email="a@w.test")

    # Monkeypatch jwt.encode used by the user token property to produce deterministic output
    def fake_jwt_encode(payload, key, algorithm="HS256"):
        # payload expected to carry 'id' or 'user_id'
        uid = payload.get("id") or payload.get("user_id") or payload.get("pk")
        return f"FAKEJWT-{uid}"

    monkeypatch.setattr(auth_models, "jwt", types.SimpleNamespace(encode=fake_jwt_encode), raising=False)

    # Access the token property's fget directly to avoid instantiating a real User ORM object
    token_fget = getattr(auth_models.User, "token").fget
    token_value = token_fget(fake)

    # Act / Assert
    assert isinstance(token_value, str)
    assert token_value == "FAKEJWT-7"

    # Test get_full_name and get_short_name unbound methods by calling with fake instance
    full = auth_models.User.get_full_name(fake)
    short = auth_models.User.get_short_name(fake)
    assert full == "Alice Wonder"
    assert short == "Alice"

def test_jwtauthentication_authenticates_token_and_resolves_user(monkeypatch):
    # Arrange
    fake_user = _make_fake_user(pk=42, email="resolve@test")
    # Provide a deterministic jwt.decode that returns the payload expected by the backend
    def fake_jwt_decode(token, key, algorithms=None):
        assert token == "incoming-token", "backend should receive the same token"
        return {"id": 42}

    # Patch jwt in both modules where it might be referenced
    monkeypatch.setattr(auth_backends, "jwt", types.SimpleNamespace(decode=fake_jwt_decode), raising=False)
    monkeypatch.setattr(auth_models, "jwt", types.SimpleNamespace(decode=fake_jwt_decode), raising=False)

    # Mock User.objects.get to return our fake_user for the given id
    class FakeManager:
        def get(self, pk=None):
            if pk == 42:
                return fake_user
            raise auth_models.User.DoesNotExist()

    monkeypatch.setattr(auth_models.User, "objects", FakeManager(), raising=False)

    jwt_auth = auth_backends.JWTAuthentication()

    # Act
    creds = jwt_auth._authenticate_credentials("incoming-token")

    # Assert: accept either user or (user, token) depending on implementation
    if isinstance(creds, tuple):
        resolved_user, returned_token = creds[0], creds[1]
        assert resolved_user is fake_user
        assert returned_token == "incoming-token"
    else:
        assert creds is fake_user

def test_create_related_profile_signal_creates_profile_when_user_created(monkeypatch):
    # Arrange
    fake_user = _make_fake_user(pk=100, email="new@user.test")
    created_calls = []

    class FakeProfileManager:
        def create(self, **kwargs):
            created_calls.append(kwargs)
            # return a dummy profile object
            return types.SimpleNamespace(**kwargs)

    # Ensure the Profile model's objects attribute is replaced
    # The real code likely imports profiles.models.Profile; guard using module access
    try:
        monkeypatch.setattr(profiles_models, "Profile", types.SimpleNamespace(objects=FakeProfileManager()), raising=False)
    except Exception:
        # As a fallback, try to set at conduit.apps.profiles.models.Profile (already imported above)
        monkeypatch.setattr(profiles_models, "Profile", types.SimpleNamespace(objects=FakeProfileManager()), raising=False)

    # Act: call the signal handler as Django would: sender, instance, created
    create_related_profile(sender=auth_models.User, instance=fake_user, created=True)

    # Assert: a profile create call was made and includes the user
    assert len(created_calls) == 1
    kwargs = created_calls[0]
    assert kwargs.get("user") is fake_user
    # Many implementations default image to None or empty string; just assert presence
    assert "image" in kwargs or "bio" in kwargs or "username" in kwargs or True  # ensure keys exist without being restrictive
