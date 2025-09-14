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
    import json
    import pytest
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.serializers import ArticleSerializer, TagSerializer
    from conduit.apps.articles.views import CommentsDestroyAPIView
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Required modules for integration tests not available: {e}", allow_module_level=True)

@pytest.mark.parametrize("renderer_class,input_data", [
    (ArticleJSONRenderer, {"title": "Test Article", "body": "Content"}),
    (CommentJSONRenderer, {"id": 1, "body": "A comment"}),
])
def test_renderer_wraps_payload_in_single_top_level_key(renderer_class, input_data):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = renderer_class()
    renderer_context = {"request": None}

    # Act
    rendered_bytes = renderer.render(input_data, renderer_context=renderer_context)
    rendered_text = rendered_bytes.decode("utf-8") if isinstance(rendered_bytes, (bytes, bytearray)) else str(rendered_bytes)
    parsed = json.loads(rendered_text)

    # Assert
    top_level_keys = list(parsed.keys())
    assert len(top_level_keys) == 1, "Renderer should produce exactly one top-level key"
    top_value = parsed[top_level_keys[0]]
    assert top_value == input_data, "Renderer must embed the original payload as the sole top-level value"

@pytest.mark.parametrize("favorited_return,favorites_count_value", [
    (True, 0),
    (False, 1),
    (True, 12345),
])
def test_article_serializer_favorited_and_favorites_count(favorited_return, favorites_count_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_obj = SimpleNamespace(id=42)
    request_obj = SimpleNamespace(user=user_obj)
    serializer = ArticleSerializer(context={"request": request_obj})

    def fake_has_favorited(user):
        # act as if only our user is checked
        assert user is user_obj
        return favorited_return

    fake_favorites = SimpleNamespace(count=lambda: favorites_count_value)
    article_obj = SimpleNamespace(has_favorited=fake_has_favorited, favorites=fake_favorites)

    # Act
    try:
        favorited_result = serializer.get_favorited(article_obj)
    except AttributeError as exc:
        raise

    try:
        favorites_count_result = serializer.get_favorites_count(article_obj)
    except AttributeError as exc:
        raise

    # Assert
    assert isinstance(favorited_result, _exc_lookup("bool", Exception)), "get_favorited should return a bool"
    assert favorited_result == favorited_return
    assert isinstance(favorites_count_result, _exc_lookup("int", Exception)), "get_favorites_count should return an int"
    assert favorites_count_result == favorites_count_value

@pytest.mark.parametrize("should_raise", [False, True])
def test_comments_destroy_api_view_calls_delete_and_handles_errors(monkeypatch, should_raise):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = CommentsDestroyAPIView()
    deletion_flag = {"deleted": False}

    def successful_delete():
        deletion_flag["deleted"] = True

    def failing_delete():
        raise RuntimeError("delete failed")

    fake_comment = SimpleNamespace(delete=successful_delete if not should_raise else failing_delete)
    # Monkeypatch the view's get_object to return our fake_comment
    monkeypatch.setattr(view, "get_object", lambda: fake_comment)

    dummy_request = SimpleNamespace(user=SimpleNamespace(id=1))

    # Act / Assert
    if should_raise:
        with pytest.raises(_exc_lookup("RuntimeError", Exception)):
            view.delete(dummy_request, pk=1)
        assert deletion_flag["deleted"] is False
    else:
        response = view.delete(dummy_request, pk=1)
        # DRF Response objects have status_code attribute; accept either int or attribute access
        status_code = getattr(response, "status_code", None) or response
        assert int(status_code) == 204
        assert deletion_flag["deleted"] is True

@pytest.mark.parametrize("tag_name", ["python", "", "a"*300])
def test_tag_serializer_to_representation_handles_various_names(tag_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer = TagSerializer()
    tag_obj = SimpleNamespace(name=tag_name)

    # Act
    try:
        rep = serializer.to_representation(tag_obj)
    except AttributeError:
        # If the serializer uses .data flow instead, try instantiating with instance and reading .data
        try:
            instance_serializer = TagSerializer(instance=tag_obj)
            rep = instance_serializer.data
        except Exception:
            raise

    # Assert
    assert isinstance(rep, _exc_lookup("dict", Exception)), "Tag serializer representation should be a dict"
    # Accept 'name' key mapping to provided tag_name
    assert rep.get("name") == tag_name, "Serialized 'name' should match the tag object's name"
