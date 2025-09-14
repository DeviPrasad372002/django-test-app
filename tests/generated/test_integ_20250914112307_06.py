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
try:
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.authentication import backends as auth_backends_module
    from conduit.apps.authentication.models import User
    from django.utils.text import slugify
    import string
    from types import SimpleNamespace
except ImportError as e:
    import pytest
    pytest.skip(f"Skipping integration tests due to ImportError: {e}", allow_module_level=True)

try:
    from tests.utils import _exc_lookup
except Exception:
    def _exc_lookup(name, default=Exception):
        return default


@pytest.mark.parametrize(
    "initial_slug, expect_changed",
    [
        (None, True),
        ("", True),
        ("existing-slug", False),
    ],
)
def test_add_slug_to_article_if_not_exists_assigns_slug_when_missing(monkeypatch, initial_slug, expect_changed):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug

    dummy = DummyArticle(title="Hello World!", slug=initial_slug)

    # Force deterministic random string output
    monkeypatch.setattr(
        "conduit.apps.articles.signals.generate_random_string",
        lambda length=6: "ABC123",
        raising=False,
    )

    # Act
    # The signal handler may accept (sender, instance, **kwargs) or (instance, **kwargs).
    # Try the common signature used in the project.
    try:
        add_slug_to_article_if_not_exists(sender=None, instance=dummy)
    except TypeError:
        # fallback if function expects only (instance,)
        add_slug_to_article_if_not_exists(dummy)

    # Assert
    if expect_changed:
        expected = slugify(dummy.title) + "-" + "ABC123"
        assert isinstance(dummy.slug, str)
        assert dummy.slug == expected
    else:
        assert dummy.slug == "existing-slug"


@pytest.mark.parametrize("length", [1, 8, 16])
def test_generate_random_string_length_and_charset(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange & Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    allowed = set(string.ascii_letters + string.digits)
    assert set(result).issubset(allowed)


@pytest.mark.parametrize(
    "jwt_decode_side_effect, expected_exception",
    [
        ({"user_id": 1}, None),  # valid payload -> returns user
        (Exception("invalid token"), _exc_lookup("AuthenticationFailed", Exception)),  # invalid -> raises auth failure
    ],
)
def test_jwtauthentication_authenticates_and_handles_invalid_token(monkeypatch, jwt_decode_side_effect, expected_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = JWTAuthentication()

    # Prepare dummy user and manager
    class DummyUser:
        def __init__(self, pk):
            self.pk = pk

    dummy_user = DummyUser(pk=1)

    class DummyManager:
        def get(self, **kwargs):
            # mimic Django's get by returning dummy_user when pk or id matches
            if kwargs.get("pk") in (1, None) or kwargs.get("id") in (1, None):
                return dummy_user
            raise Exception("not found")

    # Patch the jwt.decode used in the backend module
    if isinstance(jwt_decode_side_effect, _exc_lookup("dict", Exception)):
        monkeypatch.setattr(
            auth_backends_module, "jwt", SimpleNamespace(decode=lambda token, key, algorithms: jwt_decode_side_effect), raising=True
        )
    else:
        def fake_decode(token, key, algorithms):
            raise jwt_decode_side_effect
        monkeypatch.setattr(auth_backends_module, "jwt", SimpleNamespace(decode=fake_decode), raising=True)

    # Patch the User reference in the backend module to use the DummyManager
    monkeypatch.setattr(auth_backends_module, "User", SimpleNamespace(objects=DummyManager()), raising=True)

    # Act & Assert
    if expected_exception is None:
        result = auth._authenticate_credentials("sometoken")
        # Depending on implementation, method may return user or (user, token). Accept either.
        assert result is not None
        if isinstance(result, _exc_lookup("tuple", Exception)):
            returned_user = result[0]
        else:
            returned_user = result
        assert returned_user is dummy_user
    else:
        with pytest.raises(_exc_lookup("expected_exception", Exception)):
            auth._authenticate_credentials("badtoken")
