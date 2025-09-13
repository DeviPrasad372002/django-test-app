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
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from types import SimpleNamespace
    import json
    from conduit.apps.authentication import backends as backends_module
    from conduit.apps.authentication import serializers as auth_serializers_module
    from conduit.apps.authentication import renderers as auth_renderers_module
except ImportError as e:
    import pytest as _pytest
    _pytest.skip("Required modules for tests not available: %s" % e, allow_module_level=True)

def _exc_lookup(name, fallback):
    try:
        import rest_framework.exceptions as rf_ex
        return getattr(rf_ex, name)
    except Exception:
        return fallback

class DummyRequest:
    def __init__(self, auth_header_value=None):
        # Django request-like META mapping used by many auth classes
        self.META = {}
        if auth_header_value is not None:
            self.META['HTTP_AUTHORIZATION'] = auth_header_value

@pytest.mark.parametrize(
    "token_value, jwt_decode_behavior, manager_get_behavior, expect_exception",
    [
        # Normal case: jwt.decode returns payload with id, manager.get returns active user -> successful auth
        ("validtoken",
         lambda token, key, algorithms: {"id": 123},
         lambda **kwargs: SimpleNamespace(id=123, is_active=True),
         False),
        # Error case: jwt.decode raises an error -> authentication should raise AuthenticationFailed (or similar)
        ("badtok",
         lambda token, key, algorithms: (_ for _ in ()).throw(ValueError("bad token")),  # raise in lambda
         lambda **kwargs: SimpleNamespace(id=999, is_active=True),
         True),
        # Error case: jwt.decode returns payload but manager.get returns user with is_active False -> auth error
        ("inactive",
         lambda token, key, algorithms: {"id": 321},
         lambda **kwargs: SimpleNamespace(id=321, is_active=False),
         True),
    ]
)
def test_jwtauthentication_authenticate_flow(monkeypatch, token_value, jwt_decode_behavior, manager_get_behavior, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: Create instance of JWTAuthentication and prepare a fake request carrying "Token <token>"
    auth_instance = backends_module.JWTAuthentication()
    request = DummyRequest(auth_header_value=f"Token {token_value}")

    # Arrange: Monkeypatch the jwt.decode used inside the backend module
    def fake_decode(token, secret_key, algorithms=None):
        # Accept any args and delegate to provided behavior which may raise
        return jwt_decode_behavior(token, secret_key, algorithms)
    monkeypatch.setattr(backends_module, 'jwt', SimpleNamespace(decode=fake_decode))

    # Arrange: Monkeypatch the User object in backend module to provide a fake manager with .get(...)
    class FakeManager:
        def get(self, **kwargs):
            return manager_get_behavior(**kwargs)
    fake_user_model = SimpleNamespace(objects=FakeManager())
    monkeypatch.setattr(backends_module, 'User', fake_user_model)

    # Act / Assert
    if expect_exception:
        exc_type = _exc_lookup('AuthenticationFailed', Exception)
        with pytest.raises(_exc_lookup("exc_type", Exception)):
            auth_instance.authenticate(request)
    else:
        # Act
        result = auth_instance.authenticate(request)
        # Assert: Should return a tuple (user, token)
        assert isinstance(result, _exc_lookup("tuple", Exception)), "authenticate should return (user, token)"
        returned_user, returned_token = result
        assert returned_token == token_value
        assert getattr(returned_user, 'id', None) == 123
        assert returned_user.is_active is True

def test_registration_serializer_create_uses_user_manager(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: Prepare a fake user that the manager will create
    fake_created_user = SimpleNamespace(email="alice@example.com", username="alice", token="fixed-token")

    # Arrange: Fake manager with create_user method
    class FakeManager:
        def create_user(self, **kwargs):
            # Assert that expected keys are passed through
            assert 'email' in kwargs and 'username' in kwargs and 'password' in kwargs
            return fake_created_user

    fake_user_model = SimpleNamespace(objects=FakeManager())

    # Arrange: Monkeypatch the User reference inside the serializers module to use our fake manager
    monkeypatch.setattr(auth_serializers_module, 'User', fake_user_model)

    # Act: instantiate serializer and call create directly with validated_data
    serializer_instance = auth_serializers_module.RegistrationSerializer()
    validated_data = {"email": "alice@example.com", "username": "alice", "password": "s3cr3t"}
    created_user = serializer_instance.create(validated_data)

    # Assert: The serializer returns the object produced by the manager and token is present
    assert created_user is fake_created_user
    assert getattr(created_user, 'token') == "fixed-token"
    assert getattr(created_user, 'email') == "alice@example.com"

@pytest.mark.parametrize(
    "input_structure, expected_keys",
    [
        ({"user": {"email": "bob@example.com", "token": "t1"}}, {"user"}),
        ({"user": {"email": "c@example.com", "token": "t2", "username": "c"}}, {"user"}),
        # Edge: empty user dict still should render a user key
        ({"user": {}}, {"user"}),
    ]
)
def test_userjsonrenderer_renders_bytes_and_contains_expected_structure(input_structure, expected_keys):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: instantiate the renderer
    renderer = auth_renderers_module.UserJSONRenderer()

    # Act: call render, which should return bytes representing JSON
    rendered = renderer.render(input_structure, renderer_context={})

    # Assert: output is bytes and valid JSON
    assert isinstance(rendered, (bytes, bytearray))
    decoded = json.loads(rendered.decode('utf-8'))
    assert set(decoded.keys()) >= expected_keys
    # Ensure that inside 'user' the keys exist or at least an object is present
    assert isinstance(decoded.get('user'), dict)
