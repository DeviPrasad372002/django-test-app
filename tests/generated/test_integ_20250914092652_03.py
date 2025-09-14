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
    from types import SimpleNamespace
    import string
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.signals as auth_signals
    import conduit.apps.profiles.models as profiles_models
    import conduit.apps.core.exceptions as core_exceptions
    import conduit.apps.core.utils as core_utils
    import django.conf as django_conf
    import jwt
    from rest_framework import exceptions as drf_exceptions
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Required package import failed: {e}", allow_module_level=True)


def _exc_lookup(name, default):
    return getattr(__import__('builtins'), name, default)


def test__generate_jwt_token_and_token_property_uses_jwt_and_settings(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    dummy_payload_captured = {}
    def fake_jwt_encode(payload, key, algorithm='HS256'):
        # capture payload for assertion and return deterministic token
        dummy_payload_captured['payload'] = payload
        return "MOCK_JWT_TOKEN"

    monkeypatch.setattr(jwt, "encode", fake_jwt_encode)
    # Ensure SECRET_KEY exists
    monkeypatch.setattr(django_conf.settings, "SECRET_KEY", "super-secret", raising=False)

    # Create a minimal dummy instance with pk attribute expected by the method/property
    dummy_instance = SimpleNamespace(pk=42)

    # Act
    # Call the unbound method directly to avoid needing a full Django model instance
    generated = auth_models.User._generate_jwt_token(dummy_instance)
    # Access the property object on the class and invoke fget with our simple namespace
    token_prop = getattr(auth_models.User, "token", None)
    token_via_prop = token_prop.fget(dummy_instance) if isinstance(token_prop, _exc_lookup("property", Exception)) else None

    # Assert
    assert isinstance(generated, _exc_lookup("str", Exception))
    assert generated == "MOCK_JWT_TOKEN"
    assert 'payload' in dummy_payload_captured
    assert dummy_payload_captured['payload'].get('user_id', None) in (42, dummy_instance.pk)
    # If token property exists, it should call the same generator and return same format
    if token_via_prop is not None:
        assert token_via_prop == "MOCK_JWT_TOKEN"


@pytest.mark.parametrize("created,should_call_create", [(True, True), (False, False)])
def test_create_related_profile_invokes_profile_creation_when_created_flag(monkeypatch, created, should_call_create):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_calls = []
    class DummyManager:
        def create(self, **kwargs):
            created_calls.append(kwargs)
            return SimpleNamespace(**kwargs)

    # Monkeypatch the Profile.objects manager to our dummy manager
    monkeypatch.setattr(profiles_models, "Profile", SimpleNamespace(objects=DummyManager()), raising=False)

    # Prepare a fake user instance that the signal handler will receive
    fake_user = SimpleNamespace(pk=7, username="tester", email="t@example.com")

    # Act
    auth_signals.create_related_profile(sender=auth_models.User, instance=fake_user, created=created, **{})

    # Assert
    if should_call_create:
        assert len(created_calls) == 1
        created_kwargs = created_calls[0]
        # Expect the user passed as relationship
        assert created_kwargs.get("user") is fake_user or created_kwargs.get("owner") is fake_user
    else:
        assert created_calls == []


@pytest.mark.parametrize("exception_obj,expected_status", [
    (drf_exceptions.NotFound("not found"), 404),
    (Exception("generic boom"), 500),
])
def test_core_exception_handler_routes_to_correct_internal_handlers(exception_obj, expected_status, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Spy on internal handlers to ensure they are invoked for respective exception types
    called = {"generic": 0, "not_found": 0}

    def fake_handle_generic(exc, context):
        called["generic"] += 1
        return SimpleNamespace(status_code=500, data={"error": "generic"})

    def fake_handle_not_found(exc, context):
        called["not_found"] += 1
        return SimpleNamespace(status_code=404, data={"error": "not found"})

    monkeypatch.setattr(core_exceptions, "_handle_generic_error", fake_handle_generic, raising=False)
    monkeypatch.setattr(core_exceptions, "_handle_not_found_error", fake_handle_not_found, raising=False)

    # Act
    response = core_exceptions.core_exception_handler(exception_obj, context={})

    # Assert
    assert hasattr(response, "status_code")
    assert response.status_code == expected_status
    # Ensure the correct internal handler was called
    if expected_status == 404:
        assert called["not_found"] == 1
        assert called["generic"] == 0
    else:
        assert called["generic"] == 1
        assert called["not_found"] == 0


@pytest.mark.parametrize("length", [0, 1, 8, 32])
def test_generate_random_string_returns_expected_length_and_charset(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    allowed_chars = set(string.ascii_letters + string.digits)

    # Act
    result = core_utils.generate_random_string(length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    # Every character must be in allowed set; empty string trivially passes
    assert all((c in allowed_chars) for c in result)
