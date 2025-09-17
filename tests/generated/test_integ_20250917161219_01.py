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

import types
import pytest

try:
    from conduit.apps.articles import relations as articles_relations
    from conduit.apps.articles import serializers as articles_serializers
    from conduit.apps.articles import signals as articles_signals
    from conduit.apps.core import utils as core_utils
    from conduit.apps import profiles
    from unittest import mock
except ImportError as exc:  # pragma: no cover - guard missing project imports
    pytest.skip(f"Required project modules unavailable: {exc}", allow_module_level=True)

def test_TagRelatedField_to_internal_value_and_to_representation_roundtrip(monkeypatch):
    
    # Arrange
    field = articles_relations.TagRelatedField()
    created_flags = {}

    class FakeTag:
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return f"<FakeTag {self.name}>"

    class FakeManager:
        def get_or_create(self, name):
            # Simulate returning a tag instance and whether it was created
            created = name not in created_flags
            created_flags[name] = True
            return (FakeTag(name), created)

    # Monkeypatch the Tag model's objects manager used inside the field
    monkeypatch.setattr(articles_relations, "Tag", types.SimpleNamespace(objects=FakeManager()))

    # Act
    internal = field.to_internal_value("python")
    representation = field.to_representation(internal)

    # Assert
    assert isinstance(internal, FakeTag)
    assert internal.name == "python"
    assert representation == "python"

    
    second_internal, created = articles_relations.Tag.objects.get_or_create("python")
    assert isinstance(second_internal, FakeTag)
    assert created is False or created is False  # still deterministic: second call returns created False

def test_ArticleSerializer_get_favorited_delegates_to_profiles_has_favorited(monkeypatch):
    
    # Arrange
    called = {}

    class FakeUser:
        def __init__(self, username):
            self.username = username
            # serializer may expect a .profile attribute in some code paths
            self.profile = f"profile_of_{username}"

    fake_user = FakeUser("alice")

    # Minimal "request" object used via serializer.context['request']
    fake_request = types.SimpleNamespace(user=fake_user)

    # Create a fake article object (serializer.get_favorited likely receives the article instance)
    class FakeArticle:
        def __init__(self, slug):
            self.slug = slug

    article = FakeArticle("a-slug")

    # Spy replacement for profiles.models.has_favorited
    def fake_has_favorited(profile, art):
        # Record that it was called with expected values
        called['args'] = (profile, art)
        return True

    # Monkeypatch the has_favorited function used by serializer implementation
    monkeypatch.setattr(profiles.models, "has_favorited", fake_has_favorited)

    # Build a lightweight "self" for calling the serializer method without constructing the entire serializer
    serializer_self = types.SimpleNamespace(context={"request": fake_request})

    # Act
    result = articles_serializers.ArticleSerializer.get_favorited(serializer_self, article)

    # Assert
    assert result is True
    # Ensure underlying helper saw the profile and article we passed
    assert called['args'][0] == fake_user.profile
    assert called['args'][1] is article

def test_add_slug_to_article_if_not_exists_generates_and_saves(monkeypatch):
    
    # Arrange
    # Create a fake article lacking a slug and having a title that will be slugified
    class FakeArticle:
        def __init__(self, title, slug=""):
            self.title = title
            self.slug = slug
            self._saved = False

        def save(self):
            # mark as saved instead of touching a DB
            self._saved = True

    article = FakeArticle("Hello World")

    # Force generate_random_string to a deterministic value
    monkeypatch.setattr(core_utils, "generate_random_string", lambda length=6: "XYZ123")

    # We expect slugify-like behavior; many implementations use django.utils.text.slugify.
    # The signal likely composes slug from title and random string. We won't import slugify here;
    # assert membership of expected pieces instead.
    # Act
    # Call the signal handler as if an article was just created
    # Common signature: (sender, instance, created, **kwargs)
    articles_signals.add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    assert article._saved is True
    
    assert "XYZ123" in article.slug
    
    assert "hello" in article.slug.lower()
    assert "world" in article.slug.lower()
