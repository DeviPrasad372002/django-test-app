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
from unittest import mock

try:
    import pytest
    # Core utils
    from conduit.apps.core.utils import generate_random_string
    # Authentication models and renderers
    from conduit.apps.authentication import renderers as auth_renderers_mod
    from conduit.apps.authentication.models import User
    import conduit.apps.authentication.models as auth_models_mod
    # Core exceptions
    from conduit.apps.core import exceptions as core_exceptions
    # REST framework exceptions for creating representative exceptions
    import rest_framework.exceptions as rest_exceptions
except Exception as e:  # pragma: no cover - skip module if dependencies missing
    import pytest
    pytest.skip(f"Missing dependencies for integration tests: {e}", allow_module_level=True)

def _get_renderer_function():
    # Prefer a module-level render function; otherwise pick a sensible renderer class instance.
    if hasattr(auth_renderers_mod, "render") and callable(getattr(auth_renderers_mod, "render")):
        return getattr(auth_renderers_mod, "render")
    # Try common renderer class names
    for cls_name in ("UserJSONRenderer", "CommentJSONRenderer", "ArticleJSONRenderer"):
        if hasattr(auth_renderers_mod, cls_name):
            cls = getattr(auth_renderers_mod, cls_name)
            try:
                return cls().render
            except Exception:
                # Fall back if ctor requires args
                return cls.render
    raise RuntimeError("No renderer function/class found in authentication.renderers")

def test_generate_random_string_deterministic_with_monkeypatched_choice(monkeypatch):
    
    # Arrange
    # Force random.choice inside the module to always return 'Z'
    import conduit.apps.core.utils as utils_mod
    monkeypatch.setattr(utils_mod.random, "choice", lambda seq: "Z")
    length = 6

    # Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, str)
    assert len(result) == length
    assert result == "Z" * length

def test_user__generate_jwt_token_calls_jwt_encode_and_returns_token(monkeypatch):
    
    # Arrange
    user = User()
    # Some User models expect attributes; set minimal ones used in token payload
    setattr(user, "id", 42)
    setattr(user, "username", "tester")
    setattr(user, "email", "tester@example.com")

    # Patch jwt.encode used in the authentication.models module to avoid real signing and external libs behavior
    fake_token = b"FAKE.JWT.TOKEN"
    jwt_mock = mock.MagicMock(return_value=fake_token)
    # Replace the jwt object inside the authentication models module
    monkeypatch.setattr(auth_models_mod, "jwt", mock.MagicMock(encode=jwt_mock))

    # Act
    token = user._generate_jwt_token()

    # Assert
    # Ensure jwt.encode was called with a payload that includes the user's id
    assert jwt_mock.called, "jwt.encode was not called"
    called_payload = jwt_mock.call_args[0][0]
    assert isinstance(called_payload, dict)
    assert called_payload.get("id") == 42
    # The returned token should be the fake token (bytes or str)
    if isinstance(token, bytes):
        assert token == fake_token
    else:
        assert token == fake_token.decode()

@pytest.mark.parametrize(
    "exc,expected_handler_attr",
    [
        (rest_exceptions.NotFound(detail="missing"), "_handle_not_found_error"),
        (rest_exceptions.APIException(detail="boom"), "_handle_generic_error"),
    ],
)
def test_core_exception_handler_dispatches_to_correct_handler(monkeypatch, exc, expected_handler_attr):
    
    # Arrange
    sentinel = object()
    handler_mock = mock.MagicMock(return_value=sentinel)
    # Replace both handlers so we can ensure the one expected is called while the other is not
    monkeypatch.setattr(core_exceptions, "_handle_not_found_error", mock.MagicMock(return_value="NF"))
    monkeypatch.setattr(core_exceptions, "_handle_generic_error", mock.MagicMock(return_value="GEN"))

    # Now set the expected one to our spy to capture calls
    monkeypatch.setattr(core_exceptions, expected_handler_attr, handler_mock)

    # Act
    response = core_exceptions.core_exception_handler(exc, context={})

    # Assert
    handler_mock.assert_called_once_with(exc)
    # The core_exception_handler should return whatever the handler returned
    assert response is sentinel

def test_authentication_renderer_render_roundtrip_returns_json_bytes_and_expected_structure():
    
    # Arrange
    renderer_fn = _get_renderer_function()
    data = {"user": {"email": "a@b.com", "username": "alpha"}}

    # Act
    rendered = renderer_fn(data, accepted_media_type="application/json", renderer_context={})

    # Assert
    # Should return bytes or str JSON
    assert isinstance(rendered, (bytes, str))
    raw = rendered.decode() if isinstance(rendered, bytes) else rendered
    parsed = json.loads(raw)
    # Ensure top-level keys from the input appear in the JSON output
    assert "user" in parsed
    assert parsed["user"]["email"] == "a@b.com"
    assert parsed["user"]["username"] == "alpha"
