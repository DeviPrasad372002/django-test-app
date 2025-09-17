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
    from conduit.apps.core import utils as core_utils
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import renderers as auth_renderers
    from conduit.apps.core import exceptions as core_exceptions
    from rest_framework.exceptions import NotFound, APIException
    from django.conf import settings
except ImportError:
    pytest.skip("Required application modules are not importable", allow_module_level=True)

@pytest.mark.parametrize("length,expected", [(0, ""), (6, "XXXXXX")])
def test_generate_random_string_deterministic_and_zero_len(length, expected, monkeypatch):
    
    # Arrange
    # Force deterministic output from random.choice used inside generate_random_string
    monkeypatch.setattr(core_utils, "random", types.SimpleNamespace(choice=lambda seq: "X"))

    # Act
    result = core_utils.generate_random_string(length)

    # Assert
    assert isinstance(result, str)
    assert result == expected

def test__generate_jwt_token_and_userjsonrenderer_render(monkeypatch):
    
    # Arrange
    # Make jwt.encode deterministic and ensure settings.SECRET_KEY exists
    fake_jwt_module = types.SimpleNamespace(encode=lambda payload, key, algorithm: "FAKEJWT")
    monkeypatch.setattr(auth_models, "jwt", fake_jwt_module, raising=True)
    # settings may or may not already have SECRET_KEY; set it for the test
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret", raising=False)

    # Build a minimal user-like object acceptable to the token generator
    DummyUser = types.SimpleNamespace
    user = DummyUser(pk=42, id=42, username="alice", email="alice@example.com")

    # Act
    token = auth_models._generate_jwt_token(user)

    # Assert token produced as our fake
    assert token == "FAKEJWT"
    assert isinstance(token, str)

    # Arrange for renderer usage
    renderer = auth_renderers.UserJSONRenderer()
    payload = {"user": {"email": user.email, "token": token, "username": user.username}}

    # Act: render to JSON bytes
    rendered = renderer.render(payload, accepted_media_type="application/json", renderer_context={})

    
    assert isinstance(rendered, (bytes, bytearray))
    assert b'"token":"FAKEJWT"' in rendered
    assert b'"email":"alice@example.com"' in rendered

def test_core_exception_handler_delegates_to_helpers(monkeypatch):
    
    # Arrange
    called = {}

    def fake_not_found_handler(exc, context):
        called['not_found'] = True
        return "NOT_FOUND_HANDLED"

    def fake_generic_handler(exc, context):
        called['generic'] = True
        return "GENERIC_HANDLED"

    monkeypatch.setattr(core_exceptions, "_handle_not_found_error", fake_not_found_handler, raising=True)
    monkeypatch.setattr(core_exceptions, "_handle_generic_error", fake_generic_handler, raising=True)

    # Act & Assert: NotFound should be delegated to _handle_not_found_error
    result_nf = core_exceptions.core_exception_handler(NotFound("missing"), {})
    assert result_nf == "NOT_FOUND_HANDLED"
    assert called.get('not_found') is True
    assert 'generic' not in called

    # Reset and test generic APIException
    called.clear()
    result_gen = core_exceptions.core_exception_handler(APIException("boom"), {})
    assert result_gen == "GENERIC_HANDLED"
    assert called.get('generic') is True
    assert 'not_found' not in called
