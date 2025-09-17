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
import random

try:
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.core.utils import generate_random_string
except ImportError:
    pytest.skip("conduit app modules not available, skipping tests", allow_module_level=True)

class DummyArticle:
    def __init__(self, title, slug=None):
        self.title = title
        self.slug = slug

def test_add_slug_to_article_if_not_exists_creates_slug_from_title():
    
    # Arrange
    article = DummyArticle(title="Hello World!")
    assert article.slug is None

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    assert isinstance(article.slug, str)
    # basic slugification expectation: lowercase, hyphens, title words present
    assert "hello-world" in article.slug
    assert " " not in article.slug

def test_add_slug_to_article_if_not_exists_does_not_override_existing_slug():
    
    # Arrange
    article = DummyArticle(title="Ignored Title", slug="existing-slug-123")
    original = article.slug

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    assert article.slug == original

@pytest.mark.parametrize("length", [1, 5, 12])
def test_generate_random_string_length_and_charset(length):
    
    # Arrange
    random.seed(0)  # deterministic for the test run

    # Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, str)
    assert len(result) == length
    # allowed charset: alphanumeric (letters and digits)
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    assert set(result).issubset(allowed)
