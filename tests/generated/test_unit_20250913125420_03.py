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
_ALL_MODULES = ['__future__', 'conduit.apps.articles.signals', 'conduit.apps.authentication.signals', 'conduit.apps.core.models', 'conduit.apps.core.renderers', 'conduit.apps.core.utils', 'conduit.apps.profiles.models', 'conduit.apps.profiles.serializers', 'datetime', 'django.apps', 'django.conf', 'django.conf.urls', 'django.contrib', 'django.contrib.auth', 'django.contrib.auth.models', 'django.core.wsgi', 'django.db', 'django.db.models.deletion', 'django.db.models.signals', 'django.dispatch', 'django.utils.text', 'json', 'jwt', 'models', 'os', 'random', 'relations', 'renderers', 'rest_framework', 'rest_framework.exceptions', 'rest_framework.generics', 'rest_framework.permissions', 'rest_framework.renderers', 'rest_framework.response', 'rest_framework.routers', 'rest_framework.views', 'serializers', 'string', 'views']
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
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
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
# Disable the adapter around Django to avoid metaclass/__classcell__ issues.
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
# Minimal Django setup with detected apps
try:
    if _DJ_PRESENT:
        import django
        from django.conf import settings as _dj_settings
        if not _dj_settings.configured:
            _dj_apps = set()
            for m in list(_ALL_MODULES):
                if m.startswith("conduit.apps."):
                    parts = m.split(".")
                    if len(parts) >= 3:
                        _dj_apps.add(".".join(parts[:3]))  # conduit.apps.<app>
            _installed = ["django.contrib.auth","django.contrib.contenttypes"]
            if "rest_framework" in _ALL_MODULES:
                _installed.append("rest_framework")
            _installed += sorted(_dj_apps)
            _cfg = dict(
                SECRET_KEY="test-key",
                DEBUG=True,
                ALLOWED_HOSTS=["*"],
                INSTALLED_APPS=_installed,
                DATABASES={"default": {"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}},
                MIDDLEWARE=[],
                USE_TZ=True,
                TIME_ZONE="UTC",
                DEFAULT_AUTO_FIELD="django.db.models.AutoField",
            )
            # If a custom auth app exists, set AUTH_USER_MODEL
            if any(a.endswith(".authentication") for a in _installed):
                _cfg["AUTH_USER_MODEL"] = "authentication.User"
            _dj_settings.configure(**_cfg)
            django.setup()
except Exception as _dj_e:
    pass
_PY2_ALIASES = {'ConfigParser': 'configparser', 'Queue': 'queue', 'StringIO': 'io', 'cStringIO': 'io', 'urllib2': 'urllib.request'}
for _old, _new in list(_PY2_ALIASES.items()):
    if _old in sys.modules: continue
    try:
        __import__(_new); sys.modules[_old] = sys.modules[_new]
    except Exception: pass
def _safe_find_spec(name):
    try: return _iu.find_spec(name)
    except Exception: return None
def _ensure_pkg(name, is_pkg=None):
    if name in sys.modules:
        m = sys.modules[name]
        if getattr(m, "__spec__", None) is None:
            m.__spec__ = _im.ModuleSpec(name, loader=None, is_package=(is_pkg if is_pkg is not None else ("." not in name)))
            if "." not in name and not hasattr(m, "__path__"): m.__path__ = []
        return m
    m = _types.ModuleType(name)
    if is_pkg is None: is_pkg = ("." not in name)
    if is_pkg and not hasattr(m, "__path__"): m.__path__ = []
    m.__spec__ = _im.ModuleSpec(name, loader=None, is_package=is_pkg)
    sys.modules[name] = m
    return m
_THIRD_PARTY_TOPS = ['__future__', 'conduit', 'datetime', 'django', 'json', 'jwt', 'models', 'os', 'random', 'relations', 'renderers', 'rest_framework', 'serializers', 'string', 'views']

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

try:
    import builtins
    import json
    import types

    import pytest

    from rest_framework import status
    from rest_framework.response import Response
    from rest_framework.exceptions import NotFound

    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.core.exceptions import (
        core_exception_handler,
        _handle_generic_error,
        _handle_not_found_error,
    )
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication import signals as auth_signals

except ImportError as e:
    import pytest

    pytest.skip("Required modules for tests are not available: {}".format(e), allow_module_level=True)


def _exc_lookup(name, default=Exception):
    return getattr(builtins, name, default)


@pytest.mark.parametrize(
    "length",
    [
        0,
        1,
        8,
        64,
    ],
)
def test_generate_random_string_length_and_charset(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

    # Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    assert set(result).issubset(allowed_chars)


def test_handle_generic_error_response_structure_and_status():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc = Exception("internal failure")
    context = {}

    # Act
    response = _handle_generic_error(exc, context)

    # Assert
    assert isinstance(response, _exc_lookup("Response", Exception))
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert isinstance(response.data, dict)
    assert "errors" in response.data
    errors_value = response.data["errors"]
    assert isinstance(errors_value, _exc_lookup("dict", Exception))
    # expecting a 'detail' key with the stringified exception
    assert "detail" in errors_value
    assert errors_value["detail"] == "internal failure"


def test_handle_not_found_error_response_status_and_message():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc = Exception("ignored message")
    context = {}

    # Act
    response = _handle_not_found_error(exc, context)

    # Assert
    assert isinstance(response, _exc_lookup("Response", Exception))
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert isinstance(response.data, dict)
    # commonly implementations return {'errors': {'detail': 'Not found.'}}
    errors = response.data.get("errors") or {}
    assert isinstance(errors, _exc_lookup("dict", Exception))
    assert "detail" in errors
    # concrete message expected
    assert errors["detail"] == "Not found."


def test_core_exception_handler_delegates_to_generic_for_unknown_exceptions():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc = Exception("boom")
    context = {}

    # Act
    response = core_exception_handler(exc, context)

    # Assert
    assert isinstance(response, _exc_lookup("Response", Exception))
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data["errors"]["detail"] == "boom"


def test_core_exception_handler_returns_restframework_response_for_known_exceptions():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc = NotFound("not here")
    context = {}

    # Act
    response = core_exception_handler(exc, context)

    # Assert
    assert isinstance(response, _exc_lookup("Response", Exception))
    assert response.status_code == status.HTTP_404_NOT_FOUND
    # DRF's exception_handler usually returns {'detail': '...'} for NotFound
    assert response.data.get("detail") == "not here"


@pytest.mark.parametrize(
    "input_data, expected_structure",
    [
        ({"email": "a@x.com", "username": "ax"}, {"user": {"email": "a@x.com", "username": "ax"}}),
        ({"token": "t"}, {"user": {"token": "t"}}),
        (None, b""),
    ],
)
def test_user_json_renderer_render_returns_expected_json_or_empty(input_data, expected_structure):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = UserJSONRenderer()

    # Act
    rendered = renderer.render(input_data, accepted_media_type=None, renderer_context={})

    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    if input_data is None:
        assert rendered == b""
    else:
        parsed = json.loads(rendered.decode("utf-8"))
        assert parsed == expected_structure


def test_user_generate_jwt_token_uses_jwt_encode_and_settings(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_user = types.SimpleNamespace(id=42)
    captured = {}

    def fake_encode(payload, key, algorithm="HS256"):
        captured["payload"] = payload
        captured["key"] = key
        captured["alg"] = algorithm
        return "signed-token"

    # Ensure module-level references are patched
    monkeypatch.setattr(auth_models, "jwt", types.SimpleNamespace(encode=fake_encode), raising=False)
    # Ensure settings has SECRET_KEY attribute the method references
    if hasattr(auth_models, "settings"):
        monkeypatch.setattr(auth_models.settings, "SECRET_KEY", "secret-key", raising=False)
    else:
        # If settings isn't present for some reason, attach a dummy one
        monkeypatch.setattr(auth_models, "settings", types.SimpleNamespace(SECRET_KEY="secret-key"), raising=False)

    # Act
    token = auth_models.User._generate_jwt_token(fake_user)

    # Assert
    assert token == "signed-token"
    assert isinstance(captured.get("payload"), dict)
    assert captured["payload"].get("id") == 42
    assert captured["key"] == "secret-key"
    assert captured["alg"] == "HS256"


def test_user_get_short_name_returns_email_when_present():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_user = types.SimpleNamespace(email="short@example.com", username="user123", first_name="First", last_name="Last")

    # Act
    result = auth_models.User.get_short_name(fake_user)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    # implementation expected to prefer email as short name in this project
    assert result == "short@example.com"


def test_create_related_profile_calls_profile_get_or_create_when_created(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_calls = []

    class FakeManager:
        def get_or_create(self, **kwargs):
            created_calls.append(kwargs)
            return (types.SimpleNamespace(**kwargs), True)

    class FakeProfile:
        objects = FakeManager()

    # Patch the Profile reference used inside the signals module
    monkeypatch.setattr(auth_signals, "Profile", FakeProfile, raising=False)
    fake_user = types.SimpleNamespace(id=7)

    # Act
    auth_signals.create_related_profile(sender=None, instance=fake_user, created=True)

    # Assert
    assert len(created_calls) == 1
    assert created_calls[0].get("user") is fake_user

    # Act: when created is False it should not call manager
    created_calls.clear()
    auth_signals.create_related_profile(sender=None, instance=fake_user, created=False)
    assert created_calls == []
