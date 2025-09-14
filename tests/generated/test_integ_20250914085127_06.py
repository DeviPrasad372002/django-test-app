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
    from types import SimpleNamespace
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import backends as auth_backends
    from conduit.apps.authentication import views as auth_views
    from conduit.apps.authentication import serializers as auth_serializers
    from conduit.apps.authentication import renderers as auth_renderers
    from rest_framework.test import APIRequestFactory
    import rest_framework.exceptions as rf_exceptions
    import json
except ImportError:
    import pytest
    pytest.skip("Required test dependencies not available", allow_module_level=True)

def _exc_lookup(name, default=Exception):
    return getattr(rf_exceptions, name, default)

def test_user_generate_jwt_token_uses_jwt_encode_and_returns_string(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    mock_token_bytes = b"MOCKBYTESTOKEN"
    def fake_encode(payload, key, algorithm="HS256"):
        return mock_token_bytes
    monkeypatch.setattr(auth_models.jwt, "encode", fake_encode, raising=False)
    dummy_user = SimpleNamespace(id=123)
    # Act
    token_result = auth_models.User._generate_jwt_token(dummy_user)
    # Assert
    assert isinstance(token_result, _exc_lookup("str", Exception))
    assert "MOCKBYTESTOKEN" in token_result

@pytest.mark.parametrize("scenario", ["success", "invalid_token"])
def test_jwtauthentication_authenticate_credentials_handles_decode_and_user_lookup(monkeypatch, scenario):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    backend = auth_backends.JWTAuthentication()
    if scenario == "success":
        def fake_decode(token, key, algorithms=None):
            return {"user_id": 77}
        fake_user = SimpleNamespace(id=77, username="tester")
        fake_manager = SimpleNamespace(get=lambda **kwargs: fake_user)
        monkeypatch.setattr(auth_backends, "jwt", SimpleNamespace(decode=fake_decode), raising=False)
        # Replace User class in backend module with object exposing .objects.get
        monkeypatch.setattr(auth_backends, "User", SimpleNamespace(objects=fake_manager), raising=False)
        # Act
        result = backend._authenticate_credentials("sometoken")
        # Assert
        assert isinstance(result, _exc_lookup("tuple", Exception))
        returned_user, returned_token = result
        assert returned_user is fake_user
        assert returned_token == "sometoken"
    else:
        def raising_decode(*a, **k):
            raise Exception("invalid token")
        monkeypatch.setattr(auth_backends, "jwt", SimpleNamespace(decode=raising_decode), raising=False)
        # Act / Assert
        with pytest.raises(_exc_lookup("AuthenticationFailed", Exception)):
            backend._authenticate_credentials("badtoken")

def test_registration_and_login_api_views_use_serializers_and_renderers(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    factory = APIRequestFactory()
    registration_url = "/api/users/"
    login_url = "/api/users/login/"
    posted_registration_payload = {"user": {"username": "alice", "email": "alice@example.com", "password": "pass"}}
    posted_login_payload = {"user": {"email": "alice@example.com", "password": "pass"}}

    # Create fake user object returned by serializer.save()
    fake_user = SimpleNamespace(username="alice", email="alice@example.com", token="JWT_TOKEN")
    # Fake RegistrationSerializer class used by the view
    class FakeRegistrationSerializer:
        def __init__(self, data=None, context=None):
            self.initial_data = data
            self.context = context
            self._saved = False
        def is_valid(self, raise_exception=False):
            return True
        def save(self):
            self._saved = True
            return fake_user
        @property
        def data(self):
            return {"user": {"username": fake_user.username, "email": fake_user.email, "token": fake_user.token}}

    # Fake LoginSerializer class used by the view
    class FakeLoginSerializer:
        def __init__(self, data=None, context=None):
            self.initial_data = data
            self.context = context
        def is_valid(self, raise_exception=False):
            return True
        def save(self):
            return fake_user
        @property
        def data(self):
            return {"user": {"username": fake_user.username, "email": fake_user.email, "token": fake_user.token}}

    # Replace serializer classes in views module to ensure integration across modules
    monkeypatch.setattr(auth_views, "RegistrationSerializer", FakeRegistrationSerializer, raising=False)
    monkeypatch.setattr(auth_views, "LoginSerializer", FakeLoginSerializer, raising=False)

    # Ensure the renderer used in responses is predictable if the view consults it
    class FakeRenderer:
        def render(self, data, accepted_media_type=None, renderer_context=None):
            return json.dumps(data).encode("utf-8")
    monkeypatch.setattr(auth_views, "UserJSONRenderer", FakeRenderer, raising=False)

    # Act - Registration
    req_reg = factory.post(registration_url, posted_registration_payload, format="json")
    reg_view = auth_views.RegistrationAPIView()
    reg_response = reg_view.post(req_reg)
    # Assert - Registration
    assert hasattr(reg_response, "data")
    assert "user" in reg_response.data
    assert reg_response.data["user"]["username"] == "alice"
    assert reg_response.data["user"]["email"] == "alice@example.com"
    assert reg_response.data["user"]["token"] == "JWT_TOKEN"

    # Act - Login
    req_login = factory.post(login_url, posted_login_payload, format="json")
    login_view = auth_views.LoginAPIView()
    login_response = login_view.post(req_login)
    # Assert - Login
    assert hasattr(login_response, "data")
    assert "user" in login_response.data
    assert login_response.data["user"]["username"] == "alice"
    assert login_response.data["user"]["email"] == "alice@example.com"
    assert login_response.data["user"]["token"] == "JWT_TOKEN"
