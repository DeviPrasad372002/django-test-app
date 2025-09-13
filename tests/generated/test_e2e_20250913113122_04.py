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
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from types import SimpleNamespace
    import inspect
    import conduit.apps.profiles.serializers as profiles_serializers
    import conduit.apps.profiles.models as profiles_models
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required modules for profile tests not available", allow_module_level=True)


def _locate_callable(container, name):
    # Try module-level attribute first
    if hasattr(container, name) and callable(getattr(container, name)):
        return getattr(container, name)
    # Then search classes defined in the module
    for _, member in inspect.getmembers(container, inspect.isclass):
        if hasattr(member, name) and callable(getattr(member, name)):
            return getattr(member, name)
    raise AttributeError(f"Callable {name!r} not found in {container!r}")


def _make_self_with_context(user=None):
    # Minimal serializer-like self with a context holding a request with a user
    return SimpleNamespace(context={"request": SimpleNamespace(user=user)})


def _make_user_stub(username="user", extra_attrs=None):
    extra_attrs = extra_attrs or {}
    attrs = {"username": username}
    attrs.update(extra_attrs)
    return SimpleNamespace(**attrs)


def _make_article_stub(id=1, slug="a-slug"):
    return SimpleNamespace(id=id, slug=slug)


def _ensure_collection_attributes(obj, names):
    for name in names:
        if not hasattr(obj, name):
            setattr(obj, name, set())


def test_get_image_returns_string_and_handles_missing_image():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    get_image = _locate_callable(profiles_serializers, "get_image")
    serializer_self = SimpleNamespace()  # minimal self for unbound method call
    profile_with_image = SimpleNamespace(image="http://example.org/pic.png")
    profile_with_no_image = SimpleNamespace(image=None)

    # Act
    result_with_image = get_image(serializer_self, profile_with_image)
    result_without_image = get_image(serializer_self, profile_with_no_image)

    # Assert
    assert isinstance(result_with_image, _exc_lookup("str", Exception))
    assert result_with_image == "http://example.org/pic.png"
    assert isinstance(result_without_image, _exc_lookup("str", Exception))
    assert result_without_image == ""


@pytest.mark.parametrize("is_following_value", [True, False])
def test_get_following_reflects_user_follow_state(is_following_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    get_following = _locate_callable(profiles_serializers, "get_following")
    request_user = _make_user_stub(username="alice")
    serializer_self = _make_self_with_context(user=request_user)
    profile_user = _make_user_stub(username="bob")

    # Provide a user method that the serializer will call to check following state
    setattr(profile_user, "is_followed_by", lambda other: bool(is_following_value))
    profile_obj = SimpleNamespace(user=profile_user)

    # Act
    result = get_following(serializer_self, profile_obj)

    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result is bool(is_following_value)


def test_favorite_unfavorite_and_has_favorited_workflow():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    favorite = _locate_callable(profiles_models, "favorite")
    unfavorite = _locate_callable(profiles_models, "unfavorite")
    has_favorited = _locate_callable(profiles_models, "has_favorited")

    profile_owner = SimpleNamespace(username="author")
    article = _make_article_stub(id=42)
    # Create a minimal "self" object that will act like a profile/user with collection attributes
    actor = SimpleNamespace(username="reader")
    _ensure_collection_attributes(actor, ["favorites", "favorited", "favorites_set", "favorited_set", "favorites_rel"])

    # Some implementations may expect attribute named 'favorites' or 'favorited'; ensure both exist and alias to same set
    canonical_set = set()
    actor.favorites = canonical_set
    actor.favorited = canonical_set

    # Act: favorite the article
    favorite(actor, article)
    after_favorite_check = has_favorited(actor, article)

    # Act: unfavorite the article
    unfavorite(actor, article)
    after_unfavorite_check = has_favorited(actor, article)

    # Assert
    assert isinstance(after_favorite_check, _exc_lookup("bool", Exception))
    assert after_favorite_check is True
    assert isinstance(after_unfavorite_check, _exc_lookup("bool", Exception))
    assert after_unfavorite_check is False
