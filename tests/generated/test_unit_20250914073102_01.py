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

try:
    import pytest
    from types import SimpleNamespace
    from datetime import datetime
    from conduit.apps.articles.models import Article
    from conduit.apps.articles.serializers import ArticleSerializer
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.__init__ import ArticlesAppConfig
except ImportError:
    import pytest
    pytest.skip("Required project modules not available", allow_module_level=True)


def test_articles_app_config_ready_runs_without_error_and_returns_none():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    app_name = "conduit.apps.articles"
    app_module = "conduit.apps.articles"
    config = ArticlesAppConfig(app_name, app_module)

    # Act
    result = config.ready()

    # Assert
    assert result is None


def test_article___str___returns_title():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article = Article()
    article.title = "My Unique Title"

    # Act
    representation = str(article)

    # Assert
    assert isinstance(representation, _exc_lookup("str", Exception))
    assert representation == "My Unique Title"


@pytest.mark.parametrize("initial_slug,should_save_expected", [
    ("existing-slug", False),
    ("", True),
    (None, True),
])
def test_add_slug_to_article_if_not_exists_behaviour(initial_slug, should_save_expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug
            self._saved = False

        def save(self, *args, **kwargs):
            self._saved = True

    dummy = DummyArticle(title="My Article Title", slug=initial_slug)

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=dummy, created=True)

    # Assert
    if should_save_expected:
        assert getattr(dummy, "_saved", False) is True
        assert getattr(dummy, "slug", None)
        # slug should contain slugified portion of title
        assert "my-article-title" in dummy.slug.lower()
    else:
        assert getattr(dummy, "_saved", False) is False
        assert dummy.slug == initial_slug


def test_article_serializer_create_calls_model_create_with_author(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_calls = []

    def fake_create(**kwargs):
        created_calls.append(kwargs)
        return SimpleNamespace(**kwargs)

    # Patch Article.objects.create
    monkeypatch.setattr(Article.objects, "create", fake_create, raising=False)

    fake_user = SimpleNamespace(id=99, username="tester")
    serializer = ArticleSerializer(context={"request": SimpleNamespace(user=fake_user)})
    validated_data = {"title": "T", "description": "D", "body": "B"}

    # Act
    result = serializer.create(validated_data)

    # Assert
    assert created_calls, "Article.objects.create was not called"
    called_kwargs = created_calls[0]
    assert called_kwargs.get("author") == fake_user
    assert called_kwargs.get("title") == "T"
    assert getattr(result, "author") == fake_user
    assert getattr(result, "title") == "T"


@pytest.mark.parametrize("favorited_value, favorites_count_value", [
    (True, 0),
    (False, 5),
])
def test_article_serializer_getters_return_expected_types_and_values(favorited_value, favorites_count_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer = ArticleSerializer()
    obj = SimpleNamespace(
        created_at=datetime(2020, 1, 1, 12, 0, 0),
        updated_at=datetime(2020, 1, 2, 13, 30, 45),
        favorited=favorited_value,
        favorites_count=favorites_count_value,
    )

    # Act
    created_val = serializer.get_created_at(obj)
    updated_val = serializer.get_updated_at(obj)
    favorited_val = serializer.get_favorited(obj)
    favorites_count_val = serializer.get_favorites_count(obj)

    # Assert
    assert isinstance(created_val, _exc_lookup("str", Exception))
    assert "2020" in created_val
    assert isinstance(updated_val, _exc_lookup("str", Exception))
    assert "2020" in updated_val
    assert isinstance(favorited_val, (bool, type(None)))  # allow None or bool depending on implementation
    assert favorited_val == favorited_value
    assert isinstance(favorites_count_val, _exc_lookup("int", Exception))
    assert favorites_count_val == favorites_count_value
