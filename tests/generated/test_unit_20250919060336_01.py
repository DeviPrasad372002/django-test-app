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

import sys
import types
import datetime
import pytest

try:
    from conduit.apps.articles.__init__ import ArticlesAppConfig
    from conduit.apps.articles.relations import TagRelatedField
    from conduit.apps.articles.serializers import ArticleSerializer
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.views import ArticlesFeedAPIView
    from conduit.apps.articles.models import Article as ArticleModelForStr  # for __str__ test (used as unbound method)
    from rest_framework import serializers as drf_serializers
    from rest_framework.response import Response
except ImportError as e:
    pytest.skip("Project modules not available: %s" % e, allow_module_level=True)

def test_ready_imports_signals_by_module_name(monkeypatch):
    # Arrange
    fake_mod = types.SimpleNamespace(MARK="ok")
    module_name = "conduit.apps.articles.signals"
    monkeypatch.setitem(sys.modules, module_name, fake_mod)
    app = ArticlesAppConfig("articles", "conduit.apps.articles")

    # Act
    app.ready()

    # Assert
    assert sys.modules.get(module_name) is fake_mod
    assert getattr(sys.modules[module_name], "MARK") == "ok"

def test_article___str___returns_title_and_handles_missing_title():
    # Arrange
    class DummyWithTitle:
        title = "My Great Article"

    class DummyNoTitle:
        title = None

    # Act
    res_with = ArticleModelForStr.__str__(DummyWithTitle())
    res_no = ArticleModelForStr.__str__(DummyNoTitle())

    # Assert
    assert isinstance(res_with, str)
    assert res_with == "My Great Article"
    assert isinstance(res_no, str)

@pytest.mark.parametrize(
    "input_value,existing,expected_name,expected_created",
    [
        ("python", False, "python", True),
        ("django", True, "django", False),
    ],
)
def test_tagrelatedfield_to_internal_value_creates_or_gets(monkeypatch, input_value, existing, expected_name, expected_created):
    # Arrange
    relations_mod = __import__("conduit.apps.articles.relations", fromlist=["relations"])
    created_flag = {"value": None}

    class DummyTag:
        def __init__(self, name):
            self.name = name

    class DummyManager:
        def get_or_create(self, name):
            # simulate existing vs created
            created = not existing
            created_flag["value"] = created
            return (DummyTag(name), created)

    # Patch Tag used inside the relations module
    monkeypatch.setattr(relations_mod, "Tag", types.SimpleNamespace(objects=DummyManager()))

    field = TagRelatedField()

    # Act
    result = field.to_internal_value(input_value)

    # Assert
    assert hasattr(result, "name")
    assert result.name == expected_name
    assert created_flag["value"] == expected_created

@pytest.mark.parametrize("bad_input", [123, None, 3.14, {"a": "b"}])
def test_tagrelatedfield_to_internal_value_rejects_non_string(monkeypatch, bad_input):
    # Arrange
    field = TagRelatedField()
    # Act / Assert
    with pytest.raises(drf_serializers.ValidationError):
        field.to_internal_value(bad_input)

def test_tagrelatedfield_to_representation_returns_name():
    # Arrange
    relations_mod = __import__("conduit.apps.articles.relations", fromlist=["relations"])

    class DummyTag:
        def __init__(self, name):
            self.name = name

    field = TagRelatedField()

    # Act
    out = field.to_representation(DummyTag("pytest"))

    # Assert
    assert out == "pytest"
    assert isinstance(out, str)

def test_articleserializer_get_created_and_updated_isoformat():
    # Arrange
    now = datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
    obj = types.SimpleNamespace(created_at=now, updated_at=now)

    # Act
    created_iso = ArticleSerializer.get_created_at(None, obj)
    updated_iso = ArticleSerializer.get_updated_at(None, obj)

    # Assert
    assert created_iso == now.isoformat()
    assert updated_iso == now.isoformat()

def test_articleserializer_get_favorites_count_and_favorited(monkeypatch):
    # Arrange
    # Build an object with favorited_by that supports count() and filter(...).exists()
    class FavoritedQuery:
        def __init__(self, exists_return, count_return):
            self._exists = exists_return
            self._count = count_return

        def filter(self, **kwargs):
            return types.SimpleNamespace(exists=lambda: self._exists)

        def count(self):
            return self._count

    obj = types.SimpleNamespace(favorited_by=FavoritedQuery(True, 5))

    # Create fake request with user
    fake_user = types.SimpleNamespace(pk=42, is_anonymous=False)
    fake_request = types.SimpleNamespace(user=fake_user)

    self_like = types.SimpleNamespace(context={"request": fake_request})

    # Act
    favorited = ArticleSerializer.get_favorited(self_like, obj)
    favorites_count = ArticleSerializer.get_favorites_count(None, obj)

    # Assert
    assert isinstance(favorited, bool)
    assert favorited is True
    assert isinstance(favorites_count, int)
    assert favorites_count == 5

