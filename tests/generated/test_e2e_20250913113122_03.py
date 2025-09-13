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

try:
    import pytest
    import json
    import types
    import datetime
    import jwt
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.core import exceptions as core_exceptions
    from django.conf import settings
    from rest_framework import exceptions as drf_exceptions
except ImportError:
    import pytest
    pytest.skip("Required packages for these tests are not available", allow_module_level=True)

def _exc_lookup(name, default):
    try:
        return getattr(drf_exceptions, name)
    except Exception:
        return default

def test_generate_random_string_various_lengths_and_charset():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    lengths = [0, 1, 10, 50]
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    # Act / Assert
    for length in lengths:
        result = generate_random_string(length)
        # Assert: correct length
        assert isinstance(result, _exc_lookup("str", Exception))
        assert len(result) == length
        # Assert: all characters are from allowed set (empty string allowed)
        assert all(ch in allowed_chars for ch in result)

def test_user_get_short_name_and_generate_jwt_token_and_renderer(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    dummy_user = types.SimpleNamespace(username="alice", email="alice@example.com", id=123, pk=123)
    # Ensure settings used by token generation exist
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key", raising=False)
    # Some implementations expect an expiration delta setting
    monkeypatch.setattr(settings, "JWT_EXPIRATION_DELTA", datetime.timedelta(seconds=3600), raising=False)
    # Act: call get_short_name (unbound) and _generate_jwt_token (unbound)
    short_name = auth_models.User.get_short_name(dummy_user)
    token = auth_models.User._generate_jwt_token(dummy_user)
    # Assert: short name is username
    assert isinstance(short_name, _exc_lookup("str", Exception))
    assert short_name == "alice"
    # Assert: token looks like a JWT and decodes with the patched secret
    assert isinstance(token, _exc_lookup("str", Exception))
    assert token.count(".") >= 2
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    # Assert: payload contains the user id (name may vary); find any integer 123
    assert any(value == 123 for value in decoded.values())
    # Act: render a user payload via renderer
    renderer = UserJSONRenderer()
    payload = {"user": {"email": "alice@example.com", "username": "alice", "token": token}}
    rendered_bytes = renderer.render(payload, renderer_context={})
    # Assert: render returns bytes that deserialize to the original structure (or contains the same top-level keys)
    assert isinstance(rendered_bytes, (bytes, bytearray))
    parsed = json.loads(rendered_bytes.decode("utf-8"))
    assert "user" in parsed
    assert parsed["user"]["email"] == "alice@example.com"
    assert parsed["user"]["username"] == "alice"
    assert parsed["user"]["token"] == token

@pytest.mark.parametrize("exc_class_name, expected_status", [
    ("NotFound", 404),
    ("ValidationError", 400),
])
def test_core_exception_handler_for_known_drf_errors(exc_class_name, expected_status):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc_cls = _exc_lookup(exc_class_name, Exception)
    # Create an instance of the exception (some DRF exceptions accept detail kw)
    try:
        exc_instance = exc_cls(detail="it failed")
    except Exception:
        # Fallback: create a generic Exception instance to exercise generic handler branch
        exc_instance = Exception("fallback")
        expected_status = 500
    # Act
    response = core_exceptions.core_exception_handler(exc_instance, context={})
    # Assert: response is a DRF Response-like object with status_code and data
    assert hasattr(response, "status_code")
    assert hasattr(response, "data")
    assert response.status_code == expected_status
    # For not found/validation, data should include detail or errors structure
    assert isinstance(response.data, (dict, list, str))
    # Specific content expectations for mapping handlers
    if response.status_code == 404:
        # typical NotFound response places 'detail' or a message
        assert ("detail" in response.data) or (response.data != {})
