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
    import pytest
    import jwt
    import json
    import time
    from conduit.apps.authentication.models import User
    from conduit.apps.authentication.serializers import UserSerializer
    from conduit.apps.authentication.renderers import UserJSONRenderer
except ImportError:
    import pytest
    pytest.skip("skipping tests due to missing conduit authentication modules", allow_module_level=True)


@pytest.mark.parametrize("user_id_value", [None, 0, 12345])
def test_user_token_contains_id_and_expiration(user_id_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create a User-like instance and assign id/pk
    user_instance = User()
    # Some Django model implementations expect pk attribute; set both to be robust
    setattr(user_instance, "id", user_id_value)
    setattr(user_instance, "pk", user_id_value)
    setattr(user_instance, "email", "tester@example.com")
    setattr(user_instance, "username", "tester")

    # Act: obtain JWT token and decode without verifying signature to inspect payload
    token_value = user_instance.token
    assert isinstance(token_value, _exc_lookup("str", Exception)), "token property should return a string"
    decoded_payload = jwt.decode(token_value, options={"verify_signature": False})

    # Assert: expiration present and one of plausible id keys matches our assigned id
    assert "exp" in decoded_payload, "JWT payload must contain an 'exp' claim"
    exp_value = decoded_payload["exp"]
    assert isinstance(exp_value, _exc_lookup("int", Exception)), "'exp' should be an integer timestamp"
    assert exp_value >= int(time.time()), "'exp' should be in the future"

    id_matches = (
        decoded_payload.get("id") == user_id_value
        or decoded_payload.get("user_id") == user_id_value
        or decoded_payload.get("pk") == user_id_value
    )
    assert id_matches, f"JWT payload should include the user's id (expected {user_id_value}), got {decoded_payload}"


def test_user_serializer_representation_excludes_password_and_includes_token_and_email():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: prepare a User instance with attributes typically exposed by serializer
    user_instance = User()
    setattr(user_instance, "id", 7)
    setattr(user_instance, "pk", 7)
    setattr(user_instance, "email", "alice@example.com")
    setattr(user_instance, "username", "alice")
    setattr(user_instance, "bio", "tester bio")
    setattr(user_instance, "image", "http://example.com/avatar.png")
    # Also set a password attribute to ensure serializer does not emit it
    setattr(user_instance, "password", "supersecret")

    # Act: serialize the user
    serializer = UserSerializer(instance=user_instance)
    serialized_data = serializer.data

    # Assert: serialized structure contains public fields and excludes password
    assert isinstance(serialized_data, _exc_lookup("dict", Exception)), "serializer.data should be a dict-like mapping"
    assert "email" in serialized_data and serialized_data["email"] == "alice@example.com"
    assert "username" in serialized_data and serialized_data["username"] == "alice"
    assert "bio" in serialized_data and serialized_data["bio"] == "tester bio"
    assert "image" in serialized_data and serialized_data["image"] == "http://example.com/avatar.png"
    assert "password" not in serialized_data, "password must not be present in serialized output"
    # token should be present and should match the user's token property
    assert "token" in serialized_data
    assert isinstance(serialized_data["token"], str)
    assert serialized_data["token"] == user_instance.token


def test_user_json_renderer_outputs_wrapped_user_object():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: prepare renderer and a typical payload returned by user serializer
    renderer = UserJSONRenderer()
    user_payload = {
        "user": {
            "email": "render@example.com",
            "username": "renderuser",
            "token": "dummy-token",
        }
    }

    # Act: render the payload to bytes and parse back to Python dict
    rendered_bytes = renderer.render(user_payload)
    assert isinstance(rendered_bytes, (bytes, bytearray)), "render should return bytes or bytearray"
    rendered_text = rendered_bytes.decode("utf-8")
    parsed = json.loads(rendered_text)

    # Assert: ensure the JSON structure matches the wrapped 'user' shape
    assert isinstance(parsed, _exc_lookup("dict", Exception))
    assert "user" in parsed
    assert parsed["user"]["email"] == "render@example.com"
    assert parsed["user"]["username"] == "renderuser"
    assert parsed["user"]["token"] == "dummy-token"
