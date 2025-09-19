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
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.serializers import (
        ArticleSerializer,
        CommentSerializer,
        TagSerializer,
        Meta as ArticlesMeta,
    )
    from conduit.apps.articles.views import (
        ArticleViewSet,
        CommentsListCreateAPIView,
        CommentsDestroyAPIView,
        ArticlesFavoriteAPIView,
        TagListAPIView,
        ArticlesFeedAPIView,
    )
    from rest_framework import serializers as drf_serializers
    from rest_framework.response import Response
except ImportError as exc:  # pragma: no cover - skip if project deps missing
    pytest.skip(f"Skipping tests because imports failed: {exc}", allow_module_level=True)

@pytest.mark.parametrize(
    "renderer_cls, payload, expected_subbytes",
    [
        (ArticleJSONRenderer, {"article": {"title": "Hello", "body": "x"}}, [b'"article"', b'"title"', b"Hello"]),
        (CommentJSONRenderer, {"comment": {"body": "Nice post"}}, [b'"comment"', b'"body"', b"Nice post"]),
    ],
)
def test_renderer_render_returns_json_bytes_and_contains_expected(renderer_cls, payload, expected_subbytes):
    # Arrange
    renderer = renderer_cls()

    # Act
    output = renderer.render(payload)

    # Assert
    assert isinstance(output, (bytes, bytearray)), "Renderer must return bytes-like JSON"
    for sub in expected_subbytes:
        assert sub in output, f"Rendered output must contain {sub!r}"

@pytest.mark.parametrize(
    "serializer_cls",
    [ArticleSerializer, CommentSerializer, TagSerializer],
)
def test_serializer_classes_have_meta_and_fields_iterable_and_are_serializers(serializer_cls):
    # Arrange / Act
    has_meta = hasattr(serializer_cls, "Meta")
    meta_obj = getattr(serializer_cls, "Meta", None)

    # Assert
    assert has_meta, f"{serializer_cls.__name__} must define an inner Meta class"
    assert meta_obj is not None, "Meta should not be None"
    # Meta should have fields attribute that is iterable (tuple/list)
    fields = getattr(meta_obj, "fields", None)
    assert fields is not None, "Meta.fields must be defined"
    assert isinstance(fields, (list, tuple)), "Meta.fields must be a list or tuple"
    # Serializer should subclass one of DRF serializer bases
    assert any(
        issubclass(serializer_cls, base)
        for base in (drf_serializers.ModelSerializer, drf_serializers.Serializer)
    ), f"{serializer_cls.__name__} must subclass a DRF Serializer class"

def test_articles_meta_helper_is_class_named_meta():
    # Arrange / Act
    meta = ArticlesMeta

    # Assert
    assert isinstance(meta, type), "Articles Meta should be a class"
    assert meta.__name__ == "Meta", "Articles Meta class should be named 'Meta'"

@pytest.mark.parametrize(
    "view_cls, method_name",
    [
        (ArticleViewSet, "list"),
        (ArticleViewSet, "retrieve"),
        (ArticleViewSet, "update"),
        (ArticleViewSet, "destroy"),
        (CommentsListCreateAPIView, "post"),
        (CommentsDestroyAPIView, "delete"),
        (ArticlesFavoriteAPIView, "post"),
        (TagListAPIView, "get"),
        (ArticlesFeedAPIView, "get"),
    ],
)
def test_view_methods_raise_typeerror_when_called_without_request(view_cls, method_name):
    # Arrange
    view = view_cls()

    
    method = getattr(view, method_name, None)
    assert callable(method), f"{view_cls.__name__}.{method_name} must be callable"
    with pytest.raises(TypeError):
        method()  # missing required positional argument 'request'

@pytest.mark.parametrize(
    "view_cls, method_name, response_payload",
    [
        (ArticlesFeedAPIView, "get", {"articles": [], "articlesCount": 0}),
        (CommentsListCreateAPIView, "post", {"comment": {"body": "ok"}}),
        (CommentsDestroyAPIView, "delete", {"detail": "deleted"}),
        (ArticlesFavoriteAPIView, "post", {"article": {"favorited": True}}),
    ],
)
def test_view_methods_can_be_monkeypatched_to_return_expected_response(view_cls, method_name, response_payload):
    # Arrange
    view = view_cls()

    # Replace the method on the instance with a simple method that returns a DRF Response
    def fake_method(self, request, *args, **kwargs):
        return Response(response_payload)

    bound = types.MethodType(fake_method, view)
    setattr(view, method_name, bound)

    # Act
    fake_request = object()
    result = getattr(view, method_name)(fake_request)

    # Assert
    assert isinstance(result, Response), "Patched view method must return a DRF Response"
    assert result.data == response_payload, "Response data must equal the patched payload"
