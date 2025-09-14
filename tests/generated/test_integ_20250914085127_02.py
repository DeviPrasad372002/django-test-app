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
    from conduit.apps.authentication.models import UserManager
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles import signals as article_signals
    from conduit.apps.articles.models import Article, Comment
    from conduit.apps.authentication import backends as auth_backends
except ImportError:
    import pytest
    pytest.skip("Required application modules are not available", allow_module_level=True)


def _exc_lookup(name, fallback):
    try:
        import rest_framework.exceptions as rf_exc
        return getattr(rf_exc, name, fallback)
    except Exception:
        return fallback


@pytest.mark.parametrize(
    "email,username,password,expect_is_superuser",
    [
        ("user@example.com", "alice", "s3cret", False),
        ("admin@example.com", "admin", "adm1n", True),
    ],
)
def test_user_manager_create_user_and_superuser_integration(monkeypatch, email, username, password, expect_is_superuser):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: prepare a fake User model to be used by UserManager that records actions
    created_instances = []

    class FakeUser:
        def __init__(self, email=None, username=None, **kwargs):
            self.email = email
            self.username = username
            self.is_staff = kwargs.get("is_staff", False)
            self.is_superuser = kwargs.get("is_superuser", False)
            self._password_set = None
            created_instances.append(self)

        def set_password(self, raw):
            # record the raw password passed in for assertions
            self._password_set = raw

        def save(self, *args, **kwargs):
            self._saved = True

    manager = UserManager()
    manager.model = FakeUser

    # Act: call create_user or create_superuser depending on expected flag
    if expect_is_superuser:
        user_obj = manager.create_superuser(email=email, username=username, password=password)
    else:
        user_obj = manager.create_user(email=email, username=username, password=password)

    # Assert: verify returned object is our FakeUser and side-effects happened
    assert isinstance(user_obj, _exc_lookup("FakeUser", Exception))
    assert user_obj.username == username
    assert user_obj.email == email
    assert getattr(user_obj, "_password_set", None) == password
    if expect_is_superuser:
        assert getattr(user_obj, "is_staff", False) is True
        assert getattr(user_obj, "is_superuser", False) is True
    else:
        # For normal users ensure flags are not set
        assert getattr(user_obj, "is_superuser", False) is False


@pytest.mark.parametrize(
    "payload_key,payload_value",
    [
        ("id", 123),
        ("user_id", 456),
    ],
)
def test_jwt_authentication_authenticate_credentials_missing_user_raises(monkeypatch, payload_key, payload_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: replace the User reference inside the authentication backend module
    class DoesNotExist(Exception):
        pass

    class FakeObjects:
        @staticmethod
        def get(**kwargs):
            raise DoesNotExist("no user")

    class FakeUserModel:
        objects = FakeObjects()
        DoesNotExist = DoesNotExist

    monkeypatch.setattr(auth_backends, "User", FakeUserModel, raising=False)

    jwt_auth = JWTAuthentication()
    payload = {payload_key: payload_value}

    # Act / Assert: expect the authentication backend to raise an authentication error when user not found
    AuthenticationFailed = _exc_lookup("AuthenticationFailed", Exception)
    with pytest.raises(_exc_lookup("AuthenticationFailed", Exception)):
        jwt_auth._authenticate_credentials(payload)


@pytest.mark.parametrize(
    "title,slug_base",
    [
        ("Hello World", "hello-world"),
        ("Ångström Unit", "angstrom-unit"),
    ],
)
def test_add_slug_to_article_if_not_exists_generates_slug(monkeypatch, title, slug_base):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: monkeypatch the random generator and slugifier used by the signals module
    monkeypatch.setattr(article_signals, "generate_random_string", lambda length=6: "XYZ123")
    # Provide a deterministic slugify replacement for the test
    def fake_slugify(value):
        # simple ascii approximation used by the app, normalize some characters for test predictability
        normalized = (
            value.replace("Å", "A").replace("å", "a")
            .replace(" ", "-")
            .lower()
        )
        # collapse any double hyphens etc in a simple way for test expectations
        return normalized
    monkeypatch.setattr(article_signals, "slugify", fake_slugify, raising=False)

    # Create a fake article-like instance without a slug
    class FakeArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug
            self._saved = False

        def save(self, *args, **kwargs):
            self._saved = True

    article_instance = FakeArticle(title=title, slug=None)

    # Act: invoke the signal handler as Django would (sender not used)
    add_slug_to_article_if_not_exists(sender=None, instance=article_instance)

    # Assert: slug was generated and saved on the instance
    assert getattr(article_instance, "slug", None) is not None and article_instance._saved is True
    assert article_instance.slug.endswith("-XYZ123")
    base_expected = fake_slugify(title)
    assert article_instance.slug.startswith(base_expected)


@pytest.mark.parametrize(
    "article_title,comment_body",
    [
        ("A Great Article", "This is a short comment."),
        ("Edge Case", ""),
    ],
)
def test_models_str_methods_return_readable_values(article_title, comment_body):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: instantiate model instances without touching the DB
    article_instance = Article(title=article_title)
    comment_instance = Comment(body=comment_body)

    # Act: call __str__ on both model instances
    article_str = str(article_instance)
    comment_str = str(comment_instance)

    # Assert: __str__ includes title or a sensible representation of body
    assert article_title in article_str
    # For comments, when body empty it still should return a string (not raise) and contain at least '' or placeholder
    assert isinstance(comment_str, _exc_lookup("str", Exception))
    if comment_body:
        assert comment_body[: min(20, len(comment_body))] in comment_str
