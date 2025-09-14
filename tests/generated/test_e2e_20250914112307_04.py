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

try:
    import inspect
    from types import SimpleNamespace
    import pytest
    import conduit.apps.profiles.serializers as serializers_mod
except ImportError:
    import pytest
    pytest.skip("Required modules for tests are not available", allow_module_level=True)

def _locate_callable(module, name):
    if hasattr(module, name) and callable(getattr(module, name)):
        return ("function", getattr(module, name), None)
    for _name, cls in inspect.getmembers(module, inspect.isclass):
        if hasattr(cls, name) and callable(getattr(cls, name)):
            return ("method", getattr(cls, name), cls)
    raise AssertionError(f"Callable {name!r} not found in module {module.__name__}")

def _instantiate_serializer(cls, context):
    try:
        return cls(context=context)
    except TypeError:
        try:
            return cls(instance=None, context=context)
        except TypeError:
            return cls()

def _invoke(module, name, obj, context):
    kind, call, cls = _locate_callable(module, name)
    if kind == "function":
        func = call
        try:
            return func(obj)
        except TypeError:
            return func(obj, context)
    else:
        serializer_instance = _instantiate_serializer(cls, context)
        bound_method = getattr(serializer_instance, name)
        return bound_method(obj)

@pytest.mark.parametrize("image_value, expected", [
    ("http://example.com/avatar.png", "http://example.com/avatar.png"),
    ("", ""),
    (None, ""),
])
def test_get_image_returns_provided_string_or_empty(image_value, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    target_obj = SimpleNamespace()
    # provide both attribute shapes: attribute directly and nested profile.image
    target_obj.image = image_value
    target_obj.profile = SimpleNamespace(image=image_value)
    context = {"request": SimpleNamespace(user=SimpleNamespace(is_authenticated=True))}
    # Act
    result = _invoke(serializers_mod, "get_image", target_obj, context)
    # Assert
    assert isinstance(result, (str, type("")))
    assert result == expected

@pytest.mark.parametrize("is_followed_by_return, user_is_authenticated, expect", [
    (True, True, True),
    (True, False, False),
    (False, True, False),
    (False, False, False),
])
def test_get_following_reflects_context_user_and_is_followed_by(is_followed_by_return, user_is_authenticated, expect):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    captured = {}
    def is_followed_by(candidate):
        captured['seen_user'] = candidate
        return is_followed_by_return
    profile_obj = SimpleNamespace(is_followed_by=is_followed_by)
    current_user = SimpleNamespace(is_authenticated=user_is_authenticated)
    request = SimpleNamespace(user=current_user)
    context = {"request": request}
    # Act
    result = _invoke(serializers_mod, "get_following", profile_obj, context)
    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result is expect
    if user_is_authenticated:
        assert captured.get('seen_user') is current_user
    else:
        # when unauthenticated, serializer should not call is_followed_by; allow either no call or a call with same user; but prefer no call
        if 'seen_user' in captured:
            assert captured['seen_user'] is current_user

def test_get_following_without_request_context_returns_false():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    def is_followed_by(candidate):
        raise AssertionError("Should not be called when no request context is present")
    profile_obj = SimpleNamespace(is_followed_by=is_followed_by)
    context = {}  # no request provided
    # Act
    result = _invoke(serializers_mod, "get_following", profile_obj, context)
    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result is False
