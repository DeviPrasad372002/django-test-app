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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    import sys
    from types import SimpleNamespace, ModuleType

    import conduit.apps.articles as articles_pkg
    import conduit.apps.articles.models as articles_models
    import conduit.apps.articles.relations as relations
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required modules for these tests are not available", allow_module_level=True)


def _exc_lookup(name, default=Exception):
    return getattr(__builtins__, name, default)


def test_article_and_comment_str_returns_expected_fields():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article_title = "An Interesting Title"
    comment_body = "A thoughtful comment body"
    article = articles_models.Article(title=article_title)
    comment = articles_models.Comment(body=comment_body)

    # Act
    article_str = str(article)
    comment_str = str(comment)

    # Assert
    assert isinstance(article_str, _exc_lookup("str", Exception))
    assert isinstance(comment_str, _exc_lookup("str", Exception))
    assert article_title == article_str
    assert comment_body == comment_str


@pytest.mark.parametrize(
    "tag_name",
    [
        ("python",),
        ("unit-testing",),
        ("タグ",),  # unicode / non-ascii
    ],
)
def test_tagrelatedfield_to_representation_and_to_internal_value(tag_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    field = relations.TagRelatedField()
    class DummyTag:
        def __init__(self, name):
            self.name = name

    dummy = DummyTag(tag_name[0])
    raw_input = tag_name[0]

    # Act
    representation = field.to_representation(dummy)
    internal = field.to_internal_value(raw_input)

    # Assert
    assert isinstance(representation, _exc_lookup("str", Exception))
    assert representation == tag_name[0]
    assert internal == raw_input


def test_tagrelatedfield_to_representation_raises_on_missing_name_attribute():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    field = relations.TagRelatedField()
    class Bare:
        pass

    bare = Bare()

    # Act / Assert
    with pytest.raises(_exc_lookup("AttributeError", Exception)):
        field.to_representation(bare)


def test_articles_app_config_ready_imports_signals_safely(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    AppConfigClass = getattr(articles_pkg, "ArticlesAppConfig", None)
    assert AppConfigClass is not None, "ArticlesAppConfig must exist"
    # Provide a dummy signals module so ready can import it without side effects
    dummy_signals = ModuleType("conduit.apps.articles.signals")
    sys.modules["conduit.apps.articles.signals"] = dummy_signals
    app_config_instance = AppConfigClass("conduit.apps.articles", articles_pkg)

    # Act
    # ready should not raise even if signals module is simple/dummy
    app_config_instance.ready()

    # Assert
    assert getattr(app_config_instance, "name", None) == "conduit.apps.articles"
    # cleanup
    sys.modules.pop("conduit.apps.articles.signals", None)
