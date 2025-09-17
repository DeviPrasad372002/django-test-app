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
    import json
    import pytest

    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.serializers import (
        ArticleSerializer,
        CommentSerializer,
        TagSerializer,
    )
except ImportError:
    import pytest

    pytest.skip("Skipping tests: conduit.apps.articles imports unavailable", allow_module_level=True)

def _decode_renderer_output(raw):
    """Helper to make tests robust to renderers returning bytes or str."""
    if isinstance(raw, bytes):
        return raw.decode("utf-8")
    if isinstance(raw, str):
        return raw
    raise TypeError("Unexpected renderer output type: %s" % type(raw))

def test_ArticleJSONRenderer_render_wraps_article():
    
    # Arrange
    renderer = ArticleJSONRenderer()
    payload = {"title": "Test Article", "body": "Content"}

    # Act
    raw = renderer.render(payload)
    text = _decode_renderer_output(raw)
    parsed = json.loads(text)

    # Assert
    assert isinstance(raw, (bytes, str))
    assert "article" in parsed
    assert isinstance(parsed["article"], dict)
    assert parsed["article"]["title"] == "Test Article"
    assert parsed["article"]["body"] == "Content"

def test_CommentJSONRenderer_render_wraps_comment():
    
    # Arrange
    renderer = CommentJSONRenderer()
    payload = {"id": 1, "body": "A comment"}

    # Act
    raw = renderer.render(payload)
    text = _decode_renderer_output(raw)
    parsed = json.loads(text)

    # Assert
    assert isinstance(raw, (bytes, str))
    assert "comment" in parsed
    assert isinstance(parsed["comment"], dict)
    assert parsed["comment"]["id"] == 1
    assert parsed["comment"]["body"] == "A comment"

def test_ArticleSerializer_has_meta_with_model_and_fields():
    
    # Arrange / Act
    meta = getattr(ArticleSerializer, "Meta", None)

    # Assert
    assert meta is not None, "ArticleSerializer must define Meta"
    assert isinstance(meta, type), "ArticleSerializer.Meta should be a class"
    assert hasattr(meta, "model"), "Meta should declare a model attribute"
    assert hasattr(meta, "fields"), "Meta should declare fields"
    fields = getattr(meta, "fields")
    assert hasattr(fields, "__iter__"), "Meta.fields should be iterable"
    
    assert len(list(fields)) >= 1

@pytest.mark.parametrize(
    "serializer_cls",
    [CommentSerializer, TagSerializer],
)
def test_Serializer_classes_define_meta_with_fields(serializer_cls):
    
    # Arrange / Act
    meta = getattr(serializer_cls, "Meta", None)

    # Assert
    assert meta is not None, f"{serializer_cls.__name__} must define Meta"
    assert isinstance(meta, type)
    assert hasattr(meta, "fields")
    fields = getattr(meta, "fields")
    assert hasattr(fields, "__iter__")
    assert len(list(fields)) >= 1
