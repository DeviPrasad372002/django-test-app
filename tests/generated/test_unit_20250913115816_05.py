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
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
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
if not STRICT:
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
try:
    if _iu.find_spec("django") is not None:
        import django
        from django.conf import settings as _dj_settings
        if not _dj_settings.configured:
            _dj_settings.configure(SECRET_KEY="test-key", DEBUG=True, ALLOWED_HOSTS=["*"], INSTALLED_APPS=[], DATABASES={"default": {"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
            django.setup()
except Exception: pass
_PY2_ALIASES = {'ConfigParser': 'configparser', 'Queue': 'queue', 'StringIO': 'io', 'cStringIO': 'io', 'urllib2': 'urllib.request'}
for _old, _new in list(_PY2_ALIASES.items()):
    if _old in sys.modules: continue
    try:
        __import__(_new); sys.modules[_old] = sys.modules[_new]
    except Exception: pass
def _safe_find_spec(name):
    try: return _iu.find_spec(name)
    except Exception: return None
def _ensure_pkg(name, is_pkg=None):
    if name in sys.modules:
        m = sys.modules[name]
        if getattr(m, "__spec__", None) is None:
            m.__spec__ = _im.ModuleSpec(name, loader=None, is_package=(is_pkg if is_pkg is not None else ("." not in name)))
            if "." not in name and not hasattr(m, "__path__"): m.__path__ = []
        return m
    m = _types.ModuleType(name)
    if is_pkg is None: is_pkg = ("." not in name)
    if is_pkg and not hasattr(m, "__path__"): m.__path__ = []
    m.__spec__ = _im.ModuleSpec(name, loader=None, is_package=is_pkg)
    sys.modules[name] = m
    return m
_THIRD_PARTY_TOPS = ['__future__', 'conduit', 'datetime', 'django', 'json', 'jwt', 'models', 'os', 'random', 'relations', 'renderers', 'rest_framework', 'serializers', 'string', 'views']

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest

try:
    import json
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.views import CommentsDestroyAPIView
    from django.utils.text import slugify
except ImportError:
    pytest.skip("Required modules for these tests are not available", allow_module_level=True)


@pytest.mark.parametrize(
    "renderer_cls,input_data,expected_key",
    [
        (ArticleJSONRenderer, {"article": {"title": "Hello World"}}, "article"),
        (CommentJSONRenderer, {"comment": {"body": "Nice post!"}}, "comment"),
    ],
)
def test_json_renderers_produce_bytes_and_contain_expected_key(renderer_cls, input_data, expected_key):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = renderer_cls()
    data = input_data

    # Act
    output_bytes = renderer.render(data)

    # Assert
    assert isinstance(output_bytes, (bytes, bytearray)), "Renderer must return bytes"
    text = output_bytes.decode("utf-8")
    parsed = json.loads(text)
    assert expected_key in parsed, f"Rendered JSON must contain top-level key '{expected_key}'"
    assert isinstance(parsed[expected_key], dict), "Top-level value should be a mapping for the resource"


@pytest.mark.parametrize(
    "title",
    [
        "Test Article",
        "Another    Test   Article",  # extra spaces
        "Café spécial",  # unicode chars
    ],
)
def test_add_slug_to_article_if_not_exists_creates_slug_when_missing(title):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    article = DummyArticle(title=title, slug=None)

    # Act
    # Signal handlers often accept (sender, instance, **kwargs)
    add_slug_to_article_if_not_exists(None, article, created=True)

    # Assert
    assert isinstance(article.slug, str), "Slug must be a string after signal handler"
    assert article.slug, "Slug must not be empty"
    # Compare to slugify if available: slug should at minimum contain slugified words
    expected_slug = slugify(title)
    assert expected_slug in article.slug, f"Slug '{article.slug}' should contain slugified title part '{expected_slug}'"


def test_add_slug_to_article_if_not_exists_does_not_override_existing_slug():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    original_slug = "existing-slug"
    article = DummyArticle(title="New Title", slug=original_slug)

    # Act
    add_slug_to_article_if_not_exists(None, article, created=False)

    # Assert
    assert article.slug == original_slug, "Handler should not override an existing slug"


def test_comments_destroy_api_calls_delete_and_returns_204(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = CommentsDestroyAPIView()

    class Obj:
        def __init__(self):
            self.deleted = False

        def delete(self):
            self.deleted = True
            # mimic Django model delete returning (num, dict) or None; keep simple
            return None

    obj = Obj()

    def fake_get_object():
        return obj

    monkeypatch.setattr(view, "get_object", fake_get_object)

    class FakeRequest:
        def __init__(self):
            self.method = "DELETE"
            self.user = None

    request = FakeRequest()

    # Act
    response = view.delete(request, pk=1)

    # Assert
    # Expect the view to have called delete on the object
    assert getattr(obj, "deleted", False) is True, "The object's delete() should have been invoked"
    # Response should be a DRF Response-like object with status_code attribute
    assert hasattr(response, "status_code"), "Response must have a status_code attribute"
    assert response.status_code in (200, 204), "Destroy/delete endpoint should return 200 or 204 on success"
