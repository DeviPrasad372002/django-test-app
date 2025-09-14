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
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.authentication import serializers as auth_serializers
    from conduit.apps.authentication.renderers import UserJSONRenderer
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required modules for authentication integration tests are not available", allow_module_level=True)

@pytest.mark.parametrize(
    "first_name,last_name,expected_full,expected_short",
    [
        ("John", "Doe", "John Doe", "John"),
        ("", "", "", ""),
        ("A", "", "A", "A"),
    ],
)
def test_user_model_full_and_short_name_and_token(monkeypatch, first_name, last_name, expected_full, expected_short):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = auth_models.User(email="j@example.com", username="jdoe", first_name=first_name, last_name=last_name)
    fixed_token = "fixed.jwt.token"
    monkeypatch.setattr(auth_models.User, "_generate_jwt_token", lambda self: fixed_token)
    # Act
    full_name = user.get_full_name()
    short_name = user.get_short_name()
    token_value = user.token
    # Assert
    assert isinstance(full_name, _exc_lookup("str", Exception))
    assert isinstance(short_name, _exc_lookup("str", Exception))
    assert full_name == expected_full
    assert short_name == expected_short
    assert token_value == fixed_token
    assert isinstance(token_value, _exc_lookup("str", Exception))

def test_jwt_authentication_success_and_missing_header(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = JWTAuthentication()
    valid_token_string = "valid.token"
    decoded_payload = {"id": 42, "email": "user42@example.com"}
    # Create a simple request-like object
    class DummyRequest:
        def __init__(self, header_value=None):
            self.META = {}
            if header_value is not None:
                self.META["HTTP_AUTHORIZATION"] = header_value

    # Prepare a user instance to be returned by the mocked objects.get
    user_instance = auth_models.User(email="user42@example.com", username="user42")
    # Monkeypatch jwt.decode used inside the backend module
    import conduit.apps.authentication.backends as backends_mod
    monkeypatch.setattr(backends_mod, "jwt", SimpleNamespace(decode=lambda token, key, algorithms: decoded_payload))
    # Monkeypatch User.objects.get to return our user_instance when looked up by id or email
    class FakeObjects:
        def get(self, **kwargs):
            # emulate lookup by id or email
            if kwargs.get("id") == decoded_payload["id"] or kwargs.get("email") == decoded_payload["email"]:
                return user_instance
            raise auth_models.User.DoesNotExist()
    monkeypatch.setattr(auth_models.User, "objects", FakeObjects())
    # Act & Assert for success case
    request_with_header = DummyRequest(f"Token {valid_token_string}")
    result = auth.authenticate(request_with_header)
    assert isinstance(result, _exc_lookup("tuple", Exception))
    returned_user, returned_token = result
    assert returned_user is user_instance
    assert returned_token == valid_token_string
    # Act & Assert for missing header case
    request_without_header = DummyRequest(None)
    result_none = auth.authenticate(request_without_header)
    assert result_none is None

@pytest.mark.parametrize(
    "payload,should_be_valid,missing_field",
    [
        ({"email": "new@example.com", "username": "newuser", "password": "strongpass"}, True, None),
        ({"email": "no-password@example.com", "username": "nopass"}, False, "password"),
    ],
)
def test_registration_serializer_create_and_renderer_integration(monkeypatch, payload, should_be_valid, missing_field):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer_class = auth_serializers.RegistrationSerializer
    # Prepare a fake user that the manager will return
    created_user = auth_models.User(email=payload.get("email", ""), username=payload.get("username", ""))
    # Monkeypatch the manager create_user to return created_user when called
    def fake_create_user(email=None, username=None, password=None):
        created_user.email = email or created_user.email
        created_user.username = username or created_user.username
        created_user._raw_password = password
        return created_user
    # Attempt to set on the manager instance if available, otherwise set on the class attribute
    if hasattr(auth_models.User, "objects"):
        monkeypatch.setattr(auth_models.User.objects.__class__, "create_user", staticmethod(fake_create_user), raising=False)
    else:
        monkeypatch.setattr(auth_models.User, "create_user", fake_create_user, raising=False)
    # Act
    serializer = serializer_class(data=payload)
    is_valid = serializer.is_valid()
    # Assert validation expectation
    assert is_valid == should_be_valid
    if should_be_valid:
        saved_user = serializer.save()
        # The serializer is expected to return a user-like object
        assert isinstance(saved_user, _exc_lookup("auth_models.User", Exception))
        # Ensure fields propagated
        assert saved_user.email == payload["email"]
        assert saved_user.username == payload["username"]
        # Render the serialized user payload using the renderer to ensure integration across modules
        renderer = UserJSONRenderer()
        rendered = renderer.render({"user": serializer.data})
        assert isinstance(rendered, (bytes, str))
        # Basic sanity on serializer output structure
        assert "email" in serializer.data
        assert "username" in serializer.data
        assert "token" in serializer.data
    else:
        # For invalid payload ensure the expected missing field is reported
        assert missing_field in serializer.errors or any(missing_field in str(v) for v in serializer.errors.values())
