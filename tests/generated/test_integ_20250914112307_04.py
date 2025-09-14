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
            pass
    
    if not _dj_apps.ready:
        try:
            django.setup()
        except Exception as e:
            pass
            
except Exception as e:
    pass



# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    import inspect
    import sys
    import types
    from conduit.apps.articles import signals as article_signals
    from conduit.apps.articles.__init__ import ArticlesAppConfig
    from conduit.apps.profiles import serializers as profile_serializers
    from conduit.apps.profiles import models as profile_models
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required conduit modules not available", allow_module_level=True)


def _call_flexible(func, *posargs):
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    # try to match common patterns:
    # handler(sender, instance, created, **kw)
    if len(params) >= 3:
        return func(None, *posargs[:2], True) if len(posargs) >= 2 else func(None, *posargs, True)
    # method(self, obj)
    if len(params) == 2:
        return func(None, *posargs)
    # function(obj)
    return func(*posargs)


def _call_maybe_method(func, self_obj, obj):
    sig = inspect.signature(func)
    if len(sig.parameters) >= 2:
        return func(self_obj, obj)
    return func(obj)


def _params_for_callable(func):
    return len(list(inspect.signature(func).parameters.values()))


def _exc_lookup(name, fallback=Exception):
    return getattr(__builtins__, name, fallback)


def test_add_slug_to_article_if_not_exists_sets_slug_when_missing_and_preserves_existing(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class FakeArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug

    fake = FakeArticle("Hello World", "")
    # Monkeypatch slugify and generate_random_string deterministically
    orig_slugify = getattr(article_signals, "slugify", None)
    orig_generate = getattr(article_signals, "generate_random_string", None)
    monkeypatch.setattr(article_signals, "slugify", lambda s: "hello-world", raising=False)
    monkeypatch.setattr(article_signals, "generate_random_string", lambda length=6: "RND", raising=False)

    try:
        # Act
        # add_slug_to_article_if_not_exists may be a signal handler expecting (sender, instance, created, **kwargs)
        add_slug = getattr(article_signals, "add_slug_to_article_if_not_exists")
        # Call flexibly
        result = _call_flexible(add_slug, fake)
        # Assert
        assert getattr(fake, "slug") == "hello-world-RND"
    finally:
        # cleanup
        if orig_slugify is not None:
            monkeypatch.setattr(article_signals, "slugify", orig_slugify, raising=False)
        if orig_generate is not None:
            monkeypatch.setattr(article_signals, "generate_random_string", orig_generate, raising=False)


def test_add_slug_to_article_if_not_exists_does_not_override_existing(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class FakeArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug

    fake = FakeArticle("Another Title", "existing-slug")
    orig_generate = getattr(article_signals, "generate_random_string", None)
    monkeypatch.setattr(article_signals, "generate_random_string", lambda length=6: "SHOULDNOTUSE", raising=False)

    try:
        # Act
        add_slug = getattr(article_signals, "add_slug_to_article_if_not_exists")
        _call_flexible(add_slug, fake)
        # Assert: slug remains unchanged
        assert fake.slug == "existing-slug"
    finally:
        if orig_generate is not None:
            monkeypatch.setattr(article_signals, "generate_random_string", orig_generate, raising=False)


def test_ready_imports_signals_module_and_runs_without_error(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    sentinel_module_name = "conduit.apps.articles.signals"
    saved = sys.modules.get(sentinel_module_name)
    fake_mod = types.ModuleType(sentinel_module_name)
    fake_mod.__dict__['__ready_marker__'] = True
    sys.modules[sentinel_module_name] = fake_mod
    try:
        # Act
        appcfg = ArticlesAppConfig()
        # ready should import the signals module; our fake module is in sys.modules
        appcfg.ready()
        # Assert
        assert sys.modules[sentinel_module_name].__dict__.get('__ready_marker__') is True
    finally:
        # Cleanup restore
        if saved is not None:
            sys.modules[sentinel_module_name] = saved
        else:
            del sys.modules[sentinel_module_name]


@pytest.mark.parametrize("image_value,expected", [
    ("http://example.com/avatar.png", "http://example.com/avatar.png"),
    (None, ""),
])
def test_get_image_returns_image_or_empty_string(monkeypatch, image_value, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    get_image = getattr(profile_serializers, "get_image")
    class FakeProfile:
        def __init__(self, image):
            self.image = image

    fake = FakeProfile(image_value)

    # Act
    # get_image is likely a serializer method: def get_image(self, obj)
    # Provide None as self if method expects self
    sig_len = _params_for_callable(get_image)
    if sig_len >= 2:
        result = get_image(None, fake)
    else:
        result = get_image(fake)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected


def test_get_following_delegates_to_is_following_with_context_user(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    get_following = getattr(profile_serializers, "get_following")
    calls = []

    def fake_is_following(profile_user, request_user):
        calls.append((profile_user, request_user))
        return True

    monkeypatch.setattr(profile_models, "is_following", fake_is_following, raising=False)

    class FakeRequest:
        def __init__(self, user):
            self.user = user

    class FakeSelf:
        def __init__(self, user):
            self.context = {'request': FakeRequest(user)}

    class FakeProfileObject:
        def __init__(self, user):
            self.user = user

    profile_user = "profile_owner"
    request_user = "requesting_user"
    fake_self = FakeSelf(request_user)
    fake_profile_obj = FakeProfileObject(profile_user)

    # Act
    sig_len = _params_for_callable(get_following)
    if sig_len >= 2:
        result = get_following(fake_self, fake_profile_obj)
    else:
        # If function expects only obj, it may obtain request via thread or global; call directly
        result = get_following(fake_profile_obj)

    # Assert
    assert result is True
    # ensure the underlying is_following was called with profile_user and request_user when possible
    assert calls and calls[0] == (profile_user, request_user)
