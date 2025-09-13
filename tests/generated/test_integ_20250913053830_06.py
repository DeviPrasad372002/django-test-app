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
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet'):
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
if not STRICT:
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
try:
    if _iu.find_spec("django") is not None:
        import django
        from django.conf import settings as _dj_settings
        if not _dj_settings.configured:
            _dj_settings.configure(SECRET_KEY="test-key", DEBUG=True, ALLOWED_HOSTS=["*"], INSTALLED_APPS=[], DATABASES={"default": {"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
            django.setup()
except Exception: pass
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

import json
# If a target import fails, skip the whole module rather than passing silently.
try:
    pass
except ImportError as _e:
    import pytest as _pytest; _pytest.skip(str(_e), allow_module_level=True)
import types
import pytest

try:
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import serializers as auth_serializers
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.serializers import RegistrationSerializer, LoginSerializer, UserSerializer
except ImportError as e:
    pytest.skip("Required modules for tests are not available: {}".format(e), allow_module_level=True)


@pytest.mark.parametrize(
    "jwt_return, should_raise",
    [
        ("encoded-token-123", False),
        (ValueError("encode-failed"), True),
    ],
)
def test_user_token_generation_calls_jwt_encode(monkeypatch, jwt_return, should_raise):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    called = {"count": 0, "last_payload": None, "last_secret": None, "last_algo": None}

    def fake_encode(payload, secret, algorithm="HS256"):
        called["count"] += 1
        called["last_payload"] = payload
        called["last_secret"] = secret
        called["last_algo"] = algorithm
        if isinstance(jwt_return, _exc_lookup("Exception", Exception)):
            raise jwt_return
        return jwt_return

    # Patch the jwt.encode used inside the auth_models module
    monkeypatch.setattr(auth_models.jwt, "encode", fake_encode, raising=True)

    # Create a User instance without hitting DB; set id to known value
    user = auth_models.User()
    # Ensure attributes exist for payload generation (some implementations use pk/id)
    setattr(user, "id", 42)

    # Act / Assert
    if should_raise:
        with pytest.raises(_exc_lookup("Exception", Exception)):
            _ = user.token
        assert called["count"] == 1
    else:
        token_value = user.token
        # Assert
        assert isinstance(token_value, _exc_lookup("str", Exception))
        assert token_value == "encoded-token-123"
        assert called["count"] == 1
        # payload should include user id or pk - check at least one numeric present in payload values
        payload = called["last_payload"]
        assert isinstance(payload, _exc_lookup("dict", Exception))
        # Expect some identifier in payload
        assert any(
            (isinstance(v, _exc_lookup("int", Exception)) and v == 42) or (isinstance(v, _exc_lookup("dict", Exception)) and 42 in v.values())
            for v in payload.values()
        )
        assert called["last_algo"] in ("HS256", "HS512", None) or isinstance(called["last_algo"], str)


def test_registration_serializer_and_renderer_integration_creates_user_and_renders_json(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    class FakeUser:
        def __init__(self, username, email, password):
            self.username = username
            self.email = email
            self._password = password
            self.id = 7

        @property
        def token(self):
            return "fake-token-{}".format(self.id)

    class FakeManager:
        def create_user(self, username=None, email=None, password=None):
            return FakeUser(username=username, email=email, password=password)

    class FakeUserModel:
        objects = FakeManager()

    # Replace User in serializer module so RegistrationSerializer.create uses our fake manager
    monkeypatch.setattr(auth_serializers, "User", FakeUserModel, raising=False)

    serializer = RegistrationSerializer()

    validated_data = {"username": "newuser", "email": "newuser@example.com", "password": "securepwd"}

    # Act
    created_user = serializer.create(validated_data)

    # Assert created user properties
    assert isinstance(created_user, _exc_lookup("FakeUser", Exception))
    assert created_user.username == "newuser"
    assert created_user.email == "newuser@example.com"
    assert created_user.token == "fake-token-7"

    # Now verify UserSerializer can turn FakeUser into serializable dict and renderer emits JSON bytes
    # UserSerializer should access simple attributes, so it should work with FakeUser
    user_serialized = UserSerializer(created_user).data
    assert isinstance(user_serialized, _exc_lookup("dict", Exception))
    assert user_serialized.get("username") == "newuser"
    assert user_serialized.get("email") == "newuser@example.com"
    assert user_serialized.get("token") == "fake-token-7"

    renderer = UserJSONRenderer()
    rendered_bytes = renderer.render({"user": user_serialized})
    assert isinstance(rendered_bytes, (bytes, bytearray))
    rendered = json.loads(rendered_bytes.decode("utf-8"))
    assert "user" in rendered
    assert rendered["user"]["username"] == "newuser"
    assert rendered["user"]["email"] == "newuser@example.com"
    assert rendered["user"]["token"] == "fake-token-7"


def test_login_serializer_authenticates_and_returns_user_token(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    class FakeUser:
        def __init__(self, email, username):
            self.email = email
            self.username = username
            self.id = 99

        @property
        def token(self):
            return "login-token-99"

    def fake_authenticate(email=None, password=None):
        if email == "exist@example.com" and password == "right":
            return FakeUser(email=email, username="exist")
        return None

    # Patch authenticate in the serializers module; some implementations import authenticate from django
    monkeypatch.setattr(auth_serializers, "authenticate", fake_authenticate, raising=False)
    # Also patch django.contrib.auth.authenticate just in case serializer uses that path
    try:
        import django.contrib.auth
        monkeypatch.setattr(django.contrib.auth, "authenticate", fake_authenticate, raising=False)
    except Exception:
        # If django not available or attribute missing, ignore - serializer patch should suffice
        pass

    serializer = LoginSerializer()

    # Act
    validated = serializer.validate({"email": "exist@example.com", "password": "right"})

    # Assert
    # Depending on implementation validate may return a dict containing 'user'
    assert isinstance(validated, _exc_lookup("dict", Exception))
    assert "user" in validated
    user_obj = validated["user"]
    assert isinstance(user_obj, _exc_lookup("FakeUser", Exception))
    assert user_obj.email == "exist@example.com"
    assert user_obj.token == "login-token-99"
