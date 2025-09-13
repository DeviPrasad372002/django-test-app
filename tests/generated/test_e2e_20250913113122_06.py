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

import pytest

try:
    import json
    from types import SimpleNamespace
    import conduit.apps.authentication.backends as backends
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.serializers import UserSerializer
except ImportError:
    pytest.skip("project modules not available", allow_module_level=True)


def _exc_lookup(name, fallback):
    try:
        from rest_framework import exceptions as _rexc
        return getattr(_rexc, name, fallback)
    except Exception:
        return fallback


@pytest.mark.parametrize("image_value", [None, "http://example.test/avatar.png"])
def test_user_serializer_and_renderer_roundtrip(image_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_token = "tok_abcdef12345"
    fake_user = SimpleNamespace(
        username="alice",
        email="alice@example.test",
        bio="A test user",
        image=image_value,
        token=user_token,
    )

    # Act
    serializer = UserSerializer(instance=fake_user)
    serialized_data = serializer.data
    rendered = UserJSONRenderer().render(serialized_data)

    # Assert
    assert isinstance(serialized_data, _exc_lookup("dict", Exception))
    for expected_key in ("username", "email", "bio", "image", "token"):
        assert expected_key in serialized_data
    assert serialized_data["username"] == "alice"
    assert serialized_data["email"] == "alice@example.test"
    assert serialized_data["bio"] == "A test user"
    assert serialized_data["image"] == image_value
    assert serialized_data["token"] == user_token

    assert isinstance(rendered, (bytes, bytearray))
    parsed = json.loads(rendered.decode("utf-8"))
    assert "user" in parsed
    assert parsed["user"] == serialized_data


@pytest.mark.parametrize(
    "input_errors",
    [
        ({"errors": {"email": ["already exists"]}}),
        ({"errors": {"detail": ["invalid credentials"]}}),
    ],
)
def test_userjsonrenderer_renders_errors_as_is(input_errors):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = UserJSONRenderer()

    # Act
    rendered = renderer.render(input_errors)

    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    parsed = json.loads(rendered.decode("utf-8"))
    assert parsed == input_errors
    # ensure structure contains 'errors' key
    assert "errors" in parsed


@pytest.mark.parametrize(
    "case, jwt_decode_side_effect, expect_exception",
    [
        ("valid", {"sub": "ignored", "user_id": 42}, None),
        ("invalid_token", Exception("bad token"), _exc_lookup("AuthenticationFailed", Exception)),
    ],
)
def test_jwtauthentication_authenticate_credentials_monkeypatched(monkeypatch, case, jwt_decode_side_effect, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = backends.JWTAuthentication()
    token_input = "dummy.token.value"

    fake_user = SimpleNamespace(id=42, email="user42@example.test", is_active=True)

    class DummyManager:
        def __init__(self, user):
            self._user = user
        def get(self, **kwargs):
            # Simulate lookup by any keyword (pk, id, email) -> return user
            if kwargs:
                return self._user
            raise Exception("not found")

    class DummyUserModel:
        objects = DummyManager(fake_user)

    def fake_decode_success(token, key, algorithms=None):
        # ignore inputs and return provided payload mapping
        return jwt_payload

    # monkeypatch the User model reference and jwt.decode in the backends module
    monkeypatch.setattr(backends, "User", DummyUserModel, raising=False)

    # Setup jwt.decode behavior
    if isinstance(jwt_decode_side_effect, _exc_lookup("Exception", Exception)):
        def fake_decode_fail(token, key, algorithms=None):
            raise jwt_decode_side_effect
        monkeypatch.setattr(backends, "jwt", SimpleNamespace(decode=fake_decode_fail), raising=False)
    else:
        jwt_payload = jwt_decode_side_effect
        monkeypatch.setattr(backends, "jwt", SimpleNamespace(decode=fake_decode_success), raising=False)

    # Act / Assert
    auth_method = getattr(auth, "_authenticate_credentials", None)
    assert auth_method is not None, "Expected JWTAuthentication to expose _authenticate_credentials"

    if expect_exception is None:
        result = auth_method(token_input)
        # When successful, either the user object or tuple (user, token) can be returned depending on implementation.
        # Accept either and normalize to user object to assert identity.
        if isinstance(result, _exc_lookup("tuple", Exception)) and result:
            returned_user = result[0]
        else:
            returned_user = result
        assert returned_user is fake_user
    else:
        with pytest.raises(_exc_lookup("expect_exception", Exception)):
            auth_method(token_input)
