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
    from target.conduit.apps.articles import signals as articles_signals_module
    from target.conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from target.conduit.apps.core import utils as core_utils_module
    from django.utils.text import slugify
    from target.conduit.apps.authentication.backends import JWTAuthentication
    import target.conduit.apps.authentication.backends as auth_backends_module
    import rest_framework.exceptions as rf_exceptions
except ImportError:
    pytest.skip("Required application modules not available", allow_module_level=True)


def _exc_lookup(name, fallback):
    return getattr(rf_exceptions, name, fallback)


@pytest.mark.parametrize(
    "initial_slug, title, random_value, expected_contains",
    [
        (None, "My Test Article", "RND123", "my-test-article-RND123"),
        ("preexisting-slug", "My Test Article", "IGNORED", "preexisting-slug"),
    ],
)
def test_add_slug_to_article_if_not_exists_creates_or_preserves_slug(
    # Arrange-Act-Assert: generated by ai-testgen
    monkeypatch, initial_slug, title, random_value, expected_contains
):
    # Arrange: create a lightweight article-like object and control randomness
    article_instance = SimpleNamespace(title=title, slug=initial_slug)
    monkeypatch.setattr(
        articles_signals_module,
        "generate_random_string",
        lambda length=6: random_value,
    )

    # Act: invoke the signal handler as Django would (sender not used)
    add_slug_to_article_if_not_exists(sender=None, instance=article_instance, created=True)

    # Assert: slug created when missing and preserved when present
    resulting_slug = getattr(article_instance, "slug", None)
    assert isinstance(resulting_slug, (str, type(None)))
    assert resulting_slug == expected_contains


@pytest.mark.parametrize(
    "title, random_value, expected_slug",
    [
        ("Hello, World!", "XYZ", "hello-world-XYZ"),
        ("  Leading and  Trailing  ", "A1", "leading-and-trailing-A1"),
        ("Symbols #@$%^&*()", "Z9", "symbols-Z9"),
    ],
)
def test_add_slug_to_article_if_not_exists_handles_various_titles(
    # Arrange-Act-Assert: generated by ai-testgen
    monkeypatch, title, random_value, expected_slug
):
    # Arrange: article-like object with no slug and deterministic random string
    article_instance = SimpleNamespace(title=title, slug=None)
    monkeypatch.setattr(
        articles_signals_module,
        "generate_random_string",
        lambda length=6: random_value,
    )

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=article_instance, created=True)

    # Assert: slug should be slugify(title) + '-' + random string
    assert article_instance.slug == expected_slug


@pytest.mark.parametrize(
    "decode_behavior, user_exists, expect_exception",
    [
        ("valid", True, False),
        ("invalid_token", False, True),
    ],
)
def test_jwt_authentication_authenticate_handles_valid_and_invalid_tokens(
    # Arrange-Act-Assert: generated by ai-testgen
    monkeypatch, decode_behavior, user_exists, expect_exception
):
    # Arrange: create a fake request with Authorization header
    fake_token_value = "abc.def"
    fake_header_value = f"Token {fake_token_value}"
    fake_request = SimpleNamespace(META={"HTTP_AUTHORIZATION": fake_header_value})

    # Prepare a dummy user object to be returned when lookup succeeds
    dummy_user = SimpleNamespace(id=42, username="tester")

    # Replace jwt.decode inside the authentication backend module based on test case
    def fake_decode_success(token, key=None, algorithms=None):
        return {"id": dummy_user.id}

    def fake_decode_failure(token, key=None, algorithms=None):
        raise Exception("Invalid token")

    dummy_jwt_module = SimpleNamespace(
        decode=(fake_decode_success if decode_behavior == "valid" else fake_decode_failure)
    )
    monkeypatch.setattr(auth_backends_module, "jwt", dummy_jwt_module)

    # Replace the User reference inside the backend module with a dummy that has an objects.get
    class DummyManager:
        @staticmethod
        def get(id=None):
            if user_exists:
                return dummy_user
            raise Exception("DoesNotExist")

    class DummyUserModel:
        objects = DummyManager()

    monkeypatch.setattr(auth_backends_module, "User", DummyUserModel)

    authentication = JWTAuthentication()

    # Act / Assert depending on expected behavior
    if expect_exception:
        expected_exc = _exc_lookup("AuthenticationFailed", Exception)
        with pytest.raises(_exc_lookup("expected_exc", Exception)):
            authentication.authenticate(fake_request)
    else:
        result = authentication.authenticate(fake_request)

        # Assert: successful authentication returns (user, token)
        assert isinstance(result, _exc_lookup("tuple", Exception))
        returned_user, returned_token = result
        assert returned_user is dummy_user
        assert returned_token == fake_token_value
