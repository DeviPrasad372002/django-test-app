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
    import string
    import json
    from types import SimpleNamespace

    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.core import exceptions as core_exceptions
    from conduit.apps.authentication import renderers as auth_renderers
    from rest_framework.exceptions import NotFound
    from rest_framework.response import Response
except ImportError as e:
    import pytest
    pytest.skip(str(e), allow_module_level=True)


@pytest.mark.parametrize("length", [0, 1, 10, 64])
def test_generate_random_string_returns_expected_length_and_charset(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    allowed_chars = set(string.ascii_letters + string.digits)

    # Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    # Each character should be alphanumeric
    assert set(result).issubset(allowed_chars)


def test_user_generate_jwt_token_calls_jwt_encode_with_user_id(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = getattr(auth_models, "User")()
    # Provide a simple numeric id that should be embedded in token payload
    setattr(user, "id", 42)

    captured = {}

    class StubJWT:
        def encode(self, payload, key, algorithm="HS256"):
            captured['payload'] = payload
            captured['key'] = key
            captured['algorithm'] = algorithm
            return "stubbed.jwt.token"

    monkeypatch.setattr(auth_models, "jwt", StubJWT())

    # Act
    token_value = user._generate_jwt_token()

    # Assert
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert token_value == "stubbed.jwt.token"
    assert 'payload' in captured and captured['payload'] is not None
    # Ensure user id is somewhere in the payload representation
    assert str(getattr(user, "id")) in json.dumps(captured['payload'], default=str)


def test_core_exception_handler_maps_not_found_and_generic_exceptions_to_responses():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    not_found_exc = NotFound("resource missing")
    generic_exc = Exception("unexpected error")

    # Act
    not_found_response = core_exceptions.core_exception_handler(not_found_exc, {})
    generic_response = core_exceptions.core_exception_handler(generic_exc, {})

    # Assert for NotFound
    assert isinstance(not_found_response, _exc_lookup("Response", Exception))
    assert getattr(not_found_response, "status_code", None) == 404
    assert isinstance(not_found_response.data, dict)

    # Assert for generic exception: expect a Response and 500-ish status
    assert isinstance(generic_response, _exc_lookup("Response", Exception))
    status_code_generic = getattr(generic_response, "status_code", None)
    assert status_code_generic is not None and 400 <= status_code_generic <= 599
    assert isinstance(generic_response.data, dict)


def test_authentication_renderer_renders_user_payload_to_json_bytes():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    data = {"user": {"email": "A@B.COM", "username": "tester"}}

    # Act
    rendered = auth_renderers.render(data, None, None)

    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    # JSON should contain the key "email" and the email value (case-insensitive check)
    assert b'"email"' in rendered
    assert b'a@b.com' in rendered.lower()
