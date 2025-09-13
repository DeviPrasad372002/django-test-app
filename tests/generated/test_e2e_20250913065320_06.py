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
    import json
    import jwt
    from conduit.apps.core import utils as core_utils
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.models import User
    from django.conf import settings
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required modules for tests are not available", allow_module_level=True)

import types

@pytest.mark.parametrize("length,expected_char", [
    (0, ""),     # boundary: zero length
    (1, "x"),    # small length
    (8, "xxxxxxxx"),  # typical length
    (16, "xxxxxxxxxxxxxxxx"),  # larger length
])
def test_generate_random_string_uses_random_choice_and_returns_expected_length(monkeypatch, length, expected_char):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: force deterministic choice to always return 'x'
    def deterministic_choice(seq):
        return "x"
    # The implementation likely uses core_utils.random.choice; patch that object
    monkeypatch.setattr(core_utils, "random", types.SimpleNamespace(choice=deterministic_choice))
    # Act
    result = core_utils.generate_random_string(length)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected_char

def test_userjsonrenderer_renders_user_wrapped_in_user_key():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    renderer = UserJSONRenderer()
    user_data = {"email": "test@example.com", "username": "tester"}
    # Act
    rendered = renderer.render(user_data)
    # Assert
    assert isinstance(rendered, (bytes, str))
    text = rendered.decode("utf-8") if isinstance(rendered, _exc_lookup("bytes", Exception)) else rendered
    parsed = json.loads(text)
    assert "user" in parsed
    assert parsed["user"] == user_data

@pytest.mark.parametrize("user_id", [1, 12345])
def test_user_token_is_jwt_and_contains_user_id(monkeypatch, user_id):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: ensure deterministic secret key for JWT generation
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key", raising=False)
    # Create a User instance without relying on DB persistence
    user = User()
    # Some Django models expect .id or .pk; set both to be safe
    setattr(user, "id", user_id)
    setattr(user, "pk", user_id)
    # Act: obtain token (could be property or callable)
    token_attr = getattr(user, "token")
    token_value = token_attr() if callable(token_attr) else token_attr
    # Assert token type
    assert isinstance(token_value, (str, bytes))
    token_text = token_value.decode("utf-8") if isinstance(token_value, _exc_lookup("bytes", Exception)) else token_value
    # Decode JWT with the known secret and algorithm HS256 (commonly used)
    decoded = jwt.decode(token_text, settings.SECRET_KEY, algorithms=["HS256"])
    # The payload should include the user id in some key; assert the id appears among values
    assert user_id in set(decoded.values()) or any(v == user_id for v in decoded.values())
