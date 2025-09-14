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

def _fix_django_metaclass_compatibility():
    """Fix Django 1.10.5 metaclass compatibility with Python 3.10+"""
    try:
        import sys
        if sys.version_info >= (3, 8):
            import builtins
            original_build_class = builtins.__build_class__
            
            def patched_build_class(func, name, *bases, metaclass=None, **kwargs):
                try:
                    return original_build_class(func, name, *bases, metaclass=metaclass, **kwargs)
                except RuntimeError as e:
                    if '__classcell__' in str(e) and 'not set' in str(e):
                        # Create a new function without problematic cell variables
                        import types
                        code = func.__code__
                        if code.co_freevars:
                            # Remove free variables that cause issues
                            new_code = code.replace(
                                co_freevars=(),
                                co_names=code.co_names + code.co_freevars
                            )
                            new_func = types.FunctionType(
                                new_code,
                                func.__globals__,
                                func.__name__,
                                func.__defaults__,
                                None  # No closure
                            )
                            return original_build_class(new_func, name, *bases, metaclass=metaclass, **kwargs)
                    raise
                except Exception:
                    # Fallback for other metaclass issues
                    return original_build_class(func, name, *bases, **kwargs)
            
            builtins.__build_class__ = patched_build_class
    except Exception:
        pass

# Apply Django metaclass fix early
_fix_django_metaclass_compatibility()

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

# Handle Django configuration for tests
try:
    import django
    from django.conf import settings
    from django import apps as _dj_apps
    
    if not settings.configured:
        _cfg = dict(
            DEBUG=True,
            SECRET_KEY='test-secret-key-for-pytest',
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
            ],
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
            settings.configure(**_cfg)
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

import pytest
from types import SimpleNamespace

try:
    import conduit.apps.articles.signals as articles_signals
    import conduit.apps.articles.__init__ as articles_init
    import conduit.apps.core.utils as core_utils
    import django.utils.text as django_text
    import django.db.models.signals as django_signals
    import conduit.apps.profiles.models as profiles_models
    import conduit.apps.articles.relations as articles_relations
    import conduit.apps.articles.models as articles_models
except ImportError:
    pytest.skip("Required target packages not available", allow_module_level=True)


class _FakeFavManager:
    def __init__(self):
        self._set = set()

    def add(self, item):
        self._set.add(item)

    def remove(self, item):
        self._set.remove(item)

    def filter(self, **kwargs):
        pk = kwargs.get("pk")
        items = [i for i in self._set if getattr(i, "pk", None) == pk]
        return _FakeFilter(items)


class _FakeFilter:
    def __init__(self, items):
        self._items = items

    def exists(self):
        return bool(self._items)


def _get_unbound_method(klass, name):
    # Support both function attributes and descriptors
    attr = getattr(klass, name)
    return attr


@pytest.mark.parametrize("initial_slug", [None, "existing-slug"])
def test_add_slug_to_article_if_not_exists_sets_when_missing_and_preserves_when_present(monkeypatch, initial_slug):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article = SimpleNamespace(title="Test Title for Slug", slug=initial_slug)
    monkeypatch.setattr(core_utils, "generate_random_string", lambda *a, **k: "RND", raising=False)
    monkeypatch.setattr(django_text, "slugify", lambda v: "test-title", raising=False)

    # Act
    articles_signals.add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    if initial_slug:
        assert article.slug == "existing-slug"
    else:
        assert isinstance(article.slug, str)
        assert article.slug.startswith("test-title")
        assert "RND" in article.slug


def test_articles_appconfig_ready_connects_slug_signal(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    connected = []

    def fake_connect(func=None, sender=None, **kwargs):
        connected.append((func, sender, kwargs))

    # Replace pre_save and post_save objects with ones exposing connect
    monkeypatch.setattr(django_signals, "pre_save", SimpleNamespace(connect=fake_connect), raising=False)
    monkeypatch.setattr(django_signals, "post_save", SimpleNamespace(connect=fake_connect), raising=False)

    config = articles_init.ArticlesAppConfig("articles", "conduit.apps.articles")

    # Act
    config.ready()

    # Assert
    # Ensure at least one connect call referenced the add_slug handler from signals
    handler_found = any(called[0] is getattr(articles_signals, "add_slug_to_article_if_not_exists", None) for called in connected)
    assert handler_found, "add_slug_to_article_if_not_exists was not connected by ready()"


@pytest.mark.parametrize("initially_favorited", [False, True])
def test_favorite_unfavorite_has_favorited_flow(initially_favorited):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    favorite_method = _get_unbound_method(profiles_models.Profile, "favorite")
    unfavorite_method = _get_unbound_method(profiles_models.Profile, "unfavorite")
    has_favorited_method = _get_unbound_method(profiles_models.Profile, "has_favorited")

    fake_manager = _FakeFavManager()
    article = SimpleNamespace(pk=123)
    profile = SimpleNamespace(favorites=fake_manager)

    if initially_favorited:
        fake_manager.add(article)
        assert has_favorited_method(profile, article) is True

    # Act - favorite (idempotent)
    favorite_method(profile, article)

    # Assert after favorite
    assert has_favorited_method(profile, article) is True
    assert article in fake_manager._set

    # Act - unfavorite
    unfavorite_method(profile, article)

    # Assert after unfavorite
    assert has_favorited_method(profile, article) is False
    assert article not in fake_manager._set


@pytest.mark.parametrize("existing_flag", [True, False])
def test_tagrelatedfield_to_internal_and_to_representation(monkeypatch, existing_flag):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_records = []

    class DummyObjects:
        def get_or_create(self, name):
            tag_obj = SimpleNamespace(name=name)
            created = not existing_flag
            created_records.append((name, created))
            return tag_obj, created

    # Monkeypatch the Tag model's objects to our dummy
    monkeypatch.setattr(articles_models, "Tag", SimpleNamespace(objects=DummyObjects()), raising=False)

    field = articles_relations.TagRelatedField()

    # Act
    internal = field.to_internal_value("python")
    representation = field.to_representation(internal)

    # Assert
    assert hasattr(internal, "name")
    assert internal.name == "python"
    assert representation == "python"
    # Ensure underlying get_or_create was invoked
    assert created_records and created_records[0][0] == "python"
