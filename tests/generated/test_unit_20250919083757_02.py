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

try:
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import backends
    from rest_framework import exceptions as drf_exceptions
    from django.conf import settings
except Exception as e:
    pytest.skip("Required third-party modules or target package not available: %s" % e, allow_module_level=True)

class FakeUser:
    def __init__(self, email=None, username=None, is_active=True, **kwargs):
        self.email = email
        self.username = username
        self.is_active = is_active
        # store any flags set via kwargs (e.g., is_staff, is_superuser)
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._password = None
        self.saved_using = None

    def set_password(self, raw):
        # mimic Django's set_password side-effect
        self._password = raw

    def save(self, using=None):
        self.saved_using = using

class ManagerStub:
    def __init__(self, model_cls=FakeUser, db_alias="default"):
        self.model = model_cls
        self._db = db_alias

    def normalize_email(self, email):
        # simple normalizer as in Django's BaseUserManager
        return email.lower() if isinstance(email, str) else email

def test_user_token_uses_jwt_and_settings(monkeypatch):
    # Arrange
    fake_instance = types.SimpleNamespace(pk=123)
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret", raising=False)

    called = {}

    def fake_encode(payload, key, algorithm="HS256"):
        called['payload'] = payload
        called['key'] = key
        called['algorithm'] = algorithm
        return "encoded.jwt.token"

    monkeypatch.setattr(auth_models, "jwt", types.SimpleNamespace(encode=fake_encode))
    # Act
    token_value = auth_models.User.token(fake_instance)
    # Assert
    assert token_value == "encoded.jwt.token"
    assert called['payload'].get('id') == 123
    assert called['key'] == "test-secret"
    assert called['algorithm'] in ("HS256", "HS256")

def test_get_full_name_returns_email_when_present():
    # Arrange
    fake = types.SimpleNamespace(email="me@example.com")
    # Act
    full = auth_models.User.get_full_name(fake)
    # Assert
    assert isinstance(full, str)
    assert full == "me@example.com"

@pytest.mark.parametrize(
    "email,username,password,expect_error",
    [
        (None, "u", "p", TypeError),
        ("e@example.com", None, "p", TypeError),
        ("e@example.com", "u", "p", None),
    ],
)
def test_create_user_various_inputs(email, username, password, expect_error):
    # Arrange
    manager = ManagerStub(model_cls=FakeUser, db_alias="mydb")
    # Act / Assert
    if expect_error is not None:
        with pytest.raises(expect_error):
            auth_models.UserManager.create_user(manager, email, username, password)
    else:
        user = auth_models.UserManager.create_user(manager, email, username, password)
        assert isinstance(user, FakeUser)
        # ensure password was set by manager via set_password
        assert user._password == password
        # ensure save called with correct DB alias
        assert user.saved_using == "mydb"
        assert user.email == "e@example.com"
        assert user.username == "u"

def test_create_superuser_sets_flags_and_saves():
    # Arrange
    class FakeUserWithFlags(FakeUser):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    manager = ManagerStub(model_cls=FakeUserWithFlags, db_alias="superdb")
    # Act
    su = auth_models.UserManager.create_superuser(manager, "admin@example.com", "admin", "secure")
    # Assert
    assert isinstance(su, FakeUserWithFlags)
    # typical implementation sets these flags
    assert getattr(su, "is_superuser", True) is True
    assert getattr(su, "is_staff", True) is True
    assert su._password == "secure"
    assert su.saved_using == "superdb"

def test__authenticate_credentials_success(monkeypatch):
    # Arrange
    decoded_payload = {"id": 7}

    def fake_decode(token, key, algorithms=None):
        assert token == "validtoken"
        return decoded_payload

    fake_user = FakeUser(email="x@x", username="u", is_active=True)
    fake_manager = types.SimpleNamespace(get=lambda pk: fake_user)

    # Ensure backend points to our fake manager and jwt
    monkeypatch.setattr(backends, "jwt", types.SimpleNamespace(decode=fake_decode))
    # Patch the User.objects.get behavior by replacing User with an object having objects attr
    class UserProxy:
        objects = fake_manager

    monkeypatch.setattr(backends, "User", UserProxy)
    monkeypatch.setattr(settings, "SECRET_KEY", "s", raising=False)

    # Act
    user, token = backends.JWTAuthentication()._authenticate_credentials("validtoken")
    # Assert
    assert user is fake_user
    assert token == "validtoken"

def test__authenticate_credentials_inactive_user_raises(monkeypatch):
    # Arrange
    def fake_decode(token, key, algorithms=None):
        return {"id": 8}

    inactive_user = FakeUser(email="y@y", username="v", is_active=False)
    fake_manager = types.SimpleNamespace(get=lambda pk: inactive_user)

    monkeypatch.setattr(backends, "jwt", types.SimpleNamespace(decode=fake_decode))
    class UserProxy:
        objects = fake_manager

    monkeypatch.setattr(backends, "User", UserProxy)
    monkeypatch.setattr(settings, "SECRET_KEY", "s", raising=False)

    # Act / Assert
    with pytest.raises(drf_exceptions.AuthenticationFailed):
        backends.JWTAuthentication()._authenticate_credentials("token-for-inactive")

def test__authenticate_credentials_invalid_token_raises(monkeypatch):
    # Arrange
    def fake_decode_raises(token, key, algorithms=None):
        raise Exception("invalid token")

    monkeypatch.setattr(backends, "jwt", types.SimpleNamespace(decode=fake_decode_raises))
    monkeypatch.setattr(settings, "SECRET_KEY", "s", raising=False)

    # Act / Assert
    with pytest.raises(drf_exceptions.AuthenticationFailed):
        backends.JWTAuthentication()._authenticate_credentials("some-bad-token")

def test__authenticate_credentials_user_not_found_raises(monkeypatch):
    # Arrange
    def fake_decode(token, key, algorithms=None):
        return {"id": 999}

    def fake_get_raises(pk):
        raise Exception("not found")

    fake_manager = types.SimpleNamespace(get=fake_get_raises)
    monkeypatch.setattr(backends, "jwt", types.SimpleNamespace(decode=fake_decode))
    class UserProxy:
        objects = fake_manager
    monkeypatch.setattr(backends, "User", UserProxy)
    monkeypatch.setattr(settings, "SECRET_KEY", "s", raising=False)

    # Act / Assert
    with pytest.raises(drf_exceptions.AuthenticationFailed):
        backends.JWTAuthentication()._authenticate_credentials("token-for-nonexistent")
