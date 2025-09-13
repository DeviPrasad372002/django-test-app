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

import sys
import types

try:
    import pytest
    from types import SimpleNamespace
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.core.exceptions import _handle_generic_error
    from conduit.apps.profiles.serializers import get_image
    from conduit.apps.profiles.models import favorite, unfavorite, has_favorited
except ImportError:
    import pytest
    pytest.skip("Required modules for these tests are not available", allow_module_level=True)


def _exc_lookup(name, fallback):
    return getattr(sys.modules.get('builtins'), name, fallback)


@pytest.mark.parametrize("length", [0, 1, 8, 32])
def test_generate_random_string_length_and_characters(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    requested_length = length
    # Act
    result = generate_random_string(requested_length)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == requested_length
    # every character should be alphanumeric (typical implementations use letters/digits)
    assert all(ch.isalnum() for ch in result)


def test_generate_random_string_negative_raises_valueerror():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    bad_length = -5
    # Act / Assert
    with pytest.raises(_exc_lookup('ValueError', Exception)):
        generate_random_string(bad_length)


def test_handle_generic_error_returns_response_with_errors_key_and_status():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc = Exception("simulated failure")
    context = {}
    # Act
    response = _handle_generic_error(exc, context)
    # Assert
    # Response object from DRF should expose status_code and data
    assert hasattr(response, "status_code")
    assert isinstance(response.status_code, int)
    assert hasattr(response, "data")
    assert isinstance(response.data, dict)
    # Expect some top-level 'errors' information to be present for generic handler
    assert "errors" in response.data


@pytest.mark.parametrize(
    "initial_image, expected_exact",
    [
        ("http://example.com/avatar.png", "http://example.com/avatar.png"),
        ("", ""),  # explicit empty image should be returned as-is if present
        (None, None),  # no image -> implementation may return None
    ],
)
def test_get_image_with_various_profile_shapes(initial_image, expected_exact):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    profile_obj = SimpleNamespace(image=initial_image)
    user_obj = SimpleNamespace(profile=profile_obj)
    # Act
    result = get_image(user_obj)
    # Assert: if image value set, expect same value; if None allow None (concrete check)
    assert result == expected_exact


class _FakeFavorites:
    def __init__(self):
        self._items = []

    def add(self, item):
        if item not in self._items:
            self._items.append(item)

    def remove(self, item):
        if item in self._items:
            self._items.remove(item)

    def all(self):
        # mimic Django queryset .all()
        return list(self._items)

    def __contains__(self, item):
        return item in self._items


def test_favorite_unfavorite_and_has_favorited_flow():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article = SimpleNamespace(slug="test-article")
    favorites = _FakeFavorites()
    profile = SimpleNamespace(favorites=favorites)
    # Act - favorite
    favorite(profile, article)
    # Assert - after favoriting, article should be present
    assert article in profile.favorites.all()
    assert has_favorited(profile, article) is True
    # Act - unfavorite
    unfavorite(profile, article)
    # Assert - after unfavoriting, article should not be present
    assert article not in profile.favorites.all()
    assert has_favorited(profile, article) is False
