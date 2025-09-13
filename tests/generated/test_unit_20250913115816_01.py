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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    import types
    from datetime import datetime, timezone, timedelta

    from conduit.apps.articles.__init__ import ArticlesAppConfig
    from conduit.apps.articles.models import Article, Comment
    from conduit.apps.articles.relations import TagRelatedField
    from conduit.apps.articles.serializers import ArticleSerializer
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required modules for tests are not available", allow_module_level=True)


def test_articles_appconfig_ready_does_not_raise_and_returns_none():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    app_config = ArticlesAppConfig("articles", "conduit.apps.articles")
    # Act
    result = app_config.ready()
    # Assert
    assert result is None


@pytest.mark.parametrize(
    "article_title, comment_body",
    [
        ("Simple Title", "A short comment body"),
        ("Title With Special Characters !@#", "Body with punctuation..."),
        ("", ""),  # boundary: empty strings
    ],
)
def test_article_and_comment___str__contains_expected_text(article_title, comment_body):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article = Article(title=article_title)
    comment = Comment(body=comment_body)
    # Act
    article_str = str(article)
    comment_str = str(comment)
    # Assert
    # For Article we expect the title to appear (or empty string accepted)
    assert isinstance(article_str, _exc_lookup("str", Exception))
    assert article_title in article_str
    # For Comment we expect the body (or a substring) to appear
    assert isinstance(comment_str, _exc_lookup("str", Exception))
    if comment_body:
        assert comment_body[: min(len(comment_body), 30)] in comment_str


@pytest.mark.parametrize(
    "input_value, expected_name",
    [
        ("alpha", "alpha"),
        ("Tag With Spaces", "Tag With Spaces"),
        ("", ""),
    ],
)
def test_tagrelatedfield_to_internal_value_and_to_representation(input_value, expected_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    field = TagRelatedField()
    # Act
    internal = field.to_internal_value(input_value)
    repr_from_internal = field.to_representation(internal)
    repr_from_value = field.to_representation(input_value)
    # Assert
    # internal should be an object with a 'name' attribute matching the input
    assert hasattr(internal, "name")
    assert internal.name == expected_name
    # representation should be a string equal to the name
    assert isinstance(repr_from_internal, _exc_lookup("str", Exception))
    assert repr_from_internal == expected_name
    assert isinstance(repr_from_value, _exc_lookup("str", Exception))
    assert repr_from_value == expected_name


@pytest.mark.parametrize(
    "favorites_count, has_favorited_flag",
    [
        (0, False),
        (1, True),
        (5, False),
    ],
)
def test_article_serializer_getters_for_timestamps_and_favorites(favorites_count, has_favorited_flag):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    now = datetime.now(timezone.utc).replace(microsecond=0)
    later = now + timedelta(hours=1)
    class FakeFavorites:
        def __init__(self, n):
            self._n = n
        def count(self):
            return self._n
        def all(self):
            return [None] * self._n

    def fake_has_favorited(user):
        return has_favorited_flag

    fake_article = types.SimpleNamespace(
        created_at=now,
        updated_at=later,
        favorites=FakeFavorites(favorites_count),
        has_favorited=fake_has_favorited,
    )
    fake_request = types.SimpleNamespace(user="some-user")
    serializer = ArticleSerializer(context={"request": fake_request})
    # Act
    created_val = serializer.get_created_at(fake_article)
    updated_val = serializer.get_updated_at(fake_article)
    favorites_count_val = serializer.get_favorites_count(fake_article)
    favorited_val = serializer.get_favorited(fake_article)
    # Assert
    assert isinstance(created_val, _exc_lookup("str", Exception))
    assert created_val.startswith(now.isoformat().split("+")[0])
    assert isinstance(updated_val, _exc_lookup("str", Exception))
    assert updated_val.startswith(later.isoformat().split("+")[0])
    assert isinstance(favorites_count_val, _exc_lookup("int", Exception))
    assert favorites_count_val == favorites_count
    assert isinstance(favorited_val, _exc_lookup("bool", Exception))
    assert favorited_val == has_favorited_flag


def test_add_slug_to_article_if_not_exists_assigns_and_preserves_existing_slug():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Case A: article without slug should get a slug
    article_no_slug = types.SimpleNamespace(title="Hello World!", slug="")
    # Case B: article with existing slug should remain unchanged
    article_with_slug = types.SimpleNamespace(title="Another Title", slug="existing-slug")
    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=article_no_slug, created=True)
    add_slug_to_article_if_not_exists(sender=None, instance=article_with_slug, created=True)
    # Assert
    assert getattr(article_no_slug, "slug", None)
    assert "hello" in article_no_slug.slug.lower()
    assert article_with_slug.slug == "existing-slug"
