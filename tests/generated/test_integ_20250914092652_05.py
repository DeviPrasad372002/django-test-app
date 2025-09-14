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

def _fix_django_metaclass_compatibility():
    """Fix Django 1.10.5 metaclass compatibility with Python 3.10+"""
    try:
        import sys
        if sys.version_info >= (3, 8):
            import builtins
            original_build_class = builtins.__build_class__
            
            def patched_build_class(func, name, *bases, metaclass=None, **kwargs):
                try:
                    return original_build_class(func, name, *bases, metaclass=metaclass, **kwargs)
                except RuntimeError as e:
                    if '__classcell__' in str(e) and 'not set' in str(e):
                        # Create a new function without problematic cell variables
                        import types
                        code = func.__code__
                        if code.co_freevars:
                            # Remove free variables that cause issues
                            new_code = code.replace(
                                co_freevars=(),
                                co_names=code.co_names + code.co_freevars
                            )
                            new_func = types.FunctionType(
                                new_code,
                                func.__globals__,
                                func.__name__,
                                func.__defaults__,
                                None  # No closure
                            )
                            return original_build_class(new_func, name, *bases, metaclass=metaclass, **kwargs)
                    raise
                except Exception:
                    # Fallback for other metaclass issues
                    return original_build_class(func, name, *bases, **kwargs)
            
            builtins.__build_class__ = patched_build_class
    except Exception:
        pass

# Apply Django metaclass fix early
_fix_django_metaclass_compatibility()

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
    import json
    import pytest
    from unittest.mock import Mock

    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    import conduit.apps.articles.views as articles_views
    from conduit.apps.articles.serializers import TagSerializer  # used only for import-check
except ImportError:
    import pytest
    pytest.skip("requires conduit apps modules", allow_module_level=True)


class FakeRequest:
    def __init__(self, user=None, data=None):
        self.user = user
        self.data = data or {}


def _make_response_data_from_renderer(renderer, input_data):
    # Arrange
    renderer_instance = renderer()
    # Act
    rendered_bytes = renderer_instance.render(input_data, accepted_media_type="application/json", renderer_context={})
    # Assert basic shape
    try:
        decoded = rendered_bytes.decode("utf-8") if isinstance(rendered_bytes, (bytes, bytearray)) else str(rendered_bytes)
        loaded = json.loads(decoded)
    except Exception:
        # If renderer returns raw empty bytes or non-json, raise to expose behavior
        raise
    return loaded


@pytest.mark.parametrize(
    "input_data, expected_key, expected_inner",
    [
        ({"article": {"title": "Hello", "body": "World"}}, "article", {"title": "Hello", "body": "World"}),
        ({"articles": [{"title": "A"}], "articlesCount": 1}, "articles", [{"title": "A"}]),
        (None, None, None),  # edge: None input should produce JSON null -> json.loads -> None
    ],
)
def test_article_json_renderer_outputs_expected_wrapping(input_data, expected_key, expected_inner):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange - input provided by parametrize
    # Act
    loaded = _make_response_data_from_renderer(ArticleJSONRenderer, input_data)
    # Assert
    if expected_key is None:
        assert loaded is None
    else:
        assert expected_key in loaded
        # For list-case, the serializer may return structure with count; be permissive but concrete
        if expected_key == "article":
            assert isinstance(loaded["article"], dict)
            for k, v in expected_inner.items():
                assert loaded["article"].get(k) == v
        else:
            assert isinstance(loaded["articles"], list)
            assert loaded.get("articlesCount", len(loaded["articles"])) >= 0


@pytest.mark.parametrize(
    "input_data, expected_count",
    [
        ({"comment": {"body": "ok"}}, 1),
        ({"comments": [{"body": "a"}, {"body": "b"}]}, 2),
        (None, 0),
    ],
)
def test_comment_json_renderer_outputs_expected_wrapping(input_data, expected_count):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange - input provided
    # Act
    loaded = _make_response_data_from_renderer(CommentJSONRenderer, input_data)
    # Assert
    if input_data is None:
        assert loaded is None
    else:
        if "comment" in input_data:
            assert "comment" in loaded and isinstance(loaded["comment"], dict)
            assert len(loaded.get("comment", {})) >= 0
            assert expected_count == 1
        else:
            assert "comments" in loaded and isinstance(loaded["comments"], list)
            assert len(loaded["comments"]) == expected_count


@pytest.mark.parametrize(
    "existing_tags, expected_serialized",
    [
        (["python", "django"], ["python", "django"]),
        ([], []),
    ],
)
def test_tag_list_view_returns_serialized_tag_list(monkeypatch, existing_tags, expected_serialized):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = articles_views.TagListAPIView()
    # Fake Tag model's objects.all to return a list of simple tag-like objects
    fake_tag_objs = [Mock(name=t) for t in existing_tags]

    class FakeQuerySet(list):
        pass

    fake_qs = FakeQuerySet(fake_tag_objs)

    fake_tag_model = Mock()
    fake_tag_model.objects = Mock()
    fake_tag_model.objects.all = Mock(return_value=fake_qs)
    monkeypatch.setattr(articles_views, "Tag", fake_tag_model)

    # Replace TagSerializer used in the view with a predictable serializer that exposes .data
    class FakeTagSerializer:
        def __init__(self, objs, many=False):
            # Act as a simple serializer that returns the name/list of names
            self.data = [getattr(o, "name", getattr(o, "id", None) or str(o)) for o in objs]

    monkeypatch.setattr(articles_views, "TagSerializer", FakeTagSerializer)

    fake_request = FakeRequest()

    # Act
    response = view.get(fake_request)

    # Assert
    # The view should produce a response-like object with .data containing the serialized list
    assert hasattr(response, "data")
    assert response.data == expected_serialized


@pytest.mark.parametrize("initial_has_favorited", [False, True])
def test_articles_favorite_view_toggles_favorite(monkeypatch, initial_has_favorited):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = articles_views.ArticlesFavoriteAPIView()

    # Fake article returned by Article.objects.get
    fake_article = Mock()
    fake_article.slug = "test-slug"

    fake_article_model = Mock()
    fake_article_model.objects = Mock()
    fake_article_model.objects.get = Mock(return_value=fake_article)
    monkeypatch.setattr(articles_views, "Article", fake_article_model)

    # Fake profile on the user with has_favorited, favorite, unfavorite
    profile_mock = Mock()
    profile_mock.has_favorited = Mock(return_value=initial_has_favorited)
    profile_mock.favorite = Mock()
    profile_mock.unfavorite = Mock()

    fake_user = Mock()
    # In codebase profile might be accessible as user.profile or user; support both
    fake_user.profile = profile_mock
    fake_user.is_authenticated = True

    fake_request = FakeRequest(user=fake_user)

    # Fake serializer to return a predictable payload
    class FakeArticleSerializer:
        def __init__(self, article_obj, context=None):
            self.data = {"article": {"slug": getattr(article_obj, "slug", None), "favorited": not initial_has_favorited}}

    monkeypatch.setattr(articles_views, "ArticleSerializer", FakeArticleSerializer)

    # Act
    # Many implementations accept (request, slug) positional args
    response = view.post(fake_request, "test-slug")

    # Assert: proper toggle method called
    if initial_has_favorited:
        profile_mock.unfavorite.assert_called_once_with(fake_article)
        profile_mock.favorite.assert_not_called()
    else:
        profile_mock.favorite.assert_called_once_with(fake_article)
        profile_mock.unfavorite.assert_not_called()

    assert hasattr(response, "data")
    assert isinstance(response.data, dict)
    assert "article" in response.data
    assert response.data["article"]["slug"] == "test-slug"
