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
_ALL_MODULES = ['__future__', 'conduit.apps.articles.signals', 'conduit.apps.authentication.signals', 'conduit.apps.core.models', 'conduit.apps.core.renderers', 'conduit.apps.core.utils', 'conduit.apps.profiles.models', 'conduit.apps.profiles.serializers', 'datetime', 'django.apps', 'django.conf', 'django.conf.urls', 'django.contrib', 'django.contrib.auth', 'django.contrib.auth.models', 'django.core.wsgi', 'django.db', 'django.db.models.deletion', 'django.db.models.signals', 'django.dispatch', 'django.utils.text', 'json', 'jwt', 'models', 'os', 'random', 'relations', 'renderers', 'rest_framework', 'rest_framework.exceptions', 'rest_framework.generics', 'rest_framework.permissions', 'rest_framework.renderers', 'rest_framework.response', 'rest_framework.routers', 'rest_framework.views', 'serializers', 'string', 'views']
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
# Disable the adapter around Django to avoid metaclass/__classcell__ issues.
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
# Minimal Django setup with detected apps
try:
    if _DJ_PRESENT:
        import django
        from django.conf import settings as _dj_settings
        if not _dj_settings.configured:
            _dj_apps = set()
            for m in list(_ALL_MODULES):
                if m.startswith("conduit.apps."):
                    parts = m.split(".")
                    if len(parts) >= 3:
                        _dj_apps.add(".".join(parts[:3]))  # conduit.apps.<app>
            _installed = ["django.contrib.auth","django.contrib.contenttypes"]
            if "rest_framework" in _ALL_MODULES:
                _installed.append("rest_framework")
            _installed += sorted(_dj_apps)
            _cfg = dict(
                SECRET_KEY="test-key",
                DEBUG=True,
                ALLOWED_HOSTS=["*"],
                INSTALLED_APPS=_installed,
                DATABASES={"default": {"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}},
                MIDDLEWARE=[],
                USE_TZ=True,
                TIME_ZONE="UTC",
                DEFAULT_AUTO_FIELD="django.db.models.AutoField",
            )
            # If a custom auth app exists, set AUTH_USER_MODEL
            if any(a.endswith(".authentication") for a in _installed):
                _cfg["AUTH_USER_MODEL"] = "authentication.User"
            _dj_settings.configure(**_cfg)
            django.setup()
except Exception as _dj_e:
    pass
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
    import conduit.apps.articles.relations as relations
    import conduit.apps.articles.models as articles_models
    import conduit.apps.profiles.models as profiles_models
    import conduit.apps.profiles.serializers as profiles_serializers
except ImportError as e:
    import pytest  # re-import to satisfy linter if skipped
    pytest.skip("Required modules not available: {}".format(e), allow_module_level=True)

def _exc_lookup(name, default=Exception):
    # try common exception modules for the given name
    for module_name in ("rest_framework.exceptions", "django.core.exceptions", "exceptions"):
        try:
            module = __import__(module_name, fromlist=[name])
            exc = getattr(module, name, None)
            if exc:
                return exc
        except Exception:
            continue
    return default

class _FavoritesProxy:
    def __init__(self):
        self._set = set()
    def add(self, item):
        self._set.add(item)
    def remove(self, item):
        self._set.remove(item)
    def __contains__(self, item):
        return item in self._set
    def all(self):
        return list(self._set)

@pytest.mark.parametrize("tag_name", ["python", "django", ""])
def test_tagrelatedfield_to_representation_and_to_internal_value_happy_path(monkeypatch, tag_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    field_cls = getattr(relations, "TagRelatedField", None)
    assert field_cls is not None, "TagRelatedField missing from relations module"
    field = field_cls()
    fake_tag_obj = SimpleNamespace(name=tag_name)

    # Act / Assert: to_representation should return the tag's name
    rep = field.to_representation(fake_tag_obj)
    assert isinstance(rep, _exc_lookup("str", Exception))
    assert rep == tag_name

    # Arrange monkeypatch for Tag.objects.get_or_create used in to_internal_value
    def fake_get_or_create(name, defaults=None, **kwargs):
        return (SimpleNamespace(name=name), True)
    monkeypatch.setattr(relations, "Tag", SimpleNamespace(objects=SimpleNamespace(get_or_create=fake_get_or_create)))

    # Act
    internal = field.to_internal_value(tag_name)

    # Assert
    assert hasattr(internal, "name")
    assert internal.name == tag_name

def test_tagrelatedfield_to_internal_value_invalid_type_raises_validation_error():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    field_cls = getattr(relations, "TagRelatedField", None)
    assert field_cls is not None
    field = field_cls()

    # Act / Assert: passing a non-string should raise a ValidationError-like exception
    ValidationError = _exc_lookup("ValidationError", ValueError)
    with pytest.raises(_exc_lookup("ValidationError", Exception)):
        field.to_internal_value(12345)  # invalid input type

def test_favorite_unfavorite_has_favorited_state_changes_and_idempotency():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    favorite_fn = getattr(profiles_models, "favorite", None)
    unfavorite_fn = getattr(profiles_models, "unfavorite", None)
    has_favorited_fn = getattr(profiles_models, "has_favorited", None)

    # Fallback if defined as methods on a Profile class
    if favorite_fn is None or unfavorite_fn is None or has_favorited_fn is None:
        ProfileCls = getattr(profiles_models, "Profile", None)
        assert ProfileCls is not None, "Profile or favorite/unfavorite functions must exist"
        if favorite_fn is None:
            favorite_fn = getattr(ProfileCls, "favorite")
        if unfavorite_fn is None:
            unfavorite_fn = getattr(ProfileCls, "unfavorite")
        if has_favorited_fn is None:
            has_favorited_fn = getattr(ProfileCls, "has_favorited")

    favorites_proxy = _FavoritesProxy()
    fake_profile = SimpleNamespace(favorites=favorites_proxy)
    fake_article = SimpleNamespace(id=1, slug="test-article")

    # Act: favorite the article
    favorite_fn(fake_profile, fake_article)
    # Assert: now has_favorited should reflect True
    assert has_favorited_fn(fake_profile, fake_article) is True

    # Act: unfavorite the article
    unfavorite_fn(fake_profile, fake_article)
    # Assert: now has_favorited should reflect False
    assert has_favorited_fn(fake_profile, fake_article) is False

    # Act / Assert: calling unfavorite again should not raise (idempotent)
    try:
        unfavorite_fn(fake_profile, fake_article)
    except Exception as exc:
        pytest.fail(f"unfavorite raised an unexpected exception on idempotent call: {exc}")

@pytest.mark.parametrize("is_followed_value", [True, False])
def test_get_following_uses_profile_is_followed_by(monkeypatch, is_followed_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: locate get_following callable either at module level or on serializer classes
    get_following = getattr(profiles_serializers, "get_following", None)
    serializer_instance = None
    if get_following is None:
        # search for a class that defines get_following
        for attr_name in dir(profiles_serializers):
            candidate = getattr(profiles_serializers, attr_name)
            if hasattr(candidate, "get_following") and callable(getattr(candidate, "get_following")):
                get_following = getattr(candidate, "get_following")
                # create a lightweight instance-like object to act as self
                try:
                    serializer_instance = candidate()
                except Exception:
                    serializer_instance = SimpleNamespace()
                break
    else:
        # module-level function, self not required; create dummy
        serializer_instance = SimpleNamespace()

    assert callable(get_following), "get_following callable not found in profiles.serializers"

    fake_user = SimpleNamespace(username="u1")
    fake_request = SimpleNamespace(user=fake_user)
    # the serializer's context is often used to access the request
    serializer_self = serializer_instance if serializer_instance is not None else SimpleNamespace()
    setattr(serializer_self, "context", {"request": fake_request})

    # Profile will expose is_followed_by(user) typically
    fake_profile = SimpleNamespace(is_followed_by=lambda user: is_followed_value)

    # Act
    result = get_following(serializer_self, fake_profile)

    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result == is_followed_value
