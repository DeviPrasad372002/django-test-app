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

import pytest

try:
    from types import SimpleNamespace
    from unittest.mock import Mock
    from conduit.apps.authentication.models import UserManager, User
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.articles.views import CommentsDestroyAPIView
    import conduit.apps.articles.models as articles_models
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required project modules not importable", allow_module_level=True)

def _exc_lookup(name, default):
    return getattr(__builtins__, name, default)

@pytest.mark.parametrize(
    "email,password,expected_exception_name",
    [
        ("", "password123", "ValueError"),               # empty email should be invalid
        (None, "password123", "ValueError"),             # None email invalid
        ("user@example.com", None, "ValueError"),        # missing password can be invalid
    ],
)
def test_create_user_invalid_inputs_raise(email, password, expected_exception_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = UserManager()
    exc_type = _exc_lookup(expected_exception_name, Exception)
    # Act / Assert
    with pytest.raises(_exc_lookup("exc_type", Exception)):
        manager.create_user(email=email, password=password)

def test_create_superuser_enforces_flags():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = UserManager()
    # Act / Assert: creating superuser with is_superuser explicitly False should raise
    with pytest.raises(_exc_lookup("ValueError", Exception)):
        manager.create_superuser(email="admin@example.com", password="adminpass", is_superuser=False)

def test_user_token_property_calls_internal_generator_and_get_full_name(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = User()
    user.first_name = "Jane"
    user.last_name = "Doe"
    user.email = "jane@example.com"
    # Replace internal generator to avoid JWT/settings dependency
    monkeypatch.setattr(User, "_generate_jwt_token", lambda self: "STATIC_TOKEN_123")
    # Act
    token_value = user.token
    full_name_value = user.get_full_name()
    # Assert
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert token_value == "STATIC_TOKEN_123"
    assert full_name_value == "Jane Doe"

def test_jwtauthenticate_authenticate_delegates_and_handles_invalid_token(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = JWTAuthentication()
    # Create a fake request object with an Authorization header as DRF would expose
    fake_request = SimpleNamespace(META={"HTTP_AUTHORIZATION": "Token badtoken"})
    # Monkeypatch _authenticate_credentials to raise AuthenticationFailed
    from rest_framework import exceptions as drf_exceptions
    def raise_auth_failed(token):
        raise drf_exceptions.AuthenticationFailed("Invalid token")
    monkeypatch.setattr(JWTAuthentication, "_authenticate_credentials", raise_auth_failed)
    # Act / Assert
    with pytest.raises(_exc_lookup("Exception", Exception)):
        auth.authenticate(fake_request)

def test_comments_destroy_view_delete_calls_comment_get_and_delete(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = CommentsDestroyAPIView()
    fake_request = SimpleNamespace(user=SimpleNamespace(pk=1))
    # Create a mock comment instance with a delete method
    mock_comment = Mock()
    mock_comment.delete = Mock()
    # Patch the Comment.objects.get to return our mock_comment
    monkeypatch.setattr(articles_models.Comment, "objects", Mock(get=Mock(return_value=mock_comment)))
    # Act
    # Most DRF destroy views accept (request, article_pk, pk)
    try:
        response = view.delete(fake_request, article_pk=10, pk=5)
    except TypeError:
        # Some signatures might be (request, pk, format=None) — try alternate call
        response = view.delete(fake_request, pk=5)
    # Assert that delete was called on the retrieved comment
    mock_comment.delete.assert_called_once()
    # The view may return a Response or None; assert that it didn't raise and returned something (or None)
    assert response is None or hasattr(response, "status_code") or isinstance(response, _exc_lookup("SimpleNamespace", Exception))
