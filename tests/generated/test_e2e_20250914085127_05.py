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

def _fix_django_metaclass_compatibility():
    """Fix Django 1.10.5 metaclass compatibility with Python 3.10+"""
    try:
        import sys
        if sys.version_info >= (3, 8):
            import builtins
            original_build_class = builtins.__build_class__
            
            def patched_build_class(func, name, *bases, metaclass=None, **kwargs):
                try:
                    return original_build_class(func, name, *bases, metaclass=metaclass, **kwargs)
                except RuntimeError as e:
                    if '__classcell__' in str(e) and 'not set' in str(e):
                        # Create a new function without problematic cell variables
                        import types
                        code = func.__code__
                        if code.co_freevars:
                            # Remove free variables that cause issues
                            new_code = code.replace(
                                co_freevars=(),
                                co_names=code.co_names + code.co_freevars
                            )
                            new_func = types.FunctionType(
                                new_code,
                                func.__globals__,
                                func.__name__,
                                func.__defaults__,
                                None  # No closure
                            )
                            return original_build_class(new_func, name, *bases, metaclass=metaclass, **kwargs)
                    raise
                except Exception:
                    # Fallback for other metaclass issues
                    return original_build_class(func, name, *bases, **kwargs)
            
            builtins.__build_class__ = patched_build_class
    except Exception:
        pass

# Apply Django metaclass fix early
_fix_django_metaclass_compatibility()

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
            # Don't skip module-level, just continue
            pass
    
    if not _dj_apps.ready:
        try:
            django.setup()
        except Exception as e:
            # Don't skip module-level, just continue
            pass
            
except Exception as e:
    # Don't skip at module level - let individual tests handle Django issues
    pass



# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.core.exceptions import _handle_generic_error
    from rest_framework.response import Response
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Skipping tests due to ImportError: {e}", allow_module_level=True)

import json
from types import SimpleNamespace

@pytest.mark.parametrize(
    "article_input",
    [
        ({"title": "Hello World", "body": "Content"}),
        ({},),
        ({"title": "Spécial Çhårs", "tags": ["a", "b"]}),
    ],
)
def test_article_json_renderer_wraps_article_and_returns_bytes_or_string(article_input):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = ArticleJSONRenderer()
    article_data = article_input

    # Act
    rendered = renderer.render(article_data)

    # Assert
    assert isinstance(rendered, (bytes, str))
    rendered_text = rendered.decode("utf-8") if isinstance(rendered, _exc_lookup("bytes", Exception)) else rendered
    assert '"article"' in rendered_text
    # Ensure the provided keys are present when possible
    if isinstance(article_data, _exc_lookup("dict", Exception)) and "title" in article_data:
        assert f'"title": "{article_data["title"]}"' in rendered_text

@pytest.mark.parametrize(
    "comment_input, expected_key",
    [
        ({"body": "Nice post!"}, "comment"),
        ([{"body": "one"}, {"body": "two"}], "comments"),
    ],
)
def test_comment_json_renderer_wraps_comment_and_lists(comment_input, expected_key):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = CommentJSONRenderer()
    data = comment_input

    # Act
    rendered = renderer.render(data)

    # Assert
    assert isinstance(rendered, (bytes, str))
    rendered_text = rendered.decode("utf-8") if isinstance(rendered, _exc_lookup("bytes", Exception)) else rendered
    assert f'"{expected_key}"' in rendered_text

@pytest.mark.parametrize(
    "initial_title, initial_slug, expect_slug_generated, expected_substring",
    [
        ("Hello World", None, True, "hello-world"),
        ("Another Title", "", True, "another-title"),
        ("Already Slugged", "existing-slug", False, "existing-slug"),
    ],
)
def test_add_slug_to_article_if_not_exists_generates_slug_when_missing(
    # Arrange-Act-Assert: generated by ai-testgen
    initial_title, initial_slug, expect_slug_generated, expected_substring
):
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug
            self._saved = False
        def save(self, *args, **kwargs):
            self._saved = True

    article = DummyArticle(initial_title, initial_slug)

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    if expect_slug_generated:
        assert isinstance(article.slug, str) and article.slug != ""
        assert expected_substring in article.slug
        # ensure save was invoked by the signal handler (common behavior)
        assert getattr(article, "_saved", False) is True
    else:
        assert article.slug == expected_substring

def test_handle_generic_error_returns_response_with_data_and_status_code():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc = Exception("something went wrong")
    context = {}

    # Act
    resp = _handle_generic_error(exc, context)

    # Assert
    assert isinstance(resp, _exc_lookup("Response", Exception))
    assert hasattr(resp, "data")
    assert isinstance(resp.data, (dict, list, str))
    # Generic errors should result in 4xx or 5xx status codes
    assert isinstance(resp.status_code, int)
    assert resp.status_code >= 400
