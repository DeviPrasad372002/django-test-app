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
    import pytest
    from unittest import mock

    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.articles import signals as article_signals
    from conduit.apps.articles.views import CommentsDestroyAPIView
except ImportError:
    import pytest
    pytest.skip("Required application modules not available", allow_module_level=True)

def _exc_lookup(name, default=Exception):
    return getattr(builtins, name, default)

@pytest.mark.parametrize(
    "method,email,password,expect_error",
    [
        ("create_user", "alice@example.com", "s3cr3t", False),
        ("create_superuser", "admin@example.com", "adminpass", False),
        ("create_user", "", "nopass", True),
        ("create_superuser", None, "nopass", True),
    ],
)
def test_user_manager_create_user_and_superuser_token_and_fullname(method, email, password, expect_error):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = auth_models.UserManager()

    # Act / Assert
    if expect_error:
        with pytest.raises(_exc_lookup("ValueError", Exception)):
            getattr(manager, method)(email=email, password=password)
    else:
        user = getattr(manager, method)(email=email, password=password)
        # Assert returned object has expected attributes and behavior
        assert getattr(user, "email", None) is not None
        assert isinstance(getattr(user, "email"), str)
        token_value = getattr(user, "token", None)
        # token may be a property or method
        if callable(token_value):
            token_value = token_value()
        assert isinstance(token_value, _exc_lookup("str", Exception)) and token_value != ""
        full_name = getattr(user, "get_full_name", None)
        assert callable(full_name)
        assert isinstance(full_name(), str)

@pytest.mark.parametrize("token_is_valid", [True, False])
def test_jwt_authentication__authenticate_credentials_handles_valid_and_invalid_tokens(monkeypatch, token_is_valid):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth_backend = JWTAuthentication()
    provided_token = "dummy-token-value"

    # Prepare fake user object and manager
    class DummyUser:
        def __init__(self, pk, active=True):
            self.id = pk
            self.pk = pk
            self.is_active = active

        def __repr__(self):
            return f"<DummyUser {self.pk}>"

    class DummyManager:
        def get(self, pk):
            if pk == 999:
                raise Exception("not found")
            return DummyUser(pk, active=True)

    monkeypatch.setattr(auth_models, "User", auth_models.User, raising=False)
    # Attach dummy manager to User to simulate ORM lookup: User.objects.get(pk=...)
    try:
        original_objects = getattr(auth_models.User, "objects")
    except Exception:
        original_objects = None
    monkeypatch.setattr(auth_models.User, "objects", DummyManager(), raising=False)

    # Monkeypatch jwt.decode used inside _authenticate_credentials
    if token_is_valid:
        def fake_decode(token, key, algorithms):
            return {"user_id": 42}
        monkeypatch.setattr("jwt.decode", fake_decode, raising=False)
    else:
        def fake_decode_raises(token, key, algorithms):
            raise Exception("invalid token")
        monkeypatch.setattr("jwt.decode", fake_decode_raises, raising=False)

    # Act / Assert
    if token_is_valid:
        result = auth_backend._authenticate_credentials(provided_token)
        # Expect a user object and original token returned (or similar tuple)
        assert result is not None
        # If tuple-like (user, token) or single user allowed
        if isinstance(result, _exc_lookup("tuple", Exception)):
            user_obj, returned_token = result
            assert getattr(user_obj, "id", None) == 42
            assert returned_token == provided_token
        else:
            user_obj = result
            assert getattr(user_obj, "id", None) == 42
    else:
        with pytest.raises(_exc_lookup("Exception", Exception)):
            auth_backend._authenticate_credentials(provided_token)

def test_add_slug_to_article_if_not_exists_creates_slug_and_saves(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    saved_calls = {"count": 0}
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

        def save(self, *args, **kwargs):
            saved_calls["count"] += 1

    dummy = DummyArticle(title="Hello World", slug=None)

    # Force deterministic slug creation
    monkeypatch.setattr(article_signals, "slugify", lambda text: "hello-world", raising=False)

    # Act
    article_signals.add_slug_to_article_if_not_exists(sender=None, instance=dummy)

    # Assert
    assert dummy.slug == "hello-world"
    assert saved_calls["count"] == 1

@pytest.mark.parametrize("initial_slug,expect_deleted,expect_exception", [
    (None, True, False),    # normal delete flow: object exists and is deleted
    ("already", True, False), # even if slug exists, deletion flow unaffected for CommentsDestroyAPIView
    (None, False, True),    # simulate object retrieval error -> exception propagated
])
def test_comments_destroy_api_view_delete_flow(monkeypatch, initial_slug, expect_deleted, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = CommentsDestroyAPIView()
    delete_called = {"flag": False}

    class DummyComment:
        def __init__(self, pk, slug_val):
            self.pk = pk
            self.slug = slug_val

        def delete(self):
            delete_called["flag"] = True

    # Fake request object minimal shape
    class DummyRequest:
        def __init__(self):
            self.user = None

    request = DummyRequest()

    if expect_exception:
        def fake_get_object():
            raise Exception("not found")
        monkeypatch.setattr(view, "get_object", fake_get_object, raising=False)
    else:
        def fake_get_object():
            return DummyComment(pk=1, slug_val=initial_slug)
        monkeypatch.setattr(view, "get_object", fake_get_object, raising=False)

    # Act / Assert
    if expect_exception:
        with pytest.raises(_exc_lookup("Exception", Exception)):
            view.delete(request, pk="1")
        assert not delete_called["flag"]
    else:
        response = view.delete(request, pk="1")
        # view.delete typically returns a Response; check deletion occurred and response exists
        assert delete_called["flag"] is True
        assert response is not None
        # If it's a DRF Response, it should have a status_code attribute; accept common codes
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            assert status_code in (200, 204)
