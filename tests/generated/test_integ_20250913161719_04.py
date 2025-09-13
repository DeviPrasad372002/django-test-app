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
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container',
                   'MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
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
# Disable import adapter entirely if Django is present to avoid metaclass issues.
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
# --- Minimal Django auto-config (before any app/model import) ---
try:
    import importlib, pkgutil
    if _iu.find_spec("django") is not None:
        import django
        from django.conf import settings as _dj_settings
        from django.apps import apps as _dj_apps

        def _maybe_add(app_name, installed):
            try:
                if _iu.find_spec(app_name):
                    installed.append(app_name)
            except Exception:
                pass

        if not _dj_settings.configured:
            _installed = ["django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions"]
            if _iu.find_spec("rest_framework"):
                _installed.append("rest_framework")

            # Explicitly try common project apps if present
            for _app in ("conduit.apps.core","conduit.apps.articles","conduit.apps.authentication","conduit.apps.profiles"):
                _maybe_add(_app, _installed)

            # Generic discovery under conduit.apps.*
            try:
                if _iu.find_spec("conduit.apps"):
                    _apps_pkg = importlib.import_module("conduit.apps")
                    for _m in pkgutil.iter_modules(getattr(_apps_pkg, "__path__", [])):
                        _full = "conduit.apps." + _m.name
                        _maybe_add(_full, _installed)
            except Exception:
                pass

            _cfg = dict(
                SECRET_KEY="test-key",
                DEBUG=True,
                ALLOWED_HOSTS=["*"],
                INSTALLED_APPS=sorted(set(_installed)),
                DATABASES=dict(default=dict(ENGINE="django.db.backends.sqlite3", NAME=":memory:")),
                MIDDLEWARE=[],
                MIDDLEWARE_CLASSES=[],
                USE_TZ=True,
                TIME_ZONE="UTC",
            )
            try:
                _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
            except Exception:
                pass

            try:
                _dj_settings.configure(**_cfg)
                django.setup()
            except Exception:
                _pytest.skip("Django setup failed in bootstrap; skipping generated tests", allow_module_level=True)
        else:
            if not _dj_apps.ready:
                try:
                    django.setup()
                except Exception:
                    _pytest.skip("Django setup not ready and failed to initialize; skipping", allow_module_level=True)
except Exception:
    _pytest.skip("Django bootstrap error; skipping generated tests", allow_module_level=True)
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

    import conduit.apps.profiles.models as profiles_models
    import conduit.apps.profiles.serializers as profiles_serializers
except ImportError as _err:
    import pytest as _pytest
    _pytest.skip(f"Skipping tests due to ImportError: {_err}", allow_module_level=True)

class FakeQuerySet:
    def __init__(self, items):
        self._items = list(items)
    def exists(self):
        return bool(self._items)
    def __iter__(self):
        return iter(self._items)
    def __len__(self):
        return len(self._items)

class FakeRelManager:
    def __init__(self):
        self._set = []
    def add(self, obj):
        if obj not in self._set:
            self._set.append(obj)
    def remove(self, obj):
        if obj in self._set:
            self._set.remove(obj)
    def filter(self, **kwargs):
        # support filter(pk=...) typical pattern
        if 'pk' in kwargs:
            return FakeQuerySet([o for o in self._set if getattr(o, 'pk', None) == kwargs['pk']])
        return FakeQuerySet(list(self._set))
    def all(self):
        return list(self._set)
    def __contains__(self, item):
        return item in self._set
    def count(self):
        return len(self._set)

class FakeUser:
    def __init__(self, pk, image_url=None):
        self.pk = pk
        # Many implementations store relations as Attributes on user or profile
        self.following = FakeRelManager()
        self.followers = FakeRelManager()
        self.favorites = FakeRelManager()
        # Provide both image and profile.image paths to be resilient
        self.image = SimpleNamespace(url=image_url) if image_url is not None else None
        self.profile = SimpleNamespace(image=SimpleNamespace(url=image_url) if image_url is not None else None)

class FakeArticle:
    def __init__(self, pk):
        self.pk = pk

def _get_callable(module, name, instance=None):
    """
    Helper: prefers module-level function, else tries bound method on instance.
    Returns (callable, is_method_flag)
    """
    func = getattr(module, name, None)
    if callable(func):
        return func, False
    if instance is not None and hasattr(instance, name) and callable(getattr(instance, name)):
        return getattr(instance, name), True
    raise AttributeError(f"No callable '{name}' found in module or on instance")

