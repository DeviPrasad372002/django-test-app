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

try:
    import pytest
    import json
    from types import SimpleNamespace
    from unittest.mock import Mock
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.backends import JWTAuthentication
except ImportError as e:
    import pytest
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


@pytest.mark.parametrize("length", [0, 1, 8, 16])
def test_generate_random_string_returns_string_of_requested_length_and_alnum(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    requested_length = length

    # Act
    result = generate_random_string(requested_length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == requested_length
    if requested_length == 0:
        assert result == ""
    else:
        assert result.isalnum()


@pytest.mark.parametrize(
    "input_data",
    [
        ({"email": "alice@example.com", "username": "alice"}),
        ({"token": "sometoken", "username": "bob"}),
    ],
)
def test_userjsonrenderer_render_wraps_payload_under_user_and_returns_json_bytes(input_data):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = UserJSONRenderer()

    # Act
    rendered = renderer.render(input_data)

    # Assert
    assert isinstance(rendered, (bytes, str))
    decoded = rendered.decode() if isinstance(rendered, _exc_lookup("bytes", Exception)) else rendered
    parsed = json.loads(decoded)
    assert "user" in parsed
    assert parsed["user"] == input_data


def test_jwtauthentication_calls_internal_credential_checker_and_returns_user_token(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    jwt_auth = JWTAuthentication()
    dummy_user = SimpleNamespace(username="tester")
    dummy_token = "dummy.jwt.token"
    mock_auth_check = Mock(return_value=(dummy_user, dummy_token))
    monkeypatch.setattr(JWTAuthentication, "_authenticate_credentials", mock_auth_check)
    request = SimpleNamespace(META={"HTTP_AUTHORIZATION": "Token abc.def.ghi"})

    # Act
    result = jwt_auth.authenticate(request)

    # Assert
    assert result == (dummy_user, dummy_token)
    mock_auth_check.assert_called_once()


@pytest.mark.parametrize(
    "meta_header",
    [
        ({},),  # no header present
        ({"HTTP_AUTHORIZATION": ""},),  # empty header
    ],
)
def test_jwtauthentication_returns_none_when_authorization_missing_or_empty(meta_header):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    jwt_auth = JWTAuthentication()
    request = SimpleNamespace(META=meta_header[0])

    # Act
    result = jwt_auth.authenticate(request)

    # Assert
    assert result is None
