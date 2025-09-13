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
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from types import SimpleNamespace
    from conduit.apps.authentication.serializers import (
        RegistrationSerializer,
    )
    from conduit.apps.authentication.models import UserManager, User
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.authentication.views import RegistrationAPIView
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required modules for tests are not available", allow_module_level=True)


class DummyUser:
    def __init__(self, username=None, email=None, password=None, bio=None, image=None, pk=None, token=None):
        self.username = username
        self.email = email
        self.password = password
        self.bio = bio
        self.image = image
        self.pk = pk
        self._token = token

    @property
    def token(self):
        return self._token


@pytest.mark.parametrize(
    "payload, expect_valid, expected_error_field",
    [
        ({"username": "alice", "email": "alice@example.com", "password": "s3cr3t"}, True, None),
        ({"username": "bob", "password": "nopass"}, False, "email"),
    ],
)
def test_registration_serializer_calls_user_manager_create_user_and_validates(
    # Arrange-Act-Assert: generated by ai-testgen
    monkeypatch, payload, expect_valid, expected_error_field
):
    # Arrange
    created_call = {}

    def stub_create_user(self, username=None, email=None, password=None, **extra):
        created_call["called"] = True
        created_call["args"] = {"username": username, "email": email, "password": password, **extra}
        return DummyUser(username=username, email=email, password=password, pk=42, token="fixed-token")

    monkeypatch.setattr(UserManager, "create_user", stub_create_user, raising=True)

    serializer = RegistrationSerializer(data=payload)

    # Act
    is_valid_result = serializer.is_valid()

    # Assert
    assert is_valid_result is expect_valid

    if expect_valid:
        saved_user = serializer.save()
        # Ensure manager was invoked and returned object is accessible
        assert created_call.get("called", False) is True
        assert created_call["args"]["username"] == payload.get("username")
        assert created_call["args"]["email"] == payload.get("email")
        # The returned user should expose token property (integration point with model)
        assert getattr(saved_user, "token", None) == "fixed-token"
    else:
        errors = getattr(serializer, "errors", {})
        assert expected_error_field in errors


@pytest.mark.parametrize(
    "user_exists, expect_exception",
    [
        (True, False),
        (False, True),
    ],
)
def test_jwt_authentication__authenticate_credentials_resolves_user(monkeypatch, user_exists, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    payload = {"user_id": 99}
    dummy_user = DummyUser(username="charlie", email="charlie@example.com", pk=99)

    def stub_get(**kwargs):
        if user_exists:
            return dummy_user
        raise Exception("DoesNotExist")

    # Patch the manager get method used by the backend
    monkeypatch.setattr(User.objects, "get", lambda **kwargs: stub_get(**kwargs), raising=True)

    auth_backend = JWTAuthentication()

    # Act / Assert
    if expect_exception:
        with pytest.raises(_exc_lookup("Exception", Exception)):
            auth_backend._authenticate_credentials(payload)
    else:
        result = auth_backend._authenticate_credentials(payload)
        # support both (user, auth) and user return shapes
        returned_user = result[0] if isinstance(result, _exc_lookup("tuple", Exception)) else result
        assert getattr(returned_user, "email", None) == dummy_user.email
        assert getattr(returned_user, "pk", None) == dummy_user.pk


def test_registration_api_view_post_uses_serializer_and_returns_response(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    payload = {"username": "dora", "email": "dora@example.com", "password": "pwd"}
    dummy_user = DummyUser(username="dora", email="dora@example.com", pk=7, token="tok-7")

    class DummySerializer:
        def __init__(self, data=None, instance=None, context=None):
            self._data = data
            self._instance = instance
            self._validated = {"username": data.get("username"), "email": data.get("email")}
            self._saved = None

        def is_valid(self, raise_exception=False):
            return True

        def save(self):
            self._saved = dummy_user
            return self._saved

        @property
        def data(self):
            return {"user": {"email": dummy_user.email, "username": dummy_user.username, "token": dummy_user.token}}

    def fake_get_serializer(self, *args, **kwargs):
        return DummySerializer(data=payload)

    monkeypatch.setattr(RegistrationAPIView, "get_serializer", fake_get_serializer, raising=True)

    view = RegistrationAPIView()
    request = SimpleNamespace(data=payload)

    # Act
    response = view.post(request)

    # Assert
    assert hasattr(response, "data")
    assert response.data == {"user": {"email": "dora@example.com", "username": "dora", "token": "tok-7"}}
