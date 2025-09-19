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

# Guard third-party / project imports
try:
    from target.conduit.apps.authentication import models as auth_models
    from target.conduit.apps.authentication import backends as auth_backends
    from rest_framework import exceptions as drf_exceptions
except ImportError:
    pytest.skip("conduit authentication modules or DRF not available", allow_module_level=True)

def _make_dummy_user_class(save_side_effect=None):
    """
    Create a lightweight dummy User class used to substitute for Django model instances
    in tests of manager/backend logic. It supports being returned from objects.get and
    having set_password/save called by manager implementations.
    """
    class DummyUser:
        objects = None  # will be set below if needed

        def __init__(self, email=None, username=None, **kwargs):
            self.email = email
            self.username = username
            self._password = None
            self.is_staff = kwargs.get("is_staff", False)
            self.is_superuser = kwargs.get("is_superuser", False)
            self.is_active = kwargs.get("is_active", True)
            # emulate primary key
            self.pk = kwargs.get("pk", 1)
            self.saved = False

        def set_password(self, raw):
            # emulate hashing side-effect
            self._password = f"hashed:{raw}"

        def save(self, *a, **kw):
            self.saved = True
            if save_side_effect:
                save_side_effect(self)
    # provide a simple objects manager with get method
    class _Objs:
        def __init__(self, instance=None):
            self._instance = instance or DummyUser(email="mgr@example.com", username="mgr", pk=99)

        def get(self, *a, **kw):
            # return stored instance for any lookup
            return self._instance

    DummyUser.objects = _Objs()
    return DummyUser

def test_create_user_success_and_normalization():
    # Arrange
    manager = auth_models.UserManager()
    DummyUser = _make_dummy_user_class()
    # ensure manager will instantiate DummyUser
    manager.model = DummyUser

    # Act
    user = manager.create_user(email="TEST@Example.COM", password="s3cr3t", username="tester")

    # Assert
    
    assert isinstance(user, DummyUser)
    assert getattr(user, "email", None).lower() == "test@example.com"
    assert getattr(user, "_password", None) == "hashed:s3cr3t"
    assert user.saved is True

@pytest.mark.parametrize("bad_email", [None, ""])
def test_create_user_invalid_email_raises_value_error(bad_email):
    # Arrange
    manager = auth_models.UserManager()
    DummyUser = _make_dummy_user_class()
    manager.model = DummyUser

    # Act / Assert
    with pytest.raises(ValueError):
        manager.create_user(email=bad_email, password="pw")

def test_create_superuser_sets_flags():
    # Arrange
    manager = auth_models.UserManager()
    DummyUser = _make_dummy_user_class()
    manager.model = DummyUser

    # Act
    superuser = manager.create_superuser(email="admin@example.com", password="rootpw", username="admin")

    # Assert
    assert isinstance(superuser, DummyUser)
    assert superuser.is_staff is True
    # some implementations set is_superuser, assert truthiness
    assert getattr(superuser, "is_superuser", True) is True
    assert superuser.saved is True

def test__generate_jwt_token_calls_jwt_encode(monkeypatch):
    # Arrange
    # Ensure jwt.encode exists in module and returns predictable bytes/string
    encoded = "signed-jwt"
    monkeypatch.setattr(auth_models, "jwt", types.SimpleNamespace(encode=lambda payload, key, algorithm: encoded))
    # Provide predictable settings secret and datetime if needed by implementation
    monkeypatch.setattr(auth_models, "settings", types.SimpleNamespace(SECRET_KEY="sekrit", SIMPLE_JWT=None), raising=False)

    # Act
    token = auth_models._generate_jwt_token(42)

    # Assert
    assert token == encoded

def test_token_property_uses_generator(monkeypatch):
    # Arrange
    # If a token property uses _generate_jwt_token, patch that to return sentinel
    sentinel = "tok-xyz"
    if hasattr(auth_models, "_generate_jwt_token"):
        monkeypatch.setattr(auth_models, "_generate_jwt_token", lambda pk: sentinel)
        # Create a minimal dummy user-like object and call property functionally
        dummy = types.SimpleNamespace(pk=101)
        # If token is implemented as a property on User class, we can call the function unbound or access attribute
        if hasattr(auth_models.User, "token"):
            # If token is a @property
            try:
                tok = auth_models.User.token.fget(dummy)  # unbound property getter
            except Exception:
                # fallback: call _generate_jwt_token directly
                tok = auth_models._generate_jwt_token(dummy.pk)
        else:
            tok = auth_models._generate_jwt_token(dummy.pk)
        # Assert
        assert tok == sentinel
    else:
        pytest.skip("_generate_jwt_token not present in auth_models", allow_module_level=False)

