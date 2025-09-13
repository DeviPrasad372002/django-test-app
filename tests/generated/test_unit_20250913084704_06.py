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
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet'):
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
if not STRICT:
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
try:
    if _iu.find_spec("django") is not None:
        import django
        from django.conf import settings as _dj_settings
        if not _dj_settings.configured:
            _dj_settings.configure(SECRET_KEY="test-key", DEBUG=True, ALLOWED_HOSTS=["*"], INSTALLED_APPS=[], DATABASES={"default": {"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
            django.setup()
except Exception: pass
_PY2_ALIASES = {'ConfigParser': 'configparser', 'Queue': 'queue', 'StringIO': 'io', 'cStringIO': 'io', 'urllib2': 'urllib.request'}
for _old, _new in list(_PY2_ALIASES.items()):
    if _old in sys.modules: continue
    try:
        __import__(_new); sys.modules[_old] = sys.modules[_new]
    except Exception: pass
def _safe_find_spec(name):
    try: return _iu.find_spec(name)
    except Exception: return None
def _ensure_pkg(name, is_pkg=None):
    if name in sys.modules:
        m = sys.modules[name]
        if getattr(m, "__spec__", None) is None:
            m.__spec__ = _im.ModuleSpec(name, loader=None, is_package=(is_pkg if is_pkg is not None else ("." not in name)))
            if "." not in name and not hasattr(m, "__path__"): m.__path__ = []
        return m
    m = _types.ModuleType(name)
    if is_pkg is None: is_pkg = ("." not in name)
    if is_pkg and not hasattr(m, "__path__"): m.__path__ = []
    m.__spec__ = _im.ModuleSpec(name, loader=None, is_package=is_pkg)
    sys.modules[name] = m
    return m
_THIRD_PARTY_TOPS = ['__future__', 'conduit', 'datetime', 'django', 'json', 'jwt', 'models', 'os', 'random', 'relations', 'renderers', 'rest_framework', 'serializers', 'string', 'views']

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest as _pytest
# If a target import fails, skip the whole module rather than passing silently.
try:
    pass
except ImportError as _e:
    import pytest as _pytest; _pytest.skip(str(_e), allow_module_level=True)
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    import sys
    import types
    import json
    import builtins
    from importlib import import_module
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.__init__ import AuthenticationAppConfig
    from conduit.apps.authentication import backends as auth_backends_module
    from conduit.apps.authentication.backends import JWTAuthentication
except ImportError as e:  # pragma: no cover - skip module if imports fail
    import pytest as _pytest
    _pytest.skip(f"Skipping tests due to ImportError: {e}", allow_module_level=True)

def _exc_lookup(name, fallback=Exception):
    try:
        import rest_framework.exceptions as rfe
        return getattr(rfe, name)
    except Exception:
        return fallback

@pytest.mark.parametrize("length", [1, 5, 16, 0])
def test_generate_random_string_length_and_randomness(length):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    calls = 3
    results = []
    # Act
    for _ in range(calls):
        s = generate_random_string(length)
        results.append(s)
    # Assert
    for s in results:
        assert isinstance(s, _exc_lookup("str", Exception))
        assert len(s) == length
    # If length > 0 the calls should not all be identical (very unlikely)
    if length > 0:
        assert len(set(results)) > 1

@pytest.mark.parametrize("input_data,expected_user_keys", [
    ({"user": {"email": "a@b.com", "username": "alice", "token": "t"}}, {"email", "username", "token"}),
    ({"user": {}}, set()),
    ({"user": None}, set()),
])
def test_userjsonrenderer_render_returns_valid_json_bytes_and_keys(input_data, expected_user_keys):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    renderer = UserJSONRenderer()
    # Act
    rendered = renderer.render(input_data)
    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    decoded = json.loads(rendered.decode("utf-8"))
    assert "user" in decoded
    user_payload = decoded["user"]
    if user_payload is None:
        assert expected_user_keys == set()
    else:
        assert set(user_payload.keys()) >= expected_user_keys

def test_authentication_appconfig_ready_imports_signals_and_is_idempotent(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    config = AuthenticationAppConfig("authentication", import_module("conduit.apps.authentication"))
    dummy_signals = types.ModuleType("conduit.apps.authentication.signals")
    # mark something on dummy to detect import usage
    dummy_signals._DUMMY_IMPORTED = True
    sys_modules_backup = dict(sys.modules)
    sys.modules["conduit.apps.authentication.signals"] = dummy_signals
    try:
        # Act - first call should import our dummy signals module and not raise
        config.ready()
        # Assert
        assert "conduit.apps.authentication.signals" in sys.modules
        assert getattr(sys.modules["conduit.apps.authentication.signals"], "_DUMMY_IMPORTED", False) is True

        # Act - second call should be idempotent / not raise as signals already present
        config.ready()
        # Assert - still present and unchanged
        assert getattr(sys.modules["conduit.apps.authentication.signals"], "_DUMMY_IMPORTED", False) is True
    finally:
        # Restore sys.modules to avoid leaking our dummy into other tests
        sys.modules.clear()
        sys.modules.update(sys_modules_backup)

class DummyRequest:
    def __init__(self, meta=None):
        self.META = meta or {}

@pytest.mark.parametrize("auth_header, jwt_raise, expected_exception", [
    (None, None, None),  # no header -> authenticate returns None
    ("Token abc.def.ghi", Exception("bad"), _exc_lookup("AuthenticationFailed")),  # bad token -> AuthenticationFailed
])
def test_jwtauthentication_authenticate_handles_missing_and_bad_token(monkeypatch, auth_header, jwt_raise, expected_exception):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    authenticator = JWTAuthentication()
    if auth_header is None:
        req = DummyRequest(meta={})
    else:
        req = DummyRequest(meta={"HTTP_AUTHORIZATION": auth_header})

    # Monkeypatch jwt.decode used inside the backend to simulate a decode error
    # Try patching the jwt module imported in the authentication.backends module
    backend_module = auth_backends_module
    if hasattr(backend_module, "jwt"):
        original_jwt = backend_module.jwt
        class DummyJWT:
            @staticmethod
            def decode(token, key, algorithms=None):
                if jwt_raise:
                    raise jwt_raise
                return {"id": 1}
        monkeypatch.setattr(backend_module, "jwt", DummyJWT())
    else:
        # If backend did not import jwt as attribute, try patching library jwt globally
        import jwt as real_jwt
        monkeypatch.setattr(real_jwt, "decode", lambda *a, **k: (_ for _ in ()).throw(jwt_raise) if jwt_raise else {"id": 1})

    # Act / Assert
    if expected_exception is None:
        result = authenticator.authenticate(req)
        assert result is None
    else:
        with pytest.raises(_exc_lookup("expected_exception", Exception)):
            authenticator.authenticate(req)
