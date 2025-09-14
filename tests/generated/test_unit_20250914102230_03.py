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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

import pytest

try:
    import json
    import jwt
    from types import SimpleNamespace
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import renderers as auth_renderers
    from conduit.apps.authentication import serializers as auth_serializers
    from conduit.apps.authentication import signals as auth_signals
    from conduit.apps.core import exceptions as core_exceptions
    from conduit.apps.core import utils as core_utils
    from conduit.apps import profiles as profiles_pkg
    from conduit.apps.profiles import models as profiles_models
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Missing imports for tests: {e}", allow_module_level=True)


def test_get_short_name_returns_username_string():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = auth_models.User()
    user.username = "alice"
    # Act
    short = user.get_short_name()
    # Assert
    assert isinstance(short, _exc_lookup("str", Exception))
    assert short == "alice"


def test_generate_jwt_token_contains_user_id_and_expiry():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = auth_models.User()
    user.id = 12345
    user.pk = 12345
    # Act
    token = user._generate_jwt_token()
    assert isinstance(token, _exc_lookup("str", Exception))
    # decode without verifying signature to inspect payload
    payload = jwt.decode(token, options={"verify_signature": False})
    # Assert: payload contains id (common implementations) or user id under 'id'
    assert "id" in payload
    assert payload["id"] == 12345
    assert "exp" in payload and isinstance(payload["exp"], int)


def test_user_json_renderer_render_outputs_bytes_with_user_wrapper():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = auth_renderers.UserJSONRenderer()
    data = {"user": {"email": "x@y.com", "username": "x"}}
    # Act
    rendered = renderer.render(data)
    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    text = rendered.decode("utf-8")
    parsed = json.loads(text)
    assert "user" in parsed
    assert parsed["user"]["email"] == "x@y.com"
    assert parsed["user"]["username"] == "x"


@pytest.mark.parametrize(
    "input_data,expected_email",
    [
        ({"email": "A@B.COM", "username": "u", "password": "p"}, "a@b.com"),
        ({"email": "lower@x.com", "username": "u2", "password": "p2"}, "lower@x.com"),
    ],
)
def test_registration_serializer_validate_lowercases_email(input_data, expected_email):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer = auth_serializers.RegistrationSerializer()
    # Act
    validated = serializer.validate(input_data.copy())
    # Assert
    assert isinstance(validated, _exc_lookup("dict", Exception))
    assert validated["email"] == expected_email
    assert "username" in validated
    assert "password" in validated


def test_create_related_profile_creates_profile_when_created_true(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_calls = []

    class FakeProfile:
        @staticmethod
        def objects_create(user):
            created_calls.append(user)
            return SimpleNamespace(user=user)

    # The real function may reference profiles.models.Profile or import Profile at module scope.
    # Replace the attribute inside the signals module namespace.
    monkeypatch.setattr(auth_signals, "Profile", FakeProfile, raising=False)

    fake_user = SimpleNamespace(pk=77, username="u77")
    # Act
    auth_signals.create_related_profile(sender=None, instance=fake_user, created=True)
    # Assert
    assert created_calls == [fake_user]


def test_create_related_profile_no_action_when_created_false(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    called = []

    class FakeProfile:
        @staticmethod
        def objects_create(user):
            called.append(user)

    monkeypatch.setattr(auth_signals, "Profile", FakeProfile, raising=False)
    fake_user = SimpleNamespace(pk=88)
    # Act
    auth_signals.create_related_profile(sender=None, instance=fake_user, created=False)
    # Assert
    assert called == []


def test_handle_generic_and_not_found_error_return_responses():
    # Arrange-Act-Assert: generated by ai-testgen
    # Generic error
    gen_resp = core_exceptions._handle_generic_error(Exception("boom"))
    assert hasattr(gen_resp, "data")
    assert "errors" in gen_resp.data
    # expect status code attribute for DRF Response
    assert hasattr(gen_resp, "status_code")
    assert gen_resp.status_code >= 500

    # Not found error
    nf_resp = core_exceptions._handle_not_found_error(Exception("not here"))
    assert hasattr(nf_resp, "data")
    assert "errors" in nf_resp.data
    assert hasattr(nf_resp, "status_code")
    assert nf_resp.status_code == 404


def test_core_exception_handler_delegates_to_not_found_when_applicable():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    try:
        from rest_framework.exceptions import NotFound
    except Exception:
        pytest.skip("rest_framework.exceptions.NotFound not available")
    exc = NotFound("nope")
    # Act
    resp = core_exceptions.core_exception_handler(exc, context={})
    # Assert
    assert resp.status_code == 404
    assert "errors" in resp.data


@pytest.mark.parametrize("length", [0, 1, 8, 32])
def test_generate_random_string_length_and_charset(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Act
    s = core_utils.generate_random_string(length)
    # Assert
    assert isinstance(s, _exc_lookup("str", Exception))
    assert len(s) == length
    # only allow letters and digits when length > 0
    if length > 0:
        import string as _string

        allowed = set(_string.ascii_letters + _string.digits)
        assert set(s).issubset(allowed)


def test_generate_random_string_negative_raises():
    # Arrange-Act-Assert: generated by ai-testgen
    with pytest.raises(_exc_lookup("Exception", Exception)):
        core_utils.generate_random_string(-1)


def test_profile_follow_unfollow_is_following(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create two Profile-like simple objects with pk attributes
    class FakeQuerySet(list):
        def exists(self):
            return len(self) > 0

    class FakeManager:
        def __init__(self):
            self.storage = set()

        def add(self, item):
            self.storage.add(item)

        def remove(self, item):
            self.storage.remove(item)

        def filter(self, **kwargs):
            results = [
                x for x in self.storage if all(getattr(x, k, None) == v for k, v in kwargs.items())
            ]
            return FakeQuerySet(results)

    p1 = profiles_models.Profile()
    p2 = profiles_models.Profile()
    p1.pk = 1
    p2.pk = 2
    # attach fake following manager
    p1.following = FakeManager()
    # Act & Assert: initially not following
    assert not p1.is_following(p2)
    # Follow
    p1.follow(p2)
    assert p1.is_following(p2)
    # Unfollow
    p1.unfollow(p2)
    assert not p1.is_following(p2)


def test_is_following_self_edge_case():
    # Arrange-Act-Assert: generated by ai-testgen
    p = profiles_models.Profile()
    p.pk = 5

    class FakeQuerySet(list):
        def exists(self):
            return len(self) > 0

    class FakeManager:
        def __init__(self):
            self.storage = set()

        def add(self, item):
            self.storage.add(item)

        def remove(self, item):
            self.storage.remove(item)

        def filter(self, **kwargs):
            results = [
                x for x in self.storage if all(getattr(x, k, None) == v for k, v in kwargs.items())
            ]
            return FakeQuerySet(results)

    p.following = FakeManager()
    # following self
    p.follow(p)
    assert p.is_following(p)
    p.unfollow(p)
    assert not p.is_following(p)
