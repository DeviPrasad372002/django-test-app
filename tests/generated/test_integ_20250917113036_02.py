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

import time
import types
import pytest

try:
    import jwt as pyjwt
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import backends as auth_backends
    from conduit.apps.core import exceptions as core_exceptions
    from rest_framework import exceptions as drf_exceptions
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

def test__generate_jwt_token_is_decodable_and_contains_user_id(monkeypatch):
    
    # Arrange
    # Ensure deterministic secret
    monkeypatch.setattr("django.conf.settings.SECRET_KEY", "test-secret", raising=False)

    # Create a User instance without saving to DB; assign a primary key
    user = auth_models.User()
    user.pk = 7

    # Act
    token = user._generate_jwt_token()

    # Assert
    assert isinstance(token, (str, bytes)), "token should be a string or bytes"

    # normalize bytes -> str for pyjwt decode compatibility
    token_str = token.decode() if isinstance(token, bytes) else token
    # decode the token to inspect payload
    payload = pyjwt.decode(token_str, "test-secret", algorithms=["HS256"])
    assert isinstance(payload, dict)
    # Common implementations use 'id' or 'user_id'; accept either but require the pk to be present
    assert ("id" in payload and payload["id"] == 7) or ("user_id" in payload and payload["user_id"] == 7)
    assert "exp" in payload and isinstance(payload["exp"], int)
    # exp should be in the future
    assert payload["exp"] > int(time.time())

def test__authenticate_credentials_valid_and_invalid(monkeypatch):
    
    # Arrange
    # Prepare a fake user class with a manager that can return our instance
    class DoesNotExist(Exception):
        pass

    class FakeUser:
        DoesNotExist = DoesNotExist

        def __init__(self, pk, active=True):
            self.pk = pk
            self.is_active = active

    fake_user = FakeUser(pk=15, active=True)

    class FakeManager:
        def get(self, pk):
            if pk == 15:
                return fake_user
            raise DoesNotExist()

    FakeUser.objects = FakeManager()

    # Patch the User reference in the backends module to our FakeUser
    monkeypatch.setattr(auth_backends, "User", FakeUser, raising=False)

    # Patch jwt.decode to return a payload with id 15 for the valid case
    def fake_decode_success(token, key, algorithms=None):
        return {"id": 15, "exp": int(time.time()) + 3600}

    monkeypatch.setattr(pyjwt, "decode", fake_decode_success)

    # Act (valid)
    returned_user = auth_backends._authenticate_credentials("sometoken")

    # Assert (valid)
    assert returned_user is fake_user
    assert getattr(returned_user, "is_active", True) is True

    # Now test invalid token (expired / decode error)
    def fake_decode_fail(*args, **kwargs):
        raise pyjwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(pyjwt, "decode", fake_decode_fail)

    
    with pytest.raises(drf_exceptions.AuthenticationFailed):
        auth_backends._authenticate_credentials("badtoken")

def test_core_exception_handler_handles_not_found_and_generic():
    
    # Arrange
    # Create a NotFound exception and a generic exception
    not_found_exc = drf_exceptions.NotFound(detail="nope")
    generic_exc = Exception("unexpected")

    # Act: use the module-level helpers directly
    resp_not_found = core_exceptions._handle_not_found_error(not_found_exc, context={})
    resp_generic = core_exceptions._handle_generic_error(generic_exc, context={})

    # Assert: Not Found mapping
    assert hasattr(resp_not_found, "status_code")
    assert resp_not_found.status_code == 404
    assert isinstance(resp_not_found.data, dict)
    
    assert "errors" in resp_not_found.data or "detail" in resp_not_found.data

    # Assert: Generic error mapping (500 or 400 depending on implementation)
    assert hasattr(resp_generic, "status_code")
    # Generic handler should not return 200
    assert resp_generic.status_code != 200
    assert isinstance(resp_generic.data, dict)
    assert "errors" in resp_generic.data or "detail" in resp_generic.data
