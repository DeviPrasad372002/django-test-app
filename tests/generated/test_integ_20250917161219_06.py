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
import random
import string
import pytest

try:
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.articles.renderers import ArticleJSONRenderer
except Exception as e:  # pragma: no cover - skip when environment not prepared
    pytest.skip(f"Skipping integration tests: required modules unavailable: {e}", allow_module_level=True)

def test_generate_random_string_length_and_charset():
    
    # Arrange
    random.seed(12345)  # make generation deterministic for the test
    length = 16

    # Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, str)
    assert len(result) == length
    allowed = set(string.ascii_letters + string.digits)
    assert set(result).issubset(allowed)

def test_userjson_and_articlejson_render_roundtrip():
    
    # Arrange
    renderer_user = UserJSONRenderer()
    renderer_article = ArticleJSONRenderer()
    user_payload = {"username": "alice", "email": "alice@example.org", "token": "tok-123"}
    article_payload = {"title": "Test", "body": "content", "author": {"username": "alice"}}

    # Act
    rendered_user_bytes = renderer_user.render({"user": user_payload})
    rendered_article_bytes = renderer_article.render({"article": article_payload})

    # Assert
    assert isinstance(rendered_user_bytes, (bytes, bytearray))
    assert isinstance(rendered_article_bytes, (bytes, bytearray))

    parsed_user = json.loads(rendered_user_bytes.decode("utf-8"))
    parsed_article = json.loads(rendered_article_bytes.decode("utf-8"))

    assert parsed_user == {"user": user_payload}
    assert parsed_article == {"article": article_payload}

@pytest.mark.parametrize("input_value", [
    None,
    "a simple string",
    ["list", "of", "values"],
    {"some": "dict"},
])
def test_renderers_handle_various_input_types(input_value):
    
    # Arrange
    ur = UserJSONRenderer()
    ar = ArticleJSONRenderer()

    # Act
    out_user = ur.render(input_value)
    out_article = ar.render(input_value)

    # Assert
    # both renderers should produce valid JSON bytes that decode and parse back to original value
    assert isinstance(out_user, (bytes, bytearray))
    assert isinstance(out_article, (bytes, bytearray))

    parsed_user = json.loads(out_user.decode("utf-8"))
    parsed_article = json.loads(out_article.decode("utf-8"))

    assert parsed_user == input_value
    assert parsed_article == input_value
