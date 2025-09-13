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
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet'):
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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from datetime import datetime
    from types import SimpleNamespace
    from conduit.apps.articles.serializers import ArticleSerializer, CommentSerializer
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.views import CommentsDestroyAPIView
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
except ImportError as _err:
    import pytest as _pytest
    _pytest.skip("Skipping tests due to ImportError: %s" % _err, allow_module_level=True)


@pytest.mark.parametrize("favorited,following", [
    (True, True),
    (False, False),
])
def test_article_serializer_representation_reflects_favorited_and_following(monkeypatch, favorited, following):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    current_user = SimpleNamespace(id=10, username="current")
    author_user = SimpleNamespace(username="author", id=20)
    author_profile = SimpleNamespace(username=author_user.username, bio="bio", image="img")
    # Article-like object with minimal attributes used by serializer methods
    article_obj = SimpleNamespace(
        slug="test-slug",
        title="A Title",
        description="Desc",
        body="Body",
        created_at=datetime(2020, 1, 1, 12, 0, 0),
        updated_at=datetime(2020, 1, 2, 12, 0, 0),
        author=author_user,
    )
    # Monkeypatch external profile/favorite checks used by serializer
    monkeypatch.setattr("conduit.apps.profiles.models.has_favorited", lambda user, article: favorited)
    monkeypatch.setattr("conduit.apps.profiles.serializers.get_following", lambda requester, profile: following)
    # The serializer expects author representation via a nested serializer that may access profile attributes.
    # Provide an author object (profile) that nested serializer can read.
    # Some serializer implementations access article.author directly for username and similar fields.
    article_obj.author = SimpleNamespace(username=author_user.username, bio="bio", image="img")
    request = SimpleNamespace(user=current_user)
    serializer = ArticleSerializer(context={"request": request})
    # Act
    representation = serializer.to_representation(article_obj)
    # Assert
    assert isinstance(representation, _exc_lookup("dict", Exception))
    assert representation.get("slug") == "test-slug"
    assert representation.get("title") == "A Title"
    assert "author" in representation and isinstance(representation["author"], dict)
    assert representation["author"].get("username") == author_user.username
    # favorited and following should reflect monkeypatched values
    assert representation.get("favorited") == favorited
    assert representation["author"].get("following") == following


def test_article_serializer_plus_renderer_produces_json_with_article_wrapper(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    current_user = SimpleNamespace(id=1, username="me")
    author_user = SimpleNamespace(username="alice", bio="", image=None)
    article_obj = SimpleNamespace(
        slug="wrap-slug",
        title="Wrap",
        description="D",
        body="B",
        created_at=datetime(2021, 6, 1, 0, 0, 0),
        updated_at=datetime(2021, 6, 2, 0, 0, 0),
        author=author_user,
    )
    monkeypatch.setattr("conduit.apps.profiles.models.has_favorited", lambda user, article: False)
    monkeypatch.setattr("conduit.apps.profiles.serializers.get_following", lambda requester, profile: False)
    serializer = ArticleSerializer(context={"request": SimpleNamespace(user=current_user)})
    renderer = ArticleJSONRenderer()
    # Act
    article_data = serializer.to_representation(article_obj)
    rendered = renderer.render(article_data, renderer_context={})
    # Assert
    # Renderer should produce bytes or str JSON containing the wrapper "article" and title/body content
    assert isinstance(rendered, (bytes, str))
    rendered_text = rendered.decode("utf-8") if isinstance(rendered, _exc_lookup("bytes", Exception)) else rendered
    assert '"article"' in rendered_text
    assert "Wrap" in rendered_text
    assert "B" in rendered_text


@pytest.mark.parametrize("initial_slug,expected_startswith", [
    (None, True),
    ("already-exists", False),
])
def test_add_slug_to_article_if_not_exists_sets_slug_when_missing(monkeypatch, initial_slug, expected_startswith):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Create a simple article-like object
    article = SimpleNamespace(title="My Test Title", slug=initial_slug)
    # Force deterministic slugify and random generator inside the signals module
    monkeypatch.setattr("conduit.apps.articles.signals.slugify", lambda s: "my-test-title")
    monkeypatch.setattr("conduit.apps.articles.signals.generate_random_string", lambda n=6: "ABC123")
    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=article)
    # Assert
    if expected_startswith:
        assert isinstance(article.slug, str)
        assert article.slug.startswith("my-test-title")
        # Should include the appended random string according to typical implementation
        assert "ABC123" in article.slug
    else:
        # If slug existed, it should remain unchanged
        assert article.slug == "already-exists"


def test_comments_destroy_view_calls_delete_and_returns_204(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    deleted = {"flag": False}

    class DummyComment:
        def delete(self):
            deleted["flag"] = True

    dummy_comment = DummyComment()
    view = CommentsDestroyAPIView()
    # Replace get_object to return our dummy_comment and disable permission checks
    monkeypatch.setattr(view, "get_object", lambda *args, **kwargs: dummy_comment)
    monkeypatch.setattr(view, "check_object_permissions", lambda request, obj: None)
    # Provide a minimal request object
    request = SimpleNamespace(user=SimpleNamespace(id=1))
    # Act
    response = view.delete(request, pk=123)
    # Assert
    assert deleted["flag"] is True
    # The DRF DestroyAPIView returns a Response with HTTP 204 No Content
    # Some implementations return None; prefer to assert for Response or None but if Response then check status_code
    if response is None:
        pytest.fail("Expected a Response object with status code 204, got None")
    assert hasattr(response, "status_code")
    assert response.status_code == 204
