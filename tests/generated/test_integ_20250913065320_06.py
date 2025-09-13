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

import pytest as _pytest
# If a target import fails, skip the whole module rather than passing silently.
try:
    pass
except ImportError as _e:
    import pytest as _pytest; _pytest.skip(str(_e), allow_module_level=True)
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import inspect
    import types
    from types import SimpleNamespace
    import pytest
    from conduit.apps.authentication.models import User, UserManager
    from conduit.apps.authentication.serializers import UserSerializer, RegistrationSerializer
    from conduit.apps.authentication.backends import JWTAuthentication
    import conduit.apps.authentication.models as auth_models_module
    import jwt as jwt_module
except ImportError as exc:
    import pytest as _pytest
    _pytest.skip(f"Required modules not available: {exc}", allow_module_level=True)

def _exc_lookup(name, default):
    import builtins
    return getattr(builtins, name, default)

@pytest.mark.parametrize("username_value", ["bob", ""])
def test_user_token_and_serializer_representation_integration(monkeypatch, username_value):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    user_instance = User() if hasattr(User, "__call__") else SimpleNamespace()
    # Provide common attributes used by serializer implementations
    if hasattr(user_instance, "__dict__"):
        setattr(user_instance, "username", username_value)
        setattr(user_instance, "email", f"{username_value or 'anon'}@example.com")
        setattr(user_instance, "bio", None)
        setattr(user_instance, "image", None)
    else:
        user_instance = SimpleNamespace(
            username=username_value,
            email=f"{username_value or 'anon'}@example.com",
            bio=None,
            image=None
        )
    # Make token generation deterministic
    def fake_generate_jwt(self):
        return "fixed.jwt.token.for." + (self.username or "anon")
    # Monkeypatch the model method if present, otherwise attach
    if hasattr(User, "_generate_jwt_token"):
        monkeypatch.setattr(User, "_generate_jwt_token", fake_generate_jwt, raising=False)
    # Also patch instance method resolution if needed
    if not hasattr(user_instance, "_generate_jwt_token"):
        user_instance._generate_jwt_token = types.MethodType(fake_generate_jwt, user_instance)
    # Act
    # Some serializer implementations expect Django model instances, others accept simple objects.
    serializer = UserSerializer(user_instance)
    try:
        representation = serializer.data
    except Exception:
        # Fall back to explicit to_representation if .data fails
        representation = serializer.to_representation(user_instance)
    # Assert
    assert isinstance(representation, _exc_lookup("dict", Exception))
    assert "token" in representation
    assert representation["token"] == "fixed.jwt.token.for." + (username_value or "anon")
    assert representation.get("username") == username_value
    assert representation.get("email") == f"{username_value or 'anon'}@example.com"

@pytest.mark.parametrize("create_user_raises", [False, True])
def test_registration_serializer_calls_create_user_and_returns_user_token_integration(monkeypatch, create_user_raises):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    serializer = RegistrationSerializer()
    validated_data = {"username": "alice", "email": "alice@example.com", "password": "s3cret"}
    called = {"args": None, "kwargs": None}
    class FakeUser:
        def __init__(self, username, email):
            self.username = username
            self.email = email
        def token(self):
            return "generated.token.for." + self.username
    def fake_create_user(username=None, email=None, password=None):
        called["args"] = (username, email, password)
        called["kwargs"] = {}
        if create_user_raises:
            raise RuntimeError("create_user failed")
        return FakeUser(username=username, email=email)
    # Ensure User.objects exists and monkeypatch its create_user
    fake_manager = SimpleNamespace(create_user=fake_create_user)
    monkeypatch.setattr(User, "objects", fake_manager, raising=False)
    # Act / Assert
    if create_user_raises:
        with pytest.raises(_exc_lookup("RuntimeError", Exception)):
            serializer.create(validated_data)
    else:
        created_user = serializer.create(validated_data)
        assert hasattr(created_user, "username")
        assert created_user.username == "alice"
        # token may be method or property
        token_value = created_user.token() if callable(getattr(created_user, "token", None)) else getattr(created_user, "token", None)
        assert token_value == "generated.token.for.alice"
        assert called["args"] == ("alice", "alice@example.com", "s3cret")

@pytest.mark.parametrize("jwt_decode_raises, expected_to_raise", [(False, False), (True, True)])
def test_jwtauthentication_authenticate_credentials_integration(monkeypatch, jwt_decode_raises, expected_to_raise):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    backend = JWTAuthentication()
    fake_token = "Bearer faketoken"
    payload = {"user_id": 99}
    decode_called = {"called": False, "token_arg": None}
    def fake_jwt_decode(token, *args, **kwargs):
        decode_called["called"] = True
        decode_called["token_arg"] = token
        if jwt_decode_raises:
            raise ValueError("invalid token")
        return payload
    monkeypatch.setattr(jwt_module, "decode", fake_jwt_decode, raising=False)
    # Provide User.objects.get behavior
    def fake_get(**kwargs):
        if kwargs.get("pk") == payload["user_id"] or kwargs.get("id") == payload["user_id"]:
            return SimpleNamespace(pk=payload["user_id"], is_active=True)
        raise Exception("not found")
    fake_manager = SimpleNamespace(get=fake_get)
    # Attach to User.objects safely
    monkeypatch.setattr(User, "objects", fake_manager, raising=False)
    # Determine signature of _authenticate_credentials and build args accordingly
    auth_method = getattr(backend, "_authenticate_credentials", None)
    assert auth_method is not None, "JWTAuthentication should implement _authenticate_credentials"
    sig = inspect.signature(auth_method)
    params = list(sig.parameters.keys())
    # Build call args: if method expects (self, token) or (self, request, token) adapt
    call_args = []
    # Skip 'self'
    if len(params) == 1:
        # only self -> call without args
        pass
    elif len(params) == 2:
        # (self, token)
        call_args = [fake_token]
    else:
        # (self, request, token) -> pass None for request
        call_args = [None, fake_token]
    # Act / Assert
    if expected_to_raise:
        with pytest.raises(_exc_lookup("ValueError", Exception)):
            result = auth_method(*call_args)
    else:
        result = auth_method(*call_args)
        # Normalize result: method might return user or (user, None)
        user_obj = result[0] if isinstance(result, (list, tuple)) else result
        assert hasattr(user_obj, "pk")
        assert user_obj.pk == payload["user_id"]
        assert decode_called["called"] is True
        # Token passed into decode may be full header; ensure some form passed
        assert decode_called["token_arg"] is not None
