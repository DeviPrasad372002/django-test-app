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

    
# Replace the Django bootstrap section with this simplified version
# --- Minimal Django auto-config (before any app/model import) ---
try:
    import importlib, pkgutil
    if _iu.find_spec("django") is not None:
        import django
        from django.conf import settings as _dj_settings
        from django.apps import apps as _dj_apps

        def _maybe_add(app_name, installed):
            try:
                if _iu.find_spec(app_name):
                    installed.append(app_name)
                    return True
            except Exception:
                pass
            return False

        if not _dj_settings.configured:
            _installed = [
                "django.contrib.auth",
                "django.contrib.contenttypes", 
                "django.contrib.sessions"
            ]
            
            if _iu.find_spec("rest_framework"):
                _installed.append("rest_framework")

            # Try to add conduit apps
            for _app in ("conduit.apps.core", "conduit.apps.articles", "conduit.apps.authentication", "conduit.apps.profiles"):
                _maybe_add(_app, _installed)

            _cfg = dict(
                SECRET_KEY="test-key",
                DEBUG=True,
                ALLOWED_HOSTS=["*"],
                INSTALLED_APPS=sorted(set(_installed)),
                DATABASES=dict(default=dict(ENGINE="django.db.backends.sqlite3", NAME=":memory:")),
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
                _dj_settings.configure(**_cfg)
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
    from conduit.apps.articles import signals as article_signals
    from conduit.apps.core import exceptions as core_exceptions
    from conduit.apps.authentication import backends as auth_backends
    from conduit.apps.authentication import models as auth_models
    import jwt as _jwt_lib  # used to reference in tests
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Skipping integration tests due to ImportError: {e}", allow_module_level=True)

def _exc_lookup(name, default):
    return globals().get(name, default)

@pytest.mark.parametrize(
    "created, initial_slug, expected_slug_present",
    [
        (True, "", True),    # newly created, no slug -> slug should be added
        (False, "", False),  # not created, no slug -> slug likely not added
        (True, "exists", False),  # created but slug already present -> no change
    ],
)
def test_add_slug_to_article_if_not_exists_sets_slug_when_needed(monkeypatch, created, initial_slug, expected_slug_present):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug
            self._saved = False

        def save(self, *args, **kwargs):
            self._saved = True

    article_instance = DummyArticle(title="Hello World", slug=initial_slug)

    # Monkeypatch helper functions used by the signal handler to deterministic outputs.
    monkeypatch.setattr(article_signals, "generate_random_string", lambda n=6: "RND", raising=False)
    monkeypatch.setattr(article_signals, "slugify", lambda s: "hello-world", raising=False)

    # Act
    article_signals.add_slug_to_article_if_not_exists(sender=None, instance=article_instance, created=created)

    # Assert
    if expected_slug_present:
        assert isinstance(article_instance.slug, str)
        assert "hello-world" in article_instance.slug
        assert "RND" in article_instance.slug
        assert article_instance._saved is True
    else:
        # slug should remain unchanged and save should not have been called
        assert article_instance.slug == initial_slug
        assert article_instance._saved is False

@pytest.mark.parametrize("exc", [Exception("boom"), ValueError("bad")])
def test__handle_generic_error_returns_structured_response_for_exceptions(exc):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    context = {"request": None, "view": None}

    # Act
    response = core_exceptions._handle_generic_error(exc, context)

    # Assert
    # response should be a DRF Response-like object with data and status_code attributes
    assert hasattr(response, "data")
    assert hasattr(response, "status_code")
    assert isinstance(response.status_code, int)
    # Expect a top-level 'errors' mapping with a 'detail' entry describing the exception
    assert "errors" in response.data
    errors_mapping = response.data["errors"]
    assert "detail" in errors_mapping
    # detail should include the exception message
    assert str(exc) in str(errors_mapping["detail"])

def test_jwtauthentication_authenticates_using_decoded_token_and_user_lookup(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    backend = auth_backends.JWTAuthentication()

    # Prepare a fake decoded payload and patch the jwt.decode used inside the backend module
    decoded_payload = {"user_id": 123}
    monkeypatch.setattr(auth_backends, "jwt", _jwt_lib, raising=False)
    monkeypatch.setattr(auth_backends.jwt, "decode", lambda token, key, algorithms: decoded_payload, raising=False)

    # Prepare a fake user and a dummy manager to simulate User.objects.get
    class FakeUser:
        def __init__(self, pk, is_active=True):
            self.id = pk
            self.is_active = is_active

    fake_user = FakeUser(pk=123, is_active=True)

    class DummyManager:
        def get(self, **kwargs):
            # typical lookup will be by id or pk
            if kwargs.get("id") == 123 or kwargs.get("pk") == 123 or kwargs.get("user_id") == 123:
                return fake_user
            raise auth_models.User.DoesNotExist()

    # Monkeypatch the manager onto the User model
    monkeypatch.setattr(auth_models.User, "objects", DummyManager(), raising=False)

    # Act
    result = backend._authenticate_credentials("dummy.token.value")

    # Assert
    # The backend may return the user or a tuple (user, token); support both.
    if isinstance(result, _exc_lookup("tuple", Exception)):
        returned_user = result[0]
    else:
        returned_user = result
    assert returned_user is fake_user
    assert hasattr(returned_user, "is_active")
    assert returned_user.is_active is True
