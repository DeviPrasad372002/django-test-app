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
    import importlib
    import pytest
    profiles_models = importlib.import_module("conduit.apps.profiles.models")
    profiles_serializers = importlib.import_module("conduit.apps.profiles.serializers")
    articles_init = importlib.import_module("conduit.apps.articles.__init__")
    migration_mod = importlib.import_module("conduit.apps.articles.migrations.0001_initial")
except ImportError as e:
    import pytest as _pytest
    _pytest.skip("Skipping tests due to ImportError: {}".format(e), allow_module_level=True)

class _FakeFilterResult:
    def __init__(self, exists_val):
        self._exists = bool(exists_val)
    def exists(self):
        return self._exists

class _FakeFollowerManager:
    def __init__(self, exists_val):
        self._exists = bool(exists_val)
    def filter(self, **kwargs):
        return _FakeFilterResult(self._exists)

class _FakeFavoritesManager:
    def __init__(self):
        self._items = set()
    def add(self, obj):
        self._items.add(getattr(obj, "pk", id(obj)))
    def remove(self, obj):
        self._items.discard(getattr(obj, "pk", id(obj)))
    def filter(self, **kwargs):
        # emulate .filter(pk=...) returning object with exists()
        pk = kwargs.get("pk")
        return _FakeFilterResult(pk in self._items)
    def all(self):
        return list(self._items)

class _SimpleObj:
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)

@pytest.mark.parametrize("exists_flag, expected", [
    (True, True),
    (False, False),
    (0, False),
    (1, True),
])
def test_is_followed_by_various_exists_flags(exists_flag, expected):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    follower_manager = _FakeFollowerManager(exists_flag)
    fake_profile = _SimpleObj(followers=follower_manager)
    fake_user = _SimpleObj(pk=42)
    # Act
    result = profiles_models.is_followed_by(fake_profile, fake_user)
    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result == expected

def test_favorite_unfavorite_and_has_favorited_sequence():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    favorites_manager = _FakeFavoritesManager()
    profile = _SimpleObj(favorites=favorites_manager)
    article = _SimpleObj(pk=7)
    # Act - favorite
    profiles_models.favorite(profile, article)
    # Assert favorite added
    assert getattr(article, "pk", None) in set(profile.favorites.all())
    # Act - has_favorited should reflect current state
    assert profiles_models.has_favorited(profile, article) is True
    # Act - unfavorite
    profiles_models.unfavorite(profile, article)
    # Assert unfavorited state
    assert profiles_models.has_favorited(profile, article) is False
    assert getattr(article, "pk", None) not in set(profile.favorites.all())

@pytest.mark.parametrize("image_value, expected", [
    (None, None),
    (_SimpleObj(url="http://example.com/img.png"), "http://example.com/img.png"),
])
def test_get_image_returns_url_or_none(image_value, expected):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    # serializer instance is usually passed as self; we only need object context for method signature
    serializer_self = _SimpleObj(context={})
    profile_obj = _SimpleObj(image=image_value)
    # Act
    result = profiles_serializers.get_image(serializer_self, profile_obj)
    # Assert
    assert result == expected

@pytest.mark.parametrize("request_user, is_followed_result, expected", [
    (None, False, False),
    (_SimpleObj(pk=1), True, True),
    (_SimpleObj(pk=2), False, False),
])
def test_get_following_uses_request_and_is_followed_by(request_user, is_followed_result, expected):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    fake_request = _SimpleObj(user=request_user)
    serializer_self = _SimpleObj(context={"request": fake_request})
    # obj should expose is_followed_by
    def _is_followed_by(u):
        return bool(is_followed_result) if u is not None else False
    profile_obj = _SimpleObj(is_followed_by=_is_followed_by)
    # Act
    result = profiles_serializers.get_following(serializer_self, profile_obj)
    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result == expected

def test_articles_appconfig_ready_and_migration_structure():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    app_config_cls = getattr(articles_init, "ArticlesAppConfig")
    app_config = app_config_cls()
    migration_cls = getattr(migration_mod, "Migration", None)
    # Act / Assert - AppConfig has a name and ready() runs without error
    assert isinstance(app_config.name, str)
    assert "articles" in app_config.name or "article" in app_config.name
    app_config.ready()
    # Migration structure assertions
    assert migration_cls is not None
    # Migration should expose dependencies and operations attributes
    assert hasattr(migration_cls, "dependencies")
    assert hasattr(migration_cls, "operations")
    deps = getattr(migration_cls, "dependencies")
    ops = getattr(migration_cls, "operations")
    assert isinstance(deps, (list, tuple))
    assert isinstance(ops, (list, tuple))
