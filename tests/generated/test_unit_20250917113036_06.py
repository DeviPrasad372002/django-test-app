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
import types
from unittest.mock import Mock

import pytest

try:
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.authentication.serializers import LoginSerializer
    from rest_framework import serializers as drf_serializers
except ImportError:
    pytest.skip("conduit.authentication or rest_framework not available", allow_module_level=True)

def test_userjsonrenderer_render_wraps_user_key():
    
    # Arrange
    renderer = UserJSONRenderer()
    payload = {"email": "alice@example.com", "username": "alice"}

    # Act
    rendered = renderer.render(payload, None, None)

    # Assert
    assert isinstance(rendered, (bytes, bytearray)), "render should return bytes"
    decoded = json.loads(rendered.decode("utf-8"))
    assert "user" in decoded and decoded["user"] == payload

def test_userjsonrenderer_preserves_errors_when_present():
    
    # Arrange
    renderer = UserJSONRenderer()
    payload = {"errors": {"detail": "invalid"}}

    # Act
    rendered = renderer.render(payload, None, None)

    # Assert
    decoded = json.loads(rendered.decode("utf-8"))
    # When errors are present, renderer should not wrap them in "user"
    assert "errors" in decoded and decoded["errors"] == payload["errors"]
    assert "user" not in decoded

def test_jwtauthentication_authenticate_calls_internal_credentials_and_returns_tuple(monkeypatch):
    
    # Arrange
    auth = JWTAuthentication()
    called = {}

    def fake_authenticate_credentials(token):
        called["token"] = token
        return ("fake_user", "fake_token_value")

    # Patch the internal credential method
    monkeypatch.setattr(auth, "_authenticate_credentials", fake_authenticate_credentials)
    # Build a minimal request-like object with META mapping
    request = types.SimpleNamespace(META={"HTTP_AUTHORIZATION": "Token abc.def.ghi"})

    # Act
    result = auth.authenticate(request)

    # Assert
    assert called.get("token") == "abc.def.ghi"
    assert result == ("fake_user", "fake_token_value")

def test_jwtauthentication_authenticate_returns_none_on_missing_header():
    
    # Arrange
    auth = JWTAuthentication()
    request = types.SimpleNamespace(META={})

    # Act
    result = auth.authenticate(request)

    # Assert
    assert result is None

@pytest.mark.parametrize(
    "payload,missing_field",
    [
        ({"email": "bob@example.com"}, "password"),
        ({"password": "hunter2"}, "email"),
        ({}, "email and password"),
    ],
)
def test_loginserializer_validate_requires_email_and_password(payload, missing_field):
    
    # Arrange
    serializer = LoginSerializer(data=payload)

    # Act / Assert
    with pytest.raises(drf_serializers.ValidationError):
        serializer.is_valid(raise_exception=True)
