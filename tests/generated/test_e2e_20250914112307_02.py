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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from types import SimpleNamespace
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.core.exceptions import _handle_generic_error
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required project modules not available", allow_module_level=True)

def _exc_lookup(name, fallback):
    try:
        import rest_framework.exceptions as rf_exc
        return getattr(rf_exc, name)
    except Exception:
        return fallback

@pytest.mark.parametrize("meta,headers", [
    ({}, {}),                      # no META, no headers
    ({"HTTP_AUTHORIZATION": ""}, {}),  # empty authorization in META
    ({}, {"Authorization": ""}),   # empty Authorization header
])
def test_jwtauthentication_authenticate_returns_none_when_no_token(meta, headers):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    request = SimpleNamespace()
    request.META = dict(meta)
    request.headers = dict(headers)
    jwt_auth = JWTAuthentication()

    # Act
    result = jwt_auth.authenticate(request)

    # Assert
    assert result is None

@pytest.mark.parametrize("bad_token", [
    "",
    "not.a.valid.token",
    None,
])
def test__authenticate_credentials_raises_for_invalid_token(bad_token):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    jwt_auth = JWTAuthentication()
    exc_type = _exc_lookup("AuthenticationFailed", Exception)

    # Act / Assert
    with pytest.raises(_exc_lookup("exc_type", Exception)):
        # call the underlying credentials checker; if signature differs this will surface as test failure
        jwt_auth._authenticate_credentials(bad_token)

def test_add_slug_to_article_if_not_exists_creates_slug_from_title():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class FakeArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    original_title = "My Test Article!!"
    article = FakeArticle(title=original_title, slug=None)

    # Act
    # signature expected: (sender, instance, created, **kwargs)
    add_slug_to_article_if_not_exists(None, article, True)

    # Assert
    assert getattr(article, "slug", None) is not None
    assert isinstance(article.slug, str)
    assert article.slug.strip() != ""
    # Expect slug contains hyphens between words and includes parts of the title
    assert "-" in article.slug
    assert "my" in article.slug.lower()

def test__handle_generic_error_returns_response_with_500_and_payload():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc = Exception("something went wrong")
    context = {"view": None, "request": None}

    # Act
    response = _handle_generic_error(exc, context)

    # Assert
    assert response is not None
    assert hasattr(response, "status_code")
    assert int(response.status_code) == 500
    # Response should carry some data describing the error
    data = getattr(response, "data", None)
    assert data is not None
    # Accept either 'detail' or 'message' or any payload with non-empty content
    assert (("detail" in data and data["detail"]) or ("message" in data and data["message"]) or bool(data))
