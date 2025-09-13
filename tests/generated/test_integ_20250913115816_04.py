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

import pytest

try:
    import inspect
    import types
    from conduit.apps import authentication as auth_pkg
    from conduit.apps.authentication import models as auth_models
    from conduit.apps import profiles as profiles_pkg
    from conduit.apps.profiles import models as profiles_models
    from conduit.apps.profiles import serializers as profiles_serializers
except ImportError as e:
    pytest.skip(f"Imports failed: {e}", allow_module_level=True)


def _find_class_with_method(module, method_name):
    for obj_name, obj in vars(module).items():
        if inspect.isclass(obj) and hasattr(obj, method_name):
            return obj
    raise LookupError(f"No class with method {method_name} found in {module}")


class FakeRelatedManager:
    def __init__(self, initial=None):
        self._set = set(initial or ())

    def add(self, item):
        self._set.add(item)

    def remove(self, item):
        self._set.discard(item)

    def all(self):
        return list(self._set)

    def __contains__(self, item):
        return item in self._set

    def count(self):
        return len(self._set)


def _maybe_call(value):
    if callable(value):
        return value()
    return value


def test_user_token_is_jwt_string_structure():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    UserClass = getattr(auth_models, "User", None)
    assert UserClass is not None
    user_instance = UserClass(username="alice", email="alice@example.com")

    # Act
    token_value = _maybe_call(getattr(user_instance, "token"))

    # Assert
    assert isinstance(token_value, _exc_lookup("str", Exception))
    parts = token_value.split(".")
    assert len(parts) == 3, "JWT token should have three parts separated by dots"


def test_follow_integration_with_serializer_get_following():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    profile_class = _find_class_with_method(profiles_models, "follow")
    assert hasattr(profile_class, "is_following"), "profile class must implement is_following"

    # build fake follower and followee objects with necessary managers
    follower = types.SimpleNamespace(
        following=FakeRelatedManager(),
        followers=FakeRelatedManager(),
        favorites=FakeRelatedManager(),
    )
    followee = types.SimpleNamespace(
        following=FakeRelatedManager(),
        followers=FakeRelatedManager(),
        favorites=FakeRelatedManager(),
    )

    # Act: have follower follow followee using the class method implementation
    follow_method = getattr(profile_class, "follow")
    follow_method(follower, followee)

    # attach an is_following callable to follower that delegates to the class implementation
    is_following_impl = getattr(profile_class, "is_following")
    follower.is_following = lambda other: is_following_impl(follower, other)

    # find a serializer class that implements get_following
    serializer_class = _find_class_with_method(profiles_serializers, "get_following")
    serializer_method = getattr(serializer_class, "get_following")

    fake_serializer = types.SimpleNamespace(context={"request": types.SimpleNamespace(user=follower)})

    # Act: call serializer method to determine if followee is followed by request.user
    result = serializer_method(fake_serializer, followee)

    # Assert
    assert result is True
    # also assert underlying relation is consistent
    assert followee in follower.following._set


@pytest.mark.parametrize("initially_favorited", [False, True])
def test_favorite_unfavorite_has_favorited_integration(initially_favorited):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fav_class = _find_class_with_method(profiles_models, "favorite")
    assert hasattr(fav_class, "has_favorited")
    assert hasattr(fav_class, "unfavorite")

    user = types.SimpleNamespace(
        following=FakeRelatedManager(),
        followers=FakeRelatedManager(),
        favorites=FakeRelatedManager(),
    )
    article = types.SimpleNamespace(slug="test-article")

    # if initially_favorited, pre-populate favorites
    if initially_favorited:
        user.favorites.add(article)

    # Act: favorite the article (should be idempotent)
    favorite_method = getattr(fav_class, "favorite")
    favorite_method(user, article)

    # Assert: has_favorited should be True after favorite
    has_fav_method = getattr(fav_class, "has_favorited")
    assert has_fav_method(user, article) is True

    # Act: unfavorite and assert removed
    unfavorite_method = getattr(fav_class, "unfavorite")
    unfavorite_method(user, article)

    # Assert: has_favorited should be False after unfavorite
    assert has_fav_method(user, article) is False
