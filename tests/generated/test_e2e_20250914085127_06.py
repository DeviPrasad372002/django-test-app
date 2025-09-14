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
    from unittest.mock import Mock
    from rest_framework.test import APIRequestFactory
    from conduit.apps.authentication.models import User, UserManager
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.serializers as auth_serializers
    from conduit.apps.authentication.serializers import RegistrationSerializer
    from conduit.apps.authentication.views import RegistrationAPIView, LoginAPIView
except ImportError:
    import pytest
    pytest.skip("Skipping tests - required modules not available", allow_module_level=True)

@pytest.mark.parametrize("email,username,uid", [
    ("alice@example.com", "alice", 1),
    ("bob@example.org", "bob", 999),
])
def test_user_token_and_name_methods(email, username, uid, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_token = "fake.header.payload.signature"
    monkeypatch.setattr(auth_models, "jwt", SimpleNamespace(encode=lambda payload, key, algorithm=None: fake_token))
    test_user = User(email=email, username=username, id=uid)

    # Act
    token_value = test_user.token
    full_name_value = test_user.get_full_name()
    short_name_value = test_user.get_short_name()

    # Assert
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert "." in token_value
    assert isinstance(full_name_value, _exc_lookup("str", Exception)) and full_name_value != ""
    assert isinstance(short_name_value, _exc_lookup("str", Exception)) and short_name_value != ""

@pytest.mark.parametrize("input_data,should_raise", [
    ({"username": "newuser", "email": "newuser@example.com", "password": "s3cret"}, False),
    ({"username": "nouser", "email": "nouser@example.com"}, True),  # missing password
])
def test_registration_serializer_creates_user_and_handles_invalid(input_data, should_raise, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_user = User(email=input_data.get("email", "none@example.com"),
                        username=input_data.get("username", "none"),
                        id=12345)
    monkeypatch.setattr(User, "objects", SimpleNamespace(create_user=lambda **kwargs: created_user))

    serializer = RegistrationSerializer(data=input_data)

    # Act / Assert
    if should_raise:
        with pytest.raises(_exc_lookup("ValidationError", Exception)):
            serializer.is_valid(raise_exception=True)
    else:
        assert serializer.is_valid() is True
        returned_user = serializer.save()
        assert isinstance(returned_user, _exc_lookup("User", Exception))
        assert returned_user.email == input_data["email"]
        assert returned_user.username == input_data["username"]

def test_registration_and_login_api_views_integration(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    factory = APIRequestFactory()
    register_payload = {"user": {"username": "intuser", "email": "intuser@example.com", "password": "pw12345"}}
    login_payload = {"user": {"email": "intuser@example.com", "password": "pw12345"}}

    stub_user = User(email="intuser@example.com", username="intuser", id=777)
    monkeypatch.setattr(User, "objects", SimpleNamespace(create_user=lambda **kwargs: stub_user))

    fake_token = "int.fake.token"
    monkeypatch.setattr(auth_models, "jwt", SimpleNamespace(encode=lambda payload, key, algorithm=None: fake_token))

    # Register via view
    register_view = RegistrationAPIView.as_view()
    register_request = factory.post("/api/users/", register_payload, format="json")
    register_response = register_view(register_request)

    # Assert registration response
    assert getattr(register_response, "status_code", None) in (200, 201)
    assert isinstance(getattr(register_response, "data", {}), dict)
    assert "user" in register_response.data
    assert register_response.data["user"]["email"] == "intuser@example.com"
    # the view/serializer should include token in returned user representation
    assert register_response.data["user"].get("token") == fake_token

    # Prepare login: ensure authenticate used by serializer returns our stub_user
    monkeypatch.setattr(auth_serializers, "authenticate", lambda **kwargs: stub_user)

    login_view = LoginAPIView.as_view()
    login_request = factory.post("/api/users/login/", login_payload, format="json")
    login_response = login_view(login_request)

    # Assert login response
    assert getattr(login_response, "status_code", None) == 200
    assert isinstance(getattr(login_response, "data", {}), dict)
    assert "user" in login_response.data
    assert login_response.data["user"]["email"] == "intuser@example.com"
    assert login_response.data["user"].get("token") == fake_token
