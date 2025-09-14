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

try:
    import pytest
    from types import SimpleNamespace
    import target.conduit.apps.articles.signals as article_signals
    from target.conduit.apps.articles.__init__ import ArticlesAppConfig
    import django.db.models.signals as model_signals
    from target.conduit.apps.articles.models import Article
except ImportError:
    import pytest
    pytest.skip("Skipping integration tests due to missing project modules", allow_module_level=True)


@pytest.mark.parametrize(
    "initial_slug, title, expected_slug_root",
    [
        (None, "Hello World!", "hello-world"),
        ("", "Another Title", "another-title"),
    ],
)
def test_add_slug_sets_slug_when_missing(monkeypatch, initial_slug, title, expected_slug_root):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_calls = []

    def fake_generate_random_string(length=6):
        created_calls.append(("gen_called", length))
        return "RND"

    def fake_slugify(value):
        # ensure deterministic slugification used by the signal handler
        return expected_slug_root

    fake_article = SimpleNamespace(title=title, slug=initial_slug)

    monkeypatch.setattr(article_signals, "generate_random_string", fake_generate_random_string, raising=False)
    monkeypatch.setattr(article_signals, "slugify", fake_slugify, raising=False)

    # Act
    article_signals.add_slug_to_article_if_not_exists(sender=None, instance=fake_article)

    # Assert
    assert isinstance(fake_article.slug, str)
    assert fake_article.slug == f"{expected_slug_root}-RND"
    assert created_calls == [("gen_called", 6)]


def test_add_slug_does_not_override_existing_slug(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    random_calls = []

    def fake_generate_random_string(length=6):
        random_calls.append(length)
        return "SHOULDNOTBEUSED"

    existing_slug = "already-set-slug"
    fake_article = SimpleNamespace(title="Title Irrelevant", slug=existing_slug)

    monkeypatch.setattr(article_signals, "generate_random_string", fake_generate_random_string, raising=False)

    # Act
    article_signals.add_slug_to_article_if_not_exists(sender=None, instance=fake_article)

    # Assert
    assert fake_article.slug == existing_slug
    assert random_calls == []


@pytest.mark.parametrize("title_value", ["My Article", ""])
def test_article_str_uses_title(title_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_article = SimpleNamespace(title=title_value)

    # Act
    result = Article.__str__(fake_article)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == title_value


def test_ready_registers_pre_save_connect(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    recorded_calls = []

    def spy_connect(*args, **kwargs):
        recorded_calls.append({"args": args, "kwargs": kwargs})

    # Replace the pre_save signal object in the django signals module with a stub having connect=spy_connect
    monkeypatch.setattr(model_signals, "pre_save", SimpleNamespace(connect=spy_connect), raising=False)

    app_name = "target.conduit.apps.articles"
    app_module = SimpleNamespace(__name__=app_name)

    config = ArticlesAppConfig(app_name, app_module)

    # Act
    config.ready()

    # Assert
    assert recorded_calls, "ready() should call pre_save.connect at least once"
    # Look for any registered receiver that corresponds to our add_slug handler
    found_add_slug = False
    for call in recorded_calls:
        for candidate in list(call["args"]) + list(call["kwargs"].values()):
            try:
                if callable(candidate) and getattr(candidate, "__name__", "") == "add_slug_to_article_if_not_exists":
                    found_add_slug = True
                    break
            except Exception:
                continue
        if found_add_slug:
            break

    assert found_add_slug, "add_slug_to_article_if_not_exists should be connected via pre_save in ready()"
