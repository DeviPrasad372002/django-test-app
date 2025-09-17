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
from types import SimpleNamespace

try:
    import conduit.apps.articles.signals as article_signals
    import conduit.apps.core.utils as core_utils
    import conduit.apps.core.exceptions as core_exceptions
    from rest_framework import exceptions as drf_exceptions
    from rest_framework.response import Response
except ImportError as e:
    pytest.skip("Required project or third-party modules unavailable: " + str(e), allow_module_level=True)

def test_add_slug_to_article_if_not_exists_adds_slug(monkeypatch):
    
    # Arrange
    article = SimpleNamespace(title="Hello World", slug=None)
    # Make slug generation deterministic and independent of Django
    monkeypatch.setattr(core_utils, "generate_random_string", lambda n: "RND")
    # The signals module usually imports slugify; replace with a simple deterministic version
    monkeypatch.setattr(article_signals, "slugify", lambda s: s.lower().replace(" ", "-"))
    # Act
    # The real signal handler signature is (sender, instance, **kwargs)
    article_signals.add_slug_to_article_if_not_exists(sender=object, instance=article)
    # Assert
    assert isinstance(article.slug, str)
    assert article.slug == "hello-world-RND"

def test_add_slug_to_article_if_not_exists_keeps_existing_slug(monkeypatch):
    
    # Arrange
    article = SimpleNamespace(title="New Title", slug="already-set")
    # Ensure generate_random_string is present but should not be used
    monkeypatch.setattr(core_utils, "generate_random_string", lambda n: "SHOULDNOTUSE")
    monkeypatch.setattr(article_signals, "slugify", lambda s: s.lower().replace(" ", "-"))
    # Act
    article_signals.add_slug_to_article_if_not_exists(sender=object, instance=article)
    # Assert
    assert article.slug == "already-set"

def test_handle_not_found_error_and_core_exception_handler(monkeypatch):
    
    # Arrange
    exc = drf_exceptions.NotFound(detail="Resource missing")
    # Act
    resp = core_exceptions._handle_not_found_error(exc, context={})
    # Assert common Response contract
    assert isinstance(resp, Response)
    assert resp.status_code == 404
    assert isinstance(resp.data, dict)
    
    assert "errors" in resp.data
    assert resp.data["errors"].get("detail") == "Resource missing"
    # Also exercise the public handler to ensure it delegates appropriately
    top_resp = core_exceptions.core_exception_handler(exc, context={})
    assert isinstance(top_resp, Response)
    assert top_resp.status_code == 404
    assert top_resp.data["errors"].get("detail") == "Resource missing"
