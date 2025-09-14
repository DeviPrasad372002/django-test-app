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

import pytest
from types import SimpleNamespace

try:
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles import signals as articles_signals_module
    from conduit.apps.core.exceptions import _handle_generic_error
    from conduit.apps.core import exceptions as core_exceptions_module
    from conduit.apps.authentication.models import UserManager
except ImportError as e:
    pytest.skip(f"Missing import: {e}", allow_module_level=True)


def test_add_slug_to_article_if_not_exists_creates_slug_when_missing_and_preserves_existing(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_instance = SimpleNamespace(title="My Awesome Article", slug="")
    preexisting_instance = SimpleNamespace(title="Other Title", slug="already-set")

    # Replace slugify and generate_random_string with deterministic implementations
    monkeypatch.setattr(articles_signals_module, "slugify", lambda text: "my-awesome-article")
    monkeypatch.setattr(articles_signals_module, "generate_random_string", lambda length=6: "RND123")

    # Act: when slug is missing
    add_slug_to_article_if_not_exists(sender=None, instance=created_instance, created=True)
    # Act: when slug already exists
    add_slug_to_article_if_not_exists(sender=None, instance=preexisting_instance, created=True)

    # Assert
    assert isinstance(created_instance.slug, str)
    assert created_instance.slug == "my-awesome-article-RND123"
    assert preexisting_instance.slug == "already-set"


@pytest.mark.parametrize(
    "exc_obj, expected_status, expected_fragment",
    [
        (Exception("unexpected failure"), 500, "unexpected failure"),
        (RuntimeError("runtime issue"), 500, "runtime issue"),
    ],
)
def test_handle_generic_error_returns_response_like_object(monkeypatch, exc_obj, expected_status, expected_fragment):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    captured = {}

    class DummyResponse:
        def __init__(self, data=None, status=None):
            captured["data"] = data
            captured["status"] = status
            self.data = data
            self.status_code = status

    # Monkeypatch the Response used in the module to capture what is produced
    monkeypatch.setattr(core_exceptions_module, "Response", DummyResponse)

    # Act
    response_like = _handle_generic_error(exc_obj, {})

    # Assert
    assert isinstance(response_like, _exc_lookup("DummyResponse", Exception))
    assert captured["status"] == expected_status
    # Ensure the error message is included in the response data in some form
    assert isinstance(captured["data"], dict)
    joined = " ".join(str(v) for v in captured["data"].values())
    assert expected_fragment in joined


@pytest.mark.parametrize(
    "email, username, password, expect_error",
    [
        ("user@example.com", "user1", "s3cr3t", False),
        ("USER@Example.COM", "user2", "pwd", False),
        (None, "noemail", "pw", True),
        ("", "empty", "pw", True),
    ],
)
def test_user_manager_create_user_and_create_superuser_behaviour(email, username, password, expect_error):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_records = {}

    class DummyUser:
        def __init__(self, email=None, username=None, **kwargs):
            self.email = email
            self.username = username
            # Accept and store any flags passed (is_staff, is_superuser, is_active)
            for k, v in kwargs.items():
                setattr(self, k, v)
            self.password_set = False

        def set_password(self, raw):
            self.password_set = True
            self._password = raw

        def save(self):
            # emulate saving by storing into created_records for inspection
            created_records["last"] = self

    # Instantiate the real UserManager but swap out its model for our dummy
    manager = UserManager()
    manager.model = DummyUser

    # Act / Assert for create_user
    if expect_error:
        with pytest.raises(_exc_lookup("ValueError", Exception)):
            manager.create_user(email=email, username=username, password=password)
    else:
        user_obj = manager.create_user(email=email, username=username, password=password)
        # Assert basic properties
        assert isinstance(user_obj, _exc_lookup("DummyUser", Exception))
        assert user_obj.password_set is True
        assert "@" in user_obj.email.lower()

        # Act: create_superuser should set is_staff and is_superuser
        superuser = manager.create_superuser(email="admin@example.com", username="admin", password="adminpw")
        assert isinstance(superuser, _exc_lookup("DummyUser", Exception))
        assert getattr(superuser, "is_staff", False) is True
        assert getattr(superuser, "is_superuser", False) is True
        assert getattr(superuser, "is_active", True) is True
