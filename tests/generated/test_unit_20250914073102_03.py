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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    import string
    import types
    from unittest import mock

    from conduit.apps.core import utils as core_utils
    from conduit.apps.core import exceptions as core_exceptions
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import renderers as auth_renderers
    from conduit.apps.authentication import signals as auth_signals
    from conduit.apps.profiles import models as profiles_models
    from rest_framework import exceptions as drf_exceptions
    from rest_framework.response import Response
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required modules for tests are not available", allow_module_level=True)


@pytest.mark.parametrize("length", [0, 1, 8, 32])
def test_generate_random_string_length_and_charset(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    allowed_chars = set(string.ascii_letters + string.digits)
    # Act
    result = core_utils.generate_random_string(length)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    assert set(result).issubset(allowed_chars)


def test__generate_jwt_token_calls_jwt_encode_and_embeds_user_id(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    recorded = {}
    def fake_encode(payload, key, algorithm='HS256'):
        recorded['payload'] = payload
        recorded['key'] = key
        recorded['algorithm'] = algorithm
        return "encoded-jwt-token"
    # Replace jwt.encode used by the module
    monkeypatch.setattr(auth_models, "jwt", types.SimpleNamespace(encode=fake_encode), raising=False)
    class DummyUser:
        id = 12345
        pk = 12345
    user = DummyUser()
    # Act
    token = auth_models._generate_jwt_token(user)
    # Assert
    assert token == "encoded-jwt-token"
    assert 'payload' in recorded
    # payload should contain the user id in some key or nested value; ensure integer present
    payload_values = set()
    def collect_values(obj):
        if isinstance(obj, _exc_lookup("dict", Exception)):
            for v in obj.values():
                collect_values(v)
        elif isinstance(obj, (list, tuple, set)):
            for v in obj:
                collect_values(v)
        else:
            payload_values.add(obj)
    collect_values(recorded['payload'])
    assert any(isinstance(v, _exc_lookup("int", Exception)) and v == user.id for v in payload_values)


def _call_get_short_name_on_user_instance(user_cls, username, email):
    # utility to attempt calling get_short_name as method or function
    try:
        user = user_cls(username=username, email=email)
    except Exception:
        # fallback: simple object with attributes
        user = types.SimpleNamespace(username=username, email=email)
    if hasattr(user, "get_short_name"):
        return user.get_short_name()
    else:
        # try module-level function
        if hasattr(auth_models, "get_short_name"):
            return auth_models.get_short_name(user)
        raise AttributeError("get_short_name not found as method or function")


@pytest.mark.parametrize(
    "username,email,expected_contains",
    [
        ("alice", "alice@example.com", "alice"),
        (None, "bob@example.com", "bob"),
        ("", "charlie@example.com", "charlie"),
    ],
)
def test_get_short_name_various_inputs(username, email, expected_contains):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange / Act
    # attempt to construct User class if available, else use fallback
    UserClass = getattr(auth_models, "User", None) or types.SimpleNamespace
    short_name = _call_get_short_name_on_user_instance(UserClass, username, email)
    # Assert
    assert isinstance(short_name, _exc_lookup("str", Exception))
    assert expected_contains in short_name


def test_render_returns_json_bytes_and_raises_on_unserializable_value():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = auth_renderers if hasattr(auth_renderers, "render") else None
    assert renderer is not None
    data = {"a": 1, "b": "x"}
    # Act
    rendered = auth_renderers.render(data)
    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    import json
    parsed = json.loads(rendered.decode("utf-8"))
    assert parsed == data
    # Unserializable object should raise an error
    class Unserializable:
        pass
    with pytest.raises(_exc_lookup("TypeError", Exception)):
        auth_renderers.render({"bad": Unserializable()})


@pytest.mark.parametrize(
    "exc, expected_status",
    [
        (drf_exceptions.NotFound(detail="nope"), 404),
        (drf_exceptions.ValidationError(detail={"field": ["err"]}), 400),
        (Exception("boom"), 500),
    ],
)
def test_core_exception_handler_and_helpers_return_expected_response_status(exc, expected_status):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    context = {"request": None}
    # Act
    response = core_exceptions.core_exception_handler(exc, context)
    # Assert response type and status if returned
    assert isinstance(response, (Response, type(None)))
    if response is not None:
        assert hasattr(response, "status_code")
        assert response.status_code == expected_status
    # Test internal helpers directly for NotFound and generic
    if isinstance(exc, _exc_lookup("drf_exceptions.NotFound", Exception)):
        resp = core_exceptions._handle_not_found_error(exc)
        assert isinstance(resp, _exc_lookup("Response", Exception))
        assert resp.status_code == 404
    elif isinstance(exc, _exc_lookup("Exception", Exception)) and not isinstance(exc, _exc_lookup("drf_exceptions.APIException", Exception)):
        resp = core_exceptions._handle_generic_error(exc)
        assert isinstance(resp, _exc_lookup("Response", Exception))
        assert resp.status_code == 500


def test_create_related_profile_calls_profile_get_or_create(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    called = {}
    def fake_get_or_create(**kwargs):
        called['kwargs'] = kwargs
        class FakeProfile: pass
        return (FakeProfile(), True)
    # Monkeypatch the Profile manager used inside signals
    profiles_mod = profiles_models
    fake_profile_class = types.SimpleNamespace(objects=types.SimpleNamespace(get_or_create=fake_get_or_create))
    monkeypatch.setattr(profiles_mod, "Profile", fake_profile_class, raising=False)
    # Create a minimal user instance
    user = types.SimpleNamespace(id=101, username="u101")
    # Act: when created True it should call get_or_create
    auth_signals.create_related_profile(sender=None, instance=user, created=True)
    # Assert
    assert 'kwargs' in called
    assert called['kwargs'].get('user') == user
    # Reset and ensure when created False it does NOT call get_or_create
    called.clear()
    auth_signals.create_related_profile(sender=None, instance=user, created=False)
    assert called == {}


def test_follow_unfollow_and_is_following_with_stub_manager():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    follow_fn = getattr(profiles_models, "follow", None)
    unfollow_fn = getattr(profiles_models, "unfollow", None)
    is_following_fn = getattr(profiles_models, "is_following", None)
    # If implementations are methods on Profile class, try to fetch those
    ProfileClass = getattr(profiles_models, "Profile", None)
    if follow_fn is None and ProfileClass is not None:
        follow_fn = getattr(ProfileClass, "follow", None)
        unfollow_fn = getattr(ProfileClass, "unfollow", None)
        is_following_fn = getattr(ProfileClass, "is_following", None)
    assert follow_fn is not None and unfollow_fn is not None and is_following_fn is not None
    # Create stub manager that mimics add/remove/__contains__
    class StubManager:
        def __init__(self):
            self._set = set()
        def add(self, obj):
            self._set.add(obj)
        def remove(self, obj):
            self._set.discard(obj)
        def __contains__(self, obj):
            return obj in self._set
    class StubProfile:
        def __init__(self, name):
            self.name = name
            self.following = StubManager()
        def __repr__(self):
            return f"StubProfile({self.name})"
    alice = StubProfile("alice")
    bob = StubProfile("bob")
    # Act: call follow
    # follow_fn may be unbound (expects self, other) or bound; try both ways
    try:
        follow_fn(alice, bob)
    except TypeError:
        # maybe it's a bound method on class; call via instance
        getattr(alice, "follow")(bob)
    # Assert following state
    try:
        assert is_following_fn(alice, bob)
    except TypeError:
        assert getattr(alice, "is_following")(bob)
    # Act: unfollow
    try:
        unfollow_fn(alice, bob)
    except TypeError:
        getattr(alice, "unfollow")(bob)
    # Assert no longer following
    try:
        assert not is_following_fn(alice, bob)
    except TypeError:
        assert not getattr(alice, "is_following")(bob)
