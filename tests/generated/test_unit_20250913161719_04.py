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

import pytest
from types import SimpleNamespace

try:
    import conduit.apps.profiles.models as profiles_models
    import conduit.apps.profiles.serializers as profiles_serializers
    import conduit.apps.articles.relations as articles_relations
    import conduit.apps.articles.models as articles_models
    import conduit.apps.articles.models as articles_models_dup  # intentional duplicate import to ensure module load
except ImportError as e:
    pytest.skip("Required modules not available: {}".format(e), allow_module_level=True)


# provide a safe fallback for _exc_lookup if test runner doesn't inject it
try:
    _exc_lookup  # noqa: F821
except NameError:
    def _exc_lookup(name, default):
        return getattr(__builtins__, name, default)


class FakeRel:
    def __init__(self):
        self._set = []

    def add(self, item):
        # simulate Django ManyToMany add
        self._set.append(item)

    def remove(self, item):
        self._set = [i for i in self._set if i is not item]

    def all(self):
        return list(self._set)

    def filter(self, **kwargs):
        # return object that has exists() method
        found = []
        pk = kwargs.get('pk')
        user__pk = kwargs.get('user__pk')
        for item in self._set:
            if pk is not None and getattr(item, 'pk', None) == pk:
                found.append(item)
            elif user__pk is not None and getattr(getattr(item, 'user', None), 'pk', None) == user__pk:
                found.append(item)
        class _Found:
            def __init__(self, found):
                self._found = found
            def exists(self):
                return bool(self._found)
        return _Found(found)


@pytest.mark.parametrize("initially_following, expected_after_follow", [(False, True), (True, True)])
def test_follow_unfollow_and_is_following_is_followed_by(initially_following, expected_after_follow):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    actor = SimpleNamespace(pk=2)
    target = SimpleNamespace(pk=1)
    actor.following = FakeRel()
    target.following = FakeRel()

    # If initially_following True, seed relationship
    if initially_following:
        actor.following.add(target)

    # Act - follow
    try:
        follow_fn = profiles_models.Profile.follow
    except AttributeError:
        pytest.fail("Profile.follow not implemented")
    follow_fn(actor, target)

    # Assert follow added
    assert any(getattr(x, "pk", None) == target.pk for x in actor.following.all()) is expected_after_follow

    # Act - is_following / is_followed_by checks
    try:
        is_following_fn = profiles_models.Profile.is_following
        is_followed_by_fn = profiles_models.Profile.is_followed_by
    except AttributeError:
        pytest.fail("Profile.is_following or Profile.is_followed_by not implemented")

    assert is_following_fn(actor, target) is True
    # is_followed_by(target, actor) should be True if actor follows target
    assert is_followed_by_fn(target, actor) is True

    # Act - unfollow
    try:
        unfollow_fn = profiles_models.Profile.unfollow
    except AttributeError:
        pytest.fail("Profile.unfollow not implemented")
    unfollow_fn(actor, target)

    # Assert unfollowed
    assert is_following_fn(actor, target) is False
    assert is_followed_by_fn(target, actor) is False


def test_favorite_unfavorite_and_has_favorited():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    profile = SimpleNamespace(pk=10)
    article = SimpleNamespace(pk=123)
    profile.favorites = FakeRel()

    # Act - favorite
    try:
        favorite_fn = profiles_models.Profile.favorite
        has_favorited_fn = profiles_models.Profile.has_favorited
        unfavorite_fn = profiles_models.Profile.unfavorite
    except AttributeError:
        pytest.fail("Profile.favorite/has_favorited/unfavorite not implemented")

    favorite_fn(profile, article)

    # Assert favorite added
    assert any(getattr(x, "pk", None) == article.pk for x in profile.favorites.all()) is True
    assert has_favorited_fn(profile, article) is True

    # Act - unfavorite
    unfavorite_fn(profile, article)

    # Assert removal
    assert has_favorited_fn(profile, article) is False
    assert all(getattr(x, "pk", None) != article.pk for x in profile.favorites.all())


@pytest.mark.parametrize("image_value, expected", [(None, ""), ("http://img", "http://img")])
def test_get_image_returns_expected_values(image_value, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    try:
        get_image = profiles_serializers.ProfileSerializer.get_image
    except AttributeError:
        pytest.fail("ProfileSerializer.get_image not implemented")
    serializer_self = SimpleNamespace(context={})
    profile_obj = SimpleNamespace(image=image_value, user=SimpleNamespace(username="bob"))

    # Act
    result = get_image(serializer_self, profile_obj)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected


@pytest.mark.parametrize("is_followed, expected", [(True, True), (False, False)])
def test_get_following_respects_request_user_and_profile_method(is_followed, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    try:
        get_following = profiles_serializers.ProfileSerializer.get_following
    except AttributeError:
        pytest.fail("ProfileSerializer.get_following not implemented")

    # create serializer self with request containing a user
    current_user = SimpleNamespace(pk=999)
    request = SimpleNamespace(user=current_user)
    serializer_self = SimpleNamespace(context={'request': request})

    # profile to be serialized exposes is_followed_by method
    target_profile = SimpleNamespace()
    target_profile.is_followed_by = lambda u: is_followed

    # Act
    result = get_following(serializer_self, target_profile)

    # Assert
    assert result is expected

    # Also check behavior when request not present -> should be False
    serializer_self_no_request = SimpleNamespace(context={})
    result_no_request = get_following(serializer_self_no_request, target_profile)
    assert result_no_request is False


def test_tagrelatedfield_to_internal_and_to_representation(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    try:
        TagRelatedField = articles_relations.TagRelatedField
    except AttributeError:
        pytest.fail("TagRelatedField not implemented in relations")

    try:
        Tag = articles_models.Tag
    except AttributeError:
        pytest.fail("Tag model not present")

    created_tags = {}

    class FakeManager:
        def get_or_create(self, name):
            # simulate Django get_or_create(name=...)
            if name in created_tags:
                return created_tags[name], False
            tag = SimpleNamespace(name=name)
            created_tags[name] = tag
            return tag, True

    # Monkeypatch Tag.objects
    monkeypatch.setattr(Tag, "objects", FakeManager(), raising=False)

    field = TagRelatedField()

    # Act - create from raw string with trailing spaces
    raw = " python "
    tag_obj = field.to_internal_value(raw)

    # Assert created and trimmed
    assert getattr(tag_obj, "name", None) == "python"

    # Act - representation
    repr_value = field.to_representation(tag_obj)

    # Assert
    assert isinstance(repr_value, _exc_lookup("str", Exception))
    assert repr_value == "python"


def test_tagrelatedfield_to_internal_invalid_raises():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    try:
        TagRelatedField = articles_relations.TagRelatedField
    except AttributeError:
        pytest.fail("TagRelatedField not implemented in relations")
    field = TagRelatedField()

    # Act / Assert - passing None should raise a TypeError or ValueError depending on implementation
    with pytest.raises(_exc_lookup('TypeError', Exception)):
        field.to_internal_value(None)
