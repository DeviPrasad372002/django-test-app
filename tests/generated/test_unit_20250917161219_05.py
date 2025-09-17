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
import types
from types import SimpleNamespace

import pytest

try:
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.relations import TagRelatedField
    from conduit.apps.articles import relations as relations_mod
    from conduit.apps.articles.serializers import ArticleSerializer
except Exception as exc:  
    pytest.skip(f"Skipping tests because project imports failed: {exc}", allow_module_level=True)

def test_ArticleJSONRenderer_render_single_and_list():
    
    # Arrange
    renderer = ArticleJSONRenderer()
    single_article = {"title": "Test Article", "slug": "test-article"}
    articles_list = [
        {"title": "One", "slug": "one"},
        {"title": "Two", "slug": "two"},
    ]

    # Act
    rendered_single = renderer.render(single_article, accepted_media_type="application/json", renderer_context={})
    rendered_list = renderer.render(articles_list, accepted_media_type="application/json", renderer_context={})

    # Assert
    assert isinstance(rendered_single, (bytes, bytearray))
    assert isinstance(rendered_list, (bytes, bytearray))

    decoded_single = json.loads(rendered_single.decode("utf-8"))
    decoded_list = json.loads(rendered_list.decode("utf-8"))

    assert "article" in decoded_single and isinstance(decoded_single["article"], dict)
    assert decoded_single["article"]["title"] == "Test Article"

    assert "articles" in decoded_list and isinstance(decoded_list["articles"], list)
    assert len(decoded_list["articles"]) == 2
    assert decoded_list["articles"][0]["slug"] == "one"

def test_CommentJSONRenderer_render_single_and_list():
    
    # Arrange
    renderer = CommentJSONRenderer()
    single_comment = {"body": "Nice post!", "id": 1}
    comments_list = [{"body": "A"}, {"body": "B"}]

    # Act
    rendered_single = renderer.render(single_comment, accepted_media_type="application/json", renderer_context={})
    rendered_list = renderer.render(comments_list, accepted_media_type="application/json", renderer_context={})

    # Assert
    assert isinstance(rendered_single, (bytes, bytearray))
    assert isinstance(rendered_list, (bytes, bytearray))

    decoded_single = json.loads(rendered_single.decode("utf-8"))
    decoded_list = json.loads(rendered_list.decode("utf-8"))

    assert "comment" in decoded_single and decoded_single["comment"]["body"] == "Nice post!"
    assert "comments" in decoded_list and isinstance(decoded_list["comments"], list)
    assert decoded_list["comments"][1]["body"] == "B"

def test_TagRelatedField_to_representation_and_to_internal_value(monkeypatch):
    
    # Arrange
    field = TagRelatedField()

    # to_representation should return the .name of the tag-like object
    mock_tag_obj = SimpleNamespace(name="python")

    # Act / Assert representation
    rep = field.to_representation(mock_tag_obj)
    assert rep == "python"

    # For to_internal_value we must fake the Tag model used inside the relations module.
    # Create a fake Tag class with an objects.get_or_create method.
    def fake_get_or_create(name=None, defaults=None, **kwargs):
        return (SimpleNamespace(name=name), True)

    fake_Tag = SimpleNamespace(objects=SimpleNamespace(get_or_create=fake_get_or_create))
    monkeypatch.setattr(relations_mod, "Tag", fake_Tag, raising=False)

    # Act
    internal = field.to_internal_value("django")

    # Assert
    assert hasattr(internal, "name") and internal.name == "django"

def test_ArticleSerializer_get_favorites_count_and_get_favorited():
    
    # Arrange
    serializer = ArticleSerializer(context={"request": SimpleNamespace(user=SimpleNamespace(is_authenticated=True, username="alice"))})

    # Article-like object with favorites manager and has_favorited method
    class FakeFavorites:
        def count(self):
            return 7

    def has_favorited(user):
        return getattr(user, "username", None) == "alice"

    article = SimpleNamespace(favorites=FakeFavorites(), has_favorited=has_favorited)

    # Act
    fav_count = serializer.get_favorites_count(article)
    favorited = serializer.get_favorited(article)

    # Assert
    assert isinstance(fav_count, int) and fav_count == 7
    assert favorited is True
