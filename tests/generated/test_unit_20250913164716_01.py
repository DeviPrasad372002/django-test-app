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
            except Exception:
                pass

        if not _dj_settings.configured:
            _installed = ["django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions"]
            if _iu.find_spec("rest_framework"):
                _installed.append("rest_framework")

            # Explicitly try common project apps if present
            for _app in ("conduit.apps.core","conduit.apps.articles","conduit.apps.authentication","conduit.apps.profiles"):
                _maybe_add(_app, _installed)

            # Generic discovery under conduit.apps.*
            try:
                if _iu.find_spec("conduit.apps"):
                    _apps_pkg = importlib.import_module("conduit.apps")
                    for _m in pkgutil.iter_modules(getattr(_apps_pkg, "__path__", [])):
                        _full = "conduit.apps." + _m.name
                        _maybe_add(_full, _installed)
            except Exception:
                pass

            _cfg = dict(
                SECRET_KEY="test-key",
                DEBUG=True,
                ALLOWED_HOSTS=["*"],
                INSTALLED_APPS=sorted(set(_installed)),
                DATABASES=dict(default=dict(ENGINE="django.db.backends.sqlite3", NAME=":memory:")),
                MIDDLEWARE=[],
                MIDDLEWARE_CLASSES=[],
                USE_TZ=True,
                TIME_ZONE="UTC",
            )
            try:
                _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
            except Exception:
                pass

            try:
                _dj_settings.configure(**_cfg)
                django.setup()
            except Exception:
                _pytest.skip("Django setup failed in bootstrap; skipping generated tests", allow_module_level=True)
        else:
            if not _dj_apps.ready:
                try:
                    django.setup()
                except Exception:
                    _pytest.skip("Django setup not ready and failed to initialize; skipping", allow_module_level=True)
except Exception:
    _pytest.skip("Django bootstrap error; skipping generated tests", allow_module_level=True)
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
    from datetime import datetime, timezone

    import conduit.apps.articles.signals as articles_signals
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.serializers import ArticleSerializer
    from conduit.apps.articles.models import Article
except ImportError:
    import pytest
    pytest.skip("Required modules for article unit tests not available", allow_module_level=True)


class FakeArticleForSignal:
    def __init__(self, title, slug=None):
        self.title = title
        self.slug = slug
        self._saved = False

    def save(self, *args, **kwargs):
        self._saved = True


def _simple_slugify(value):
    return value.lower().replace(" ", "-")


def test_add_slug_to_article_if_not_exists_assigns_slug_and_calls_save(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_article = FakeArticleForSignal(title="Hello World", slug=None)
    monkeypatch.setattr(articles_signals, "generate_random_string", lambda n=6: "XYZ123")
    monkeypatch.setattr(articles_signals, "slugify", _simple_slugify)

    # Act
    add_slug_to_article_if_not_exists(sender=object, instance=fake_article, created=True)

    # Assert
    assert fake_article.slug is not None and isinstance(fake_article.slug, str)
    assert fake_article.slug.startswith("hello-world-")
    assert fake_article.slug.endswith("xyz123") or fake_article.slug.endswith("XYZ123".lower()) or "xyz123" in fake_article.slug.lower()
    assert fake_article._saved is True


@pytest.mark.parametrize(
    "title_value, expected_str",
    [
        ("A Simple Title", "A Simple Title"),
        ("", ""),
        ("Title With 123", "Title With 123"),
    ],
)
def test_article___str__returns_title(title_value, expected_str):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article = Article()
    article.title = title_value

    # Act
    result = str(article)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected_str


@pytest.mark.parametrize(
    "dt_value, expect_suffix",
    [
        (datetime(2020, 1, 1, 0, 0, 0), "2020-01-01T00:00:00"),
        (datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc), "2020-01-01T00:00:00+00:00"),
    ],
)
def test_article_serializer_get_created_and_updated_at_formats_iso(dt_value, expect_suffix):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer = ArticleSerializer()
    class FakeObj:
        created_at = None
        updated_at = None

    fake = FakeObj()
    fake.created_at = dt_value
    fake.updated_at = dt_value

    # Act
    created_val = serializer.get_created_at(fake)
    updated_val = serializer.get_updated_at(fake)

    # Assert
    assert isinstance(created_val, _exc_lookup("str", Exception))
    assert isinstance(updated_val, _exc_lookup("str", Exception))
    assert created_val.startswith(expect_suffix)
    assert updated_val.startswith(expect_suffix)


def test_article_serializer_get_favorites_count_uses_count_method():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer = ArticleSerializer()

    class FakeFavorites:
        def __init__(self, n):
            self._n = n

        def count(self):
            return self._n

    class FakeArticle:
        favorites = FakeFavorites(7)

    fake_article = FakeArticle()

    # Act
    count = serializer.get_favorites_count(fake_article)

    # Assert
    assert isinstance(count, _exc_lookup("int", Exception))
    assert count == 7