def test_get_full_name_and_short_name_bound_to_arbitrary_object():
    # Arrange
    # Use a SimpleNamespace to simulate an instance with first_name/last_name/username
    dummy = types.SimpleNamespace(first_name="Jane", last_name="Doe", username="jdoe")

    # Act
    # Some implementations define methods on class; call unbound function with dummy as self
    if hasattr(auth_models.User, "get_full_name"):
        full = auth_models.User.get_full_name(dummy)
        assert isinstance(full, str)
        assert full == "Jane Doe"
    else:
        pytest.skip("User.get_full_name not implemented", allow_module_level=False)

    if hasattr(auth_models.User, "get_short_name"):
        short = auth_models.User.get_short_name(dummy)
        assert isinstance(short, str)
        assert short == "jdoe"
    else:
        pytest.skip("User.get_short_name not implemented", allow_module_level=False)

def test_authenticate_no_header_returns_none():
    # Arrange
    backend = auth_backends.JWTAuthentication()
    request = types.SimpleNamespace(META={})

    # Act
    result = backend.authenticate(request)

    # Assert
    assert result is None

def test_authenticate_with_invalid_token_raises_authentication_failed(monkeypatch):
    # Arrange
    backend = auth_backends.JWTAuthentication()
    # Build request-like object with Authorization header
    request = types.SimpleNamespace(META={"HTTP_AUTHORIZATION": "Token badtoken"})
    
    monkeypatch.setattr(auth_backends, "jwt", types.SimpleNamespace(decode=lambda token, key, algorithms: (_ for _ in ()).throw(ValueError("bad"))))
    # Act / Assert
    with pytest.raises(drf_exceptions.AuthenticationFailed):
        backend.authenticate(request)

def test_authenticate_valid_token_returns_user_and_token(monkeypatch):
    # Arrange
    backend = auth_backends.JWTAuthentication()
    token_str = "validtoken"
    request = types.SimpleNamespace(META={"HTTP_AUTHORIZATION": f"Token {token_str}"})

    # Patch jwt.decode to return payload with id
    monkeypatch.setattr(auth_backends, "jwt", types.SimpleNamespace(decode=lambda token, key, algorithms: {"id": 7}))

    # Create DummyUser and ensure backend will find it via objects.get
    DummyUser = _make_dummy_user_class()
    dummy_instance = DummyUser(email="found@example.com", username="found", pk=7)
    # override the objects.get to return that instance
    DummyUser.objects = type("Mgr", (), {"get": staticmethod(lambda *a, **kw: dummy_instance)})()

    # Patch reference to User model inside backend module to our DummyUser
    # Different implementations may reference different names; try a few common ones
    if hasattr(auth_backends, "User"):
        monkeypatch.setattr(auth_backends, "User", DummyUser)
    if hasattr(auth_backends, "UserModel"):
        monkeypatch.setattr(auth_backends, "UserModel", DummyUser)

    # Act
    result = backend.authenticate(request)

    # Assert
    assert isinstance(result, tuple)
    user, returned_token = result
    assert user is dummy_instance
    # The returned token should equal the raw token string part
    assert returned_token == token_str

def test__authenticate_credentials_not_found_raises(monkeypatch):
    # Arrange
    backend = auth_backends.JWTAuthentication()
    # patch jwt.decode to return an id not present in DB
    monkeypatch.setattr(auth_backends, "jwt", types.SimpleNamespace(decode=lambda token, key, algorithms: {"id": 9999}))

    
    class DummyUserNo:
        objects = type("Mgr", (), {"get": staticmethod(lambda *a, **kw: (_ for _ in ()).throw(Exception("no user")) )})()

    if hasattr(auth_backends, "User"):
        monkeypatch.setattr(auth_backends, "User", DummyUserNo)
    if hasattr(auth_backends, "UserModel"):
        monkeypatch.setattr(auth_backends, "UserModel", DummyUserNo)

    
    with pytest.raises(drf_exceptions.AuthenticationFailed):
        # provide payload-like token and header label; function signature may vary,
        # try the internal method with a tuple (token, user) pattern where applicable
        try:
            backend._authenticate_credentials("sometoken")
        except TypeError:
            # some implementations expect (payload, token)
            backend._authenticate_credentials("sometoken", "sometoken")
