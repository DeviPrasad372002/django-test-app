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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from types import SimpleNamespace
    import sys

    from target.conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from target.conduit.apps.authentication.backends import JWTAuthentication
    import target.conduit.apps.authentication.backends as auth_backends
    from target.conduit.apps.articles.views import filter_queryset
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Skipping tests due to ImportError: {e}", allow_module_level=True)


def _exc_lookup(name, default):
    try:
        import rest_framework.exceptions as _exc_mod
        return getattr(_exc_mod, name, default)
    except Exception:
        return default


@pytest.mark.parametrize(
    "title,expected_slug",
    [
        ("Hello World!", "hello-world"),
        ("  Leading and trailing  ", "leading-and-trailing"),
        ("Café Münchner Kindl", "caf%C3%A9-m%C3%BCnchner-kindl" if False else "café-münchner-kindl"),  # best-effort expectation (fallback)
    ],
)
def test_add_slug_to_article_if_not_exists_sets_and_preserves_slug(title, expected_slug):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article = SimpleNamespace(title=title, slug=None)
    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=article)
    first_slug = getattr(article, "slug", None)
    # Act again to ensure idempotence
    add_slug_to_article_if_not_exists(sender=None, instance=article)
    second_slug = getattr(article, "slug", None)
    # Assert
    assert first_slug is not None and isinstance(first_slug, _exc_lookup("str", Exception))
    assert second_slug == first_slug
    # Basic slug format expectations: lowercased, no leading/trailing spaces
    assert first_slug == first_slug.strip()
    assert " " not in first_slug


def test_JWTAuthentication__authenticate_credentials_raises_on_invalid_token(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    authenticator = JWTAuthentication()
    # Make jwt.decode raise an error to simulate invalid token
    class DummyJWT:
        def decode(self, *args, **kwargs):
            raise Exception("invalid token")
    monkeypatch.setattr(auth_backends, "jwt", DummyJWT())
    # Act / Assert
    expected_exc = _exc_lookup("AuthenticationFailed", Exception)
    with pytest.raises(_exc_lookup("expected_exc", Exception)):
        # signature may be _authenticate_credentials(self, key)
        authenticator._authenticate_credentials("not_a_valid_token")


@pytest.mark.parametrize(
    "auth_header_key,header_value",
    [
        ("HTTP_AUTHORIZATION", "Token abc.def.ghi"),
        ("Authorization", "Bearer abc.def.ghi"),
    ],
)
def test_JWTAuthentication_authenticate_parses_header_and_delegates(monkeypatch, auth_header_key, header_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    authenticator = JWTAuthentication()
    captured = {}
    def fake_authenticate_credentials(token):
        captured['called_with'] = token
        return ("fake_user", "the_token")
    monkeypatch.setattr(JWTAuthentication, "_authenticate_credentials", staticmethod(fake_authenticate_credentials))
    request = SimpleNamespace(META={auth_header_key: header_value}, headers={auth_header_key: header_value})
    # Act
    result = authenticator.authenticate(request)
    # Assert
    assert result == ("fake_user", "the_token")
    # token extracted should not include scheme prefix
    assert captured['called_with'] == "abc.def.ghi"


def test_filter_queryset_applies_author_and_tag_filters():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class FakeQuerySet:
        def __init__(self):
            self.filters = []
        def filter(self, **kwargs):
            self.filters.append(kwargs)
            return self
    fake_qs = FakeQuerySet()
    view = SimpleNamespace(request=SimpleNamespace(query_params={"author": "alice", "tag": "python"}))
    # Act
    result_qs = filter_queryset(view, fake_qs)
    # Assert
    assert result_qs is fake_qs
    # Expect that at least one filter call was made and that keys reflect author/tag filtering
    assert any("author__username" in f or "author" in f for f in result_qs.filters)
    assert any("tags__name" in f or "tag" in f for f in result_qs.filters)
