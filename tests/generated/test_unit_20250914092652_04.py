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
    import pytest
    from types import SimpleNamespace
    import builtins

    import conduit.apps.profiles.models as profiles_models
    import conduit.apps.profiles.serializers as profiles_serializers
    import conduit.apps.articles.relations as articles_relations
except ImportError:
    import pytest
    pytest.skip("Skipping tests because target package is not available", allow_module_level=True)


def _resolve_callable(module, names):
    """
    Try to resolve a callable from a module by several candidate names.
    names: list of str like "favorite" or "Profile.favorite" or "User.favorite"
    Returns (callable, owner_is_class_bool)
    """
    for candidate in names:
        if "." in candidate:
            cls_name, attr_name = candidate.split(".", 1)
            cls = getattr(module, cls_name, None)
            if cls is not None and hasattr(cls, attr_name):
                return getattr(cls, attr_name), True
        else:
            if hasattr(module, candidate):
                return getattr(module, candidate), False
    raise AttributeError("None of candidates found: %r" % names)


class FakeM2M:
    def __init__(self, initial=None):
        self._set = set(initial or [])

    def add(self, item):
        self._set.add(item)

    def remove(self, item):
        self._set.discard(item)

    def __contains__(self, item):
        return item in self._set

    def all(self):
        return list(self._set)

    def filter(self, **kwargs):
        """
        Simulate Django queryset filter(pk=...) returning object with exists()
        Accepts pk or id key; will check membership by comparing item.pk
        """
        key, value = next(iter(kwargs.items()))
        expected = value
        items = [it for it in self._set if getattr(it, 'pk', getattr(it, 'id', None)) == expected]
        class Q:
            def __init__(self, found):
                self._found = found
            def exists(self):
                return bool(self._found)
        return Q(items)


class FakeUser:
    def __init__(self, pk=None):
        self.pk = pk
        self.favorites = FakeM2M()
        # followers/following used in profile following model
        self.followers = FakeM2M()
        self.following = FakeM2M()
        self.image = None  # used by serializer get_image


@pytest.mark.parametrize("initially_favorited", [False, True])
def test_favorite_and_unfavorite_and_has_favorited(initially_favorited):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    favorite_callable, owned_on_class = _resolve_callable(
        profiles_models, ["favorite", "Profile.favorite", "User.favorite"]
    )
    unfavorite_callable, _ = _resolve_callable(
        profiles_models, ["unfavorite", "Profile.unfavorite", "User.unfavorite"]
    )
    has_favorited_callable, _ = _resolve_callable(
        profiles_models, ["has_favorited", "Profile.has_favorited", "User.has_favorited"]
    )

    user = FakeUser(pk=10)
    article = SimpleNamespace(pk=5)
    if initially_favorited:
        user.favorites.add(article)

    # Act - favorite should be idempotent: after favoriting it's favorited
    # Call as bound/unbound: if owned_on_class True call function(user, article) else call as module-level
    if owned_on_class:
        favorite_callable(user, article)
    else:
        favorite_callable(user, article)

    # Assert favorite recorded
    assert (article in user.favorites) is True
    # Act & Assert has_favorited reports presence
    if owned_on_class:
        result = has_favorited_callable(user, article)
    else:
        result = has_favorited_callable(user, article)
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result is True

    # Act - unfavorite should remove without raising if not present
    if owned_on_class:
        unfavorite_callable(user, article)
    else:
        unfavorite_callable(user, article)

    # Assert removed
    assert (article in user.favorites) is False
    if owned_on_class:
        after = has_favorited_callable(user, article)
    else:
        after = has_favorited_callable(user, article)
    assert after is False


def test_follow_unfollow_is_following_is_followed_by_state_changes():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    follow_callable, _ = _resolve_callable(
        profiles_models, ["follow", "Profile.follow", "User.follow"]
    )
    unfollow_callable, _ = _resolve_callable(
        profiles_models, ["unfollow", "Profile.unfollow", "User.unfollow"]
    )
    is_following_callable, _ = _resolve_callable(
        profiles_models, ["is_following", "Profile.is_following", "User.is_following"]
    )
    is_followed_by_callable, _ = _resolve_callable(
        profiles_models, ["is_followed_by", "Profile.is_followed_by", "User.is_followed_by"]
    )

    follower = FakeUser(pk=1)
    followee = FakeUser(pk=2)

    # Pre-conditions
    assert not (followee in follower.following)
    assert not (follower in followee.followers)

    # Act - follower follows followee
    follow_callable(follower, followee)

    # Assert linking is symmetric (implementation may add both directions)
    assert (followee in follower.following) or (follower in followee.followers)
    # Use provided helpers
    assert isinstance(is_following_callable(follower, followee), bool)
    assert isinstance(is_followed_by_callable(followee, follower), bool)
    assert is_following_callable(follower, followee) is True
    assert is_followed_by_callable(followee, follower) is True

    # Act - unfollow and ensure relationships removed
    unfollow_callable(follower, followee)
    assert is_following_callable(follower, followee) is False
    assert is_followed_by_callable(followee, follower) is False


@pytest.mark.parametrize("img_attr, expected", [
    (None, None),
    ("http://example.com/pic.png", "http://example.com/pic.png"),
])
def test_get_image_and_get_following_and_tagrelatedfield(img_attr, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange - resolve serializer helper functions
    get_image_callable = getattr(profiles_serializers, "get_image", None)
    get_following_callable = getattr(profiles_serializers, "get_following", None)

    # TagRelatedField may be exported as class in articles_relations
    TagRelatedField = getattr(articles_relations, "TagRelatedField", None)

    # Make a fake profile/user and serializer context
    user = FakeUser(pk=99)
    profile = FakeUser(pk=100)
    # prepare image attribute structure: either None or object with url
    if img_attr is None:
        profile.image = None
    else:
        profile.image = SimpleNamespace(url=img_attr)

    # Serializer instance replacement with context that contains request.user
    fake_serializer = SimpleNamespace(context={"request": SimpleNamespace(user=user)})

    # Ensure get_image exists and behaves reasonably
    if get_image_callable is not None:
        image_output = get_image_callable(fake_serializer, profile)
        assert image_output == expected

    # Simulate that user is following profile by setting followers/following
    # Add user to profile.followers to simulate user follows profile (i.e., profile is followed by user)
    profile.followers.add(user)
    if get_following_callable is not None:
        following_output = get_following_callable(fake_serializer, profile)
        # following should be boolean and True because we added user in followers
        assert isinstance(following_output, _exc_lookup("bool", Exception))
        assert following_output is True

    # TagRelatedField should at least transform a tag-like object to a string representation
    if TagRelatedField is not None:
        trf = TagRelatedField()
        fake_tag = SimpleNamespace(name="python", slug="python")
        # to_representation may prefer 'name' or 'slug'
        rep = trf.to_representation(fake_tag)
        assert isinstance(rep, (str, bytes))
        assert "python" in str(rep)

        # to_internal_value often accepts a string and returns a Tag-like object or string; ensure acceptance and type
        internal = trf.to_internal_value("django")
        assert internal is not None
        assert isinstance(internal, (str, bytes)) or hasattr(internal, "name") or hasattr(internal, "slug")
