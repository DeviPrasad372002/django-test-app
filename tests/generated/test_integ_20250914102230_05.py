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
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.views import CommentsDestroyAPIView, ArticlesFavoriteAPIView
    from conduit.apps.articles import serializers as articles_serializers_module
except ImportError:
    import pytest
    pytest.skip("Skipping tests because conduit app modules are not available", allow_module_level=True)


def _exc_lookup(name, default):
    for modname in ("rest_framework.exceptions", "django.core.exceptions", "exceptions"):
        try:
            mod = __import__(modname, fromlist=[name])
            return getattr(mod, name)
        except Exception:
            continue
    return default


@pytest.mark.parametrize(
    "renderer_cls,input_data,expected_key",
    [
        (ArticleJSONRenderer, {"article": {"title": "t"}}, b'"article"'),
        (ArticleJSONRenderer, {"articles": [{"title": "t1"}, {"title": "t2"}]}, b'"articles"'),
        (CommentJSONRenderer, {"comment": {"body": "c"}}, b'"comment"'),
        (CommentJSONRenderer, {"comments": [{"body": "c1"}]}, b'"comments"'),
    ],
)
def test_json_renderers_wrap_expected_root(renderer_cls, input_data, expected_key):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = renderer_cls()
    # Act
    output_bytes = renderer.render(input_data)
    # Assert
    assert isinstance(output_bytes, (bytes, bytearray))
    assert expected_key in output_bytes


@pytest.mark.parametrize("same_author", [True, False])
def test_comments_destroy_view_handles_delete_and_permissions(monkeypatch, same_author):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = CommentsDestroyAPIView()

    class FakeUser:
        def __init__(self, username):
            self.username = username

    author_user = FakeUser("author")
    other_user = FakeUser("other")

    class FakeComment:
        def __init__(self, author):
            self.author = author
            self.delete_called = False

        def delete(self):
            self.delete_called = True

    fake_comment = FakeComment(author_user)

    def fake_get_object(*args, **kwargs):
        return fake_comment

    monkeypatch.setattr(view, "get_object", fake_get_object)

    request_user = author_user if same_author else other_user
    fake_request = type("Req", (), {"user": request_user})

    PermissionDenied = _exc_lookup("PermissionDenied", Exception)

    # Act / Assert
    if same_author:
        response = view.delete(fake_request, slug="some-slug", pk="1")
        status = getattr(response, "status_code", None)
        assert status in (200, 204)
        assert fake_comment.delete_called is True
    else:
        with pytest.raises(_exc_lookup("PermissionDenied", Exception)):
            view.delete(fake_request, slug="some-slug", pk="1")


def test_articles_favorite_view_uses_serializer_and_returns_serialized_article(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    stored_inits = []

    class FakeSerializer:
        def __init__(self, instance, context=None):
            stored_inits.append({"instance": instance, "context": context})
            self._instance = instance
            self._context = context or {}

        @property
        def data(self):
            return {"mocked": True, "instance_id": id(self._instance)}

    monkeypatch.setattr(articles_serializers_module, "ArticleSerializer", FakeSerializer)

    view = ArticlesFavoriteAPIView()

    class FakeArticle:
        def __init__(self):
            self.toggle_called = False

        def favorite(self, user):
            self.toggle_called = True

        def unfavorite(self, user):
            self.toggle_called = True

    fake_article = FakeArticle()

    def fake_get_object(*args, **kwargs):
        return fake_article

    monkeypatch.setattr(view, "get_object", fake_get_object)

    class FakeUser:
        pass

    fake_user = FakeUser()
    fake_request = type("Req", (), {"user": fake_user})

    # Act
    response = view.post(fake_request, slug="an-article-slug")

    # Assert serializer was instantiated with object and request context
    assert stored_inits, "Serializer was not instantiated"
    init_info = stored_inits[0]
    assert init_info["instance"] is fake_article
    assert isinstance(init_info["context"], dict)
    assert init_info["context"].get("request") is fake_request

    # Assert response contains serialized article under expected key
    resp_data = getattr(response, "data", None)
    assert isinstance(resp_data, _exc_lookup("dict", Exception))
    assert "article" in resp_data
    assert resp_data["article"] == {"mocked": True, "instance_id": id(fake_article)}
