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

import pytest

try:
    import json
    import jwt
    from types import SimpleNamespace

    from target.conduit.apps.authentication import models as auth_models
    from target.conduit.apps.authentication import backends as auth_backends
    from target.conduit.apps.authentication import renderers as auth_renderers
    from rest_framework import exceptions as drf_exceptions
except Exception as exc:  
    import pytest as pytest

def _ensure_callable_attr(obj, name):
    if not hasattr(obj, name):
        pytest.skip(f"Skipping because required attribute {name!r} is missing on {obj!r}")

def _decode_payload_without_verification(token):
    # PyJWT accepts either str or bytes; ensure a string
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return jwt.decode(token, options={"verify_signature": False})

def test_user__generate_jwt_token_encodes_id_and_expiry():
    # Arrange
    _ensure_callable_attr(auth_models.User, "_generate_jwt_token")
    dummy_user = SimpleNamespace(id=999, pk=999)

    # Act
    token = auth_models.User._generate_jwt_token(dummy_user)

    # Assert
    assert isinstance(token, (str, bytes)), "Token must be a string or bytes"
    payload = _decode_payload_without_verification(token)
    assert isinstance(payload, dict), "Decoded payload must be a dict"
    # The token implementation is expected to include the user's id and an exp timestamp
    assert "id" in payload, "Payload must contain 'id'"
    assert payload["id"] == 999
    assert "exp" in payload, "Payload must contain 'exp'"
    assert isinstance(payload["exp"], (int, float)), "'exp' must be a numeric timestamp"
    # exp should be in the future relative to now
    import time
    now = int(time.time())
    assert int(payload["exp"]) > now, "Token expiration must be in the future"

def test_jwtauth__authenticate_credentials_raises_on_invalid_token():
    # Arrange
    _ensure_callable_attr(auth_backends.JWTAuthentication, "_authenticate_credentials")
    jwtauth = auth_backends.JWTAuthentication()

    
    with pytest.raises(drf_exceptions.AuthenticationFailed):
        jwtauth._authenticate_credentials("this-is-not-a-valid-jwt-token")

@pytest.mark.parametrize(
    "input_payload, expected_present_keys, expected_absent_keys",
    [
        ({"user": {"email": "a@b.com", "password": "secret", "token": "xyz"}}, {"email", "token"}, {"password"}),
        ({"user": {"email": "a@b.com", "token": "xyz"}}, {"email", "token"}, set()),
    ],
)
def test_userjsonrenderer_render_strips_password_and_formats(input_payload, expected_present_keys, expected_absent_keys):
    # Arrange
    _ensure_callable_attr(auth_renderers.UserJSONRenderer, "render")
    renderer = auth_renderers.UserJSONRenderer()

    # Act
    rendered = renderer.render(input_payload)

    # Assert
    # The render result is expected to be bytes (JSON). Parse and assert structure.
    assert isinstance(rendered, (bytes, str)), "Renderer output must be bytes or str"
    if isinstance(rendered, bytes):
        parsed = json.loads(rendered.decode("utf-8"))
    else:
        parsed = json.loads(rendered)
    assert "user" in parsed and isinstance(parsed["user"], dict), "Rendered JSON must have a 'user' object"
    for k in expected_present_keys:
        assert k in parsed["user"], f"Expected key {k!r} present in rendered user"
    for k in expected_absent_keys:
        assert k not in parsed["user"], f"Did not expect key {k!r} in rendered user"
