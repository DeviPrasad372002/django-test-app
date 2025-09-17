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

try:
    import pytest
    import json
    from django.utils.text import slugify
    from rest_framework.exceptions import NotFound
    from rest_framework.response import Response

    from conduit.apps.articles.renderers import ArticleJSONRenderer
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.core.exceptions import _handle_not_found_error
except ImportError:
    import pytest
    pytest.skip("Skipping tests because required project modules are not importable", allow_module_level=True)

def test_ArticleJSONRenderer_render_wraps_article():
    
    # Arrange
    renderer = ArticleJSONRenderer()
    article_payload = {"title": "Hello", "body": "world"}
    # Act
    output = renderer.render(article_payload, media_type="application/json")
    # Assert
    assert isinstance(output, (bytes, str))
    decoded = output.decode("utf-8") if isinstance(output, bytes) else output
    parsed = json.loads(decoded)
    assert isinstance(parsed, dict)
    assert "article" in parsed
    assert parsed["article"] == article_payload

def test_UserJSONRenderer_render_wraps_user():
    
    # Arrange
    renderer = UserJSONRenderer()
    user_payload = {"username": "alice", "email": "a@example.com"}
    # Act
    output = renderer.render(user_payload, media_type="application/json")
    # Assert
    assert isinstance(output, (bytes, str))
    decoded = output.decode("utf-8") if isinstance(output, bytes) else output
    parsed = json.loads(decoded)
    assert isinstance(parsed, dict)
    assert "user" in parsed
    assert parsed["user"] == user_payload

def test_add_slug_to_article_if_not_exists_sets_slug_when_missing(monkeypatch):
    
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    dummy = DummyArticle("My Test Title", slug=None)

    # Force deterministic random string used by the signal
    monkeypatch.setattr(
        "conduit.apps.articles.signals.generate_random_string",
        lambda length=6: "abc123",
    )

    expected_prefix = slugify(dummy.title)

    # Act
    # The typical signal signature is (sender, instance, **kwargs)
    add_slug_to_article_if_not_exists(None, dummy)

    # Assert
    assert isinstance(dummy.slug, str)
    assert dummy.slug.startswith(expected_prefix + "-")
    assert dummy.slug == f"{expected_prefix}-abc123"

def test__handle_not_found_error_returns_404_response():
    
    # Arrange
    exc = NotFound(detail="Not here")
    # Act
    resp = _handle_not_found_error(exc)
    # Assert
    assert isinstance(resp, Response)
    assert resp.status_code == 404
    assert isinstance(resp.data, dict)
    # Expect an 'errors' key mapping in the project's handler
    assert "errors" in resp.data
    
    data_str = json.dumps(resp.data)
    assert "Not here" in data_str
