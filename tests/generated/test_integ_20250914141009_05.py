import importlib.util, pytest
if importlib.util.find_spec('django') is None:
    pytest.skip('django not installed; skipping module', allow_module_level=True)

# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib as _importlib, importlib.util as _iu, importlib.machinery as _im, types as _types, pytest as _pytest, builtins as _builtins
import warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

_target = os.environ.get("TARGET_ROOT") or os.environ.get("ANALYZE_ROOT") or "target"
if _target and os.path.exists(_target):
    if _target not in sys.path: sys.path.insert(0, _target)
    try: os.chdir(_target)
    except Exception: pass
_TARGET_ABS = os.path.abspath(_target)

def _exc_lookup(name, default):
    try:
        mod_name, _, cls_name = str(name).rpartition(".")
        if mod_name:
            mod = __import__(mod_name, fromlist=[cls_name])
            return getattr(mod, cls_name, default)
        return getattr(sys.modules.get("builtins"), str(name), default)
    except Exception:
        return default

def _apply_compatibility_fixes():
    try:
        import jinja2
        if not hasattr(jinja2, 'Markup'):
            try:
                from markupsafe import Markup, escape
                jinja2.Markup = Markup
                if not hasattr(jinja2, 'escape'):
                    jinja2.escape = escape
            except Exception:
                pass
    except ImportError:
        pass
    try:
        import flask
        if not hasattr(flask, "escape"):
            try:
                from markupsafe import escape
                flask.escape = escape
            except Exception:
                pass
        try:
            import threading
            from flask import _app_ctx_stack, _request_ctx_stack
            for _stack in (_app_ctx_stack, _request_ctx_stack):
                if _stack is not None and not hasattr(_stack, "__ident_func__"):
                    _stack.__ident_func__ = getattr(threading, "get_ident", None) or (lambda: 0)
        except Exception:
            pass
    except ImportError:
        pass
    try:
        import collections as _collections, collections.abc as _abc
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container',
                   'MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
            if not hasattr(_collections, _n) and hasattr(_abc, _n):
                setattr(_collections, _n, getattr(_abc, _n))
    except Exception:
        pass
    try:
        import marshmallow as _mm
        if not hasattr(_mm, "__version__"):
            _mm.__version__ = "4"
    except Exception:
        pass

_apply_compatibility_fixes()
_ADAPTED_MODULES = set()

def _attach_module_getattr(_m):
    try:
        if getattr(_m, "__name__", None) in _ADAPTED_MODULES: return
        mfile = getattr(_m, "__file__", "") or ""
        if not mfile or not os.path.abspath(mfile).startswith(_TARGET_ABS + os.sep): return
        if hasattr(_m, "__getattr__"):
            _ADAPTED_MODULES.add(_m.__name__); return
        def __getattr__(name):
            for _nm, _obj in list(_m.__dict__.items()):
                if isinstance(_obj, type) and not _nm.startswith("_"):
                    try: _inst = _obj()
                    except Exception: continue
                    if hasattr(_inst, name):
                        _val = getattr(_inst, name)
                        try: setattr(_m, name, _val)
                        except Exception: pass
                        return _val
            raise AttributeError(f"module {_m.__name__!r} has no attribute {name!r}")
        _m.__getattr__ = __getattr__; _ADAPTED_MODULES.add(_m.__name__)
    except Exception:
        pass

# Disable import adapter entirely if Django is present to avoid metaclass issues.
_DJ_PRESENT = _iu.find_spec("django") is not None
if not STRICT and not _DJ_PRESENT:
    _orig_import = _builtins.__import__
    def _import_with_adapter(name, globals=None, locals=None, fromlist=(), level=0):
        mod = _orig_import(name, globals, locals, fromlist, level)
        try:
            if isinstance(mod, _types.ModuleType): _attach_module_getattr(mod)
            if fromlist:
                for attr in fromlist:
                    try:
                        sub = getattr(mod, attr, None)
                        if isinstance(sub, _types.ModuleType): _attach_module_getattr(sub)
                    except Exception: pass
        except Exception: pass
        return mod
    _builtins.__import__ = _import_with_adapter

