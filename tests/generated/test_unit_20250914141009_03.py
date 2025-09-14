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
    import json
    import string
    import types
    import time

    import pytest

    from rest_framework import exceptions as drf_exceptions
    from rest_framework.response import Response

    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.serializers import RegistrationSerializer
    from conduit.apps.authentication import signals as auth_signals
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.core import exceptions as core_exceptions
    from conduit.apps.profiles import models as profiles_models
except ImportError:
    import pytest
    pytest.skip("Required project modules not available", allow_module_level=True)


def _exc_lookup(name, default):
    try:
        module = __import__("rest_framework.exceptions", fromlist=[name])
        return getattr(module, name)
    except Exception:
        return default


@pytest.mark.parametrize(
    "username_value, expected",
    [
        ("alice", "alice"),
        ("", ""),
        ("user.name", "user.name"),
    ],
)
def test_get_short_name_returns_expected_value(username_value, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    dummy_self = types.SimpleNamespace(username=username_value)
    func = auth_models.User.get_short_name

    # Act
    result = func(dummy_self)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected


def test__generate_jwt_token_calls_jwt_encode_and_includes_userid_and_exp(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    captured = {}

    class FakeJWT:
        def encode(self, payload, secret, algorithm="HS256"):
            captured["payload"] = payload
            captured["secret"] = secret
            captured["algorithm"] = algorithm
            return "fake.token.string"

    fake_jwt = FakeJWT()
    monkeypatch.setattr(auth_models, "jwt", fake_jwt)

    dummy_user = types.SimpleNamespace(id=123)

    # Act
    token = auth_models.User._generate_jwt_token(dummy_user)

    # Assert
    assert isinstance(token, _exc_lookup("str", Exception))
    assert token == "fake.token.string"
    assert "payload" in captured
    assert "id" in captured["payload"]
    assert captured["payload"]["id"] == 123
    assert "exp" in captured["payload"]
    assert isinstance(captured["payload"]["exp"], int)
    assert captured["algorithm"] == "HS256"


@pytest.mark.parametrize(
    "input_data",
    [
        ({"email": "a@b.com", "username": "u", "token": "t"}),
        ({"email": "x@y.com", "username": "user2", "bio": "bio text"}),
    ],
)
def test_userjsonrenderer_render_wraps_user_key(input_data):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = UserJSONRenderer()
    # Act
    rendered = renderer.render(input_data, media_type=None, renderer_context=None)
    # Assert
    assert isinstance(rendered, (bytes, str))
    loaded = json.loads(rendered.decode() if isinstance(rendered, _exc_lookup("bytes", Exception)) else rendered)
    assert "user" in loaded
    assert loaded["user"] == input_data


@pytest.mark.parametrize(
    "attrs, should_raise",
    [
        ({"email": "test@example.com", "username": "tester", "password": "securepass"}, False),
        ({"email": "test@example.com", "username": "tester"}, True),  # missing password
        ({}, True),
    ],
)
def test_registration_serializer_validate_behaviour(attrs, should_raise):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer = RegistrationSerializer()

    # Act / Assert
    if should_raise:
        with pytest.raises(_exc_lookup("ValidationError", Exception)):
            serializer.validate(attrs)
    else:
        validated = serializer.validate(attrs)
        assert isinstance(validated, _exc_lookup("dict", Exception))
        # Concrete expectations for provided fields
        for key in attrs:
            assert key in validated


def test_create_related_profile_calls_get_or_create_only_when_created(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calls = {"count": 0, "args": None, "kwargs": None}

    class FakeManager:
        def get_or_create(self, *args, **kwargs):
            calls["count"] += 1
            calls["args"] = args
            calls["kwargs"] = kwargs
            return ("profile", True)

    class FakeProfileModel:
        objects = FakeManager()

    monkeypatch.setattr(auth_signals, "Profile", FakeProfileModel)

    fake_user_instance = types.SimpleNamespace(pk=7, id=7)

    # Act - created=True should call get_or_create
    auth_signals.create_related_profile(sender=None, instance=fake_user_instance, created=True)

    # Assert
    assert calls["count"] == 1
    assert calls["kwargs"]  # called with kwargs

    # Act - created=False should not call additionally
    auth_signals.create_related_profile(sender=None, instance=fake_user_instance, created=False)

    # Assert unchanged count
    assert calls["count"] == 1


@pytest.mark.parametrize(
    "exc_instance, expected_status_range",
    [
        (Exception("generic error"), (400, 599)),
    ],
)
def test_core_exception_handler_returns_response_for_generic_errors(exc_instance, expected_status_range):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Act
    response = core_exceptions.core_exception_handler(exc_instance, context={})
    # Assert
    assert isinstance(response, _exc_lookup("Response", Exception))
    assert isinstance(response.status_code, int)
    assert expected_status_range[0] <= response.status_code <= expected_status_range[1]


def test_handle_specific_handlers_return_responses():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    generic = Exception("ouch")
    not_found = Exception("not found")

    # Act
    resp_generic = core_exceptions._handle_generic_error(generic)
    resp_not_found = core_exceptions._handle_not_found_error(not_found)

    # Assert
    assert isinstance(resp_generic, _exc_lookup("Response", Exception))
    assert isinstance(resp_not_found, _exc_lookup("Response", Exception))
    assert isinstance(resp_generic.status_code, int)
    assert isinstance(resp_not_found.status_code, int)
    assert resp_generic.status_code >= 400
    assert resp_not_found.status_code >= 400


@pytest.mark.parametrize("length", [0, 1, 5, 32, 100])
def test_generate_random_string_length_and_charset(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange / Act
    out = generate_random_string(length)
    # Assert
    assert isinstance(out, _exc_lookup("str", Exception))
    assert len(out) == length
    allowed = set(string.ascii_letters + string.digits)
    assert set(out).issubset(allowed)


def test_follow_unfollow_and_is_following_manage_fake_manager_state():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Create fake related manager that mimics add/remove/filter(...).exists()
    class FakeQuerySet:
        def __init__(self, backing_set, user):
            self.backing_set = backing_set
            self.user = user

        def exists(self):
            return self.user in self.backing_set

    class FakeManager:
        def __init__(self):
            self._backing = set()

        def add(self, user):
            self._backing.add(user)

        def remove(self, user):
            self._backing.discard(user)

        def filter(self, **kwargs):
            user = kwargs.get("user")
            return FakeQuerySet(self._backing, user)

    fake_manager_a = FakeManager()
    fake_manager_b = FakeManager()

    fake_profile_a = types.SimpleNamespace(user="alice_user", following=fake_manager_a)
    fake_profile_b = types.SimpleNamespace(user="bob_user", following=fake_manager_b)

    # Act - follow
    profiles_models.Profile.follow(fake_profile_a, fake_profile_b)

    # Assert follow added bob to alice's following
    assert "bob_user" in fake_manager_a._backing

    # Act - is_following should reflect current state
    res_after_follow = profiles_models.Profile.is_following(fake_profile_a, fake_profile_b)

    # Assert
    assert isinstance(res_after_follow, _exc_lookup("bool", Exception))
    assert res_after_follow is True

    # Act - unfollow
    profiles_models.Profile.unfollow(fake_profile_a, fake_profile_b)

    # Assert unfollow removed bob
    assert "bob_user" not in fake_manager_a._backing

    # Act - is_following after unfollow
    res_after_unfollow = profiles_models.Profile.is_following(fake_profile_a, fake_profile_b)
    assert res_after_unfollow is False
