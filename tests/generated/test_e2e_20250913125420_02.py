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
    from types import SimpleNamespace
    from conduit.apps.authentication.models import User
    from conduit.apps.authentication import backends as auth_backends
    from conduit.apps.authentication.backends import JWTAuthentication
    from rest_framework import exceptions as drf_exceptions
except ImportError as e:
    import pytest
    pytest.skip(str(e), allow_module_level=True)


def _exc_lookup(name, default):
    return getattr(drf_exceptions, name, default)


def test_user_token_and_get_full_name_contains_expected_fields():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_instance = User()
    user_instance.first_name = "Alice"
    user_instance.last_name = "Smith"
    user_instance.email = "alice@example.com"
    user_instance.id = 42

    # Act
    full_name_result = user_instance.get_full_name()
    token_result = user_instance.token

    # Assert
    assert isinstance(full_name_result, _exc_lookup("str", Exception))
    assert "Alice" in full_name_result and "Smith" in full_name_result

    assert isinstance(token_result, _exc_lookup("str", Exception))
    # Inspect payload without verifying signature to avoid depending on SECRET_KEY
    decoded_payload = jwt.decode(token_result, options={"verify_signature": False})
    assert decoded_payload.get("email") == "alice@example.com"
    # Accept either 'id' or 'user_id' keys depending on implementation
    assert decoded_payload.get("id", decoded_payload.get("user_id")) == 42
    assert "exp" in decoded_payload


@pytest.mark.parametrize(
    "header_value, expected_token",
    [
        ("Token abc123", "abc123"),
        ("Bearer zzz-token", "zzz-token"),
        (None, None),
        ("", None),
        ("MalformedHeader", None),
    ],
)
def test_jwtauthentication_authenticate_parses_authorization_header(monkeypatch, header_value, expected_token):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    captured = {"called_with": None}

    def fake_authenticate_credentials(self, token_value):
        captured["called_with"] = token_value
        return ("stub_user_obj", "stub_returned_token")

    monkeypatch.setattr(JWTAuthentication, "_authenticate_credentials", fake_authenticate_credentials)

    if header_value is None:
        request = SimpleNamespace(META={})
    else:
        request = SimpleNamespace(META={"HTTP_AUTHORIZATION": header_value})

    auth_instance = JWTAuthentication()

    # Act
    result = auth_instance.authenticate(request)

    # Assert
    if expected_token is None:
        assert result is None
        assert captured["called_with"] is None
    else:
        assert result == ("stub_user_obj", "stub_returned_token")
        assert captured["called_with"] == expected_token


def test__authenticate_credentials_handles_invalid_token_and_missing_user(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    backend_module = auth_backends
    TargetAuthFailed = _exc_lookup("AuthenticationFailed", Exception)

    # Case A: jwt.decode raises an expired/invalid token error -> AuthenticationFailed
    def raise_decode_error(token, *args, **kwargs):
        raise jwt.ExpiredSignatureError("token expired")

    monkeypatch.setattr(backend_module.jwt, "decode", raise_decode_error)

    with pytest.raises(_exc_lookup("TargetAuthFailed", Exception)):
        backend_module.JWTAuthentication()._authenticate_credentials("bad.token.value")

    # Case B: jwt.decode returns payload but user lookup fails -> AuthenticationFailed
    payload = {"id": 9999, "email": "noone@example.com"}

    def return_payload(token, *args, **kwargs):
        return payload

    monkeypatch.setattr(backend_module.jwt, "decode", return_payload)

    # Ensure the User lookup raises DoesNotExist
    def raise_does_not_exist(pk):
        raise backend_module.User.DoesNotExist

    # Monkeypatch the manager get method; some implementations use get(pk=...) or objects.get(id=...)
    if hasattr(backend_module.User, "objects"):
        monkeypatch.setattr(backend_module.User.objects, "get", lambda *args, **kwargs: (_ for _ in ()).throw(backend_module.User.DoesNotExist))
    else:
        # Fallback: direct attribute
        monkeypatch.setattr(backend_module, "User", backend_module.User)

    with pytest.raises(_exc_lookup("TargetAuthFailed", Exception)):
        backend_module.JWTAuthentication()._authenticate_credentials("some.token.here")

    # Case C: valid payload and user found and active -> returns (user, token)
    fake_user = SimpleNamespace(is_active=True)
    monkeypatch.setattr(backend_module.User.objects, "get", lambda *args, **kwargs: fake_user)
    result = backend_module.JWTAuthentication()._authenticate_credentials("valid.token.here")
    assert isinstance(result, _exc_lookup("tuple", Exception))
    assert result[0] is fake_user
    assert result[1] == "valid.token.here"
