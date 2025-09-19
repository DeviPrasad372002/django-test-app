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
import datetime
import builtins

try:
    import pytest
    from unittest import mock
    from rest_framework.renderers import JSONRenderer
    from rest_framework.test import APIRequestFactory
    from rest_framework.request import Request as DRFRequest
    from rest_framework.response import Response
    from conduit.apps.articles import renderers as article_renderers
    from conduit.apps.articles import serializers as article_serializers
    from conduit.apps.articles import views as article_views
except ImportError as e:
    import pytest as pytest  # rebind for skip call

def _make_fake_article_obj(created_at=None, updated_at=None, favorited_count=0):
    class FakeFavCollection:
        def __init__(self, count):
            self._count = count

        def count(self):
            return self._count

    class FakeArticle:
        def __init__(self, created_at, updated_at, fav_count):
            self.created_at = created_at
            self.updated_at = updated_at
            self.favorited_by = FakeFavCollection(fav_count)

    return FakeArticle(created_at or datetime.datetime(2020, 1, 1, 12, 0, 0),
                       updated_at or datetime.datetime(2020, 1, 2, 12, 0, 0),
                       favorited_count)

def _make_fake_user_with_profile(profile_obj=None, user_id=1):
    class FakeUser:
        def __init__(self, profile, uid):
            self.profile = profile
            self.id = uid

    return FakeUser(profile_obj, user_id)

def _make_fake_profile():
    class FakeProfile:
        def __init__(self):
            self._fav_called_with = None
            self._follow_called_with = None

        def favorite(self, article):
            self._fav_called_with = article
            return None

        def unfavorite(self, article):
            self._fav_called_with = article
            return None

        def follow(self, other):
            self._follow_called_with = other
            return None

    return FakeProfile()

# Arrange/Act/Assert structured tests

@pytest.mark.parametrize("input_data,expected_key,expect_nested", [
    ({"title": "A"}, "article", False),
    ({"article": {"title": "A"}}, "article", True),
    ({"articles": [{"title": "A"}]}, "articles", True),
])
def test_articlejsonrenderer_render_variants(input_data, expected_key, expect_nested):
    # Arrange
    renderer = article_renderers.ArticleJSONRenderer()
    # Act
    rendered = renderer.render(input_data)
    assert isinstance(rendered, (bytes, str))
    if isinstance(rendered, str):
        rendered_bytes = rendered.encode("utf-8")
    else:
        rendered_bytes = rendered
    # Assert - top-level JSON must include the expected root key
    assert (('"{}"'.format(expected_key)).encode("utf-8")) in rendered_bytes
    # Ensure we did not double-wrap when already wrapped: if expect_nested True, original structure preserved
    if expect_nested:
        # For simple article case ensure original title exists exactly once
        assert b'"title"' in rendered_bytes

@pytest.mark.parametrize("input_data,expected_key", [
    ({"body": "hello"}, "comment"),
    ({"comment": {"body": "hello"}}, "comment"),
])
def test_commentjsonrenderer_render_variants(input_data, expected_key):
    # Arrange
    renderer = article_renderers.CommentJSONRenderer()
    # Act
    rendered = renderer.render(input_data)
    assert isinstance(rendered, (bytes, str))
    if isinstance(rendered, str):
        rendered_bytes = rendered.encode("utf-8")
    else:
        rendered_bytes = rendered
    # Assert
    assert (('"{}"'.format(expected_key)).encode("utf-8")) in rendered_bytes
    # ensure comment body is present
    assert b'"body"' in rendered_bytes

def test_article_serializer_get_created_updated_and_favorites_count():
    # Arrange
    fake_article = _make_fake_article_obj(
        created_at=datetime.datetime(2021, 5, 4, 10, 30, 0),
        updated_at=datetime.datetime(2021, 6, 4, 11, 30, 0),
        favorited_count=7
    )
    serializer = article_serializers.ArticleSerializer()
    # Act
    created_val = serializer.get_created_at(fake_article)
    updated_val = serializer.get_updated_at(fake_article)
    favorites_count = serializer.get_favorites_count(fake_article)
    # Assert types and concrete formatting
    assert isinstance(created_val, str)
    assert created_val.startswith("2021-05-04T10:30")
    assert isinstance(updated_val, str)
    assert updated_val.startswith("2021-06-04T11:30")
    assert isinstance(favorites_count, int)
    assert favorites_count == 7

