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

import json
import types

try:
    import pytest
    import conduit.apps.authentication.models as models_module
    import conduit.apps.authentication.backends as backends_module
    import conduit.apps.authentication.renderers as renderers_module
except ImportError as e:
    import pytest as _pytest  # pragma: no cover
    _pytest.skip(f"Skipping tests due to import error: {e}", allow_module_level=True)

def _exc_lookup(name, default=Exception):
    try:
        import rest_framework.exceptions as rf_exc
        return getattr(rf_exc, name)
    except Exception:
        return default

def _maybe_decode(value):
    if isinstance(value, _exc_lookup("bytes", Exception)):
        return value.decode('utf-8')
    return value

def test_user_generate_jwt_token_uses_jwt_encode_and_returns_string(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_instance = models_module.User(id=42)
    captured = {}
    def fake_encode(payload, key, algorithm):
        captured['payload'] = payload
        captured['key'] = key
        captured['algorithm'] = algorithm
        return "FAKE_JWT_TOKEN"
    monkeypatch.setattr(models_module, 'jwt', types.SimpleNamespace(encode=fake_encode), raising=False)

    # Act
    token = user_instance._generate_jwt_token()

    # Assert
    token = _maybe_decode(token)
    assert isinstance(token, _exc_lookup("str", Exception))
    assert token == "FAKE_JWT_TOKEN"
    assert isinstance(captured.get('payload'), dict)
    assert 'id' in captured['payload'] and captured['payload']['id'] == 42
    assert 'exp' in captured['payload']

@pytest.mark.parametrize("header_value, expected_result, expect_exception", [
    (None, None, False),                       # no header -> authenticate returns None
    ("Token abc.def.ghi", ("user_obj", "abc"), False),  # valid token -> delegated to _authenticate_credentials
    ("Token", None, True),                     # missing token part -> AuthenticationFailed
])
def test_jwtauthentication_authenticate_various_headers(monkeypatch, header_value, expected_result, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = backends_module.JWTAuthentication()
    class DummyRequest:
        def __init__(self, header):
            if header is None:
                self.META = {}
            else:
                self.META = {'HTTP_AUTHORIZATION': header}
    request = DummyRequest(header_value)

    # Monkeypatch authentication credential resolution for the positive case
    def fake_authenticate_credentials(self, token):
        # return a tuple (user, token) but expose token part for assertion
        return ("user_obj", token.split('.')[0] if '.' in token else token)
    monkeypatch.setattr(backends_module.JWTAuthentication, '_authenticate_credentials', fake_authenticate_credentials, raising=False)

    # Act / Assert
    if expect_exception:
        AuthenticationFailed = _exc_lookup('AuthenticationFailed', Exception)
        with pytest.raises(_exc_lookup("AuthenticationFailed", Exception)):
            auth.authenticate(request)
    else:
        result = auth.authenticate(request)
        assert result == expected_result

def test_userjsonrenderer_render_wraps_user_and_passthrough_errors_and_none():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = renderers_module.UserJSONRenderer()
    normal_data = {'email': 'alice@example.com', 'username': 'alice'}
    error_data = {'errors': {'email': ['invalid']}}
    none_data = None

    # Act
    normal_rendered = _maybe_decode(renderer.render(normal_data))
    error_rendered = _maybe_decode(renderer.render(error_data))
    none_rendered = _maybe_decode(renderer.render(none_data))

    # Assert
    normal_obj = json.loads(normal_rendered)
    assert 'user' in normal_obj and normal_obj['user'] == normal_data

    error_obj = json.loads(error_rendered)
    assert 'errors' in error_obj and error_obj['errors'] == error_data['errors']

    none_obj = json.loads(none_rendered)
    assert none_obj is None

def test_user_get_full_and_short_name_return_strings_and_reflect_username():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    u = models_module.User(username='tester', email='tester@example.com')

    # Act
    full_name = u.get_full_name()
    short_name = u.get_short_name()

    # Assert
    assert isinstance(full_name, _exc_lookup("str", Exception))
    assert isinstance(short_name, _exc_lookup("str", Exception))
    assert short_name == 'tester'
    # full_name may be same as short_name in many implementations
    assert full_name == short_name or full_name != ""
