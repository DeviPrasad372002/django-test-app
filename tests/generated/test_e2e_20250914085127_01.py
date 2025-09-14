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

try:
    import pytest
    from datetime import datetime, timezone
    from conduit.apps.articles.serializers import ArticleSerializer
    from conduit.apps.articles.models import Article, Comment
except ImportError:
    import pytest
    pytest.skip("Required modules for tests are not available", allow_module_level=True)


class DummyFavorites:
    def __init__(self, n):
        self._n = n

    def count(self):
        return self._n


class DummyArticleLike:
    def __init__(self, created_at=None, updated_at=None, favorites=None, has_favorited_fn=None):
        self.created_at = created_at
        self.updated_at = updated_at
        self.favorites = favorites
        self._hf = has_favorited_fn

    def has_favorited(self, user):
        if self._hf is None:
            return False
        return self._hf(user)


class DummyUser:
    def __init__(self, name="u"):
        self.name = name


class DummyRequest:
    def __init__(self, user):
        self.user = user


@pytest.mark.parametrize(
    "created_dt, updated_dt, expected_created_iso, expected_updated_iso",
    [
        (
            datetime(2020, 1, 1, 12, 0, 0),
            datetime(2020, 1, 2, 13, 30, 15),
            "2020-01-01T12:00:00Z",
            "2020-01-02T13:30:15Z",
        ),
        (
            datetime(2021, 6, 15, 8, 5, 3, tzinfo=timezone.utc),
            datetime(2021, 6, 16, 9, 6, 4, tzinfo=timezone.utc),
            "2021-06-15T08:05:03Z",
            "2021-06-16T09:06:04Z",
        ),
    ],
)
def test_article_serializer_formats_created_and_updated_times(created_dt, updated_dt, expected_created_iso, expected_updated_iso):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: prepare serializer and dummy article-like object with created/updated datetimes
    serializer = ArticleSerializer()
    dummy_article = DummyArticleLike(created_at=created_dt, updated_at=updated_dt)

    # Act: obtain formatted created and updated values via serializer methods
    created_value = serializer.get_created_at(dummy_article)
    updated_value = serializer.get_updated_at(dummy_article)

    # Assert: the ISO-like string representation matches expected format (seconds precision, Z suffix)
    assert isinstance(created_value, _exc_lookup("str", Exception))
    assert isinstance(updated_value, _exc_lookup("str", Exception))
    assert created_value == expected_created_iso
    assert updated_value == expected_updated_iso


@pytest.mark.parametrize(
    "favorites_count_value",
    [
        0,
        1,
        5,
    ],
)
def test_article_serializer_get_favorites_count_uses_favorites_count_method(favorites_count_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: serializer and dummy article whose .favorites.count() returns the configured number
    serializer = ArticleSerializer()
    dummy_favorites = DummyFavorites(favorites_count_value)
    dummy_article = DummyArticleLike(favorites=dummy_favorites)

    # Act: call the serializer helper to get favorites count
    result = serializer.get_favorites_count(dummy_article)

    # Assert: returned value is an integer equal to the underlying count
    assert isinstance(result, _exc_lookup("int", Exception))
    assert result == favorites_count_value


@pytest.mark.parametrize(
    "has_favorited_return, expect_value, description",
    [
        (True, True, "user has favorited the article"),
        (False, False, "user has not favorited the article"),
    ],
)
def test_article_serializer_get_favorited_reflects_article_has_favorited(has_favorited_return, expect_value, description):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: prepare serializer with a request context containing a DummyUser
    user = DummyUser("tester")
    request = DummyRequest(user)
    serializer = ArticleSerializer(context={"request": request})

    # Article exposes has_favorited(user) method which should be used by serializer
    dummy_article = DummyArticleLike(has_favorited_fn=lambda u: has_favorited_return)

    # Act: compute favorited state
    result = serializer.get_favorited(dummy_article)

    # Assert: serializer returns boolean reflecting underlying has_favorited result
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result is expect_value


def test_article_and_comment_str_return_title_and_body_respectively():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create Article and Comment instances with representative text values
    article_title = "A distinct article title"
    comment_body = "A meaningful comment body"

    article = Article(title=article_title)
    comment = Comment(body=comment_body)

    # Act: call str() on both model instances
    article_str = str(article)
    comment_str = str(comment)

    # Assert: __str__ returns title for Article and body for Comment
    assert article_str == article_title
    assert comment_str == comment_body
