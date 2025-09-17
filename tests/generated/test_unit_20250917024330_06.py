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

import importlib
import json
import random
import types

import pytest

try:
    from conduit.apps.core import utils as core_utils
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.serializers import RegistrationSerializer
    from conduit.apps.authentication.backends import JWTAuthentication
    from rest_framework.exceptions import ValidationError
except ImportError as e:
    pytest.skip(f"skipping tests due to missing dependency: {e}", allow_module_level=True)

def test_generate_random_string_deterministic(monkeypatch):
    
    # Arrange
    monkeypatch.setattr(core_utils.random, "choice", lambda seq: "Z")
    length = 8

    # Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, str)
    assert result == "Z" * length
    assert len(result) == length

def test_userjsonrenderer_render_wraps_user_key():
    
    # Arrange
    renderer = UserJSONRenderer()
    payload = {"email": "joe@example.com", "username": "joe"}

    # Act
    rendered = renderer.render(payload)

    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    parsed = json.loads(rendered.decode("utf-8"))
    assert "user" in parsed
    assert parsed["user"]["email"] == "joe@example.com"
    assert parsed["user"]["username"] == "joe"

def test_registration_serializer_validate_password_mismatch_raises():
    
    # Arrange
    serializer = RegistrationSerializer()
    bad_data = {"email": "a@b.com", "username": "u", "password": "one", "password2": "two"}

    # Act / Assert
    with pytest.raises(ValidationError):
        serializer.validate(bad_data)

def test_jwtauthentication_authenticate_no_header_returns_none():
    
    # Arrange
    auth = JWTAuthentication()

    class DummyRequest:
        def __init__(self):
            # common places for authorization info
            self.META = {}
            self.headers = {}
            self.COOKIES = {}

    req = DummyRequest()

    # Act
    result = auth.authenticate(req)

    # Assert
    assert result is None
