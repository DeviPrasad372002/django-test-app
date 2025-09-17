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

import pytest

try:
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.serializers import ArticleSerializer, CommentSerializer, TagSerializer
    from conduit.apps.articles.models import Article, Comment, Tag
except ImportError as exc:  # pragma: no cover - environment missing target package
    pytest.skip("conduit.apps.articles not available: %s" % exc, allow_module_level=True)

from types import SimpleNamespace
import datetime

def test_articlejsonrenderer_render_dict_returns_bytes_and_contains_keys():
    
    # Arrange
    renderer = ArticleJSONRenderer()
    payload = {"article": {"title": "Hello World", "body": "Content"}}

    # Act
    output = renderer.render(payload, renderer_context={})

    # Assert
    assert isinstance(output, (bytes, bytearray)), "Rendered output must be bytes-like"
    assert b'"article"' in output
    assert b'"title"' in output
    assert b'Hello World' in output

def test_commentjsonrenderer_render_dict_returns_bytes_and_contains_comment_body():
    
    # Arrange
    renderer = CommentJSONRenderer()
    payload = {"comment": {"body": "Nice article"}}

    # Act
    output = renderer.render(payload, renderer_context={})

    # Assert
    assert isinstance(output, (bytes, bytearray))
    assert b'"comment"' in output
    assert b'"body"' in output
    assert b'Nice article' in output

def test_serializer_meta_models_and_field_presence():
    
    # Arrange / Act
    article_meta = getattr(ArticleSerializer, "Meta", None)
    comment_meta = getattr(CommentSerializer, "Meta", None)
    tag_meta = getattr(TagSerializer, "Meta", None)

    # Assert meta classes exist and point to expected models
    assert article_meta is not None and getattr(article_meta, "model", None) is Article
    assert comment_meta is not None and getattr(comment_meta, "model", None) is Comment
    assert tag_meta is not None and getattr(tag_meta, "model", None) is Tag

    # Assert expected common field names are present in Meta.fields
    article_fields = tuple(getattr(article_meta, "fields", ()))
    comment_fields = tuple(getattr(comment_meta, "fields", ()))
    tag_fields = tuple(getattr(tag_meta, "fields", ()))

    assert "title" in article_fields, "ArticleSerializer.Meta.fields must include 'title'"
    assert "body" in article_fields, "ArticleSerializer.Meta.fields must include 'body'"
    assert "body" in comment_fields, "CommentSerializer.Meta.fields must include 'body'"
    assert "name" in tag_fields, "TagSerializer.Meta.fields must include 'name'"

@pytest.mark.parametrize("method_name, attr_name", [
    ("get_created_at", "created_at"),
    ("get_updated_at", "updated_at"),
])
def test_article_serializer_get_timestamp_methods_return_iso_strings(method_name, attr_name):
    
    # Arrange
    method = getattr(ArticleSerializer(), method_name, None)
    if method is None:
        pytest.skip(f"{method_name} not implemented on ArticleSerializer")
    # create a simple object with the timestamp attribute
    ts = datetime.datetime(2020, 1, 2, 3, 4, 5, 123456)
    obj = SimpleNamespace(**{attr_name: ts})

    # Act
    result = method(obj)

    # Assert
    assert isinstance(result, str)
    # Expect the year and time components to appear - tolerate different ISO flavors
    assert "2020" in result
    assert "03" in result or "3" in result  # hour component should be present in some form
    assert "01" in result or "1" in result  # month component present
    # Ensure non-empty
    assert len(result) > 0
