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

try:
    import pytest
    import types
    import builtins
    from unittest import mock
    from types import SimpleNamespace
    from conduit.apps.authentication.models import User
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.views import ArticleViewSet
    import jwt as jwt_module
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Skipping tests due to ImportError: {e}", allow_module_level=True)


def test_user_token_and_full_name(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_instance = User()
    user_instance.first_name = "Ada"
    user_instance.last_name = "Lovelace"
    generated_token_value = "fixed-token-123"

    def fake_generate_jwt(self):
        return generated_token_value

    monkeypatch.setattr(User, "_generate_jwt_token", fake_generate_jwt, raising=False)

    # Act
    returned_token = user_instance.token()
    full_name = user_instance.get_full_name()

    # Assert
    assert returned_token == generated_token_value
    assert isinstance(full_name, _exc_lookup("str", Exception))
    assert full_name == "Ada Lovelace"


@pytest.mark.parametrize(
    "payload, expected_user_id, decode_raises, expect_exception",
    [
        ({"user_id": 42}, 42, None, False),  # normal path with 'user_id'
        ({"id": 7}, 7, None, False),  # alternate key 'id'
        (None, None, jwt_module.InvalidTokenError("bad"), True),  # decode fails
    ],
)
def test_jwtauthentication_auth_flow(monkeypatch, payload, expected_user_id, decode_raises, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    jwt_instance = JWTAuthentication()
    fake_token = "sometoken"

    # Prepare a fake user returned by User.objects.get
    fake_user = SimpleNamespace(pk=expected_user_id, username="tester")

    class FakeManager:
        def get(self, **kwargs):
            # Return fake_user for any pk lookup, raise if pk missing
            if "pk" in kwargs or "id" in kwargs:
                return fake_user
            raise LookupError("no such user")

    # Patch jwt.decode
    if decode_raises:
        def fake_decode(token, key, algorithms):
            raise decode_raises
        monkeypatch.setattr(jwt_module, "decode", fake_decode)
    else:
        def fake_decode(token, key, algorithms):
            return payload
        monkeypatch.setattr(jwt_module, "decode", fake_decode)

    # Patch settings import inside backend if used (JWT secret); many implementations pass settings.SECRET_KEY directly to jwt.decode,
    # but our test focuses on decode behavior so no need to patch settings.
    # Patch User.objects.get used inside _authenticate_credentials
    monkeypatch.setattr(User, "objects", FakeManager(), raising=False)

    # Act / Assert
    if expect_exception:
        auth_exc = _exc_lookup("AuthenticationFailed", Exception)
        with pytest.raises(_exc_lookup("auth_exc", Exception)):
            jwt_instance._authenticate_credentials(fake_token)
    else:
        returned = jwt_instance._authenticate_credentials(fake_token)
        # Implementation may return tuple (user, token) or just user; accept both forms
        assert returned is not None
        if isinstance(returned, _exc_lookup("tuple", Exception)):
            returned_user, returned_token = returned
            assert getattr(returned_user, "pk", None) == expected_user_id
            assert returned_token == fake_token
        else:
            assert getattr(returned, "pk", None) == expected_user_id


def test_add_slug_to_article_if_not_exists_generates_slug(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    dummy = DummyArticle(title="Hello World", slug=None)

    # Patch generate_random_string to deterministic value
    monkeypatch.setattr("conduit.apps.core.utils.generate_random_string", lambda length=6: "XYZ", raising=False)

    # Patch slugify from django.utils.text if it exists, else rely on behavior inside function
    try:
        from django.utils.text import slugify as real_slugify
        monkeypatch.setattr("django.utils.text.slugify", lambda s: "hello-world", raising=False)
    except Exception:
        # If django not available, still proceed; add_slug_to_article_if_not_exists might import slugify differently
        pass

    # Act
    add_slug_to_article_if_not_exists(sender=object, instance=dummy)

    # Assert
    assert isinstance(dummy.slug, str)
    # Expect slug contains slugified title and the deterministic random suffix
    assert dummy.slug.startswith("hello-world")
    assert "XYZ" in dummy.slug


@pytest.mark.parametrize(
    "query_params, expected_keys_present",
    [
        ({"tag": "python"}, {"tags__name__in", "tag__name__in"}),
        ({"author": "alice"}, {"author__username"}),
        ({"tag": "t", "author": "bob"}, {"tags__name__in", "author__username", "tag__name__in"}),
        ({}, set()),
    ],
)
def test_articleviewset_filter_queryset_calls_underlying_queryset(query_params, expected_keys_present, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = ArticleViewSet()
    view.request = SimpleNamespace(GET=query_params)

    class FakeQS:
        def __init__(self):
            self.called_filters = []
            self.ordered = False

        def filter(self, **kwargs):
            self.called_filters.append(kwargs)
            return self

        def order_by(self, *args, **kwargs):
            self.ordered = True
            return self

    fake_qs = FakeQS()

    # Act
    returned_qs = view.filter_queryset(fake_qs)

    # Assert
    # returned_qs should be the same fake_qs (method chaining)
    assert returned_qs is fake_qs
    # Ensure order_by was called (typical behavior to order articles by '-created_at')
    assert fake_qs.ordered is True or fake_qs.ordered == True
    # Collect all keys used in filter calls
    used_keys = set().union(*(set(d.keys()) for d in fake_qs.called_filters)) if fake_qs.called_filters else set()
    # If no query params provided we expect no filter keys
    if expected_keys_present:
        # At least one of the expected keys should be present in the used keys
        assert bool(used_keys & expected_keys_present) is True
    else:
        assert used_keys == set()
