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
import random
import string
import types

import pytest

try:
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.core.exceptions import core_exception_handler
    from rest_framework import exceptions as drf_exceptions
    from rest_framework.response import Response as DRFResponse
except ImportError as e:
    pytest.skip(f"Required project modules or DRF not available: {e}", allow_module_level=True)

def _make_renderer_call(renderer, data):
    # helper to feed renderer consistent signature in case signature expects more args
    try:
        return renderer.render(data)
    except TypeError:
        # some renderers accept (data, media_type=None, renderer_context=None)
        return renderer.render(data, media_type=None, renderer_context={})

@pytest.mark.parametrize(
    "renderer_cls,input_data,expected_top_key",
    [
        (ArticleJSONRenderer, {"title": "Hello", "body": "x"}, "article"),
        (CommentJSONRenderer, {"body": "Nice post", "author": {"username": "a"}}, "comment"),
        (UserJSONRenderer, {"username": "tester", "email": "t@example.com"}, "user"),
    ],
)
def test_renderer_wraps_payload_into_expected_top_level_key(renderer_cls, input_data, expected_top_key):
    # Arrange
    renderer = renderer_cls()

    # Act
    rendered_bytes = _make_renderer_call(renderer, input_data)

    # Assert
    assert isinstance(rendered_bytes, (bytes, bytearray)), "Renderer must return bytes"
    decoded = rendered_bytes.decode("utf-8")
    parsed = json.loads(decoded)
    # Concrete shape: top-level key exists and value equals the provided input
    assert expected_top_key in parsed, f"Top key '{expected_top_key}' not present in renderer output"
    assert parsed[expected_top_key] == input_data

def test_renderer_handles_empty_payload_and_none():
    # Arrange
    renderer = ArticleJSONRenderer()

    # Act
    rendered_bytes = _make_renderer_call(renderer, None)

    # Assert
    assert isinstance(rendered_bytes, (bytes, bytearray))
    decoded = rendered_bytes.decode("utf-8")
    parsed = json.loads(decoded)
    # When data is None, many renderers produce an empty object under the key
    assert "article" in parsed
    # Accept either None or empty dict depending on implementation, but assert type existence
    assert parsed["article"] is None or isinstance(parsed["article"], dict)

def test_generate_random_string_uses_random_choice(monkeypatch):
    # Arrange
    # Force deterministic output by making random.choice always return 'Z'
    monkeypatch.setattr("conduit.apps.core.utils.random.choice", lambda seq: "Z")
    length = 8

    # Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, str)
    assert len(result) == length
    assert result == "Z" * length

@pytest.mark.parametrize(
    "exc_instance,expected_status,expected_detail_key",
    [
        (drf_exceptions.NotFound(detail="not found"), 404, "detail"),
        (drf_exceptions.ValidationError(detail={"field": ["bad"]}), 400, "detail"),
        (drf_exceptions.PermissionDenied(detail="no"), 403, "detail"),
    ],
)
def test_core_exception_handler_maps_common_exceptions(exc_instance, expected_status, expected_detail_key):
    # Arrange
    context = {"view": None, "args": (), "kwargs": {}}

    # Act
    response = core_exception_handler(exc_instance, context)

    # Assert
    # Handler should return a DRF Response for known exceptions
    assert isinstance(response, DRFResponse)
    assert getattr(response, "status_code", None) == expected_status
    # Response data should include error information; ensure expected key exists
    assert isinstance(response.data, dict)
    assert expected_detail_key in response.data

def test_core_exception_handler_returns_none_for_unhandled_exception():
    # Arrange
    class CustomExc(Exception):
        pass

    exc = CustomExc("boom")
    context = {}

    # Act
    result = core_exception_handler(exc, context)

    # Assert
    
    assert result is None

def test_renderers_and_exception_handler_integration_roundtrip(monkeypatch):
    # Arrange
    
    exc = drf_exceptions.NotFound(detail="nope")
    context = {}

    # Act
    resp = core_exception_handler(exc, context)
    # Ensure handler produced a Response
    assert isinstance(resp, DRFResponse)
    # Now use ArticleJSONRenderer to render the response.data
    renderer = ArticleJSONRenderer()
    rendered = _make_renderer_call(renderer, resp.data)

    # Assert
    parsed = json.loads(rendered.decode("utf-8"))
    # The renderer should place the response data under the article key
    assert "article" in parsed
    
    assert parsed["article"].get("detail") == "nope" or parsed["article"].get("detail") == ["nope"]

def test_renderers_are_bytes_and_idempotent_on_serializable_input():
    # Arrange
    article_renderer = ArticleJSONRenderer()
    sample = {"title": "once", "tags": ["a", "b"], "meta": {"count": 1}}

    # Act
    first = _make_renderer_call(article_renderer, sample)
    second = _make_renderer_call(article_renderer, json.loads(first.decode("utf-8"))["article"])

    # Assert
    assert first == second
    assert first.startswith(b"{") and first.endswith(b"}")
