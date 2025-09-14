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
    import importlib
    import types
    import json
    import pytest
    from unittest import mock

    auth_models = importlib.import_module("conduit.apps.authentication.models")
    auth_renderers = importlib.import_module("conduit.apps.authentication.renderers")
    auth_serializers = importlib.import_module("conduit.apps.authentication.serializers")
    auth_signals = importlib.import_module("conduit.apps.authentication.signals")
    core_exceptions = importlib.import_module("conduit.apps.core.exceptions")
    core_utils = importlib.import_module("conduit.apps.core.utils")
    profile_models = importlib.import_module("conduit.apps.profiles.models")
    rest_exceptions = importlib.import_module("rest_framework.exceptions")
    rest_response_mod = importlib.import_module("rest_framework.response")
except ImportError:
    import pytest
    pytest.skip("Required modules for tests are not available", allow_module_level=True)


def _exc_lookup(name, default=Exception):
    try:
        mod = importlib.import_module("rest_framework.exceptions")
        return getattr(mod, name)
    except Exception:
        return default


def test_get_short_name_returns_username_when_present():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    dummy = types.SimpleNamespace(username="alice", email="alice@example.com")
    method = getattr(auth_models.User, "get_short_name", None) or getattr(
        auth_models, "get_short_name", None
    )
    assert method is not None

    # Act
    result = method(dummy)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == "alice"


def test__generate_jwt_token_uses_jwt_encode_and_returns_string(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    DummyUser = types.SimpleNamespace(id=42)
    method = getattr(auth_models.User, "_generate_jwt_token", None) or getattr(
        auth_models, "_generate_jwt_token", None
    )
    assert method is not None

    called = {}

    def fake_encode(payload, key, algorithm="HS256"):
        called["payload"] = payload
        return "signed-token-for-{}".format(payload.get("user_id"))

    # Patch jwt.encode inside the authentication models module
    monkeypatch.setattr(auth_models, "jwt", types.SimpleNamespace(encode=fake_encode))

    # Act
    token = method(DummyUser)

    # Assert
    assert isinstance(token, _exc_lookup("str", Exception))
    assert "signed-token-for-42" in token
    assert called["payload"]["user_id"] == 42


def test_render_returns_bytes_and_contains_user_key():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = getattr(auth_renderers, "UserJSONRenderer", None)
    if renderer is None:
        render_func = getattr(auth_renderers, "render", None)
        assert render_func is not None
        # Act
        result = render_func({"user": {"email": "x@y"}}, renderer_context={})
    else:
        r = renderer()
        # Act
        result = r.render({"user": {"email": "x@y"}}, renderer_context={})

    # Assert
    assert isinstance(result, (bytes, bytearray))
    assert b'"user"' in result


@pytest.mark.parametrize(
    "attrs,should_raise",
    [
        ({"email": "a@b.c", "password": "pw", "password2": "pw"}, False),
        ({"email": "a@b.c", "password": "pw", "password2": "different"}, True),
        ({"email": "a@b.c", "password": "", "password2": ""}, True),
    ],
)
def test_validate_registration_serializer_behaviour(attrs, should_raise):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    Serializer = getattr(auth_serializers, "RegistrationSerializer", None)
    assert Serializer is not None
    validate_method = getattr(Serializer, "validate", None)
    assert validate_method is not None

    # Act / Assert
    if should_raise:
        exc_class = _exc_lookup("ValidationError", Exception)
        with pytest.raises(_exc_lookup("exc_class", Exception)):
            # call as unbound method
            validate_method(None, attrs)
    else:
        returned = validate_method(None, attrs)
        assert isinstance(returned, _exc_lookup("dict", Exception))
        assert returned["email"] == "a@b.c"


def test_create_related_profile_creates_profile_when_created_true(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_calls = []

    class FakeProfileObjects:
        @staticmethod
        def create(user):
            created_calls.append(user)
            return "fake-profile"

    FakeProfile = types.SimpleNamespace(objects=FakeProfileObjects())

    monkeypatch.setattr(auth_signals, "Profile", FakeProfile, raising=False)

    dummy_user = types.SimpleNamespace(id=7)

    # Act
    auth_signals.create_related_profile(sender=type(dummy_user), instance=dummy_user, created=True)

    # Assert
    assert created_calls == [dummy_user]


def test_create_related_profile_noop_when_created_false(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_calls = []

    class FakeProfileObjects:
        @staticmethod
        def create(user):
            created_calls.append(user)
            return "fake-profile"

    FakeProfile = types.SimpleNamespace(objects=FakeProfileObjects())
    monkeypatch.setattr(auth_signals, "Profile", FakeProfile, raising=False)
    dummy_user = types.SimpleNamespace(id=8)

    # Act
    auth_signals.create_related_profile(sender=type(dummy_user), instance=dummy_user, created=False)

    # Assert
    assert created_calls == []


@pytest.mark.parametrize(
    "exc_cls,expected_status",
    [
        (_exc_lookup("NotFound", rest_exceptions.NotFound), 404),
        (_exc_lookup("PermissionDenied", rest_exceptions.PermissionDenied), 403),
    ],
)
def test_core_exception_handler_delegates_to_specific_handlers(exc_cls, expected_status):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc_instance = exc_cls(detail="not found")
    context = {}

    # Act
    response = core_exceptions.core_exception_handler(exc_instance, context)

    # Assert
    assert hasattr(response, "status_code")
    assert response.status_code == expected_status


def test_handle_generic_and_not_found_error_return_responses():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    generic = Exception("boom")
    not_found_cls = _exc_lookup("NotFound", rest_exceptions.NotFound)
    not_found = not_found_cls(detail="nope")
    # Act
    generic_response = core_exceptions._handle_generic_error(generic, {})
    not_found_response = core_exceptions._handle_not_found_error(not_found, {})
    # Assert
    assert hasattr(generic_response, "status_code")
    assert generic_response.status_code == 500
    assert hasattr(not_found_response, "status_code")
    assert not_found_response.status_code == 404


@pytest.mark.parametrize("length", [0, 1, 8, 32])
def test_generate_random_string_lengths(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange / Act
    s = core_utils.generate_random_string(length)
    # Assert
    assert isinstance(s, _exc_lookup("str", Exception))
    assert len(s) == length


def test_generate_random_string_negative_raises():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange / Act / Assert
    with pytest.raises(_exc_lookup("Exception", Exception)):
        core_utils.generate_random_string(-1)


def test_follow_unfollow_and_is_following_behaviour():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    follow_func = getattr(profile_models, "follow", None) or getattr(profile_models, "Profile").follow
    unfollow_func = getattr(profile_models, "unfollow", None) or getattr(profile_models, "Profile").unfollow
    is_following_func = getattr(profile_models, "is_following", None) or getattr(profile_models, "Profile").is_following

    assert follow_func is not None
    assert unfollow_func is not None
    assert is_following_func is not None

    class SimpleFollowersManager:
        def __init__(self):
            self._set = set()

        def add(self, user):
            self._set.add(id(user))

        def remove(self, user):
            self._set.discard(id(user))

        def __contains__(self, user):
            return id(user) in self._set

    follower = types.SimpleNamespace(followers=SimpleFollowersManager())
    target = types.SimpleNamespace()

    # Act - follow
    follow_func(follower, target)
    # Assert follow happened
    assert is_following_func(follower, target) is True

    # Act - unfollow
    unfollow_func(follower, target)
    # Assert unfollow happened
    assert is_following_func(follower, target) is False

    # Act - unfollow again (should be idempotent)
    unfollow_func(follower, target)
    # Assert still False
    assert is_following_func(follower, target) is False
