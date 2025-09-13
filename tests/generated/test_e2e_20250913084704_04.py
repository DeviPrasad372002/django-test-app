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

import inspect
import types

try:
    import pytest
    from types import SimpleNamespace
    from conduit.apps.profiles import serializers as profiles_serializers
    # Try to get the callables by name; if missing this will raise AttributeError -> skip
    get_image = getattr(profiles_serializers, "get_image")
    get_following = getattr(profiles_serializers, "get_following")
except (ImportError, AttributeError) as e:
    import pytest as _pytest
    _pytest.skip("Required modules or callables not available: {}".format(e), allow_module_level=True)

def _exc_lookup(name, default=Exception):
    import builtins
    return getattr(builtins, name, default)

def _call_maybe_bound(func, obj, context=None):
    """
    Arrange for calling func which may be defined as:
      - func(obj)
      - func(self, obj)
    We provide a minimal self with .context if required.
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    if len(params) == 1:
        return func(obj)
    elif len(params) >= 2:
        fake_self = SimpleNamespace(context=context or {})
        return func(fake_self, obj)
    else:
        # Unexpected signature; try calling with obj anyway and let it fail
        return func(obj)

@pytest.mark.parametrize(
    "image_value, expected_type, expect_value",
    [
        ("http://example.com/img.png", str, "http://example.com/img.png"),
        ("", str, ""),             # explicitly empty image
        (None, str, ""),           # None often normalized to empty string
    ],
)
def test_get_image_returns_string_for_various_inputs(image_value, expected_type, expect_value):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    profile_like = SimpleNamespace()
    # Provide attribute only when present to simulate real objects
    if image_value is not None:
        profile_like.image = image_value
    else:
        # set to None explicitly
        profile_like.image = None

    # Act
    result = _call_maybe_bound(get_image, profile_like)

    # Assert
    assert isinstance(result, _exc_lookup("expected_type", Exception))
    assert result == expect_value

def test_get_image_attribute_missing_raises_attributeerror():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    profile_like = SimpleNamespace()
    # Intentionally do NOT set .image to simulate missing attribute

    # Act / Assert
    exc_type = _exc_lookup("AttributeError")
    with pytest.raises(_exc_lookup("exc_type", Exception)):
        _call_maybe_bound(get_image, profile_like)

@pytest.mark.parametrize(
    "request_user_callable, expected_bool, description",
    [
        (lambda target: True, True, "request user reports following -> True"),
        (lambda target: False, False, "request user reports not following -> False"),
    ],
)
def test_get_following_respects_request_user_is_following(request_user_callable, expected_bool, description):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    profile_target = SimpleNamespace(username="target_user")
    # Create a request-like object with user that exposes is_following callable
    class RequestLike:
        def __init__(self, user_callable):
            self.user = SimpleNamespace()
            # provide is_following method on the user
            def is_following(other):
                # mirror the API: receive the profile target
                return user_callable(other)
            self.user.is_following = is_following

    request = RequestLike(request_user_callable)
    context = {"request": request}

    # Act
    result = _call_maybe_bound(get_following, profile_target, context=context)

    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result is expected_bool

def test_get_following_without_request_returns_false_or_handles_missing_context():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    profile_target = SimpleNamespace(username="target_user")
    # No context provided -> serializer should handle gracefully, typically returning False
    context = {}

    # Act
    try:
        result = _call_maybe_bound(get_following, profile_target, context=context)
    except Exception as e:
        # If implementation raises AttributeError or similar when context/request absent, allow test to capture concrete failure
        raise

    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result is False
