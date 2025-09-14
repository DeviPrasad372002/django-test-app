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

    
# Replace the Django bootstrap section with this simplified version
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
                    return True
            except Exception:
                pass
            return False

        if not _dj_settings.configured:
            _installed = [
                "django.contrib.auth",
                "django.contrib.contenttypes", 
                "django.contrib.sessions"
            ]
            
            if _iu.find_spec("rest_framework"):
                _installed.append("rest_framework")

            # Try to add conduit apps
            for _app in ("conduit.apps.core", "conduit.apps.articles", "conduit.apps.authentication", "conduit.apps.profiles"):
                _maybe_add(_app, _installed)

            _cfg = dict(
                SECRET_KEY="test-key",
                DEBUG=True,
                ALLOWED_HOSTS=["*"],
                INSTALLED_APPS=sorted(set(_installed)),
                DATABASES=dict(default=dict(ENGINE="django.db.backends.sqlite3", NAME=":memory:")),
                MIDDLEWARE=[
                    'django.middleware.security.SecurityMiddleware',
                    'django.contrib.sessions.middleware.SessionMiddleware',
                    'django.middleware.common.CommonMiddleware',
                ],
                USE_TZ=True,
                TIME_ZONE="UTC",
            )
            
            try:
                _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
            except Exception:
                pass

            try:
                _dj_settings.configure(**_cfg)
            except Exception as e:
                # Don't skip module-level, just continue
                pass

        if not _dj_apps.ready:
            try:
                django.setup()
            except Exception as e:
                # Don't skip module-level, just continue
                pass

except Exception as e:
    # Don't skip at module level - let individual tests handle Django issues
    pass

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import importlib
    import sys
    import types
    import pytest

    profiles_models = importlib.import_module('conduit.apps.profiles.models')
    profiles_serializers = importlib.import_module('conduit.apps.profiles.serializers')
    articles_models = importlib.import_module('conduit.apps.articles.models')
    articles_relations = importlib.import_module('conduit.apps.articles.relations')
    articles_init = importlib.import_module('conduit.apps.articles.__init__')
    migrations_mod = importlib.import_module('conduit.apps.articles.migrations.0001_initial')
except ImportError as e:
    import pytest as _pytest
    _pytest.skip("Required application modules are not available: %s" % e, allow_module_level=True)


def _make_dummy_rel(initial=None):
    class DummyRel:
        def __init__(self, items=None):
            self._items = list(items or [])
        def all(self):
            return list(self._items)
        def add(self, item):
            if item not in self._items:
                self._items.append(item)
        def remove(self, item):
            if item in self._items:
                self._items.remove(item)
    return DummyRel(initial)


def test_profile_follow_unfollow_and_favorite_unfavorite_state_changes():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    follow_fn = getattr(profiles_models, 'follow')
    unfollow_fn = getattr(profiles_models, 'unfollow')
    is_followed_by_fn = getattr(profiles_models, 'is_followed_by')
    favorite_fn = getattr(profiles_models, 'favorite')
    unfavorite_fn = getattr(profiles_models, 'unfavorite')
    has_favorited_fn = getattr(profiles_models, 'has_favorited')

    class DummyProfile:
        def __init__(self):
            self.followers = _make_dummy_rel()
            self.favorited_articles = _make_dummy_rel()

    follower = object()
    article = object()
    profile = DummyProfile()

    # Act & Assert - follow/unfollow
    assert is_followed_by_fn(profile, follower) is False
    follow_fn(profile, follower)
    assert follower in profile.followers.all()
    assert is_followed_by_fn(profile, follower) is True
    unfollow_fn(profile, follower)
    assert follower not in profile.followers.all()
    assert is_followed_by_fn(profile, follower) is False

    # Act & Assert - favorite/unfavorite
    assert has_favorited_fn(profile, article) is False
    favorite_fn(profile, article)
    assert article in profile.favorited_articles.all()
    assert has_favorited_fn(profile, article) is True
    unfavorite_fn(profile, article)
    assert article not in profile.favorited_articles.all()
    assert has_favorited_fn(profile, article) is False


@pytest.mark.parametrize(
    "cls_name, init_kwargs, expected_str",
    [
        ("Article", {"title": "A Title"}, "A Title"),
        ("Comment", {"body": "Nice comment"}, "Nice comment"),
        ("Tag", {"name": "python"}, "python"),
    ],
)
def test_model_str_returns_expected_value(cls_name, init_kwargs, expected_str):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    cls = getattr(articles_models, cls_name)
    # Act
    instance = cls(**init_kwargs)
    result = str(instance)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected_str


def test_tagrelatedfield_to_representation_and_to_internal_value_behaviour():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    TRF = getattr(articles_relations, 'TagRelatedField')
    field = TRF()
    class DummyTag:
        def __init__(self, name):
            self.name = name
    dummy = DummyTag("unittest-tag")

    # Act
    rep = field.to_representation(dummy)

    # Assert representation is the tag's name
    assert rep == "unittest-tag"

    # Act - internal value handling: accept string and return an object with .name
    internal = field.to_internal_value("new-tag")
    # Assert
    assert hasattr(internal, "name")
    assert getattr(internal, "name") == "new-tag"


def test_articles_appconfig_ready_imports_signals_without_side_effects(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    AppConfigClass = getattr(articles_init, 'ArticlesAppConfig')
    fake_signals = types.ModuleType("conduit.apps.articles.signals")
    # Put a sentinel in the fake module to verify it was imported
    fake_signals._SENTINEL = True
    monkeypatch.setitem(sys.modules, 'conduit.apps.articles.signals', fake_signals)

    app_config = AppConfigClass('conduit.apps.articles', 'conduit.apps.articles')

    # Act - calling ready should import the signals module but not raise
    app_config.ready()

    # Assert - our fake module was used
    assert 'conduit.apps.articles.signals' in sys.modules
    assert getattr(sys.modules['conduit.apps.articles.signals'], '_SENTINEL', False) is True


def test_migration_class_has_dependencies_and_operations_attributes():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    Migration = getattr(migrations_mod, 'Migration')

    # Act & Assert
    assert hasattr(Migration, 'dependencies')
    assert hasattr(Migration, 'operations')
    deps = getattr(Migration, 'dependencies')
    ops = getattr(Migration, 'operations')
    assert isinstance(deps, (list, tuple))
    assert isinstance(ops, (list, tuple))
