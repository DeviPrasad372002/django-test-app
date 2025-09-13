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
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
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
    from types import SimpleNamespace
    from conduit.apps.profiles import serializers as profiles_serializers
except ImportError:
    import pytest
    pytest.skip("Skipping tests because required modules are not importable", allow_module_level=True)


@pytest.mark.parametrize(
    "input_image, expected_output",
    [
        ("http://example.com/pic.png", "http://example.com/pic.png"),  # normal case: explicit image URL
        ("", ""),  # boundary: empty string should round-trip as string
        (None, ""),  # edge: None should be normalized to empty string
    ],
)
def test_profile_serializer_get_image_returns_string_for_various_inputs(input_image, expected_output):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    ProfileSerializer = getattr(profiles_serializers, "ProfileSerializer")
    get_image = getattr(ProfileSerializer, "get_image")
    fake_self = SimpleNamespace(context={})
    profile_obj = SimpleNamespace(image=input_image)

    # Act
    result = get_image(fake_self, profile_obj)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected_output


@pytest.mark.parametrize(
    "context_request, user_is_anonymous, user_is_following_return, expected_following",
    [
        (None, True, False, False),  # no request in context -> not following
        (SimpleNamespace(user=SimpleNamespace(is_anonymous=True, is_following=lambda o: False)), True, False, False),  # anonymous user -> not following
        (SimpleNamespace(user=SimpleNamespace(is_anonymous=False, is_following=lambda o: True)), False, True, True),  # authenticated and is_following -> True
        (SimpleNamespace(user=SimpleNamespace(is_anonymous=False, is_following=lambda o: False)), False, False, False),  # authenticated but not following -> False
    ],
)
def test_profile_serializer_get_following_respects_request_context_and_user_methods(
    # Arrange-Act-Assert: generated by ai-testgen
    context_request, user_is_anonymous, user_is_following_return, expected_following
):
    # Arrange
    ProfileSerializer = getattr(profiles_serializers, "ProfileSerializer")
    get_following = getattr(ProfileSerializer, "get_following")

    # Build fake self with a context that may or may not include a request
    if context_request is None:
        fake_self = SimpleNamespace(context={})
    else:
        fake_self = SimpleNamespace(context={"request": context_request})

    # Target object can be any simple object; methods above delegate to user.is_following
    profile_obj = SimpleNamespace(username="target")

    # Act
    result = get_following(fake_self, profile_obj)

    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result is expected_following


def test_profile_serializer_get_following_calls_user_is_following_when_authenticated(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    ProfileSerializer = getattr(profiles_serializers, "ProfileSerializer")
    get_following = getattr(ProfileSerializer, "get_following")

    called = {"count": 0, "last_arg": None}

    def fake_is_following(obj):
        called["count"] += 1
        called["last_arg"] = obj
        return True

    fake_user = SimpleNamespace(is_anonymous=False, is_following=fake_is_following)
    fake_request = SimpleNamespace(user=fake_user)
    fake_self = SimpleNamespace(context={"request": fake_request})
    profile_obj = SimpleNamespace(pk=123)

    # Act
    result = get_following(fake_self, profile_obj)

    # Assert
    assert result is True
    assert called["count"] == 1
    assert called["last_arg"] is profile_obj
