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
    import json
    from types import SimpleNamespace
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles import signals as articles_signals
except ImportError as _err:
    import pytest as _pytest
    _pytest.skip(f"Skipping tests due to ImportError: {_err}", allow_module_level=True)


def _exc_lookup(name, default):
    try:
        return globals().get(name) or __import__('builtins').__dict__.get(name) or default
    except Exception:
        return default


def test_article_json_renderer_wraps_article_key_and_returns_bytes():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = ArticleJSONRenderer()
    sample_payload = {"title": "Hello World", "body": "content"}
    expected_outer_key = "article"

    # Act
    result_bytes = renderer.render(sample_payload, media_type="application/json", renderer_context={})

    # Assert
    assert isinstance(result_bytes, (bytes, bytearray))
    decoded = result_bytes.decode("utf-8")
    parsed = json.loads(decoded)
    assert expected_outer_key in parsed
    assert parsed[expected_outer_key] == sample_payload


@pytest.mark.parametrize(
    "input_value, expected_key",
    [
        ({"id": 1, "body": "one comment"}, "comment"),
        ([{"id": 1, "body": "one"}, {"id": 2, "body": "two"}], "comments"),
    ],
)
def test_comment_json_renderer_handles_single_and_list(input_value, expected_key):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = CommentJSONRenderer()

    # Act
    result = renderer.render(input_value, media_type="application/json", renderer_context={})

    # Assert
    assert isinstance(result, (bytes, bytearray))
    parsed = json.loads(result.decode("utf-8"))
    assert expected_key in parsed
    assert parsed[expected_key] == input_value


def test_add_slug_to_article_if_not_exists_does_not_override_existing_slug(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyInstance:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug
            self.saved = False

        def save(self, *args, **kwargs):
            self.saved = True

    dummy = DummyInstance(title="Some Title", slug="existing-slug")

    # Ensure slugify and generate_random_string are present but should not be used to override
    monkeypatch.setattr(articles_signals, "slugify", lambda s: "won't-be-used")
    monkeypatch.setattr(articles_signals, "generate_random_string", lambda n=6: "XXXXXX")

    # Provide a fake Article manager to avoid DB access (not used in this path)
    class DummyManager:
        @staticmethod
        def filter(**kwargs):
            return []

    monkeypatch.setattr(articles_signals, "Article", SimpleNamespace(objects=DummyManager()))

    # Act
    articles_signals.add_slug_to_article_if_not_exists(sender=None, instance=dummy)

    # Assert
    assert dummy.slug == "existing-slug"


def test_add_slug_to_article_if_not_exists_generates_when_missing(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyInstance:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug
            self.saved = False

        def save(self, *args, **kwargs):
            self.saved = True

    dummy = DummyInstance(title="My Fancy Title", slug=None)

    # Control slugify and random generator to produce deterministic output
    monkeypatch.setattr(articles_signals, "slugify", lambda s: "my-fancy-title")
    monkeypatch.setattr(articles_signals, "generate_random_string", lambda n=6: "RND123")

    # Fake Article manager: no existing slugs -> unique
    class DummyManager:
        @staticmethod
        def filter(**kwargs):
            # Simulate no existing slugs found
            return []

    monkeypatch.setattr(articles_signals, "Article", SimpleNamespace(objects=DummyManager()))

    # Act
    articles_signals.add_slug_to_article_if_not_exists(sender=None, instance=dummy)

    # Assert
    assert dummy.slug is not None and dummy.slug != ""
    # The slug should at least include the slugified title
    assert "my-fancy-title" in dummy.slug
    # When generate_random_string is used, its output should be part of slug as well
    assert "RND123" in dummy.slug or dummy.slug == "my-fancy-title"
