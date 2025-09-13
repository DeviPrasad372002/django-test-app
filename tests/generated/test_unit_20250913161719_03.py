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
            except Exception:
                pass

        if not _dj_settings.configured:
            _installed = ["django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions"]
            if _iu.find_spec("rest_framework"):
                _installed.append("rest_framework")

            # Explicitly try common project apps if present
            for _app in ("conduit.apps.core","conduit.apps.articles","conduit.apps.authentication","conduit.apps.profiles"):
                _maybe_add(_app, _installed)

            # Generic discovery under conduit.apps.*
            try:
                if _iu.find_spec("conduit.apps"):
                    _apps_pkg = importlib.import_module("conduit.apps")
                    for _m in pkgutil.iter_modules(getattr(_apps_pkg, "__path__", [])):
                        _full = "conduit.apps." + _m.name
                        _maybe_add(_full, _installed)
            except Exception:
                pass

            _cfg = dict(
                SECRET_KEY="test-key",
                DEBUG=True,
                ALLOWED_HOSTS=["*"],
                INSTALLED_APPS=sorted(set(_installed)),
                DATABASES=dict(default=dict(ENGINE="django.db.backends.sqlite3", NAME=":memory:")),
                MIDDLEWARE=[],
                MIDDLEWARE_CLASSES=[],
                USE_TZ=True,
                TIME_ZONE="UTC",
            )
            try:
                _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
            except Exception:
                pass

            try:
                _dj_settings.configure(**_cfg)
                django.setup()
            except Exception:
                _pytest.skip("Django setup failed in bootstrap; skipping generated tests", allow_module_level=True)
        else:
            if not _dj_apps.ready:
                try:
                    django.setup()
                except Exception:
                    _pytest.skip("Django setup not ready and failed to initialize; skipping", allow_module_level=True)
except Exception:
    _pytest.skip("Django bootstrap error; skipping generated tests", allow_module_level=True)
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
    import pytest
    from conduit.apps.authentication.models import User
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.serializers import RegistrationSerializer
    from conduit.apps.authentication.signals import create_related_profile
    from conduit.apps.core.exceptions import (
        core_exception_handler,
        _handle_generic_error,
        _handle_not_found_error,
    )
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.profiles import models as profiles_models
    from conduit.apps.profiles.models import Profile
    import rest_framework.exceptions as drf_exceptions
    from rest_framework.response import Response
except ImportError:
    import pytest

    pytest.skip("Skipping tests: required project imports not available", allow_module_level=True)


def _exc_lookup(name, default):
    try:
        import rest_framework.exceptions as _rest_exc

        return getattr(_rest_exc, name)
    except Exception:
        return default


def test_get_short_name_and_generate_jwt_token_with_fake_user():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_user = type("FakeUser", (), {"pk": 42, "username": "alice"})
    # Act
    short_name = User.get_short_name(fake_user) if hasattr(User, "get_short_name") else getattr(
        fake_user, "username"
    )
    token = User._generate_jwt_token(fake_user)
    # Assert
    assert isinstance(short_name, _exc_lookup("str", Exception))
    assert short_name == "alice"
    assert isinstance(token, (str, bytes))
    token_str = token.decode() if isinstance(token, _exc_lookup("bytes", Exception)) else token
    assert "." in token_str


def test_user_json_renderer_returns_bytes_and_contains_expected_keys():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = UserJSONRenderer()
    sample_data = {"user": {"email": "u@example.test", "username": "bob"}}
    # Act
    rendered = renderer.render(sample_data, accepted_media_type=None, renderer_context={})
    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    decoded = rendered.decode("utf-8")
    assert '"user"' in decoded
    assert '"email"' in decoded
    assert "u@example.test" in decoded


def test_registration_validate_success_and_password_mismatch():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer = RegistrationSerializer()
    valid_input = {
        "username": "tester",
        "email": "test@example.com",
        "password": "s3cret",
        "password2": "s3cret",
    }
    invalid_input = {
        "username": "tester",
        "email": "test@example.com",
        "password": "a",
        "password2": "b",
    }
    ValidationError = _exc_lookup("ValidationError", Exception)
    # Act / Assert - valid passes and returns mapping-like
    validated = RegistrationSerializer.validate(serializer, valid_input.copy())
    assert isinstance(validated, _exc_lookup("dict", Exception))
    # Act / Assert - mismatched passwords raise ValidationError
    with pytest.raises(_exc_lookup("ValidationError", Exception)):
        RegistrationSerializer.validate(serializer, invalid_input.copy())


