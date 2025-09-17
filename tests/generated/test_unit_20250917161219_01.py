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
import random
import string

import pytest

try:
    from django.utils.text import slugify
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.articles.models import Article
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
except ImportError as exc:
    pytest.skip("Django or project imports unavailable: %s" % exc, allow_module_level=True)

def test_generate_random_string_default_length_and_charset():
    
    # Arrange
    random.seed(0)
    sig = inspect.signature(generate_random_string)
    params = sig.parameters
    if "length" in params:
        default_length = params["length"].default
        # if no explicit default, fall back to 8 (safety)
        if default_length is inspect._empty:
            default_length = 8
    else:
        default_length = 8

    # Act
    result = generate_random_string()

    # Assert
    assert isinstance(result, str)
    assert len(result) == default_length
    allowed = set(string.ascii_letters + string.digits)
    assert set(result).issubset(allowed)

def test_article___str__returns_title():
    
    # Arrange
    a = Article(title="My Test Article")

    # Act
    s = str(a)

    # Assert
    assert isinstance(s, str)
    assert s == "My Test Article"

def test_add_slug_to_article_if_not_exists_sets_and_preserves_slug():
    
    # Arrange
    class Dummy:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug

    # Case 1: missing slug -> should be set
    inst_missing = Dummy(title="A Complex Title! With Punctuation", slug=None)

    # Act
    # signal handlers often accept (sender, instance, **kwargs)
    add_slug_to_article_if_not_exists(sender=None, instance=inst_missing, created=True)

    # Assert
    assert isinstance(inst_missing.slug, str)
    assert inst_missing.slug != ""
    expected_prefix = slugify(inst_missing.title)[:50]
    assert inst_missing.slug.startswith(expected_prefix)

    
    inst_existing = Dummy(title="Other Title", slug="existing-slug-123")
    original = inst_existing.slug

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=inst_existing, created=True)

    # Assert
    assert inst_existing.slug == original
