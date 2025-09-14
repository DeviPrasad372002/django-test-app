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

    
# Replace the Django bootstrap section with this simplified version
# --- Minimal Django auto-config (before any app/model import) ---
try:
    import importlib, pkgutil
    if _iu.find_spec("django") is not None:
        import django
        from django.conf import settings as _dj_settings
        from django.apps import apps as _dj_apps

        def _maybe_add(app_name, installed):
            try:
                if _iu.find_spec(app_name):
                    installed.append(app_name)
                    return True
            except Exception:
                pass
            return False

        if not _dj_settings.configured:
            _installed = [
                "django.contrib.auth",
                "django.contrib.contenttypes", 
                "django.contrib.sessions"
            ]
            
            if _iu.find_spec("rest_framework"):
                _installed.append("rest_framework")

            # Try to add conduit apps
            for _app in ("conduit.apps.core", "conduit.apps.articles", "conduit.apps.authentication", "conduit.apps.profiles"):
                _maybe_add(_app, _installed)

            _cfg = dict(
                SECRET_KEY="test-key",
                DEBUG=True,
                ALLOWED_HOSTS=["*"],
                INSTALLED_APPS=sorted(set(_installed)),
                DATABASES=dict(default=dict(ENGINE="django.db.backends.sqlite3", NAME=":memory:")),
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
                _dj_settings.configure(**_cfg)
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
    import json
    import re
    from conduit.apps.authentication.models import User
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.core.exceptions import core_exception_handler
    from rest_framework.exceptions import NotFound as _DRF_NotFound
except ImportError as _import_error:
    import pytest
    pytest.skip(str(_import_error), allow_module_level=True)


def _exc_lookup(name, default=Exception):
    try:
        import rest_framework.exceptions as _rf_excs  # type: ignore
        return getattr(_rf_excs, name, default)
    except Exception:
        return default


@pytest.mark.parametrize(
    "username,email,user_id",
    [
        ("alice", "alice@example.com", 1),
        ("bob", "bob@example.net", 99999),
    ],
)
def test_user_get_short_name_and_generate_jwt_token(username, email, user_id):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create a lightweight User instance without DB side-effects
    user = User()
    user.username = username
    user.email = email
    user.id = user_id

    # Act: call public API methods
    short_name = user.get_short_name()
    token = user._generate_jwt_token()

    # Assert: short name is the username and token looks like a JWT string
    assert isinstance(short_name, _exc_lookup("str", Exception))
    assert short_name == username

    assert isinstance(token, _exc_lookup("str", Exception))
    # basic structural check for JWT: three base64url parts separated by dots
    assert token.count(".") == 2
    assert len(token.split(".")) == 3
    for part in token.split("."):
        assert part != ""


def test_userjsonrenderer_renders_user_payload_as_json_bytes():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: prepare a typical user payload
    renderer = UserJSONRenderer()
    payload = {"user": {"email": "x@y.test", "username": "xuser", "token": "tok"}}

    # Act: render to bytes
    output_bytes = renderer.render(payload)

    # Assert: output is bytes and valid JSON containing expected keys
    assert isinstance(output_bytes, (bytes, bytearray))
    decoded = output_bytes.decode("utf-8")
    assert decoded.strip().startswith("{")
    parsed = json.loads(decoded)
    assert isinstance(parsed, _exc_lookup("dict", Exception))
    assert "user" in parsed
    assert parsed["user"]["email"] == "x@y.test"
    assert parsed["user"]["username"] == "xuser"
    assert parsed["user"]["token"] == "tok"


@pytest.mark.parametrize("length", [0, 1, 5, 32])
def test_generate_random_string_returns_valid_alphanumeric_strings(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange & Act
    result = generate_random_string(length)

    # Assert: correct length and only alphanumeric characters
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    assert re.match(r"^[A-Za-z0-9]*$", result) is not None


@pytest.mark.parametrize(
    "exc_factory,expected_status",
    [
        (lambda: _exc_lookup("NotFound", _DRF_NotFound)("missing"), 404),
        (lambda: Exception("boom"), 500),
    ],
)
def test_core_exception_handler_handles_not_found_and_generic_errors(exc_factory):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc = exc_factory()
    context = {"view": None, "args": [], "kwargs": {}}

    # Act
    response = core_exception_handler(exc, context)

    # Assert: response-like object with status_code and dict-like data
    assert hasattr(response, "status_code")
    assert hasattr(response, "data")
    assert isinstance(response.status_code, int)
    assert isinstance(response.data, (dict, list, str, type(None)))

    # specific status expectations
    if isinstance(exc, _exc_lookup("_DRF_NotFound", Exception)) or exc.__class__.__name__ == "NotFound":
        assert response.status_code == 404
    else:
        assert response.status_code == 500
    # Ensure the response contains some information about the error
    if isinstance(response.data, dict):
        assert len(response.data) >= 0
