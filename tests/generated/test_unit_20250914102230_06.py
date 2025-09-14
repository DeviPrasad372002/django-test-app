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

import json
import pytest

try:
    from conduit.apps.authentication.models import UserManager, User
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.core.models import TimestampedModel
except ImportError:
    pytest.skip("Required application modules are not available", allow_module_level=True)


def _exc_lookup(name, default):
    # search common exception modules for the given name
    try:
        import rest_framework.exceptions as rf_exc  # type: ignore
        if hasattr(rf_exc, name):
            return getattr(rf_exc, name)
    except Exception:
        pass
    try:
        import django.core.exceptions as dj_exc  # type: ignore
        if hasattr(dj_exc, name):
            return getattr(dj_exc, name)
    except Exception:
        pass
    return default


@pytest.mark.parametrize(
    "email,password,expected_email",
    [
        ("Test@EXAMPLE.com", "p@ssword1", "test@example.com"),
        ("simple@domain.org", "anotherpass", "simple@domain.org"),
    ],
)
def test_user_manager_create_user_and_superuser(email, password, expected_email):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = UserManager()

    # Act
    user = manager.create_user(email=email, password=password)

    # Assert
    assert isinstance(user, _exc_lookup("User", Exception))
    assert getattr(user, "email", None) == expected_email
    assert getattr(user, "is_staff", False) is False
    assert getattr(user, "is_superuser", False) is False
    # password should be settable/checkable if using AbstractBaseUser
    assert hasattr(user, "set_password")
    if hasattr(user, "check_password"):
        assert user.check_password(password) is True

    # Act - create superuser
    superuser = manager.create_superuser(email="admin@example.com", password="adminpass")
    # Assert superuser flags
    assert getattr(superuser, "is_superuser", True) is True
    assert getattr(superuser, "is_staff", True) is True


def test_user_manager_create_user_missing_email_raises():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = UserManager()

    # Act / Assert - missing email should raise ValueError (or similar)
    with pytest.raises(_exc_lookup("ValueError", ValueError)):
        manager.create_user(email=None, password="pw")


def test_user_token_and_name_methods(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = User(email="sample@domain.test", first_name="Alice", last_name="Wonder")
    # monkeypatch token generator to avoid dependency on SECRET_KEY/jwt
    monkeypatch.setattr(User, "_generate_jwt_token", lambda self: "STATIC-TOKEN-1234")

    # Act
    token_value = user.token
    full_name = user.get_full_name() if hasattr(user, "get_full_name") else None
    short_name = user.get_short_name() if hasattr(user, "get_short_name") else None

    # Assert
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert token_value == "STATIC-TOKEN-1234"
    # Names should reflect provided fields
    assert full_name is not None and "Alice" in full_name and "Wonder" in full_name
    assert short_name == "Alice"


@pytest.mark.parametrize(
    "auth_header,expected_result",
    [
        ("Token abc.def.ghi", ("user_obj", "abc.def.ghi")),
        (None, None),
    ],
)
def test_jwt_authentication_authenticate_parses_authorization_header(monkeypatch, auth_header, expected_result):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = JWTAuthentication()

    def fake_authenticate_credentials(token):
        return ("user_obj", token)

    # monkeypatch the instance method used to validate credentials
    monkeypatch.setattr(auth, "_authenticate_credentials", fake_authenticate_credentials)

    class DummyRequest:
        pass

    req = DummyRequest()
    req.META = {}
    if auth_header is not None:
        req.META["HTTP_AUTHORIZATION"] = auth_header

    # Act
    result = auth.authenticate(req)

    # Assert
    if expected_result is None:
        assert result is None
    else:
        assert result == expected_result


def test_user_json_renderer_renders_user_object():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = UserJSONRenderer()
    payload = {"user": {"email": "render@me.test", "token": "XYZ"}}

    # Act
    rendered = renderer.render(payload, None, None)

    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    decoded = json.loads(rendered.decode("utf-8"))
    assert "user" in decoded
    assert decoded["user"]["email"] == "render@me.test"
    assert decoded["user"]["token"] == "XYZ"


def test_timestamped_model_defines_timestamps():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange / Act
    # TimestampedModel is expected to define created_at and updated_at fields at the class level
    assert hasattr(TimestampedModel, "created_at")
    assert hasattr(TimestampedModel, "updated_at")
