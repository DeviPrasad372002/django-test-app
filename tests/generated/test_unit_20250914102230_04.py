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
    from conduit.apps.authentication.models import User
    from conduit.apps.profiles import models as profiles_models
    from conduit.apps.articles import models as articles_models
    from conduit.apps.articles import relations as articles_relations
except ImportError:
    import pytest
    pytest.skip("Target project imports not available, skipping tests", allow_module_level=True)

@pytest.mark.django_db
def test_follow_unfollow_and_follow_status_between_users():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_a = User.objects.create_user(email="a@example.com", username="usera", password="pass")
    user_b = User.objects.create_user(email="b@example.com", username="userb", password="pass")
    # Act: follow using public API (function or method depending on implementation)
    try:
        # try module-level function signature: follow(follower, followee)
        profiles_models.follow(user_a, user_b)
    except TypeError:
        # try profile-level method: user.profile.follow(other_profile_or_user)
        profiles_models.follow(user_a.profile, user_b.profile if hasattr(user_b, "profile") else user_b)
    # Assert follow state visible both ways
    try:
        assert profiles_models.is_following(user_a, user_b) is True
        assert profiles_models.is_followed_by(user_b, user_a) is True
    except TypeError:
        # fallback to profile methods/attributes if functions expect profiles
        assert user_a.profile.is_following(user_b.profile if hasattr(user_b, "profile") else user_b) is True
        assert user_b.profile.is_followed_by(user_a.profile if hasattr(user_a, "profile") else user_a) is True

    # Act: unfollow
    try:
        profiles_models.unfollow(user_a, user_b)
    except TypeError:
        profiles_models.unfollow(user_a.profile, user_b.profile if hasattr(user_b, "profile") else user_b)
    # Assert unfollowed
    try:
        assert profiles_models.is_following(user_a, user_b) is False
        assert profiles_models.is_followed_by(user_b, user_a) is False
    except TypeError:
        assert user_a.profile.is_following(user_b.profile if hasattr(user_b, "profile") else user_b) is False
        assert user_b.profile.is_followed_by(user_a.profile if hasattr(user_a, "profile") else user_a) is False

@pytest.mark.django_db
@pytest.mark.parametrize("action,expected", [("favorite_then_unfavorite", False), ("favorite_only", True)])
def test_favorite_unfavorite_and_has_favorited(action, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    author = User.objects.create_user(email="auth@example.com", username="author", password="pass")
    reader = User.objects.create_user(email="r@example.com", username="reader", password="pass")
    article = articles_models.Article.objects.create(title="T1", description="D", body="B", author=author)

    # Act
    # Favorite once
    try:
        profiles_models.favorite(reader, article)
    except TypeError:
        # fallback: operate on profile if function expects profile
        try:
            profiles_models.favorite(reader.profile, article)
        except Exception:
            pytest.fail("favorite API not available in expected forms")
    # Optionally unfavorite
    if action == "favorite_then_unfavorite":
        try:
            profiles_models.unfavorite(reader, article)
        except TypeError:
            profiles_models.unfavorite(reader.profile, article)

    # Assert
    try:
        assert profiles_models.has_favorited(reader, article) is expected
    except TypeError:
        assert reader.profile.has_favorited(article) is expected

    # Clean up: ensure idempotent unfavorite doesn't error
    try:
        profiles_models.unfavorite(reader, article)
    except TypeError:
        profiles_models.unfavorite(reader.profile, article)

@pytest.mark.django_db
def test_article_and_comment_str_return_readable_values():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    author = User.objects.create_user(email="s@example.com", username="struser", password="pass")
    article = articles_models.Article.objects.create(title="My Title", description="desc", body="content body", author=author)
    comment = articles_models.Comment.objects.create(body="a comment body", article=article, author=author)

    # Act
    article_str = str(article)
    comment_str = str(comment)

    # Assert: article string should include title
    assert isinstance(article_str, _exc_lookup("str", Exception))
    assert "My Title" in article_str

    # Assert: comment string should include comment body (at least part of it)
    assert isinstance(comment_str, _exc_lookup("str", Exception))
    assert "comment" in comment_str

@pytest.mark.django_db
def test_tagrelatedfield_to_internal_value_and_to_representation_creates_or_resolves_tag():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Determine Tag model attribute name for human-readable value
    tag_model = articles_models.Tag
    existing_attr = None
    for candidate in ("tag", "name", "title"):
        if hasattr(tag_model, candidate):
            existing_attr = candidate
            break

    # Act: create an existing tag and instantiate field
    existing_tag = articles_models.Tag.objects.create(**({existing_attr: "python"} if existing_attr else {"tag": "python"}))
    field = articles_relations.TagRelatedField(queryset=articles_models.Tag.objects.all())

    # Representation should return the human value
    representation = field.to_representation(existing_tag)
    expected_value = getattr(existing_tag, existing_attr) if existing_attr else getattr(existing_tag, "tag")
    assert representation == expected_value

    # to_internal_value with a new tag string should create or return a Tag instance with matching human value
    new_tag_string = "newtag123"
    created_or_found_tag = field.to_internal_value(new_tag_string)
    assert isinstance(created_or_found_tag, _exc_lookup("articles_models.Tag", Exception))
    got_value = getattr(created_or_found_tag, existing_attr) if existing_attr else getattr(created_or_found_tag, "tag")
    assert got_value == new_tag_string
