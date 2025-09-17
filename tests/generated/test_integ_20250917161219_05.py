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

import json
from types import SimpleNamespace

import pytest

try:
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.serializers import ArticleSerializer
    from conduit.apps.articles.relations import TagRelatedField
    import conduit.apps.profiles.models as profiles_models
    import conduit.apps.articles.relations as relations_module
    import conduit.apps.articles.serializers as articles_serializers
except ImportError as e:
    pytest.skip(f"Skipping integration tests; import failed: {e}", allow_module_level=True)

def _decode_render_output(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)

def test_article_json_renderer_wraps_single_and_list_articles():
    
    # Arrange
    renderer = ArticleJSONRenderer()
    single = {"title": "Integration Testing", "slug": "int-test"}
    many = [single, {"title": "Second", "slug": "second"}]

    # Act
    out_single = renderer.render(single)
    out_many = renderer.render(many)

    # Assert
    parsed_single = _decode_render_output(out_single)
    parsed_many = _decode_render_output(out_many)

    # When rendering a single article expect top-level key "article" mapping to the payload
    assert "article" in parsed_single
    assert parsed_single["article"]["title"] == "Integration Testing"
    assert parsed_single["article"]["slug"] == "int-test"

    # When rendering multiple articles expect top-level key "articles" mapping to a list
    assert "articles" in parsed_many
    assert isinstance(parsed_many["articles"], list)
    assert parsed_many["articles"][0]["title"] == "Integration Testing"
    assert parsed_many["articles"][1]["slug"] == "second"

def test_comment_json_renderer_wraps_comment():
    
    # Arrange
    renderer = CommentJSONRenderer()
    comment = {"id": 7, "body": "Nice work"}

    # Act
    out = renderer.render(comment)

    # Assert
    parsed = _decode_render_output(out)
    assert "comment" in parsed
    assert parsed["comment"]["id"] == 7
    assert parsed["comment"]["body"] == "Nice work"

def test_article_serializer_get_favorited_and_favorites_count(monkeypatch):
    
    # Arrange
    user = SimpleNamespace(pk=42)
    # Serializer expects context['request'].user
    serializer = ArticleSerializer()
    serializer.context = {"request": SimpleNamespace(user=user)}

    # Fake article exposing a favorites-like manager with count()
    class FakeFavorites:
        def __init__(self, n):
            self._n = n

        def count(self):
            return self._n

    article = SimpleNamespace(pk=11, favorites=FakeFavorites(5))

    # Monkeypatch the has_favorited helper in profiles to simulate a favorited article
    monkeypatch.setattr(profiles_models, "has_favorited", lambda u, a: u.pk == 42 and a.pk == 11)

    # Act
    is_favorited = serializer.get_favorited(article)
    favorites_count = serializer.get_favorites_count(article)

    # Assert
    assert is_favorited is True
    assert isinstance(favorites_count, int)
    assert favorites_count == 5

def test_tag_related_field_to_internal_value_and_to_representation(monkeypatch):
    
    # Arrange
    # Create a fake Tag model with objects.get_or_create
    class FakeTag:
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return f"<FakeTag {self.name!r}>"

    class FakeManager:
        @staticmethod
        def get_or_create(name):
            # mimic Django (instance, created)
            return FakeTag(name), True

    FakeTag.objects = FakeManager

    # Replace Tag in the relations module with our fake
    monkeypatch.setattr(relations_module, "Tag", FakeTag, raising=False)

    field = TagRelatedField()

    # Act
    internal = field.to_internal_value("python")
    representation = field.to_representation(internal)

    # Assert
    assert isinstance(internal, FakeTag)
    assert internal.name == "python"
    assert representation == "python"
