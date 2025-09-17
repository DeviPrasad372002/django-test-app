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
    import conduit.apps.authentication.backends as backends
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.authentication.models import User, UserManager
    import rest_framework.authentication as rf_auth
    from rest_framework.exceptions import AuthenticationFailed
    import jwt
except ImportError as e:
    import pytest
    pytest.skip("Skipping tests due to missing dependency: {}".format(e), allow_module_level=True)

def test_JWTAuthentication_authenticate_no_authorization_header_returns_none(monkeypatch):
    
    # Arrange
    monkeypatch.setattr(rf_auth, "get_authorization_header", lambda req: b"")
    auth = JWTAuthentication()
    dummy_request = object()

    # Act
    result = auth.authenticate(dummy_request)

    # Assert
    assert result is None

def test_JWTAuthentication_authenticate_delegates_to__authenticate_credentials(monkeypatch):
    
    # Arrange
    monkeypatch.setattr(rf_auth, "get_authorization_header", lambda req: b"Bearer sometoken123")
    called = {}

    def fake_auth_credentials(self, token):
        called['token'] = token
        return ("fake_user", "fake_token")

    monkeypatch.setattr(backends.JWTAuthentication, "_authenticate_credentials", fake_auth_credentials)
    auth = JWTAuthentication()
    dummy_request = object()

    # Act
    result = auth.authenticate(dummy_request)

    # Assert
    assert result == ("fake_user", "fake_token")
    assert called.get("token") == b"sometoken123" or called.get("token") == "sometoken123"

def test__authenticate_credentials_invalid_jwt_raises_AuthenticationFailed(monkeypatch):
    
    # Arrange
    def raise_decode(*args, **kwargs):
        raise jwt.DecodeError("invalid token")

    monkeypatch.setattr(backends.jwt, "decode", raise_decode)
    auth = JWTAuthentication()

    # Act / Assert
    with pytest.raises(AuthenticationFailed):
        auth._authenticate_credentials("badtoken")

def test_User_get_full_name_and_token_property(monkeypatch):
    
    # Arrange
    user = User()
    user.first_name = "John"
    user.last_name = "Doe"
    user.email = "john@example.com"

    # Ensure token generation is deterministic by stubbing internal generator
    monkeypatch.setattr(User, "_generate_jwt_token", lambda self: "STATIC_JWT")
    
    # Act
    full_name = user.get_full_name()
    token_value = user.token

    # Assert
    assert isinstance(full_name, str)
    assert full_name == "John Doe"
    assert token_value == "STATIC_JWT"

def test_UserManager_create_user_raises_ValueError_when_email_missing():
    
    # Arrange
    manager = UserManager()

    # Act / Assert
    with pytest.raises(ValueError):
        manager.create_user(email=None, password="pw")
