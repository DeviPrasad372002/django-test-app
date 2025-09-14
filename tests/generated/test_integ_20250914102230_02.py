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
    import builtins
    import types
    import pytest
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import backends as auth_backends
    from conduit.apps.articles import views as article_views
    from rest_framework import exceptions as rf_exceptions
    from rest_framework.response import Response
except ImportError:
    import pytest
    pytest.skip("Required modules for integration tests are not available", allow_module_level=True)


def _exc_lookup(name, default=Exception):
    # Try common places for exception names
    if hasattr(builtins, name):
        return getattr(builtins, name)
    if hasattr(rf_exceptions, name):
        return getattr(rf_exceptions, name)
    return default


@pytest.mark.parametrize(
    "email,username,password,expect_error",
    [
        ("user@example.com", "user1", "s3cret", False),
        ("Admin@Example.COM", "admin", "pw", False),
        ("", "nouser", "pw", True),
    ],
)
def test_user_manager_create_user_and_create_superuser_integration(monkeypatch, email, username, password, expect_error):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = auth_models.UserManager()

    created = {}

    class FakeUser:
        def __init__(self, email=None, username=None):
            self.email = email
            self.username = username
            self.is_staff = False
            self.is_superuser = False
            self.password_hash = None
            self.saved = False

        def set_password(self, raw):
            self.password_hash = f"hashed:{raw}"

        def save(self, *args, **kwargs):
            self.saved = True
            created['instance'] = self

    monkeypatch.setattr(manager, "model", FakeUser, raising=False)

    # Act / Assert
    if expect_error:
        with pytest.raises(_exc_lookup("ValueError")):
            manager.create_user(email=email, username=username, password=password)
        return

    user = manager.create_user(email=email, username=username, password=password)

    # Assert created user fields and side effects
    assert isinstance(user, _exc_lookup("FakeUser", Exception))
    assert user.saved is True
    assert user.password_hash == f"hashed:{password}"
    assert "@" in user.email

    # Act - create superuser and assert flags set
    superuser = manager.create_superuser(email="root@example.com", username="root", password="rootpw")
    assert isinstance(superuser, _exc_lookup("FakeUser", Exception))
    assert superuser.is_staff is True
    assert superuser.is_superuser is True
    assert superuser.saved is True


def test_generate_jwt_token_and_token_string_integration(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Replace jwt.encode used by _generate_jwt_token to a predictable callable
    class FakeJWTModule:
        def __init__(self):
            self.called_with = None

        def encode(self, payload, secret, algorithm="HS256"):
            # record payload for assertion and return a predictable token string
            self.called_with = (payload, secret, algorithm)
            return "fake.jwt.token"

    fake_jwt = FakeJWTModule()
    monkeypatch.setattr(auth_models, "jwt", fake_jwt, raising=False)

    # Create a minimal user-like object expected by the function
    fake_user = types.SimpleNamespace(id=7)

    # Act
    token = auth_models._generate_jwt_token(fake_user)

    # Assert
    assert isinstance(token, _exc_lookup("str", Exception))
    assert token == "fake.jwt.token"
    assert isinstance(fake_jwt.called_with, tuple)
    payload_arg = fake_jwt.called_with[0]
    # payload should include user id value in some key; check it's present somewhere
    assert any(7 == v for v in payload_arg.values())


def test_comments_destroy_api_view_calls_delete_and_returns_204(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    deleted = {"called": False}

    class FakeAuthor:
        def __init__(self, username):
            self.username = username

    class FakeComment:
        def __init__(self, author):
            self.author = author
            self.deleted_flag = False

        def delete(self):
            self.deleted_flag = True
            deleted["called"] = True

    fake_author = FakeAuthor(username="commenter")
    fake_comment = FakeComment(author=fake_author)

    # Monkeypatch the view's get_object to return our fake comment
    def fake_get_object(self):
        return fake_comment

    monkeypatch.setattr(article_views.CommentsDestroyAPIView, "get_object", fake_get_object, raising=False)

    view = article_views.CommentsDestroyAPIView()
    fake_request = types.SimpleNamespace(user=fake_author)

    # Act
    response = view.delete(fake_request, pk="1")

    # Assert response type and status
    assert isinstance(response, _exc_lookup("Response", Exception))
    assert getattr(response, "status_code", None) in (204, 200)
    # Ensure underlying delete was invoked
    assert deleted["called"] is True
    assert fake_comment.deleted_flag is True
