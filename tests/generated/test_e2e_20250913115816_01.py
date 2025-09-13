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

try:
    import pytest
    from types import SimpleNamespace
    from datetime import datetime, timezone
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.models import Article, Comment
    from conduit.apps.articles.serializers import ArticleSerializer
except ImportError:
    import pytest
    pytest.skip("Required modules for tests not available", allow_module_level=True)


@pytest.mark.parametrize(
    "title_variant",
    [
        "Hello World",
        "Hello, World!",
        "  Multiple   Spaces  ",
        "Title With Ünicode — and symbols!",
    ],
)
def test_add_slug_to_article_if_not_exists_generates_nonempty_slug_for_various_titles(title_variant):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article_like = SimpleNamespace(title=title_variant, slug=None)
    sender_placeholder = SimpleNamespace()
    created_flag = True

    # Act
    add_slug_to_article_if_not_exists(sender=sender_placeholder, instance=article_like, created=created_flag)

    # Assert
    generated_slug = getattr(article_like, "slug", None)
    assert isinstance(generated_slug, _exc_lookup("str", Exception))
    assert len(generated_slug) > 0
    assert " " not in generated_slug  # slug should not contain spaces
    assert generated_slug == generated_slug.lower()  # slug should be lowercase


def test_article_and_comment_str_return_readable_content_substrings():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article_title = "An Interesting Article"
    comment_body = "This is a thoughtful comment about the article's topic."

    article_instance = Article(title=article_title)
    comment_instance = Comment(body=comment_body)

    # Act
    article_str = str(article_instance)
    comment_str = str(comment_instance)

    # Assert
    assert isinstance(article_str, _exc_lookup("str", Exception))
    assert article_title in article_str

    assert isinstance(comment_str, _exc_lookup("str", Exception))
    # comment string representation should contain a meaningful substring of the body
    assert comment_body[:10] in comment_str


def test_article_serializer_date_and_favorite_helpers_behave_without_request_context():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer_instance = ArticleSerializer(context={})
    now_dt = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    article_like = SimpleNamespace(created_at=now_dt, updated_at=now_dt, favorites_count=7)

    # Act
    created_at_value = serializer_instance.get_created_at(article_like)
    updated_at_value = serializer_instance.get_updated_at(article_like)
    favorites_count_value = serializer_instance.get_favorites_count(article_like)
    favorited_value = serializer_instance.get_favorited(article_like)

    # Assert
    assert isinstance(created_at_value, _exc_lookup("str", Exception))
    assert ":" in created_at_value and created_at_value.startswith("2020")
    assert isinstance(updated_at_value, _exc_lookup("str", Exception))
    assert ":" in updated_at_value and updated_at_value.startswith("2020")

    assert isinstance(favorites_count_value, _exc_lookup("int", Exception))
    assert favorites_count_value == 7

    # Without a request/user in serializer context, the article should not be reported as favorited
    assert favorited_value is False
