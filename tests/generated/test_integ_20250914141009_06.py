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

import pytest
from types import SimpleNamespace
import json

try:
    import conduit.apps.authentication.serializers as auth_serializers
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.renderers as auth_renderers
    import conduit.apps.authentication.backends as auth_backends
    import rest_framework.exceptions as rf_exceptions
except ImportError:
    pytest.skip("conduit.authentication modules not available", allow_module_level=True)


def _exc_lookup(name, default):
    try:
        return getattr(rf_exceptions, name)
    except Exception:
        return default


def test_registration_serializer_calls_create_user_and_user_serializer_produces_expected_fields(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    input_data = {"username": "alice", "email": "alice@example.com", "password": "s3cr3t"}
    created_kwargs = {}

    fake_user = SimpleNamespace(username="alice", email="alice@example.com", bio=None, image=None)
    # Provide a token attribute that's accessed by UserSerializer
    setattr(fake_user, "token", "fake.jwt.token")

    def fake_create_user(**kwargs):
        created_kwargs.update(kwargs)
        return fake_user

    # Act - monkeypatch the create_user on the User manager
    monkeypatch.setattr(auth_models.User, "objects", auth_models.User.objects, raising=False)
    monkeypatch.setattr(auth_models.User.objects, "create_user", fake_create_user, raising=False)

    serializer = auth_serializers.RegistrationSerializer(data=input_data)
    is_valid_result = serializer.is_valid()
    assert is_valid_result is True  # Assert validation passes

    saved_user = serializer.save()

    # Assert - creation was called with expected fields and returned object used
    assert saved_user is fake_user
    assert created_kwargs.get("username") == "alice"
    assert created_kwargs.get("email") == "alice@example.com"
    assert "password" in created_kwargs

    # Further integration: the UserSerializer should produce a representation including token and email
    representation = auth_serializers.UserSerializer(saved_user).data
    assert isinstance(representation, _exc_lookup("dict", Exception))
    assert representation.get("email") == "alice@example.com"
    assert representation.get("token") == "fake.jwt.token"


@pytest.mark.parametrize("authenticate_returns_user,expect_user_in_validated", [
    (True, True),
    (False, False),
])
def test_login_serializer_uses_authenticate_and_userserializer(monkeypatch, authenticate_returns_user, expect_user_in_validated):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    input_data = {"email": "bob@example.com", "password": "hunter2"}

    fake_user = SimpleNamespace(username="bob", email="bob@example.com", bio=None, image=None)
    setattr(fake_user, "token", "login.jwt.token")

    def fake_authenticate(username=None, password=None):
        # Simulate authenticate called with username=email
        assert username == "bob@example.com"
        assert password == "hunter2"
        return fake_user if authenticate_returns_user else None

    # Act - monkeypatch the authenticate function used by the serializer module
    monkeypatch.setattr(auth_serializers, "authenticate", fake_authenticate, raising=False)

    serializer = auth_serializers.LoginSerializer(data=input_data)
    is_valid = serializer.is_valid()

    if expect_user_in_validated:
        assert is_valid is True
        validated_user = serializer.validated_data.get("user")
        assert validated_user is fake_user
        # Integration check: the UserSerializer produces token in its output
        user_repr = auth_serializers.UserSerializer(validated_user).data
        assert user_repr.get("email") == "bob@example.com"
        assert user_repr.get("token") == "login.jwt.token"
    else:
        # When authenticate returns None, validation should fail
        assert is_valid is False
        # The serializer errors should indicate credentials issue
        assert "non_field_errors" in serializer.errors or "email" in serializer.errors or "password" in serializer.errors


@pytest.mark.parametrize("payload, user_exists, raises_expected", [
    ({"id": 7}, True, None),
    ({}, False, _exc_lookup("AuthenticationFailed", Exception)),
])
def test_jwt_authentication__authenticate_credentials_parametrized(monkeypatch, payload, user_exists, raises_expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    backend = auth_backends.JWTAuthentication()

    fake_user = SimpleNamespace(pk=7, username="charlie", email="charlie@example.com")
    # Provide attributes that may be accessed downstream
    setattr(fake_user, "is_active", True)

    def fake_get(pk):
        if user_exists:
            return fake_user
        else:
            raise auth_models.User.DoesNotExist()

    # Act - monkeypatch User.objects.get used by authentication backend
    monkeypatch.setattr(auth_models.User, "objects", auth_models.User.objects, raising=False)
    monkeypatch.setattr(auth_models.User.objects, "get", lambda **kwargs: fake_get(kwargs.get("pk") or kwargs.get("id")), raising=False)

    if raises_expected is None:
        # Act
        result = backend._authenticate_credentials(payload)
        # Assert
        assert result is fake_user
    else:
        # Expect an authentication-related exception
        with pytest.raises(_exc_lookup("raises_expected", Exception)):
            backend._authenticate_credentials(payload)
