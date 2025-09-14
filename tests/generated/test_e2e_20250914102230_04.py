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

import inspect
import types
import pytest

try:
    import conduit.apps.profiles.models as profiles_models
    import conduit.apps.profiles.serializers as profiles_serializers
    import conduit.apps.articles.serializers as articles_serializers
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


@pytest.mark.parametrize(
    "case,obj,expected,expected_exc",
    [
        ("with_image", types.SimpleNamespace(image="http://img.local/pic.png"), "http://img.local/pic.png", None),
        ("none_image", types.SimpleNamespace(image=None), None, None),
        ("missing_image", types.SimpleNamespace(), None, AttributeError),
    ],
)
def test_get_image_returns_underlying_image_or_raises_for_missing(case, obj, expected, expected_exc):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    func = getattr(profiles_serializers, "get_image", None)
    assert func is not None, "profiles.serializers.get_image must exist"
    # Act / Assert
    if expected_exc is not None:
        with pytest.raises(_exc_lookup("expected_exc", Exception)):
            func(obj)
    else:
        result = func(obj)
        # Assert concrete output and type
        assert result == expected
        assert (result is None) or isinstance(result, (str, type(None)))


@pytest.mark.parametrize("stub_value", [True, False])
def test_get_following_delegates_to_profiles_is_following(monkeypatch, stub_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    func = getattr(profiles_serializers, "get_following", None)
    assert func is not None, "profiles.serializers.get_following must exist"
    recorded_calls = []

    def fake_is_following(*args, **kwargs):
        recorded_calls.append((args, kwargs))
        return stub_value

    monkeypatch.setattr(profiles_models, "is_following", fake_is_following)
    fake_request_user = types.SimpleNamespace(username="request_user")
    target_profile = types.SimpleNamespace(username="target_profile")
    # Build possible parameter mapping based on signature names
    sig = inspect.signature(func)
    call_args = []
    call_kwargs = {}
    for i, param in enumerate(sig.parameters.values()):
        name = param.name
        if name in ("instance", "obj", "profile", "target", "to_user", "user", "target_user"):
            call_args.append(target_profile)
        elif name in ("request", "ctx", "context"):
            call_args.append(types.SimpleNamespace(user=fake_request_user))
        elif name in ("current_user", "request_user"):
            call_args.append(fake_request_user)
        else:
            # Provide None for unknown params
            call_args.append(None)
    # Act
    result = func(*call_args, **call_kwargs)
    # Assert that result matches stub and that stub was invoked once
    assert result is stub_value
    assert len(recorded_calls) == 1
    call_args_recorded, call_kwargs_recorded = recorded_calls[0]
    # Ensure either the request user or the target profile was passed into is_following
    assert any(
        fake_request_user is a or fake_request_user in a or target_profile is a or target_profile in a
        for a in call_args_recorded
    )


@pytest.mark.parametrize("stub_value", [True, False])
def test_article_serializer_get_favorited_delegates_to_profiles_has_favorited(monkeypatch, stub_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    func = getattr(articles_serializers, "get_favorited", None)
    assert func is not None, "articles.serializers.get_favorited must exist"
    recorded_calls = []

    def fake_has_favorited(*args, **kwargs):
        recorded_calls.append((args, kwargs))
        return stub_value

    monkeypatch.setattr(profiles_models, "has_favorited", fake_has_favorited)
    fake_request_user = types.SimpleNamespace(username="request_user")
    fake_article = types.SimpleNamespace(slug="a-slug", author=types.SimpleNamespace(username="author"))
    # Build call args based on signature introspection
    sig = inspect.signature(func)
    call_args = []
    for param in sig.parameters.values():
        name = param.name
        if name in ("instance", "obj", "article", "instance_obj"):
            call_args.append(fake_article)
        elif name in ("request", "context", "ctx"):
            call_args.append(types.SimpleNamespace(user=fake_request_user))
        elif name in ("user", "request_user", "current_user"):
            call_args.append(fake_request_user)
        else:
            call_args.append(None)
    # Act
    result = func(*call_args)
    # Assert result and that the underlying has_favorited was called once
    assert result is stub_value
    assert len(recorded_calls) == 1
    called_args, called_kwargs = recorded_calls[0]
    # Verify that the article or user was forwarded to has_favorited
    assert any(fake_article is a or fake_request_user is a or fake_request_user in a or fake_article in a for a in called_args)
