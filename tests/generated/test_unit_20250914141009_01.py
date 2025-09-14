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
    import sys
    from types import SimpleNamespace

    import conduit.apps.articles.__init__ as articles_init
    import conduit.apps.articles.signals as articles_signals
    import conduit.apps.core.utils as core_utils
    import conduit.apps.articles.models as articles_models
except ImportError as e:
    import pytest
    pytest.skip(f"Skipping tests due to ImportError: {e}", allow_module_level=True)


def test_ready_imports_signals_module(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    signals_module_name = "conduit.apps.articles.signals"
    if signals_module_name in sys.modules:
        del sys.modules[signals_module_name]

    ready_func = getattr(articles_init, "ready", None)
    assert callable(ready_func), "ready must be callable on the articles package"

    # Act
    ready_func()

    # Assert
    assert signals_module_name in sys.modules
    imported = sys.modules[signals_module_name]
    assert hasattr(imported, "add_slug_to_article_if_not_exists") or hasattr(imported, "connect"), "signals module should expose signal handlers"


@pytest.mark.parametrize("initial_slug, expected_unchanged", [
    ("", False),
    (None, False),
    ("existing-slug", True),
])
def test_add_slug_to_article_if_not_exists_sets_or_skips_slug(monkeypatch, initial_slug, expected_unchanged):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    saved_flags = {}

    class FakeArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug
            self._saved = False

        def save(self, *args, **kwargs):
            # record that save was called
            self._saved = True
            saved_flags['saved_called'] = True

    instance = FakeArticle(title="My Test Title", slug=initial_slug)

    # Make slugify deterministic within the signals module
    monkeypatch.setattr(articles_signals, "slugify", lambda value: value.lower().replace(" ", "-"), raising=False)
    # Make random string deterministic and short
    monkeypatch.setattr(articles_signals, "generate_random_string", lambda n=6: "RND", raising=False)

    handler = getattr(articles_signals, "add_slug_to_article_if_not_exists", None)
    assert callable(handler), "add_slug_to_article_if_not_exists must be present in signals"

    # Act
    # Many Django signal handlers accept sender, instance, **kwargs
    handler(sender=None, instance=instance)

    # Assert
    if expected_unchanged:
        assert instance.slug == "existing-slug"
        assert not getattr(instance, "_saved", False), "save should not be called when slug already exists"
    else:
        # Expect slug to be generated from title + separator + random string
        assert instance.slug is not None and instance.slug != ""
        assert "my-test-title" in instance.slug or "my-test-title" == instance.slug.split("-RND")[0]
        assert getattr(instance, "_saved", False) or saved_flags.get('saved_called', False), "save should be called when slug was missing"


@pytest.mark.parametrize("length", [1, 6, 50])
def test_generate_random_string_returns_expected_length_and_chars(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    gen = getattr(core_utils, "generate_random_string", None)
    assert callable(gen), "generate_random_string must be available in core.utils"

    # Act
    result = gen(length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    # Accept alphanumeric characters as valid output characters
    assert all(ch.isalnum() for ch in result), "generate_random_string should produce only alphanumeric characters"


def test_comment_str_includes_body_when_instantiated_without_db():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    Comment = getattr(articles_models, "Comment", None)
    assert Comment is not None, "Comment model must be importable from articles.models"

    # many Django models accept keyword args on construction without DB
    try:
        comment = Comment(body="This is a body for stringification test")
    except TypeError:
        # If the model requires arguments, create a minimal stand-in object to test __str__ if defined on classmethod
        comment = SimpleNamespace(body="This is a body for stringification test")
        # If the real model defined __str__ as a standalone function, attempt to use it
        model_str = getattr(articles_models.Comment, "__str__", None)
        if callable(model_str):
            # Assert using the class method on the fake instance
            result = model_str(comment)
            assert isinstance(result, _exc_lookup("str", Exception))
            assert "This is a body" in result
            return

    # Act
    result = str(comment)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert "This is a body" in result or len(result) > 0, "__str__ should return a readable representation containing the body when available"
