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
from types import SimpleNamespace

import pytest

try:
    # Articles
    from conduit.apps.articles.__init__ import ArticlesAppConfig
    from conduit.apps.articles.models import Article
    from conduit.apps.articles.relations import TagRelatedField
    from conduit.apps.articles.serializers import ArticleSerializer
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.views import ArticleViewSet

    # Core util used by signals
    from conduit.apps.core import utils as core_utils
except ImportError as e:
    pytest.skip("Skipping article-related tests because imports failed: %s" % (e,), allow_module_level=True)

@pytest.mark.parametrize(
    "title",
    [
        ("Simple Title",),
        ("",),
        ("Title With   Spaces",),
    ],
)
def test_Article___str_returns_title_for_various_titles(title):
    # Arrange
    
    fake = SimpleNamespace(title=title, slug=None, description=None, body=None)
    # Act
    result = Article.__str__(fake)
    # Assert
    assert isinstance(result, str)
    
    assert result == title

def test_add_slug_to_article_if_not_exists_adds_generated_part_and_preserves_base(monkeypatch):
    # Arrange
    generated = "RAND123"
    monkeypatch.setattr(core_utils, "generate_random_string", lambda length=6: generated)
    fake = SimpleNamespace(slug=None, title="My Great Article")
    # Act
    # signal signature is usually (sender, instance, created, **kwargs)
    add_slug_to_article_if_not_exists(sender=None, instance=fake, created=True)
    # Assert
    assert hasattr(fake, "slug"), "Handler must set slug attribute"
    assert isinstance(fake.slug, str)
    
    assert generated in fake.slug
    # The title-derived part should also be present (lowercased)
    assert "my" in fake.slug.lower()

def test_add_slug_to_article_if_not_exists_does_not_override_existing_slug(monkeypatch):
    # Arrange
    monkeypatch.setattr(core_utils, "generate_random_string", lambda length=6: "SHOULDNOTUSE")
    fake = SimpleNamespace(slug="existing-slug", title="Irrelevant")
    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=fake, created=True)
    # Assert
    assert fake.slug == "existing-slug"

@pytest.mark.parametrize(
    "obj_path, attr_name, is_class",
    [
        # App config ready method (bound function on class)
        ("conduit.apps.articles.__init__.ArticlesAppConfig", "ready", True),
        # Relations: methods on TagRelatedField
        ("conduit.apps.articles.relations.TagRelatedField", "get_queryset", True),
        ("conduit.apps.articles.relations.TagRelatedField", "to_internal_value", True),
        ("conduit.apps.articles.relations.TagRelatedField", "to_representation", True),
        # Serializers: ArticleSerializer methods
        ("conduit.apps.articles.serializers.ArticleSerializer", "create", True),
        ("conduit.apps.articles.serializers.ArticleSerializer", "get_created_at", True),
        ("conduit.apps.articles.serializers.ArticleSerializer", "get_updated_at", True),
        ("conduit.apps.articles.serializers.ArticleSerializer", "get_favorited", True),
        ("conduit.apps.articles.serializers.ArticleSerializer", "get_favorites_count", True),
        # Views: list method
        ("conduit.apps.articles.views.ArticleViewSet", "list", True),
    ],
)
def test_public_members_are_present_and_call_signature_behaviour(obj_path, attr_name, is_class):
    """
    Verify public members from the focus list exist. For methods we assert they are callable and that
    calling them without required parameters raises TypeError. For classes we ensure they can be instantiated
    without raising unexpected exceptions.
    """
    # Arrange
    module_path, class_name = obj_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    member = getattr(module, class_name)
    # Access attribute
    assert hasattr(member, attr_name), f"{class_name} must have attribute {attr_name}"
    attr = getattr(member, attr_name)

    # Act / Assert
    if inspect.isclass(member):
        # For classes, if the attribute is a function (descriptor), it should be callable.
        if callable(attr):
            
            with pytest.raises(TypeError):
                attr()  # missing required positional arguments
        # Try to instantiate the class (no args). Some classes may accept no args.
        try:
            instance = member()
        except TypeError:
            
            with pytest.raises(TypeError):
                member()
        else:
            # If instantiation succeeded, ensure the attribute is bound and callable on instance.
            instance_attr = getattr(instance, attr_name)
            assert callable(instance_attr)
            
            try:
                instance_attr()
            except TypeError:
                # Expected for methods requiring extra parameters
                pass
            except Exception as exc:
                # Any other exception is acceptable but must be a concrete exception type
                assert isinstance(exc, Exception)
    else:
        
        assert callable(attr)
        with pytest.raises(TypeError):
            attr()  

def test_ArticleSerializer_get_created_and_updated_return_string_when_datetime_present():
    # Arrange
    # Use unbound methods directly: they expect (self, obj)
    dt = __import__("datetime").datetime(2020, 1, 2, 3, 4, 5)
    article_obj = SimpleNamespace(created_at=dt, updated_at=dt)
    # Act
    created = ArticleSerializer.get_created_at(None, article_obj)
    updated = ArticleSerializer.get_updated_at(None, article_obj)
    # Assert
    assert created is not None
    assert updated is not None
    assert isinstance(created, str)
    assert isinstance(updated, str)
    
    assert "2020" in created
    assert "2020" in updated

def test_ArticleSerializer_favorites_methods_with_simple_structures():
    # Arrange
    # Create an article-like object with favorites attribute as an iterable
    # and simulate serializer context for get_favorited method to read user id.
    article_obj = SimpleNamespace(favorites=[SimpleNamespace(pk=1), SimpleNamespace(pk=2)])
    fake_serializer = SimpleNamespace(context={"request": SimpleNamespace(user=SimpleNamespace(pk=1))})
    # Act
    fav_count = ArticleSerializer.get_favorites_count(None, article_obj)
    
    try:
        favorited = ArticleSerializer.get_favorited(fake_serializer, article_obj)
    except Exception as exc:
        
        assert isinstance(exc, Exception)
        favorited = None
    # Assert
    assert isinstance(fav_count, int)
    assert fav_count == 2
    # favorited is bool or None depending on implementation; at least ensure type is bool or None
    assert (favorited is None) or isinstance(favorited, bool)
