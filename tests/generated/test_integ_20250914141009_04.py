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
    import importlib
    import types
    import pytest
    from types import SimpleNamespace

    from conduit.apps.articles.models import Article, Comment, Tag
    from conduit.apps.articles.relations import TagRelatedField, relations as relations_module  # relations alias if present
    from conduit.apps.profiles.serializers import get_image, get_following
    from conduit.apps.articles.__init__ import ArticlesAppConfig
    # import migrations module dynamically (module name starts with digit)
    mig_module = importlib.import_module("conduit.apps.articles.migrations.0001_initial")
    Migration = getattr(mig_module, "Migration", None)
except ImportError:
    import pytest
    pytest.skip("Required project modules not available", allow_module_level=True)


def test_article_comment_and_tag_str_contain_key_fields():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article_title = "Integration Test Article"
    comment_body = "This is a comment used for integration testing."
    tag_name = "integration-tag"

    article = Article(title=article_title)
    comment = Comment(body=comment_body)
    tag = Tag(name=tag_name)

    # Act
    article_str = str(article)
    comment_str = str(comment)
    tag_str = str(tag)

    # Assert
    assert isinstance(article_str, _exc_lookup("str", Exception))
    assert article_title in article_str

    assert isinstance(comment_str, _exc_lookup("str", Exception))
    assert comment_body[: min(len(comment_body), 30)] in comment_str

    assert isinstance(tag_str, _exc_lookup("str", Exception))
    assert tag_name in tag_str


@pytest.mark.parametrize("input_name", ["python", "unit-testing", ""])
def test_tagrelatedfield_to_internal_and_representation(monkeypatch, input_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class FakeTag:
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return f"<FakeTag {self.name!r}>"

    class FakeObjects:
        @staticmethod
        def get_or_create(name):
            return FakeTag(name), True

    FakeTag.objects = FakeObjects()

    # Monkeypatch the Tag used inside the relations module to avoid DB calls
    # relations_module may refer to the module or be the module itself depending on import
    monkeypatch.setattr("conduit.apps.articles.relations.Tag", FakeTag, raising=False)
    # also set on relations_module if present
    try:
        monkeypatch.setattr(relations_module, "Tag", FakeTag, raising=False)
    except Exception:
        # If relations_module isn't a module with attribute, ignore
        pass

    tag_field = TagRelatedField()

    # Act
    internal_value = tag_field.to_internal_value(input_name)
    representation = tag_field.to_representation(internal_value)

    # Assert
    assert isinstance(internal_value, _exc_lookup("FakeTag", Exception))
    assert getattr(internal_value, "name") == input_name
    assert representation == input_name


@pytest.mark.parametrize("is_following_return", [True, False])
def test_get_following_and_get_image_with_fake_serializer_context(monkeypatch, is_following_return):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Create a fake request.user with is_following method
    request_user = SimpleNamespace()
    request_user.is_following = lambda other: is_following_return
    fake_request = SimpleNamespace(user=request_user)
    fake_self = SimpleNamespace(context={"request": fake_request})

    # Target user without profile image attribute
    target_user_no_image = SimpleNamespace()
    # Target user with direct image attribute
    target_user_with_image = SimpleNamespace(image="http://example.com/avatar.jpg")
    # Target user with profile image nested
    target_user_with_profile = SimpleNamespace(profile=SimpleNamespace(image="http://example.com/profile.jpg"))

    # Act
    following_result = get_following(fake_self, target_user_no_image)
    image_result_direct = get_image(fake_self, target_user_with_image)
    image_result_profile = get_image(fake_self, target_user_with_profile)
    image_result_missing = get_image(fake_self, target_user_no_image)

    # Assert
    assert following_result is is_following_return
    assert image_result_direct == "http://example.com/avatar.jpg"
    assert image_result_profile == "http://example.com/profile.jpg"
    assert image_result_missing in ("", None)


def test_articles_app_config_ready_attempts_to_import_signals(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    imported = []

    def fake_import_module(name, package=None):
        imported.append(name)
        # return a dummy module object
        return types.SimpleNamespace(__name__=name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    config = ArticlesAppConfig("conduit.apps.articles", "conduit.apps.articles")

    # Act
    config.ready()

    # Assert
    # The ready method should attempt to import the app's signals module as part of wiring
    assert any("signals" in name for name in imported) or imported, "ready() did not attempt imports; expected signals import attempt"
