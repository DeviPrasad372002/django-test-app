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
from datetime import datetime, timezone

import pytest

try:
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.serializers import TagSerializer, CommentSerializer
except ImportError as e:
    pytest.skip(f"Skipping integration tests due to missing imports: {e}", allow_module_level=True)

class SimpleUser:
    def __init__(self, username, bio=None, image=None, following=False):
        self.username = username
        self.bio = bio
        self.image = image
        # some serializers use 'is_following' like attrs or callables; keep simple attr too
        self.following = following

class SimpleTag:
    def __init__(self, name):
        self.name = name

class SimpleComment:
    def __init__(self, id_, body, author, created_at=None, updated_at=None):
        self.id = id_
        self.body = body
        self.author = author
        # Use timezone-aware datetimes to be compatible with DRF DateTimeField
        self.created_at = created_at or datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.updated_at = updated_at or self.created_at

def _parse_rendered_bytes(b):
    # renderer.render usually returns bytes
    if isinstance(b, bytes):
        return json.loads(b.decode("utf-8"))
    if isinstance(b, str):
        return json.loads(b)
    return b

def test_tag_serializer_and_article_renderer_renders_combined():
    
    # Arrange
    tags = [SimpleTag("Python"), SimpleTag("Testing"), SimpleTag("DRF")]
    # TagSerializer should accept simple objects with .name
    serialized_tags = TagSerializer(tags, many=True).data

    # Build an article-like payload that mimics what ArticleSerializer would produce
    article_payload = {
        "title": "Integration testing article",
        "slug": "integration-testing-article",
        "description": "desc",
        "body": "content here",
        "tagList": [t["name"] if isinstance(t, dict) and "name" in t else t for t in (serialized_tags or [])],
        "createdAt": "2020-01-01T12:00:00Z",
        "updatedAt": "2020-01-01T12:00:00Z",
        "favorited": False,
        "favoritesCount": 0,
        "author": {"username": "alice", "bio": "dev", "image": None, "following": False},
    }

    renderer = ArticleJSONRenderer()

    # Act
    rendered = renderer.render(article_payload, renderer_context={})
    data = _parse_rendered_bytes(rendered)

    # Assert
    assert isinstance(data, dict)
    assert "article" in data, "Expected top-level 'article' key in rendered output"
    art = data["article"]
    assert art["title"] == "Integration testing article"
    assert art["slug"] == "integration-testing-article"
    assert art["body"] == "content here"
    # tagList should match names produced by TagSerializer
    assert art["tagList"] == ["Python", "Testing", "DRF"]

def test_comment_serializer_and_comment_renderer_wraps_comments_and_preserves_author():
    
    # Arrange
    author = SimpleUser(username="bob", bio="commenter", image="http://img", following=True)
    comments = [
        SimpleComment(1, "First!", author, created_at=datetime(2021, 6, 1, 9, 0, tzinfo=timezone.utc)),
        SimpleComment(2, "Nice post", author, created_at=datetime(2021, 6, 1, 10, 0, tzinfo=timezone.utc)),
    ]

    # CommentSerializer will transform comment objects into dicts expected by the renderer
    serialized = CommentSerializer(comments, many=True).data

    renderer = CommentJSONRenderer()

    # Act
    rendered = renderer.render(serialized, renderer_context={})
    data = _parse_rendered_bytes(rendered)

    # Assert
    assert isinstance(data, dict)
    assert "comments" in data
    assert isinstance(data["comments"], list)
    assert len(data["comments"]) == 2
    first = data["comments"][0]
    assert first["id"] == 1
    assert first["body"] == "First!"
    
    assert "author" in first and isinstance(first["author"], dict)
    assert first["author"]["username"] == "bob"
    assert first["author"]["image"] == "http://img"

def test_comment_renderer_handles_empty_list_gracefully():
    
    # Arrange
    renderer = CommentJSONRenderer()
    empty_serialized = []

    # Act
    rendered = renderer.render(empty_serialized, renderer_context={})
    data = _parse_rendered_bytes(rendered)

    # Assert
    assert data == {"comments": []} or (isinstance(data, dict) and "comments" in data and data["comments"] == [])