def test_articleserializer_get_favorited_returns_false_for_anonymous():
    # Arrange
    obj = types.SimpleNamespace(favorited_by=types.SimpleNamespace(filter=lambda **kw: types.SimpleNamespace(exists=lambda: True)))
    anon_user = types.SimpleNamespace(is_anonymous=True)
    request = types.SimpleNamespace(user=anon_user)
    self_like = types.SimpleNamespace(context={"request": request})

    # Act
    res = ArticleSerializer.get_favorited(self_like, obj)

    # Assert
    assert res is False

def test_articleserializer_create_calls_model_manager_and_returns_instance(monkeypatch):
    # Arrange
    serializers_mod = __import__("conduit.apps.articles.serializers", fromlist=["converters"])
    created_kwargs = {}

    class DummyArticle:
        def __init__(self, **kwargs):
            created_kwargs.update(kwargs)
            for k, v in kwargs.items():
                setattr(self, k, v)

    class DummyManager:
        def create(self, **kwargs):
            return DummyArticle(**kwargs)

    # Patch Article class in serializers module to use DummyManager
    monkeypatch.setattr(serializers_mod, "Article", types.SimpleNamespace(objects=DummyManager()))

    # Provide a self-like object with context including request.user
    fake_user = types.SimpleNamespace(pk=99)
    self_like = types.SimpleNamespace(context={"request": types.SimpleNamespace(user=fake_user)})

    validated_data = {"title": "T", "body": "B", "description": "D", "tagList": ["a", "b"]}

    # Act
    created = ArticleSerializer.create(self_like, validated_data.copy())

    # Assert
    assert hasattr(created, "title")
    assert created.title == "T"
    # The created kwargs should include author or similar field referencing the user pk or user object
    assert created_kwargs != {}
    # Ensure that the returned object has attributes set from validated_data
    assert getattr(created, "body") == "B"

@pytest.mark.parametrize(
    "initial_slug,expected_contains",
    [
        (None, "hello-world-XYZ"),
        ("custom-slug", "custom-slug"),
    ],
)
def test_add_slug_to_article_if_not_exists_sets_and_preserves(monkeypatch, initial_slug, expected_contains):
    # Arrange
    signals_mod = __import__("conduit.apps.articles.signals", fromlist=["signals"])
    # Patch slugify and generate_random_string to deterministic returns
    monkeypatch.setattr(signals_mod, "slugify", lambda v: "hello-world")
    monkeypatch.setattr(signals_mod, "generate_random_string", lambda length=6: "XYZ")

    instance = types.SimpleNamespace(title="Hello World!", slug=initial_slug)

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=instance, raw=False)

    # Assert
    assert isinstance(instance.slug, str)
    assert expected_contains in instance.slug

def test_articlesfeed_view_list_returns_serialized_data(monkeypatch):
    # Arrange
    view = ArticlesFeedAPIView()
    fake_request = types.SimpleNamespace(user=types.SimpleNamespace(pk=1))
    view.request = fake_request

    # Prepare queryset and expected serialized data
    articles_qs = [types.SimpleNamespace(id=1, title="A"), types.SimpleNamespace(id=2, title="B")]
    expected_serialized = [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]

    # Monkeypatch get_queryset and get_serializer
    monkeypatch.setattr(view, "get_queryset", lambda: articles_qs)
    monkeypatch.setattr(view, "get_serializer", lambda *args, **kwargs: types.SimpleNamespace(data=expected_serialized))

    # Act
    response = view.list(fake_request)

    # Assert
    assert isinstance(response, Response)
    assert response.data == expected_serialized

def test_articlesfeed_view_list_handles_empty_queryset(monkeypatch):
    # Arrange
    view = ArticlesFeedAPIView()
    fake_request = types.SimpleNamespace(user=types.SimpleNamespace(pk=1))
    view.request = fake_request

    monkeypatch.setattr(view, "get_queryset", lambda: [])
    monkeypatch.setattr(view, "get_serializer", lambda *args, **kwargs: types.SimpleNamespace(data=[]))

    # Act
    response = view.list(fake_request)

    # Assert
    assert isinstance(response, Response)
    assert response.data == []
