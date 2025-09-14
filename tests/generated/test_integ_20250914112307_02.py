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
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import backends as auth_backends
    from conduit.apps.articles import signals as article_signals
    from conduit.apps.articles import views as articles_views
    from conduit.apps.core import utils as core_utils
    from django.utils import text as django_text
    import jwt
    import rest_framework.exceptions as drf_exceptions
except ImportError:
    pytest.skip("Required application modules not available", allow_module_level=True)


def _exc_lookup(name, default_exception):
    return getattr(drf_exceptions, name, default_exception)


def test_user_token_and_full_name(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = auth_models.User()
    user.username = "jdoe"
    user.email = "jdoe@example.com"
    user.first_name = "John"
    user.last_name = "Doe"

    def fake_jwt_encode(payload, key, algorithm="HS256"):
        return b"faketokenbytes"

    monkeypatch.setattr(jwt, "encode", fake_jwt_encode)

    # Act
    token_value = user.token()
    full_name = user.get_full_name()

    # Assert
    assert isinstance(token_value, (str, bytes))
    assert "fake" in (token_value.decode() if isinstance(token_value, _exc_lookup("bytes", Exception)) else token_value)
    assert full_name == "John Doe"


def test_jwt_authentication_valid_and_invalid(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    jwt_token = "sometoken"
    fake_user = object()

    class FakeManager:
        @staticmethod
        def get(**kwargs):
            return fake_user

    FakeUserModel = type("FakeUserModel", (), {"objects": FakeManager()})
    monkeypatch.setattr(auth_backends, "User", FakeUserModel)

    def fake_jwt_decode_valid(token, key, algorithms=None):
        return {"id": 1}

    monkeypatch.setattr(jwt, "decode", fake_jwt_decode_valid)

    auth = auth_backends.JWTAuthentication()

    # Act
    returned = auth._authenticate_credentials(jwt_token)

    # Assert
    assert returned is fake_user

    # Now simulate invalid token decoding -> should raise AuthenticationFailed
    def fake_jwt_decode_invalid(token, key, algorithms=None):
        raise Exception("invalid token")

    monkeypatch.setattr(jwt, "decode", fake_jwt_decode_invalid)

    expected_exc = _exc_lookup("AuthenticationFailed", Exception)
    with pytest.raises(_exc_lookup("expected_exc", Exception)):
        auth._authenticate_credentials(jwt_token)


def test_add_slug_to_article_if_not_exists_assigns_slug_and_saves(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class FakeArticle:
        def __init__(self, title):
            self.title = title
            self.slug = None
            self.saved = False

        def save(self, *args, **kwargs):
            self.saved = True

    article = FakeArticle("My Title")

    monkeypatch.setattr(core_utils, "generate_random_string", lambda length=6: "RND")
    monkeypatch.setattr(django_text, "slugify", lambda value: "my-title")

    # Act
    article_signals.add_slug_to_article_if_not_exists(None, instance=article, created=True)

    # Assert
    assert article.saved is True
    assert article.slug is not None
    assert "my-title" in article.slug
    assert "RND".lower() in article.slug.lower()


@pytest.mark.parametrize(
    "query_params, expected_filters",
    [
        ({}, []),
        ({"author": "alice"}, [{"author__username": "alice"}]),
    ],
)
def test_filter_queryset_applies_expected_filters(query_params, expected_filters):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    recorded_filters = []

    class FakeQuerySet:
        def filter(self, **kwargs):
            recorded_filters.append(kwargs)
            return self

    qs = FakeQuerySet()

    class DummyRequest:
        def __init__(self, query_params):
            self.query_params = query_params
            self.user = None

    class ViewLike:
        def __init__(self, query_params):
            self.request = DummyRequest(query_params)
            self.kwargs = {}

    view_instance = ViewLike(query_params)

    # Use the bound method from the module (function-like) to avoid full DRF setup
    filter_method = articles_views.ArticleViewSet.filter_queryset

    # Act
    result_qs = filter_method(view_instance, qs)

    # Assert
    assert result_qs is qs
    assert recorded_filters == expected_filters
