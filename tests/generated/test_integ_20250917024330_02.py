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

import importlib
import random
from unittest import mock

import pytest

try:
    from conduit.apps.core import utils as core_utils
    from conduit.apps.articles import signals as articles_signals
    from conduit.apps.authentication import signals as auth_signals
    from conduit.apps.core import exceptions as core_exceptions
    from rest_framework import exceptions as drf_exceptions
    from rest_framework.response import Response
except ImportError:
    pytest.skip("Project modules (conduit.* or rest_framework) are not available", allow_module_level=True)

def test_generate_random_string_deterministic_and_length():
    
    # Arrange
    length = 8
    random.seed(12345)

    # Act
    value1 = core_utils.generate_random_string(length)
    # Re-seed to confirm determinism
    random.seed(12345)
    value2 = core_utils.generate_random_string(length)

    # Assert
    assert isinstance(value1, str)
    assert isinstance(value2, str)
    assert value1 == value2
    assert len(value1) == length
    # characters should be alphanumeric
    assert all(ch.isalnum() for ch in value1)

@pytest.mark.parametrize(
    "initial_slug,expected_changed",
    [
        (None, True),
        ("", True),
        ("existing-slug", False),
    ],
)
def test_add_slug_to_article_if_not_exists_sets_slug_when_missing(monkeypatch, initial_slug, expected_changed):
    
    # Arrange
    # Ensure deterministic random part used in slug generation
    monkeypatch.setattr(articles_signals, "generate_random_string", lambda length=6: "RND")
    # Create a minimal dummy article-like object used by the signal
    class DummyArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug
            self.saved = False

        def save(self):
            self.saved = True

    article = DummyArticle(title="Hello World", slug=initial_slug)

    # Act
    articles_signals.add_slug_to_article_if_not_exists(sender=object, instance=article, created=True)

    # Assert
    if expected_changed:
        assert article.slug is not None and article.slug != ""
        # Expect slugified title plus random part; slugify("Hello World") -> "hello-world"
        assert article.slug == "hello-world-RND"
        assert article.saved is True
    else:
        
        assert article.slug == "existing-slug"
        assert article.saved is False

def test_create_related_profile_calls_profile_create_only_on_created(monkeypatch):
    
    # Arrange
    calls = []

    class MockObjects:
        def create(self, **kwargs):
            calls.append(kwargs)
            return "created-profile"

    class MockProfile:
        objects = MockObjects()

    # Patch the Profile reference inside the signals module
    monkeypatch.setattr(auth_signals, "Profile", MockProfile, raising=False)

    user = object()

    # Act: created=True should create profile
    auth_signals.create_related_profile(sender=object, instance=user, created=True)

    # Assert
    assert len(calls) == 1
    assert calls[0] == {"user": user}

    # Reset and test created=False does not create
    calls.clear()
    auth_signals.create_related_profile(sender=object, instance=user, created=False)
    assert calls == []

@pytest.mark.parametrize(
    "exc, expected_status",
    [
        (drf_exceptions.NotFound(detail="not found"), 404),
        (Exception("boom"), 500),
    ],
)
def test_core_exception_handler_returns_expected_response_for_common_exceptions(exc, expected_status):
    
    # Arrange
    context = {"view": None}

    # Act
    response = core_exceptions.core_exception_handler(exc, context)

    # Assert
    # Handler should return a DRF Response instance for these cases
    assert isinstance(response, Response)
    assert isinstance(response.status_code, int)
    assert response.status_code == expected_status
    # response.data should be a mapping/dict-like
    assert hasattr(response, "data")
    assert isinstance(response.data, dict)
