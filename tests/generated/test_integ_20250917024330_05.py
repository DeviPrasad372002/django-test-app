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

try:
    import pytest
    import json
    from conduit.apps.articles import renderers as articles_renderers_module
    from conduit.apps.articles import serializers as articles_serializers_module
    from conduit.apps.articles import views as articles_views_module
except ImportError:
    import pytest  # re-import for skip
    pytest.skip("Django or target modules not available, skipping integration tests", allow_module_level=True)

class FakeSerializerSingle:
    def __init__(self, instance, many=False):
        # many ignored for single
        self.data = self._convert(instance)

    def _convert(self, item):
        if isinstance(item, dict):
            return item
        if hasattr(item, "__dict__"):
            return dict(item.__dict__)
        return {"value": item}

class FakeSerializerMany:
    def __init__(self, instance, many=False):
        # expect instance is iterable
        self.data = [self._convert(i) for i in instance]

    def _convert(self, item):
        if isinstance(item, dict):
            return item
        if hasattr(item, "__dict__"):
            return dict(item.__dict__)
        return {"value": item}

def make_fake_comments(n):
    return [{"id": i, "body": f"comment-{i}", "author": {"username": f"user{i}"}} for i in range(n)]

def make_fake_articles(n):
    return [{"slug": f"slug-{i}", "title": f"title-{i}", "body": f"body-{i}"} for i in range(n)]

def test_article_jsonrenderer_wraps_single_serializer_output(monkeypatch):
    
    # Arrange
    fake_article = {"slug": "my-article", "title": "A", "body": "B"}
    monkeypatch.setattr(articles_serializers_module, "ArticleSerializer", FakeSerializerSingle, raising=False)
    renderer = articles_renderers_module.ArticleJSONRenderer()

    # Act
    serializer = articles_serializers_module.ArticleSerializer(fake_article)
    data = serializer.data
    rendered = renderer.render(data)

    # Assert
    assert isinstance(rendered, (bytes, str))
    parsed = json.loads(rendered.decode() if isinstance(rendered, bytes) else rendered)
    # concrete keys and values
    assert "article" in parsed, "Renderer must wrap single article under 'article'"
    assert parsed["article"]["slug"] == "my-article"
    assert parsed["article"]["title"] == "A"
    assert parsed["article"]["body"] == "B"

def test_comment_jsonrenderer_and_comments_list_integration(monkeypatch):
    
    # Arrange
    comments = make_fake_comments(3)
    # patch view to return our fake queryset/list
    monkeypatch.setattr(articles_views_module.CommentsListCreateAPIView, "get_queryset", lambda self: comments, raising=False)
    # patch serializer used by view/consumers
    monkeypatch.setattr(articles_serializers_module, "CommentSerializer", FakeSerializerMany, raising=False)
    renderer = articles_renderers_module.CommentJSONRenderer()

    # Act
    view = articles_views_module.CommentsListCreateAPIView()
    qs = view.get_queryset()
    serializer = articles_serializers_module.CommentSerializer(qs, many=True)
    data = serializer.data
    rendered = renderer.render(data)

    # Assert
    assert isinstance(data, list)
    assert len(data) == 3
    parsed = json.loads(rendered.decode() if isinstance(rendered, bytes) else rendered)
    assert "comments" in parsed
    assert isinstance(parsed["comments"], list)
    assert parsed["comments"][0]["id"] == 0
    assert parsed["comments"][-1]["body"] == "comment-2"

def test_articles_feed_view_uses_article_serializer_and_renderer_for_list(monkeypatch):
    
    # Arrange
    articles = make_fake_articles(2)
    monkeypatch.setattr(articles_views_module.ArticlesFeedAPIView, "get_queryset", lambda self: articles, raising=False)
    monkeypatch.setattr(articles_serializers_module, "ArticleSerializer", FakeSerializerMany, raising=False)
    renderer = articles_renderers_module.ArticleJSONRenderer()

    # Act
    view = articles_views_module.ArticlesFeedAPIView()
    qs = view.get_queryset()
    serializer = articles_serializers_module.ArticleSerializer(qs, many=True)
    data = serializer.data
    rendered = renderer.render(data)

    # Assert
    assert isinstance(data, list)
    assert len(data) == 2
    parsed = json.loads(rendered.decode() if isinstance(rendered, bytes) else rendered)
    # Expect renderer to expose list under 'articles'
    assert "articles" in parsed, "Renderer must wrap article lists under 'articles'"
    assert parsed["articles"][0]["slug"] == "slug-0"
    assert parsed["articles"][1]["title"] == "title-1"
