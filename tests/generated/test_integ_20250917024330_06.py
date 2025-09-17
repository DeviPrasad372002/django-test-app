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

import json
from types import SimpleNamespace

try:
    import pytest
    from target.conduit.apps.authentication import models as auth_models
    from target.conduit.apps.authentication import backends as auth_backends
    from target.conduit.apps.authentication import renderers as auth_renderers
except Exception as e:
    import pytest
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

from unittest import mock

def test__generate_jwt_token_encodes_user_id_and_returns_token(monkeypatch):
    
    # Arrange
    fake_user = SimpleNamespace(id=123)

    # Create a fake jwt module with an encode that echoes back the user_id for deterministic behavior
    class FakeJWT:
        def encode(self, payload, key, algorithm=None):
            
            assert "user_id" in payload and payload["user_id"] == 123
            assert "exp" in payload and isinstance(payload["exp"], int)
            return f"encoded-{payload['user_id']}"

    monkeypatch.setattr(auth_models, "jwt", FakeJWT())

    # Act
    token = auth_models._generate_jwt_token(fake_user)

    # Assert
    assert isinstance(token, str)
    assert token == "encoded-123"

def test_JWTAuthentication_authenticate_delegates_to__authenticate_credentials_and_handles_missing_header(monkeypatch):
    
    # Arrange
    auth_instance = auth_backends.JWTAuthentication()

    # Patch the internal credential handler to ensure it returns a known tuple regardless of input
    def fake_authenticate_credentials(self, token):
        # The token passed should be a string-like or bytes-like token extracted from header
        assert token is not None
        return ("fake_user_object", "fake_token_value")

    monkeypatch.setattr(auth_backends.JWTAuthentication, "_authenticate_credentials", fake_authenticate_credentials)

    # Create a fake request with an Authorization header
    request_with_header = SimpleNamespace(META={"HTTP_AUTHORIZATION": "Token sometoken"})

    # Act
    result = auth_instance.authenticate(request_with_header)

    # Assert
    assert result == ("fake_user_object", "fake_token_value")

    # Now verify that missing header returns None
    request_no_header = SimpleNamespace(META={})
    result_none = auth_instance.authenticate(request_no_header)
    assert result_none is None

def test_UserJSONRenderer_render_produces_json_bytes_matching_input():
    
    # Arrange
    renderer = auth_renderers.UserJSONRenderer()
    input_data = {"user": {"email": "tester@example.com", "username": "tester", "token": "tok-1"}}

    # Act
    rendered = renderer.render(input_data)

    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    parsed = json.loads(rendered.decode("utf-8"))
    assert parsed == input_data