# Handle Django configuration for tests
try:
    import django
    from django.conf import settings
    from django import apps as _dj_apps
    
    if not settings.configured:
        _cfg = dict(
            DEBUG=True,
            SECRET_KEY='test-secret-key-for-pytest',
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
            ],
            MIDDLEWARE=[
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
            ],
            USE_TZ=True,
            TIME_ZONE="UTC",
        )
        try:
            _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
        except Exception:
            pass
        try:
            settings.configure(**_cfg)
        except Exception as e:
            pass
    
    if not _dj_apps.ready:
        try:
            django.setup()
        except Exception as e:
            pass
            
except Exception as e:
    pass



# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest

try:
    import json
    from types import SimpleNamespace
    from unittest.mock import Mock

    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.views import CommentsDestroyAPIView
    from conduit.apps.core.exceptions import _handle_generic_error
    from conduit.apps.core import utils as core_utils
except ImportError as e:
    import pytest
    pytest.skip(f"Skipping tests due to import error: {e}", allow_module_level=True)


@pytest.mark.parametrize(
    "renderer_class,payload",
    [
        (ArticleJSONRenderer, {"title": "Test Article", "body": "Content"}),
        (ArticleJSONRenderer, {"id": 1, "tags": ["python", "pytest"]}),
        (CommentJSONRenderer, {"id": 2, "body": "A comment"}),
        (CommentJSONRenderer, {"comments": [{"id": 3, "body": "nested"}]}),
    ],
)
def test_renderers_wrap_payloads(renderer_class, payload):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = renderer_class()

    # Act
    rendered_bytes = renderer.render(payload)

    # Assert
    assert isinstance(rendered_bytes, (bytes, bytearray))
    parsed = json.loads(rendered_bytes.decode("utf-8"))
    assert isinstance(parsed, _exc_lookup("dict", Exception))
    # The renderer should wrap the provided payload as the single top-level value
    assert len(parsed) == 1
    top_level_value = list(parsed.values())[0]
    assert top_level_value == payload


@pytest.mark.parametrize(
    "initial_slug,expected_saved",
    [
        (None, True),       # No slug -> should generate and save
        ("existing-slug", False),  # Existing slug -> should not overwrite or save
    ],
)
def test_add_slug_to_article_if_not_exists_generates_when_missing(monkeypatch, initial_slug, expected_saved):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    generated_token = "RND123"
    monkeypatch.setattr(core_utils, "generate_random_string", lambda length=6: generated_token)

    saved_calls = []

    def fake_save():
        saved_calls.append(True)

    article_instance = SimpleNamespace(slug=initial_slug, title="Hello World", save=fake_save)

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=article_instance, created=True)

    # Assert
    if initial_slug is None:
        # slug should be set and include generated token
        assert getattr(article_instance, "slug") is not None
        assert generated_token in article_instance.slug
        assert saved_calls, "Expected save() to be called when slug was missing"
    else:
        # slug should remain unchanged and save should not be called
        assert article_instance.slug == "existing-slug"
        assert saved_calls == []


def test_comments_destroy_view_calls_delete_and_returns_response():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = CommentsDestroyAPIView()
    delete_called = []

    # Mock comment instance with author and delete
    mock_author = SimpleNamespace(pk=10)
    mock_comment = SimpleNamespace(author=mock_author, delete=lambda: delete_called.append(True))

    # Ensure the view will return our mock object
    view.get_object = Mock(return_value=mock_comment)

    # Create a fake request where user is the author (allowed to delete)
    fake_request = SimpleNamespace(user=mock_author)

    # Act
    # Many DRF destroy views accept (request, *args, **kwargs)
    response = view.delete(fake_request, pk=1)

    # Assert
    assert delete_called == [True], "Expected the comment's delete() to be invoked exactly once"
    assert hasattr(response, "status_code"), "Expected a Response-like object with status_code"
    assert isinstance(response.status_code, int)
    assert response.status_code in (200, 204), "Expected successful deletion status code"


@pytest.mark.parametrize(
    "exception_message",
    [
        ("unexpected error"),
        ("database failure"),
    ],
)
def test_handle_generic_error_returns_response_with_server_error(exception_message):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc = Exception(exception_message)
    context = {"view": None}

    # Act
    response = _handle_generic_error(exc, context)

    # Assert
    assert hasattr(response, "status_code"), "Expected a Response-like object"
    assert isinstance(response.status_code, int)
    # Generic handler should indicate server error
    assert response.status_code >= 500 and response.status_code < 600
    # Response data should be a mapping with some information about the error
    assert hasattr(response, "data")
    assert isinstance(response.data, dict) and response.data, "Expected non-empty dict body describing the error"
