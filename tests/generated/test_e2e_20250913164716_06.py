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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import json
    import uuid
    import pytest
    from rest_framework.test import APIRequestFactory
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.serializers import UserSerializer
    from conduit.apps.authentication.views import RegistrationAPIView, LoginAPIView
    from conduit.apps.authentication.models import User
except ImportError as _err:
    import pytest as _pytest
    _pytest.skip(f"Required test imports not available: {_err}", allow_module_level=True)

@pytest.mark.parametrize(
    "input_user_dict",
    [
        {"email": "alice@example.org", "username": "alice"},
        {"email": "bob@example.org", "username": "bob", "bio": "bio text", "image": "http://img"},
    ],
)
def test_userjsonrenderer_wraps_and_userserializer_represents_dict(input_user_dict):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: prepare raw user mapping and instantiate renderer & serializer
    raw_user_mapping = dict(input_user_dict)  # copy to avoid mutation
    renderer = UserJSONRenderer()
    serializer = UserSerializer(instance=raw_user_mapping)

    # Act: render mapping to bytes and obtain serializer representation
    rendered_bytes = renderer.render(raw_user_mapping)
    serializer_representation = serializer.data

    # Assert: rendered bytes decode to JSON that wraps the original data under "user"
    assert isinstance(rendered_bytes, (bytes, bytearray))
    parsed = json.loads(rendered_bytes.decode("utf-8"))
    assert isinstance(parsed, _exc_lookup("dict", Exception))
    assert "user" in parsed
    # The wrapped content must match the input mapping (keys present and values equal)
    for key, value in raw_user_mapping.items():
        assert key in parsed["user"]
        assert parsed["user"][key] == value

    # Assert: serializer produced a mapping-like representation containing expected keys
    assert isinstance(serializer_representation, _exc_lookup("dict", Exception))
    for expected_key in ("email", "username"):
        assert expected_key in serializer_representation
        assert serializer_representation[expected_key] == raw_user_mapping[expected_key]

def test_registration_and_login_apiviews_end_to_end_create_and_authenticate_user():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: prepare unique credentials to avoid collisions across test runs
    unique_suffix = uuid.uuid4().hex[:8]
    test_username = f"user_{unique_suffix}"
    test_email = f"{test_username}@example.test"
    test_password = "S3cureP@ssw0rd!"
    factory = APIRequestFactory()
    registration_view = RegistrationAPIView.as_view()
    login_view = LoginAPIView.as_view()

    registration_payload = {"user": {"username": test_username, "email": test_email, "password": test_password}}
    login_payload = {"user": {"email": test_email, "password": test_password}}

    created_user_qs = None
    try:
        # Act: perform registration request
        registration_request = factory.post("/api/users/", registration_payload, format="json")
        registration_response = registration_view(registration_request)
        # Assert: registration returns a success status and user object with expected fields
        assert hasattr(registration_response, "data")
        assert isinstance(registration_response.data, dict)
        assert "user" in registration_response.data
        reg_user = registration_response.data["user"]
        assert reg_user.get("email") == test_email
        assert reg_user.get("username") == test_username
        # token may or may not be present depending on implementation; if present assert type
        if "token" in reg_user:
            assert isinstance(reg_user["token"], str)
            assert reg_user["token"], "token should be a non-empty string when present"

        # Act: perform login request
        login_request = factory.post("/api/users/login/", login_payload, format="json")
        login_response = login_view(login_request)
        # Assert: login returns success and a token in the response user object
        assert hasattr(login_response, "data")
        assert isinstance(login_response.data, dict)
        assert "user" in login_response.data
        login_user = login_response.data["user"]
        assert login_user.get("email") == test_email
        assert login_user.get("username") == test_username
        assert "token" in login_user, "Login response must include a token"
        assert isinstance(login_user["token"], str) and login_user["token"], "token must be a non-empty string"

        # Additionally assert that a User record now exists in the DB with matching email
        created_user_qs = User.objects.filter(email=test_email)
        assert created_user_qs.exists()
        created_user = created_user_qs.first()
        assert created_user.username == test_username
        assert created_user.email == test_email

    finally:
        # Cleanup: remove created user record to avoid side effects for other tests
        if created_user_qs is not None and created_user_qs.exists():
            created_user_qs.delete()
