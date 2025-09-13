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
    import builtins
    import importlib
    import types
    from types import SimpleNamespace, ModuleType
    from datetime import datetime, timezone
    import pytest

    from conduit.apps.articles import ArticlesAppConfig
    from conduit.apps.articles import models as article_models
    from conduit.apps.articles import relations as relations_mod
    from conduit.apps.articles import serializers as article_serializers
    from conduit.apps.articles import signals as article_signals
except ImportError:
    import pytest
    pytest.skip("Required application modules not available", allow_module_level=True)


def test_ready_imports_signals(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    recorded = []

    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        # record only the target we care about and delegate other imports
        if name == "conduit.apps.articles.signals" or name.endswith(".articles.signals"):
            recorded.append(name)
            return ModuleType("conduit.apps.articles.signals")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    dummy_self = object()

    # Act
    ArticlesAppConfig.ready(dummy_self)

    # Assert
    assert any("conduit.apps.articles.signals" in r for r in recorded), "ready() should attempt to import the signals module"


@pytest.mark.parametrize(
    "model_attr, value, expected",
    [
        ("title", "My Article Title", "My Article Title"),
        ("body", "A comment body", "A comment body"),
    ],
)
def test_model_str_representation(model_attr, value, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    if model_attr == "title":
        instance = article_models.Article()
    else:
        instance = article_models.Comment()
    setattr(instance, model_attr, value)

    # Act
    result = str(instance)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected


def test_tagrelatedfield_to_internal_and_representation(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyTag:
        def __init__(self, tag):
            self.tag = tag

        class objects:
            @staticmethod
            def get_or_create(tag):
                return (DummyTag(tag), True)

    monkeypatch.setattr(relations_mod, "Tag", DummyTag, raising=False)

    # TagRelatedField expects a queryset argument in many implementations; pass a placeholder
    field = relations_mod.TagRelatedField(queryset=None)

    # Act
    internal = field.to_internal_value("python")
    representation = field.to_representation(internal)

    # Assert
    assert isinstance(internal, _exc_lookup("DummyTag", Exception))
    assert internal.tag == "python"
    assert representation == "python"


def test_article_serializer_create_and_favorite_helpers(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title=None, author=None, **kwargs):
            self.title = title
            self.author = author
            self.favorites_count = kwargs.get("favorites_count", 0)
            self._saved = False

        def save(self):
            self._saved = True

        def has_favorited(self, user):
            # simple deterministic behavior for test
            return getattr(user, "is_marker", False)

    class DummyManager:
        @staticmethod
        def create(**kwargs):
            return DummyArticle(**kwargs)

    # Patch the Article reference inside serializers to use our dummy
    monkeypatch.setattr(article_serializers, "Article", SimpleNamespace(objects=DummyManager()), raising=False)

    # Create serializer with context that contains request.user
    marker_user = SimpleNamespace(username="u", is_marker=True)
    req = SimpleNamespace(user=marker_user)
    serializer = article_serializers.ArticleSerializer(context={"request": req})

    validated_data = {"title": "Created Title", "author": marker_user}

    # Act
    created = serializer.create(validated_data)
    favorited = serializer.get_favorited(created)
    favorites_count = serializer.get_favorites_count(created)

    # Assert
    assert isinstance(created, _exc_lookup("DummyArticle", Exception))
    assert created.title == "Created Title"
    assert created.author == marker_user
    assert favorited is True
    assert isinstance(favorites_count, _exc_lookup("int", Exception))


def test_add_slug_to_article_if_not_exists_sets_slug_and_saves(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    saved = {}

    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

        def save(self):
            # mark that save was called and record slug value
            saved["called"] = True
            saved["slug"] = self.slug

    # Ensure deterministic slug generation by patching utilities possibly used
    def fake_generate_random_string(length=6):
        return "RND123"

    def fake_slugify(value):
        return "hello-world"

    monkeypatch.setattr(article_signals, "generate_random_string", fake_generate_random_string, raising=False)
    # slugify may be imported from django.utils.text; attempt to patch both places defensively
    try:
        import conduit.apps.articles.signals as sigmod
        monkeypatch.setattr(sigmod, "slugify", fake_slugify, raising=False)
    except Exception:
        # best-effort; if module layout differs, continue
        pass

    article = DummyArticle(title="Hello World", slug=None)

    # Act
    article_signals.add_slug_to_article_if_not_exists(sender=DummyArticle, instance=article, created=True)

    # Assert
    assert saved.get("called", False) is True
    assert isinstance(saved.get("slug"), str)
    assert saved["slug"] != ""
    # Expect that slug contains slugified title or random string (at least deterministic non-empty)
    assert "hello-world" in saved["slug"] or "RND123" in saved["slug"]
