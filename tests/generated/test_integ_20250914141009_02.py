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
    from types import SimpleNamespace
    from conduit.apps.articles import signals as articles_signals
    from conduit.apps.core import utils as core_utils
    from conduit.apps.core import exceptions as core_exceptions
    from conduit.apps.articles import views as articles_views
except ImportError:
    import pytest  # re-import to satisfy linter after skip
    pytest.skip("conduit package not available", allow_module_level=True)


@pytest.mark.parametrize(
    "initial_slug, expected_slug_suffix",
    [
        (None, "abcd"),
        ("existing-slug", "existing-slug"),
    ],
)
def test_add_slug_to_article_if_not_exists_sets_or_preserves_slug(monkeypatch, initial_slug, expected_slug_suffix):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    monkeypatch.setattr(core_utils, "generate_random_string", lambda length=6: "abcd")
    article_instance = SimpleNamespace(title="My Article!", slug=initial_slug)

    # Act
    articles_signals.add_slug_to_article_if_not_exists(sender=None, instance=article_instance)

    # Assert
    if initial_slug is None:
        actual_slug = getattr(article_instance, "slug", None)
        assert isinstance(actual_slug, _exc_lookup("str", Exception))
        assert actual_slug.endswith("-abcd")
        assert actual_slug.startswith("my-article")
    else:
        assert article_instance.slug == expected_slug_suffix


def test_handle_generic_error_returns_response_with_error_body():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    sample_exception = Exception("Boom")
    # Act
    response = core_exceptions._handle_generic_error(sample_exception)
    # Assert
    assert hasattr(response, "data"), "response must have data attribute"
    assert "errors" in response.data, "response.data must contain 'errors' key"
    body_errors = response.data["errors"].get("body")
    assert isinstance(body_errors, _exc_lookup("list", Exception)), "errors.body must be a list"
    assert str(sample_exception) in body_errors[0]


def test_comments_destroy_deletes_comment_and_returns_204(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    deleted_flag = {"called": False}

    class MockComment:
        def __init__(self):
            self.id = 1

        def delete(self):
            deleted_flag["called"] = True

    mock_comment_instance = MockComment()

    class MockObjects:
        @staticmethod
        def get(pk=None):
            if pk == 1:
                return mock_comment_instance
            raise LookupError("Not found")

    monkeypatch.setattr(articles_views, "Comment", SimpleNamespace(objects=MockObjects()))

    mock_request = SimpleNamespace(user=SimpleNamespace(pk=1))
    view_instance = articles_views.CommentsDestroyAPIView()

    # Act
    response = view_instance.delete(mock_request, pk=1)

    # Assert
    assert deleted_flag["called"] is True
    assert hasattr(response, "status_code")
    assert response.status_code == 204
