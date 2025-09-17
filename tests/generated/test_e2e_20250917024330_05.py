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

import inspect
import json
import random

import pytest

try:
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
except ImportError:
    pytest.skip("Required target modules not available", allow_module_level=True)

def _decode_rendered(value):
    # helper: renderer.render can return bytes or str
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        return value
    # Some renderers might return already-structured types (rare)
    return value

def test_generate_random_string_deterministic_and_length():
    
    # Arrange
    sig = inspect.signature(generate_random_string)
    accepts_length = len(sig.parameters) >= 1

    # Act
    random.seed(20250101)
    if accepts_length:
        s1 = generate_random_string(12)
    else:
        s1 = generate_random_string()

    
    random.seed(20250101)
    if accepts_length:
        s2 = generate_random_string(12)
    else:
        s2 = generate_random_string()

    # Assert
    assert isinstance(s1, str), "generate_random_string must return a str"
    assert s1 == s2, "generate_random_string must be deterministic given the same PRNG state"
    if accepts_length:
        assert len(s1) == 12, "generate_random_string(length) must honor the requested length"
    else:
        assert len(s1) > 0, "generate_random_string() must produce a non-empty string"

@pytest.mark.parametrize(
    "renderer_cls,wrapper_key,payload",
    [
        (ArticleJSONRenderer, "article", {"title": "Deterministic Article", "body": "content"}),
        (CommentJSONRenderer, "comment", {"body": "A comment body", "author": "alice"}),
    ],
)
def test_renderers_wrap_payload_under_expected_root(renderer_cls, wrapper_key, payload):
    
    # Arrange
    renderer = renderer_cls()

    # Act
    rendered = renderer.render(payload)
    text = _decode_rendered(rendered)

    # If renderer returned structured object, normalize to JSON string first
    if not isinstance(text, str):
        # fallback, ensure it's JSONizable
        text = json.dumps(text)

    parsed = json.loads(text)

    # Assert
    assert isinstance(parsed, dict), "Rendered output should be a JSON object/dict"
    assert wrapper_key in parsed, f"Rendered JSON must contain top-level key '{wrapper_key}'"
    assert parsed[wrapper_key] == payload, "Renderer must preserve the payload under the wrapper key"