def test_article_serializer_get_favorited_respects_request_user(monkeypatch):
    # Arrange
    fake_article = _make_fake_article_obj(favorited_count=0)
    
    class FakeProfile:
        def __init__(self, favors):
            self._favors = favors
        def has_favorited(self, article):
            return self._favors

    class FakeUser:
        def __init__(self, profile):
            self.profile = profile

    fake_profile = FakeProfile(favors=True)
    fake_user = FakeUser(profile=fake_profile)
    # Build a DRF Request-like context to pass into serializer
    dummy_request = types.SimpleNamespace(user=fake_user)
    serializer = article_serializers.ArticleSerializer(context={"request": dummy_request})
    # Act
    favorited_flag = serializer.get_favorited(fake_article)
    # Assert
    assert isinstance(favorited_flag, bool)
    assert favorited_flag is True

def test_articles_favorite_view_post_calls_profile_favorite_and_returns_article_structure(monkeypatch):
    # Arrange
    factory = APIRequestFactory()
    django_req = factory.post("/api/articles/test-slug/favorite/")
    drf_req = DRFRequest(django_req)
    fake_profile = _make_fake_profile()
    fake_user = _make_fake_user_with_profile(fake_profile, user_id=42)
    drf_req.user = fake_user

    # Fake article object returned by get_object_or_404
    fake_article = types.SimpleNamespace(slug="test-slug", title="T")

    # Monkeypatch get_object_or_404 used inside the view
    monkeypatch.setattr(article_views, "get_object_or_404", lambda *args, **kwargs: fake_article)

    # Provide a fake serializer class in the view module to control output
    class FakeArticleSerializer:
        def __init__(self, instance, context=None):
            self.instance = instance
            self.context = context
            self.data = {"slug": instance.slug, "favorited": True, "favoritesCount": 1}

    monkeypatch.setattr(article_views, "ArticleSerializer", FakeArticleSerializer)

    view = article_views.ArticlesFavoriteAPIView()
    # Act
    response = view.post(drf_req, slug="test-slug")
    
    assert isinstance(response, Response)
    assert response.status_code == 200
    # Expecting top-level 'article' key per API convention
    assert isinstance(response.data, dict)
    assert "article" in response.data
    assert response.data["article"]["slug"] == "test-slug"
    assert response.data["article"]["favorited"] is True
    assert response.data["article"]["favoritesCount"] == 1
    # Ensure profile.favorite was called with the returned article
    assert fake_profile._fav_called_with is fake_article

def test_comments_destroy_view_delete_authorized_deletes(monkeypatch):
    # Arrange
    factory = APIRequestFactory()
    django_req = factory.delete("/api/articles/test-slug/comments/1/")
    drf_req = DRFRequest(django_req)
    # Fake comment object that remembers deletion
    class FakeComment:
        def __init__(self, author_id):
            self.author = types.SimpleNamespace(id=author_id)
            self._deleted = False
        def delete(self):
            self._deleted = True

    fake_comment = FakeComment(author_id=7)
    # Monkeypatch get_object_or_404 to return our fake comment
    monkeypatch.setattr(article_views, "get_object_or_404", lambda *args, **kwargs: fake_comment)

    # Create a request user that matches the author id to permit deletion
    drf_req.user = types.SimpleNamespace(id=7)

    view = article_views.CommentsDestroyAPIView()
    # Act
    response = view.delete(drf_req, article_slug="test-slug", pk=1)
    # Assert that delete was invoked and response is 204 No Content
    assert fake_comment._deleted is True
    assert isinstance(response, Response)
    assert response.status_code == 204

def test_articles_feed_view_returns_serialized_list(monkeypatch):
    # Arrange
    factory = APIRequestFactory()
    django_req = factory.get("/api/articles/feed/")
    drf_req = DRFRequest(django_req)
    drf_req.user = types.SimpleNamespace(id=100)

    # Fake queryset and serializer
    fake_articles = [types.SimpleNamespace(slug="a1"), types.SimpleNamespace(slug="a2")]

    # Monkeypatch the view's get_queryset to return our fake list
    monkeypatch.setattr(article_views.ArticlesFeedAPIView, "get_queryset", lambda self: fake_articles)

    # Patch serializer class used by the view to control output
    class FakeArticleSerializer:
        def __init__(self, instance, many=False, context=None):
            # instance may be a list when many=True
            if many:
                self.data = [{"slug": getattr(i, "slug", None)} for i in instance]
            else:
                self.data = {"slug": getattr(instance, "slug", None)}

    monkeypatch.setattr(article_views, "ArticleSerializer", FakeArticleSerializer)

    view = article_views.ArticlesFeedAPIView()
    # Act
    response = view.get(drf_req)
    # Assert
    assert isinstance(response, Response)
    assert response.status_code == 200
    assert "articles" in response.data
    assert isinstance(response.data["articles"], list)
    assert response.data["articles"][0]["slug"] == "a1"
    assert response.data["articles"][1]["slug"] == "a2"