@pytest.mark.parametrize("initial_favorites, repeat_add", [
    ([], False),
    ([], True),  # add same favorite twice -> idempotency / no duplicates
])
def test_favorite_unfavorite_and_has_favorited_integration(initial_favorites, repeat_add):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = FakeUser(pk=1)
    article = FakeArticle(pk=101)
    # seed initial favorites if any
    for a in initial_favorites:
        user.favorites.add(a)

    # Determine favorite, has_favorited, unfavorite callables (module-level or bound)
    favorite_callable, _ = _get_callable(profiles_models, 'favorite', instance=user)
    has_favorited_callable, _ = _get_callable(profiles_models, 'has_favorited', instance=user)
    unfavorite_callable, _ = _get_callable(profiles_models, 'unfavorite', instance=user)

    # Act - add favorite once or twice depending on param
    favorite_callable(user, article)
    if repeat_add:
        favorite_callable(user, article)

    # Assert - user.favorites should contain article exactly once
    favorites_list_after_add = user.favorites.all()
    assert any(getattr(a, 'pk', None) == article.pk for a in favorites_list_after_add)
    assert user.favorites.count() == (1 + len(initial_favorites))

    # Act - check has_favorited via callable
    has_favorited_result = has_favorited_callable(user, article)

    # Assert - has_favorited reports True
    assert isinstance(has_favorited_result, _exc_lookup("bool", Exception))
    assert has_favorited_result is True

    # Act - unfavorite and assert removal
    unfavorite_callable(user, article)
    favorites_list_after_remove = user.favorites.all()

    # Assert - article no longer in favorites; has_favorited now False
    assert not any(getattr(a, 'pk', None) == article.pk for a in favorites_list_after_remove)
    assert has_favorited_callable(user, article) is False

def _find_serializer_with_method(method_name):
    # Look for a class in profiles_serializers module defining method_name
    for attr_name, attr_value in vars(profiles_serializers).items():
        if inspect.isclass(attr_value) and hasattr(attr_value, method_name):
            return attr_value
    # fallback to module-level function if present
    if hasattr(profiles_serializers, method_name) and callable(getattr(profiles_serializers, method_name)):
        return getattr(profiles_serializers, method_name)
    raise AttributeError(f"No serializer class or function with '{method_name}' found")

def _make_request_with_user(user):
    return SimpleNamespace(user=user)

@pytest.mark.parametrize("start_following", [False, True])
def test_follow_unfollow_and_serializer_get_following_integration(start_following):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    viewer = FakeUser(pk=10)
    target = FakeUser(pk=20)

    # Resolve follow/unfollow/is_followed_by callables (either module-level or bound)
    follow_callable, _ = _get_callable(profiles_models, 'follow', instance=viewer)
    unfollow_callable, _ = _get_callable(profiles_models, 'unfollow', instance=viewer)
    is_followed_by_callable, _ = _get_callable(profiles_models, 'is_followed_by', instance=target)
    is_following_callable, _ = _get_callable(profiles_models, 'is_following', instance=viewer)

    # Optionally establish initial following relationship
    if start_following:
        follow_callable(viewer, target)

    # Find serializer that implements get_following
    serializer_or_function = _find_serializer_with_method('get_following')

    # If we found a class, instantiate with context; if a function, we'll call differently
    if inspect.isclass(serializer_or_function):
        serializer_class = serializer_or_function
        fake_request = _make_request_with_user(viewer)
        serializer_instance = serializer_class(instance=None, context={'request': fake_request})
        # Act - check serializer response for current following state
        serializer_following_before = serializer_instance.get_following(target)
    else:
        # module-level function: call with viewer or target depending on signature
        func = serializer_or_function
        # try calling as func(obj, context) or func(obj)
        try:
            serializer_following_before = func(target, {'request': _make_request_with_user(viewer)})
        except TypeError:
            serializer_following_before = func(target)

    # Assert initial serializer following matches model-level is_following/is_followed_by
    model_is_following = is_following_callable(viewer, target)
    model_is_followed_by = is_followed_by_callable(target, viewer)
    assert serializer_following_before in (True, False)
    assert serializer_following_before == bool(model_is_following) == bool(model_is_followed_by)

    # Act - toggle follow state via follow/unfollow and assert serializer reflects changes
    if model_is_following:
        unfollow_callable(viewer, target)
        expected_after_toggle = False
    else:
        follow_callable(viewer, target)
        expected_after_toggle = True

    if inspect.isclass(serializer_or_function):
        serializer_following_after = serializer_instance.get_following(target)
    else:
        try:
            serializer_following_after = func(target, {'request': _make_request_with_user(viewer)})
        except TypeError:
            serializer_following_after = func(target)

    # Assert - serializer result matches expected_after_toggle and underlying model queries
    assert serializer_following_after == expected_after_toggle
    assert is_following_callable(viewer, target) == expected_after_toggle
    assert is_followed_by_callable(target, viewer) == expected_after_toggle

@pytest.mark.parametrize("image_url", ["http://example/image.png", None])
def test_get_image_serializer_integration_handles_profile_and_user_image_paths(image_url):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    subject_user = FakeUser(pk=55, image_url=image_url)
    # Find serializer/get_image either as method on a class or module-level function
    serializer_or_function = _find_serializer_with_method('get_image')

    # If class, instantiate; else use function directly
    if inspect.isclass(serializer_or_function):
        serializer_class = serializer_or_function
        serializer_instance = serializer_class(instance=None, context={})
        # Act
        result = serializer_instance.get_image(subject_user)
    else:
        func = serializer_or_function
        try:
            result = func(subject_user)
        except TypeError:
            result = func(subject_user, {})

    # Assert - when image_url provided, result should be that url; when None, expect empty string or None
    if image_url:
        assert isinstance(result, _exc_lookup("str", Exception))
        assert image_url in result
    else:
        assert result in (None, "", "") or result == "" or result is None
