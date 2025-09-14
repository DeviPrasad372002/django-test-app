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
    import re

    import conduit.apps.articles.signals as signals_mod
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    import conduit.apps.articles.serializers as serializers_mod
    from conduit.apps.articles.serializers import ArticleSerializer
    import conduit.apps.articles.relations as relations_mod
    from conduit.apps.articles.relations import TagRelatedField
except ImportError:
    import pytest
    pytest.skip("Required modules for integration tests not available", allow_module_level=True)


@pytest.mark.parametrize("title, random_suffix", [
    ("My Title", "XYZ"),
    ("A Complex! Title--With@@Chars", "RND"),
])
def test_add_slug_to_article_if_not_exists_generates_and_assigns_slug(monkeypatch, title, random_suffix):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    dummy = DummyArticle(title=title, slug=None)

    def fake_generate_random_string(length=6):
        return random_suffix

    monkeypatch.setattr(signals_mod, "generate_random_string", fake_generate_random_string)

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=dummy, created=True)

    # Assert
    assert isinstance(dummy.slug, str)
    # Produce a slug-like prefix for expectation similar to django.utils.text.slugify
    expected_prefix = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    assert dummy.slug.endswith("-" + random_suffix)
    assert dummy.slug.startswith(expected_prefix)


def test_article_serializer_get_favorited_and_get_favorites_count_use_profile_helpers(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_user = SimpleNamespace(username="tester")
    fake_request = SimpleNamespace(user=fake_user)
    serializer = ArticleSerializer(context={"request": fake_request})

    # prepare fake article with favorites.count()
    class FakeFavorites:
        def __init__(self, count_value):
            self._count = count_value

        def count(self):
            return self._count

    class FakeArticle:
        def __init__(self, count_value):
            self.favorites = FakeFavorites(count_value)

    fake_article = FakeArticle(count_value=7)

    # Monkeypatch the has_favorited helper that ArticleSerializer delegates to
    monkeypatch.setattr(serializers_mod, "has_favorited", lambda user, article: user.username == "tester" and article.favorites.count() == 7)

    # Act
    favorited_result = serializer.get_favorited(fake_article)
    favorites_count_result = serializer.get_favorites_count(fake_article)

    # Assert
    assert isinstance(favorited_result, _exc_lookup("bool", Exception))
    assert favorited_result is True
    assert isinstance(favorites_count_result, _exc_lookup("int", Exception))
    assert favorites_count_result == 7


@pytest.mark.parametrize("tag_name", ["python", "unit-test"])
def test_tagrelatedfield_to_internal_and_to_representation(monkeypatch, tag_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    trf = TagRelatedField()

    # Fake Tag model and its manager get_or_create
    class FakeTagInstance:
        def __init__(self, name):
            self.name = name

    class FakeTagObjects:
        @staticmethod
        def get_or_create(name):
            return (FakeTagInstance(name), True)

    class FakeTagModel:
        objects = FakeTagObjects()

    monkeypatch.setattr(relations_mod, "Tag", FakeTagModel, raising=False)

    # Act
    internal = trf.to_internal_value(tag_name)
    representation = trf.to_representation(internal)

    # Assert
    assert hasattr(internal, "name")
    assert internal.name == tag_name
    assert representation == tag_name


def test_article_serializer_create_calls_article_and_tag_creation_and_attaches_tags(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Prepare fake Article model with objects.create
    created_articles = []

    class FakeTagInstance:
        def __init__(self, name):
            self.name = name

    class FakeTagObjects:
        def __init__(self):
            self.created = []

        def get_or_create(self, name):
            inst = FakeTagInstance(name)
            self.created.append(name)
            return (inst, True)

    class FakeTagModel:
        objects = FakeTagObjects()

    class FakeTagsCollection:
        def __init__(self):
            self.added = []

        def add(self, tag_obj):
            self.added.append(tag_obj)

    class FakeArticleInstance:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.tags = FakeTagsCollection()

    class FakeArticleObjects:
        def create(self, **kwargs):
            inst = FakeArticleInstance(**kwargs)
            created_articles.append(inst)
            return inst

    class FakeArticleModel:
        objects = FakeArticleObjects()

    monkeypatch.setattr(serializers_mod, "Article", FakeArticleModel, raising=False)
    monkeypatch.setattr(serializers_mod, "Tag", FakeTagModel, raising=False)

    serializer = ArticleSerializer()

    validated_data = {
        "title": "Integration Title",
        "description": "Desc",
        "body": "Body",
        "tagList": ["alpha", "beta"],
        "author": SimpleNamespace(username="creator"),
    }

    # Act
    created = serializer.create(validated_data.copy())

    # Assert
    assert created in created_articles
    assert getattr(created, "title", None) == "Integration Title"
    # Ensure tags were created via Tag.objects.get_or_create and added to article.tags
    assert isinstance(created.tags, FakeTagsCollection)
    # order and actual objects depend on implementation but both names should be present in tag objects
    added_names = [getattr(t, "name", None) for t in created.tags.added]
    assert set(added_names) == {"alpha", "beta"}
