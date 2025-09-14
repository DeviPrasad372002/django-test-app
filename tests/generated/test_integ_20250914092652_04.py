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

import pytest

try:
    from types import SimpleNamespace
    import conduit.apps.profiles.serializers as profiles_serializers
    import conduit.apps.profiles.models as profiles_models
    import conduit.apps.articles.serializers as articles_serializers
except ImportError:
    pytest.skip("requires conduit package", allow_module_level=True)

def _make_request_user(username):
    return SimpleNamespace(username=username)

def _make_profile_user(username, image=None, bio=None):
    return SimpleNamespace(username=username, image=image, bio=bio)

def _make_profile_obj(user, image=None):
    return SimpleNamespace(user=user, image=image)

def _make_article_obj(slug="a-slug", favorites_count=0, author=None):
    if author is None:
        author = _make_profile_user("author")
    return SimpleNamespace(slug=slug, favorites_count=favorites_count, author=author)

def _serializer_instance_or_fail(serializer_module, class_name, instance, context):
    cls = getattr(serializer_module, class_name, None)
    assert cls is not None, f"{class_name} not found in module"
    return cls(instance=instance, context=context)

def _ensure_method(obj, name):
    fn = getattr(obj, name, None)
    assert callable(fn), f"Method {name} missing or not callable"
    return fn

def test_profile_serializer_get_image_and_get_following(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer_cls = getattr(profiles_serializers, "ProfileSerializer", None)
    assert serializer_cls is not None, "ProfileSerializer must be present in profiles.serializers"
    target_user = _make_profile_user("alice", image="http://img.example/alice.png", bio="bio")
    profile_obj = _make_profile_obj(target_user, image=None)
    actor_user = _make_request_user("bob")
    request = SimpleNamespace(user=actor_user)
    serializer_instance = serializer_cls(instance=profile_obj, context={"request": request})

    # Replace underlying model-level function to avoid DB and to simulate logic seam
    def fake_is_following(target_user_arg, actor_user_arg):
        # Assert integration seam receives the expected objects (duck-typed)
        assert getattr(target_user_arg, "username", None) == "alice"
        assert getattr(actor_user_arg, "username", None) == "bob"
        return True
    monkeypatch.setattr(profiles_models, "is_following", fake_is_following, raising=False)

    # Act
    get_image_fn = _ensure_method(serializer_instance, "get_image")
    image_result = get_image_fn(profile_obj)
    get_following_fn = _ensure_method(serializer_instance, "get_following")
    following_result = get_following_fn(profile_obj)

    # Assert
    assert isinstance(image_result, (str, type(None)))
    assert image_result == "http://img.example/alice.png"
    assert following_result is True

@pytest.mark.parametrize("initial_favorites, favorite_action_sequence, expected_counts", [
    (0, ["favorite",], [1]),
    (1, ["unfavorite",], [0]),
])
def test_article_favoriting_flow_integration(monkeypatch, initial_favorites, favorite_action_sequence, expected_counts):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article_cls = getattr(articles_serializers, "ArticleSerializer", None)
    assert article_cls is not None, "ArticleSerializer must be present in articles.serializers"
    actor_user = _make_request_user("contributor")
    # Attach an attribute to emulate in-memory favorites set for the fake user
    setattr(actor_user, "_favorites", set())
    # Pre-seed a favorite if requested
    article = _make_article_obj(slug="int-article", favorites_count=initial_favorites, author=_make_profile_user("author"))
    if initial_favorites:
        actor_user._favorites.add(article.slug)

    # Monkeypatch model-level favoriting functions to manipulate in-memory state
    def fake_favorite(user_obj, article_obj):
        favs = getattr(user_obj, "_favorites", None)
        if favs is None:
            favs = set()
            setattr(user_obj, "_favorites", favs)
        if article_obj.slug not in favs:
            favs.add(article_obj.slug)
            article_obj.favorites_count = getattr(article_obj, "favorites_count", 0) + 1
        return None

    def fake_unfavorite(user_obj, article_obj):
        favs = getattr(user_obj, "_favorites", set())
        if article_obj.slug in favs:
            favs.remove(article_obj.slug)
            # Avoid negatives
            article_obj.favorites_count = max(0, getattr(article_obj, "favorites_count", 1) - 1)
        return None

    def fake_has_favorited(user_obj, article_obj):
        return article_obj.slug in getattr(user_obj, "_favorites", set())

    monkeypatch.setattr(profiles_models, "favorite", fake_favorite, raising=False)
    monkeypatch.setattr(profiles_models, "unfavorite", fake_unfavorite, raising=False)
    monkeypatch.setattr(profiles_models, "has_favorited", fake_has_favorited, raising=False)

    serializer_instance = article_cls(instance=article, context={"request": SimpleNamespace(user=actor_user)})

    # Ensure serializer exposes the expected accessors
    get_favorited_fn = _ensure_method(serializer_instance, "get_favorited")
    get_favorites_count_fn = _ensure_method(serializer_instance, "get_favorites_count")

    # Act & Assert sequence for each action in test scenario
    results = []
    for action in favorite_action_sequence:
        if action == "favorite":
            profiles_models.favorite(actor_user, article)
        elif action == "unfavorite":
            profiles_models.unfavorite(actor_user, article)
        else:
            raise AssertionError("Unexpected action in test sequence")
        results.append((get_favorited_fn(article), get_favorites_count_fn(article)))

    # Verify results against expected counts and boolean favorited values
    for idx, expected_count in enumerate(expected_counts):
        favorited_bool, count = results[idx]
        assert isinstance(favorited_bool, _exc_lookup("bool", Exception))
        assert count == expected_count

@pytest.mark.parametrize("has_favorited_return_value, expected_bool", [
    (0, False),
    (1, True),
    (None, False),
])
def test_get_favorited_handles_various_backend_return_types(monkeypatch, has_favorited_return_value, expected_bool):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article_cls = getattr(articles_serializers, "ArticleSerializer", None)
    assert article_cls is not None, "ArticleSerializer must be present in articles.serializers"
    actor_user = _make_request_user("edgecase_user")
    article = _make_article_obj(slug="edge-article", favorites_count=0)

    # Provide serializer with no request in context to exercise default-handling path
    serializer_instance_no_request = article_cls(instance=article, context={})
    get_favorited_no_req = _ensure_method(serializer_instance_no_request, "get_favorited")
    # When there is no request, many serializers return False gracefully
    no_req_result = get_favorited_no_req(article)
    assert no_req_result is False

    # Now monkeypatch the backend to return various truthy/falsey values
    def fake_has_favorited(user_obj, article_obj):
        return has_favorited_return_value

    monkeypatch.setattr(profiles_models, "has_favorited", fake_has_favorited, raising=False)

    # Provide serializer with request context now
    serializer_instance = article_cls(instance=article, context={"request": SimpleNamespace(user=actor_user)})
    get_favorited_fn = _ensure_method(serializer_instance, "get_favorited")

    # Act
    result = get_favorited_fn(article)

    # Assert: ensure non-boolean returns are normalized to boolean
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result is expected_bool
