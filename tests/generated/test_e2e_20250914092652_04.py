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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from conduit.apps.profiles import serializers as profiles_serializers
except ImportError:
    import pytest as _pytest
    _pytest.skip("conduit.apps.profiles.serializers not available", allow_module_level=True)

class DummyUser:
    def __init__(self, is_anonymous=False, follow_result=False):
        self.is_anonymous = is_anonymous
        self._follow_result = follow_result

    def is_following(self, other):
        return self._follow_result

class DummyProfile:
    def __init__(self, image, user):
        self.image = image
        self.user = user

class DummyRequest:
    def __init__(self, user):
        self.user = user

@pytest.mark.parametrize(
    "image_value, expected",
    [
        ("http://example.com/avatar.png", "http://example.com/avatar.png"),
        ("", ""),
        (None, ""),  # edge: None should be normalized to empty string if implemented that way
    ],
)
def test_get_image_returns_image_or_empty(image_value, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    profile_user = DummyUser(is_anonymous=True)  # user details not relevant for image
    dummy_profile = DummyProfile(image=image_value, user=profile_user)
    serializer_instance = profiles_serializers.ProfileSerializer(instance=dummy_profile, context={})

    # Act
    image_result = serializer_instance.get_image(dummy_profile)

    # Assert
    assert isinstance(image_result, _exc_lookup("str", Exception))
    assert image_result == expected

@pytest.mark.parametrize(
    "context_request_user_is_anonymous, profile_user_follow_result, expected_following",
    [
        (None, None, False),   # no request in context => should be not following
        (True, False, False),  # anonymous request user => not following
        (False, True, True),   # authenticated request user and profile.user reports following => True
        (False, False, False), # authenticated request user and profile.user reports not following => False
    ],
)
def test_get_following_respects_request_and_profile_relation(
    # Arrange-Act-Assert: generated by ai-testgen
    context_request_user_is_anonymous, profile_user_follow_result, expected_following
):
    # Arrange
    # Build profile.user depending on whether follow_result is specified
    if profile_user_follow_result is None:
        profile_user = DummyUser(is_anonymous=False, follow_result=False)
    else:
        profile_user = DummyUser(is_anonymous=False, follow_result=profile_user_follow_result)

    dummy_profile = DummyProfile(image=None, user=profile_user)

    if context_request_user_is_anonymous is None:
        context = {}
    else:
        request_user = DummyUser(is_anonymous=context_request_user_is_anonymous)
        dummy_request = DummyRequest(user=request_user)
        context = {"request": dummy_request}

    serializer_instance = profiles_serializers.ProfileSerializer(instance=dummy_profile, context=context)

    # Act
    following_result = serializer_instance.get_following(dummy_profile)

    # Assert
    assert isinstance(following_result, _exc_lookup("bool", Exception))
    assert following_result is expected_following
