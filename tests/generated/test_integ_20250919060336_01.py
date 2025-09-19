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

import random
import string

try:
    import pytest
    from conduit.apps.core import utils as core_utils
    from conduit.apps.articles import signals as article_signals
    from django.utils.text import slugify
except Exception as e:
    import pytest
    pytest.skip(f"Skipping integration tests because imports failed: {e}", allow_module_level=True)

@pytest.mark.parametrize("length", [1, 2, 8, 16])
def test_generate_random_string_length_and_charset(length):
    # Arrange
    random.seed(42)
    allowed = string.ascii_letters + string.digits

    # Act
    result = core_utils.generate_random_string(length)

    # Assert
    assert isinstance(result, str)
    assert len(result) == length
    assert all(ch in allowed for ch in result)

def test_generate_random_string_is_deterministic_with_seed():
    # Arrange
    random.seed(123)

    # Act
    first = core_utils.generate_random_string(12)
    # reseed to ensure deterministic repeat
    random.seed(123)
    second = core_utils.generate_random_string(12)

    # Assert
    assert isinstance(first, str)
    assert first == second

def test_add_slug_to_article_if_not_exists_creates_slug_from_title():
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    article = DummyArticle(title="Hello World! Test", slug=None)

    # Act
    article_signals.add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    assert isinstance(article.slug, str)
    # slug should include a slugified form of the title (lowercase words joined by hyphens)
    expected_fragment = slugify(article.title).split('-')[0]
    assert expected_fragment in article.slug and len(article.slug) > 0

def test_add_slug_to_article_if_not_exists_does_not_override_existing_slug():
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    existing = "existing-slug-123"
    article = DummyArticle(title="Irrelevant Title", slug=existing)

    # Act
    article_signals.add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    assert article.slug == existing

def test_add_slug_to_article_if_not_exists_handles_empty_title():
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    article = DummyArticle(title="", slug=None)

    # Act
    article_signals.add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    assert isinstance(article.slug, str)
    assert article.slug != ""
