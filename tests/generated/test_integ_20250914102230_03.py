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

try:
    import pytest
    import string
    from types import SimpleNamespace
    from unittest.mock import Mock

    from conduit.apps.core import utils as core_utils
    from conduit.apps.core import exceptions as core_exceptions
    from conduit.apps.authentication import signals as auth_signals
    from conduit.apps.profiles import models as profiles_models
    from rest_framework import exceptions as drf_exceptions
except ImportError:
    import pytest
    pytest.skip("Skipping integration tests - required modules not available", allow_module_level=True)


def _exc_lookup(name, default):
    return getattr(__builtins__, name, default)


@pytest.mark.parametrize(
    "length,expect_exception",
    [
        (0, None),
        (1, None),
        (16, None),
        (64, None),
        ("a", _exc_lookup("TypeError", Exception)),
    ],
)
def test_generate_random_string_various_lengths(length, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    allowed_chars = set(string.ascii_letters + string.digits)

    # Act / Assert
    if expect_exception is not None:
        with pytest.raises(_exc_lookup("expect_exception", Exception)):
            core_utils.generate_random_string(length)
        return

    result = core_utils.generate_random_string(length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    assert set(result).issubset(allowed_chars)


def test_core_exception_handler_handles_not_found_and_generic():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    not_found_exc = drf_exceptions.NotFound(detail="resource missing")
    generic_exc = Exception("something bad")

    # Act
    not_found_response = core_exceptions.core_exception_handler(not_found_exc, context={})
    generic_response = core_exceptions.core_exception_handler(generic_exc, context={})

    # Assert for NotFound
    assert hasattr(not_found_response, "status_code")
    assert not_found_response.status_code == 404
    assert hasattr(not_found_response, "data")
    assert isinstance(not_found_response.data, dict)
    # Expect an 'errors' structure or message containing our detail
    data_str_nf = str(not_found_response.data)
    assert "resource missing" in data_str_nf or "errors" in not_found_response.data

    # Assert for generic exception -> handled to 500-level response
    assert hasattr(generic_response, "status_code")
    assert generic_response.status_code >= 500
    assert hasattr(generic_response, "data")
    assert isinstance(generic_response.data, dict)
    data_str_gen = str(generic_response.data)
    assert "error" in data_str_gen.lower() or "errors" in generic_response.data


def test_create_related_profile_invokes_profile_creation(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_user = SimpleNamespace(pk=123, username="tester", email="t@example.com")
    mock_create = Mock()
    mock_get_or_create = Mock()

    # Try to patch both possible call targets so the signal handler's implementation
    # (whether it calls create or get_or_create) will be captured.
    if hasattr(profiles_models, "Profile") and hasattr(profiles_models.Profile, "objects"):
        monkeypatch.setattr(profiles_models.Profile.objects, "create", mock_create, raising=False)
        monkeypatch.setattr(profiles_models.Profile.objects, "get_or_create", mock_get_or_create, raising=False)
    else:
        # If the module layout is different, attempt to set on the module level Profile attr
        monkeypatch.setattr(profiles_models, "Profile", SimpleNamespace(objects=SimpleNamespace(create=mock_create, get_or_create=mock_get_or_create)), raising=False)

    # Act
    auth_signals.create_related_profile(sender=type(created_user), instance=created_user, created=True)

    # Assert: either create or get_or_create was called with a reference to the user instance
    called_create = mock_create.called
    called_get_or_create = mock_get_or_create.called
    assert called_create or called_get_or_create
    if called_create:
        called_args, called_kwargs = mock_create.call_args
        # Expect the created profile to be associated with the user passed in (common kw name 'user')
        assert any(created_user is v for v in called_kwargs.values()) or (called_args and created_user in called_args)
    if called_get_or_create:
        called_args, called_kwargs = mock_get_or_create.call_args
        assert any(created_user is v for v in called_kwargs.values()) or (called_args and created_user in called_args)