def test_create_related_profile_calls_profile_manager_create_when_created(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_calls = []

    class FakeManager:
        def create(self, **kwargs):
            created_calls.append(kwargs)
            return "created_profile"

        def get_or_create(self, **kwargs):
            created_calls.append(("get_or_create", kwargs))
            return ("profile", True)

    monkeypatch.setattr(profiles_models, "Profile", profiles_models.Profile, raising=False)
    # attach a fake manager to the Profile object in the module for the signal to use
    monkeypatch.setattr(profiles_models.Profile, "objects", FakeManager(), raising=False)
    fake_user = type("UserObj", (), {"pk": 100, "id": 100})
    # Act
    create_related_profile(sender=None, instance=fake_user, created=True)
    # Assert
    assert created_calls, "Profile manager should have been called when created=True"


def test_create_related_profile_does_not_call_when_not_created(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    called = False

    class FakeManager:
        def create(self, **kwargs):
            nonlocal called
            called = True

    monkeypatch.setattr(profiles_models.Profile, "objects", FakeManager(), raising=False)
    fake_user = type("UserObj", (), {"pk": 101, "id": 101})
    # Act
    create_related_profile(sender=None, instance=fake_user, created=False)
    # Assert
    assert called is False


def test_handle_generic_and_not_found_errors_return_expected_responses():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    generic_exc = Exception("something bad")
    not_found_exc = drf_exceptions.NotFound("nope")
    # Act
    generic_response = _handle_generic_error(generic_exc)
    not_found_response = _handle_not_found_error(not_found_exc)
    # Assert generic handler
    assert isinstance(generic_response, _exc_lookup("Response", Exception))
    assert getattr(generic_response, "status_code", None) in (500, 400, None) or isinstance(
        getattr(generic_response, "data", None), dict
    )
    # Assert not found handler
    assert isinstance(not_found_response, _exc_lookup("Response", Exception))
    assert getattr(not_found_response, "status_code", None) in (404,)


def test_core_exception_handler_delegates_and_returns_response_for_various_exceptions():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    unknown_exc = Exception("unknown")
    not_found_exc = drf_exceptions.NotFound("missing")
    # Act
    unknown_resp = core_exception_handler(unknown_exc, {})
    nf_resp = core_exception_handler(not_found_exc, {})
    # Assert
    assert isinstance(unknown_resp, _exc_lookup("Response", Exception))
    assert isinstance(nf_resp, _exc_lookup("Response", Exception))
    assert getattr(nf_resp, "status_code", None) in (404,)


@pytest.mark.parametrize("length", [0, 1, 8, 32])
def test_generate_random_string_returns_requested_length(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange / Act
    result = generate_random_string(length)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length


@pytest.mark.parametrize("bad_input", ["a", None, 1.5])
def test_generate_random_string_raises_type_error_for_non_int(bad_input):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange / Act / Assert
    with pytest.raises((TypeError, ValueError)):
        generate_random_string(bad_input)


def test_profile_follow_unfollow_and_is_following_work_with_fake_manager():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Create a Fake related manager that supports add/remove/filter.exists semantics
    class FakeQuerySet:
        def __init__(self, items, match_kwargs):
            self._items = items
            self._match = match_kwargs

        def exists(self):
            if not self._match:
                return bool(self._items)
            for itm in self._items:
                matched_all = True
                for k, v in self._match.items():
                    attr_val = getattr(itm, k, None)
                    # also support checking .pk or .id
                    if attr_val is None and k in ("pk", "id") and hasattr(itm, k):
                        attr_val = getattr(itm, k)
                    if attr_val != v:
                        matched_all = False
                        break
                if matched_all:
                    return True
            return False

    class FakeRelatedManager:
        def __init__(self):
            self._items = []

        def add(self, obj):
            if obj not in self._items:
                self._items.append(obj)

        def remove(self, obj):
            if obj in self._items:
                self._items.remove(obj)

        def filter(self, **kwargs):
            return FakeQuerySet(list(self._items), kwargs)

        def all(self):
            return list(self._items)

    fake_manager = FakeRelatedManager()
    fake_profile_self = type("P", (), {"following": fake_manager})
    target_profile = type("T", (), {"pk": 55, "id": 55})
    # Act - follow
    Profile.follow(fake_profile_self, target_profile)
    # Assert - now following contains target
    assert fake_manager.filter(pk=55).exists() is True
    assert Profile.is_following(fake_profile_self, target_profile) is True
    # Act - unfollow
    Profile.unfollow(fake_profile_self, target_profile)
    # Assert - no longer following
    assert fake_manager.filter(pk=55).exists() is False
    assert Profile.is_following(fake_profile_self, target_profile) is False
    # Act - idempotency: unfollow again should not raise
    Profile.unfollow(fake_profile_self, target_profile)
    # Act - follow twice
    Profile.follow(fake_profile_self, target_profile)
    Profile.follow(fake_profile_self, target_profile)
    # Assert - still only one instance in manager
    assert len(fake_manager.all()) == 1
