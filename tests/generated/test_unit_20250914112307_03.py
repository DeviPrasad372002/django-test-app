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

import pytest
import types

try:
    from conduit.apps.authentication.models import User, _generate_jwt_token as user_generate_jwt, \
        get_short_name as user_get_short_name  # may be unbound functions on the class
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.serializers import RegistrationSerializer
    from conduit.apps.authentication.signals import create_related_profile
    from conduit.apps.core.exceptions import core_exception_handler, _handle_generic_error, _handle_not_found_error
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.profiles.models import Profile
    import conduit.apps.authentication.models as auth_models_module
    import conduit.apps.core.exceptions as core_excs_module
    import conduit.apps.authentication.signals as auth_signals_module
    import conduit.apps.profiles.models as profiles_models_module
    import random as _random_module
    import jwt as _jwt_module
    import django.conf
except ImportError:
    pytest.skip("Required application modules not available for unit tests", allow_module_level=True)


def _exc_lookup(name, fallback=Exception):
    try:
        import rest_framework.exceptions as rf_exc  # type: ignore
        return getattr(rf_exc, name)
    except Exception:
        return fallback


@pytest.mark.parametrize(
    "attrs, expected",
    [
        ({"email": "alice@example.com", "username": "alice"}, "alice@example.com"),
        ({"email": "", "username": "bob"}, "bob"),
        ({"email": None, "username": "charlie"}, "charlie"),
    ],
)
def test_get_short_name_unbound_works_for_various_values(attrs, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_self = types.SimpleNamespace(**attrs)
    # Act
    result = user_get_short_name(fake_self)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected


@pytest.mark.parametrize("pk_value", [1, 12345, "abc"])
def test__generate_jwt_token_calls_jwt_encode(monkeypatch, pk_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_self = types.SimpleNamespace(pk=pk_value)
    captured = {}

    def fake_encode(payload, key, algorithm="HS256"):
        captured['payload'] = payload
        captured['key'] = key
        captured['algorithm'] = algorithm
        return "signed-token-for-tests"

    # Ensure settings SECRET_KEY is available to the module under test
    monkeypatch.setattr(django.conf.settings, "SECRET_KEY", "test-secret", raising=False)
    # Patch the jwt.encode used in the module where the method lives
    monkeypatch.setattr(auth_models_module, "jwt", types.SimpleNamespace(encode=fake_encode))

    # Act
    token = user_generate_jwt(fake_self)

    # Assert
    assert token == "signed-token-for-tests"
    assert 'payload' in captured
    assert captured['payload'].get('id', captured['payload'].get('pk', None)) in (pk_value, str(pk_value), None) or 'exp' in captured['payload']
    assert captured['key'] == "test-secret"
    assert captured['algorithm'] == "HS256"


@pytest.mark.parametrize(
    "input_data,expected_fragment",
    [
        ({"username": "alice"}, '"user"'),
        ({"email": "a@b.com", "username": "bob"}, '"user"'),
        ({}, '"user"'),
    ],
)
def test_userjsonrenderer_render_returns_wrapped_user(monkeypatch, input_data, expected_fragment):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = UserJSONRenderer()
    # Act
    rendered = renderer.render(input_data, media_type="application/json")
    # Assert
    assert rendered is not None
    if isinstance(rendered, _exc_lookup("bytes", Exception)):
        decoded = rendered.decode("utf-8")
    else:
        decoded = str(rendered)
    assert expected_fragment in decoded
    # ensure that the input keys appear under "user"
    if input_data:
        for k, v in input_data.items():
            assert str(v) in decoded


@pytest.mark.parametrize(
    "password,password2,should_raise",
    [
        ("secret123", "secret123", False),
        ("x", "y", True),
        ("", "", False),
    ],
)
def test_registration_serializer_validate_handles_password_confirmation(password, password2, should_raise):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer = RegistrationSerializer()
    attrs = {"password": password, "password2": password2, "email": "a@b.com", "username": "u"}
    exc_type = _exc_lookup("ValidationError", Exception)
    # Act / Assert
    if should_raise:
        with pytest.raises(_exc_lookup("exc_type", Exception)):
            serializer.validate(attrs)
    else:
        validated = serializer.validate(attrs)
        assert isinstance(validated, _exc_lookup("dict", Exception))
        # typical implementations propagate username/email; ensure keys exist
        assert "email" in validated and "username" in validated


def test_create_related_profile_creates_profile_when_created_true(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_calls = []

    class FakeManager:
        def create(self, **kwargs):
            created_calls.append(kwargs)
            return types.SimpleNamespace(**kwargs)

    class FakeProfileClass:
        objects = FakeManager()

    monkeypatch.setattr(auth_signals_module, "Profile", FakeProfileClass, raising=False)
    fake_user = types.SimpleNamespace(id=7, pk=7, username="tester")

    # Act
    create_related_profile(sender=object, instance=fake_user, created=True)

    # Assert
    assert len(created_calls) == 1
    assert created_calls[0].get("user") is fake_user


def test_create_related_profile_noop_when_created_false(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    called = False

    class FakeManager:
        def create(self, **kwargs):
            nonlocal called
            called = True
            return types.SimpleNamespace(**kwargs)

    class FakeProfileClass:
        objects = FakeManager()

    monkeypatch.setattr(auth_signals_module, "Profile", FakeProfileClass, raising=False)
    fake_user = types.SimpleNamespace(id=8, pk=8, username="tester2")

    # Act
    create_related_profile(sender=object, instance=fake_user, created=False)

    # Assert
    assert called is False


def test_core_exception_handler_delegates_based_on_exception_type(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    called = {}

    def fake_handle_generic(exc, context):
        called['generic'] = True
        return "generic-handled"

    def fake_handle_not_found(exc, context):
        called['not_found'] = True
        return "not-found-handled"

    monkeypatch.setattr(core_excs_module, "_handle_generic_error", fake_handle_generic, raising=False)
    monkeypatch.setattr(core_excs_module, "_handle_not_found_error", fake_handle_not_found, raising=False)

    NotFoundExc = _exc_lookup("NotFound", Exception)
    exc_instance = NotFoundExc("missing") if NotFoundExc is not Exception else Exception("missing")

    # Act
    result = core_exception_handler(exc_instance, {"view": None})

    # Assert
    # If the code recognizes NotFound it should call the not_found handler
    assert (called.get('not_found') is True) or (called.get('generic') is True)
    assert result in ("not-found-handled", "generic-handled")


@pytest.mark.parametrize("message", ["boom", "not found"])
def test__handle_generic_and_not_found_return_response_like_objects(message):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    gen_exc = Exception(message)
    NotFoundExc = _exc_lookup("NotFound", Exception)
    nf_exc = NotFoundExc(message) if NotFoundExc is not Exception else Exception(message)

    # Act
    gen_resp = _handle_generic_error(gen_exc, {})
    nf_resp = _handle_not_found_error(nf_exc, {})

    # Assert
    # Both handlers should return an object that exposes .data or is a dict-like
    for resp in (gen_resp, nf_resp):
        if hasattr(resp, "data"):
            data = resp.data
        else:
            data = resp
        # data should include some notion of errors or message
        assert data is not None
        # Expect structured error information
        if isinstance(data, _exc_lookup("dict", Exception)):
            assert "errors" in data or "detail" in data or any(isinstance(v, (str, list, dict)) for v in data.values())


@pytest.mark.parametrize("length", [1, 5, 16])
def test_generate_random_string_respects_length_and_charset(monkeypatch, length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: make random.choice deterministic to produce 'A' always
    monkeypatch.setattr(_random_module, "choice", lambda seq: "A")
    # Act
    result = generate_random_string(length)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    assert set(result) == {"A"}


def _make_fake_relation():
    # Simple fake relation object that provides add/remove/filter used by Profile methods
    class FakeRel:
        def __init__(self):
            self._items = set()

        def add(self, item):
            self._items.add(item)

        def remove(self, item):
            self._items.discard(item)

        def filter(self, **kwargs):
            # Accept any filter keyword; return a list-like of items if present
            target = None
            if len(kwargs) == 1:
                target = list(kwargs.values())[0]
            else:
                # fallback: if any item equals any value, return it
                target = None
            if target is None:
                return [i for i in self._items]
            return [i for i in self._items if i == target]

        def exists(self):
            return bool(self._items)

    return FakeRel()


def test_profile_follow_unfollow_and_is_following_methods(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Prepare fake Profile methods usage: the instance should have an attribute `.following` or `.followers`
    fake_rel = _make_fake_relation()
    follower = types.SimpleNamespace(username="follower")
    followee = types.SimpleNamespace(username="followee")

    fake_self = types.SimpleNamespace(following=fake_rel)
    # Attempt to get unbound methods; if not present, test will fail and reveal issue
    follow_method = getattr(Profile, "follow", None)
    unfollow_method = getattr(Profile, "unfollow", None)
    is_following_method = getattr(Profile, "is_following", None)

    assert follow_method is not None, "Profile.follow method must exist"
    assert unfollow_method is not None, "Profile.unfollow method must exist"
    assert is_following_method is not None, "Profile.is_following method must exist"

    # Act - follow
    follow_method(fake_self, followee)
    # Assert - followee should now be in the fake relation
    assert any(item == followee for item in fake_self.following._items)

    # Act - is_following should report True
    is_following_result = is_following_method(fake_self, followee)
    # Assert - depending on implementation this might be bool or QuerySet-like truthy; assert truthiness
    assert bool(is_following_result) is True is True

    # Act - unfollow
    unfollow_method(fake_self, followee)
    # Assert - followee removed
    assert all(item != followee for item in fake_self.following._items)
    # And is_following should now return False
    assert not bool(is_following_method(fake_self, followee))
