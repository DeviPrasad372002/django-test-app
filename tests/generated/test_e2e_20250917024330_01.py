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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

import json

try:
    import pytest
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.articles.renderers import ArticleJSONRenderer
    from conduit.apps.core.exceptions import core_exception_handler
    from rest_framework.exceptions import NotFound
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

def test_UserJSONRenderer_render_wraps_user_key():
    
    # Arrange
    renderer = UserJSONRenderer()
    payload = {"email": "alice@example.com", "username": "alice", "token": "tok"}

    # Act
    rendered = renderer.render(payload)

    # Assert
    assert isinstance(rendered, (bytes, str)), "render should return bytes or str"
    decoded = rendered.decode("utf-8") if isinstance(rendered, bytes) else rendered
    parsed = json.loads(decoded)
    assert "user" in parsed, "Rendered output must contain top-level 'user' key"
    assert parsed["user"] == payload, "The 'user' value must match the input payload exactly"

@pytest.mark.parametrize(
    "input_data,expected_top_key",
    [
        ({"title": "Article One", "body": "content"}, "article"),
        ([{"title": "A1"}, {"title": "A2"}], "articles"),
    ],
)
def test_ArticleJSONRenderer_render_wraps_expected_key(input_data, expected_top_key):
    
    # Arrange
    renderer = ArticleJSONRenderer()

    # Act
    rendered = renderer.render(input_data)

    # Assert
    assert isinstance(rendered, (bytes, str)), "render should return bytes or str"
    decoded = rendered.decode("utf-8") if isinstance(rendered, bytes) else rendered
    parsed = json.loads(decoded)
    assert expected_top_key in parsed, f"Rendered output must contain top-level '{expected_top_key}' key"
    # Ensure payload preserved under that key (for lists/dicts)
    assert parsed[expected_top_key] == input_data, "Rendered top-level value must equal the input data"

def test_core_exception_handler_maps_not_found_and_generic_errors():
    
    # Arrange
    not_found_exc = NotFound(detail="no such resource")
    generic_exc = Exception("boom")

    # Act
    resp_not_found = core_exception_handler(not_found_exc, context={})
    resp_generic = core_exception_handler(generic_exc, context={})

    # Assert for NotFound
    assert resp_not_found is not None, "Handler must return a Response for NotFound"
    assert hasattr(resp_not_found, "status_code"), "Response must have status_code attribute"
    assert resp_not_found.status_code == 404, "NotFound must map to HTTP 404"
    assert isinstance(resp_not_found.data, dict), "Response data must be a dict for NotFound responses"

    # Assert for generic exception
    assert resp_generic is not None, "Handler must return a Response for generic exceptions"
    assert hasattr(resp_generic, "status_code"), "Response must have status_code attribute"
    # Expect an internal server error mapping
    assert resp_generic.status_code == 500, "Generic exceptions must map to HTTP 500"
    assert isinstance(resp_generic.data, dict), "Response data must be a dict for generic error responses"
