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

import pytest
try:
    import jwt
    import types
    from types import SimpleNamespace
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.backends as auth_backends
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required modules for tests are not available", allow_module_level=True)


def _exc_lookup(name, default):
    try:
        import rest_framework.exceptions as rf_exc
        return getattr(rf_exc, name, default)
    except Exception:
        return default


@pytest.mark.parametrize(
    "first,last,expected_full",
    [
        ("Alice", "Smith", "Alice Smith"),
        ("", "Doe", " Doe"),
        ("John", "", "John "),
    ],
)
def test_get_full_name_and_token_contains_jwt_structure(first, last, expected_full):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_cls = getattr(auth_models, "User", None)
    assert user_cls is not None, "User class must be present in auth models"
    # Create a lightweight User-like instance without DB interaction
    user_instance = user_cls()
    user_instance.first_name = first
    user_instance.last_name = last
    # Some implementations expect an id attribute for token generation
    user_instance.id = 42

    # Act
    full_name = getattr(user_instance, "get_full_name")()
    token_value = getattr(user_instance, "token")

    # Assert
    assert isinstance(full_name, _exc_lookup("str", Exception))
    assert full_name == expected_full
    assert isinstance(token_value, _exc_lookup("str", Exception))
    # JWTs have two '.' separators (header.payload.signature)
    assert token_value.count(".") == 2


def test__generate_jwt_token_encodes_id_and_expiration():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    gen_fn = getattr(auth_models, "_generate_jwt_token", None)
    assert gen_fn is not None, "_generate_jwt_token must exist"
    test_id = 999

    # Act
    token = gen_fn(test_id)

    # Assert basic type and structure
    assert isinstance(token, _exc_lookup("str", Exception))
    assert token.count(".") == 2

    # Decode payload without verifying signature to inspect contents
    # This uses PyJWT; ignore signature verification for unit test inspection
    decoded = jwt.decode(token, options={"verify_signature": False})
    assert isinstance(decoded, _exc_lookup("dict", Exception))
    assert decoded.get("id") == test_id
    assert "exp" in decoded


@pytest.mark.parametrize(
    "scenario,prepare_get,expected_result,expect_exception",
    [
        ("found_active", lambda: SimpleNamespace(get=lambda pk: SimpleNamespace(id=pk, is_active=True)), True, None),
        ("found_inactive", lambda: SimpleNamespace(get=lambda pk: SimpleNamespace(id=pk, is_active=False)), None, "AuthenticationFailed"),
        ("not_found", lambda: SimpleNamespace(get=lambda pk: (_ for _ in ()).throw(Exception("no user"))), None, "AuthenticationFailed"),
    ],
)
def test_jwtauthenticate_credentials_various_states(monkeypatch, scenario, prepare_get, expected_result, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    jwt_auth_cls = getattr(auth_backends, "JWTAuthentication", None)
    assert jwt_auth_cls is not None, "JWTAuthentication must be present"
    backend_module = auth_backends
    # Replace the User manager inside the backends module to control lookup behavior
    DummyUserModel = SimpleNamespace()
    DummyUserModel.objects = prepare_get()
    monkeypatch.setattr(backend_module, "User", DummyUserModel, raising=False)
    auth_instance = jwt_auth_cls()

    payload = {"id": 123}

    # Act / Assert
    exc_type = _exc_lookup(expect_exception, Exception) if expect_exception else None
    if exc_type:
        with pytest.raises(_exc_lookup("exc_type", Exception)):
            auth_instance._authenticate_credentials(payload)
    else:
        returned = auth_instance._authenticate_credentials(payload)
        assert returned is not None
        assert getattr(returned, "id", None) == payload["id"]
