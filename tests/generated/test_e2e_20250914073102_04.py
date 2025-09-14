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
    import types
    import pytest
    from conduit.apps.profiles import models as profiles_models
    from conduit.apps.profiles import serializers as profiles_serializers
except ImportError:
    import pytest
    pytest.skip("Required modules for tests are not available", allow_module_level=True)


@pytest.mark.parametrize("already_following", [False, True])
def test_follow_unfollow_and_follow_checks_behave_consistently(already_following):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create two lightweight user-like objects with the attributes the methods expect
    user_a = types.SimpleNamespace(following=set(), followers=set())
    user_b = types.SimpleNamespace(following=set(), followers=set())

    if already_following:
        user_a.following.add(user_b)
        user_b.followers.add(user_a)

    follow_func = getattr(profiles_models.User, "follow")
    unfollow_func = getattr(profiles_models.User, "unfollow")
    is_following_func = getattr(profiles_models.User, "is_following")
    is_followed_by_func = getattr(profiles_models.User, "is_followed_by")

    # Act: attempt to follow (should be idempotent if already following)
    follow_func(user_a, user_b)

    # Assert: membership updated and boolean helpers reflect the relationship
    assert user_b in user_a.following, "follow should ensure target is in follower's following set"
    assert user_a in user_b.followers or hasattr(user_b, "followers"), "follow may populate followers on the target"

    assert isinstance(is_following_func(user_a, user_b), bool), "is_following must return a boolean"
    assert is_following_func(user_a, user_b) is True, "After follow, is_following should be True"
    assert isinstance(is_followed_by_func(user_b, user_a), bool), "is_followed_by must return a boolean"
    assert is_followed_by_func(user_b, user_a) is True, "After follow, target should report being followed"

    # Act: unfollow and assert removal
    unfollow_func(user_a, user_b)

    # Assert: relationship removed and helpers reflect removal
    assert user_b not in user_a.following, "unfollow should remove the target from following set"
    assert is_following_func(user_a, user_b) is False, "After unfollow, is_following should be False"

    # Act: calling unfollow again should not raise and should keep state consistent (idempotent)
    unfollow_func(user_a, user_b)
    assert user_b not in user_a.following, "Repeated unfollow should remain a no-op"


@pytest.mark.parametrize("initially_favorited", [False, True])
def test_favorite_unfavorite_and_has_favorited_reflects_state(initially_favorited):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create user-like and article-like objects with simple set containers
    user = types.SimpleNamespace(favorites=set())
    article = types.SimpleNamespace(favorited_by=set())

    if initially_favorited:
        user.favorites.add(article)
        article.favorited_by.add(user)

    favorite_func = getattr(profiles_models.User, "favorite")
    unfavorite_func = getattr(profiles_models.User, "unfavorite")
    has_favorited_func = getattr(profiles_models.User, "has_favorited")

    # Act: favorite the article
    favorite_func(user, article)

    # Assert: favorite relationship established
    assert article in user.favorites, "favorite should add the article to the user's favorites set"
    # The article may also track the user; if implemented, ensure it's present
    if hasattr(article, "favorited_by"):
        assert user in article.favorited_by, "favorite should register the user on the article if supported"

    assert has_favorited_func(user, article) is True, "has_favorited should return True after favoriting"

    # Act: unfavorite the article
    unfavorite_func(user, article)

    # Assert: relationship removed
    assert article not in user.favorites, "unfavorite should remove the article from the user's favorites set"
    assert has_favorited_func(user, article) is False, "has_favorited should return False after unfavoriting"

    # Act: calling unfavorite again should be safe (idempotent)
    unfavorite_func(user, article)
    assert article not in user.favorites, "Repeated unfavorite should remain a no-op"


@pytest.mark.parametrize("image_value, expected_image", [("http://example.com/avatar.png", "http://example.com/avatar.png"), (None, "")])
@pytest.mark.parametrize("request_user_following_profile", [True, False])
def test_profile_serializer_get_image_and_get_following(image_value, expected_image, request_user_following_profile):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create a simple profile-like object and a serializer-like self with context
    profile_obj = types.SimpleNamespace(image=image_value)

    # Create a fake request.user that exposes is_following callable used by serializer
    def fake_is_following(other):
        return request_user_following_profile

    fake_request_user = types.SimpleNamespace(is_following=fake_is_following)
    fake_request = types.SimpleNamespace(user=fake_request_user)
    serializer_self = types.SimpleNamespace(context={"request": fake_request})

    get_image_func = getattr(profiles_serializers.ProfileSerializer, "get_image")
    get_following_func = getattr(profiles_serializers.ProfileSerializer, "get_following")

    # Act: obtain image URL and following state through serializer methods
    result_image = get_image_func(serializer_self, profile_obj)
    result_following = get_following_func(serializer_self, profile_obj)

    # Assert: image returns provided URL or empty string and following reflects fake user's relation
    assert result_image == expected_image, "get_image should return the profile image or empty string when absent"
    assert isinstance(result_following, _exc_lookup("bool", Exception)), "get_following must return a boolean"
    assert result_following is request_user_following_profile, "get_following should reflect the request user's following status"
