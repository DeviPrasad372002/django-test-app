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
    import importlib
    import types
    from types import SimpleNamespace
    import pytest
    import jwt as pyjwt
    import conduit.apps.authentication.backends as backends
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.authentication.models import UserManager
except ImportError:
    import pytest
    pytest.skip("Required modules for tests are not available", allow_module_level=True)

def _exc_lookup(name, default):
    mod = importlib.import_module('rest_framework.exceptions')
    return getattr(mod, name, default)

def test_jwt_authentication_returns_none_when_no_authorization_header():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = JWTAuthentication()
    request = SimpleNamespace(META={}, headers={})
    # Act
    result = auth.authenticate(request)
    # Assert
    assert result is None

def test_jwt_authentication_calls_internal_authenticate_credentials(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    expected_user = object()
    expected_token = "abc.def.ghi"
    called = {}
    def fake_authenticate_credentials(self, token):
        called['token'] = token
        return (expected_user, token)
    monkeypatch.setattr(JWTAuthentication, '_authenticate_credentials', fake_authenticate_credentials, raising=True)
    auth = JWTAuthentication()
    # request might expose headers or META depending on implementation
    request = SimpleNamespace(META={'HTTP_AUTHORIZATION': f"Token {expected_token}"}, headers={'Authorization': f"Token {expected_token}"})
    # Act
    result = auth.authenticate(request)
    # Assert
    assert result == (expected_user, expected_token)
    assert called.get('token') == expected_token

@pytest.mark.parametrize("decode_side_effect, expected_exception", [
    (pyjwt.InvalidTokenError("invalid"), _exc_lookup('AuthenticationFailed', Exception)),
    (Exception("other decode error"), _exc_lookup('AuthenticationFailed', Exception)),
])
def test__authenticate_credentials_raises_on_invalid_token(monkeypatch, decode_side_effect, expected_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = JWTAuthentication()
    # Ensure jwt.decode raises the provided side effect
    monkeypatch.setattr(backends, 'jwt', types.SimpleNamespace(decode=lambda *a, **k: (_ for _ in ()).throw(decode_side_effect)))
    # Act / Assert
    with pytest.raises(_exc_lookup("expected_exception", Exception)):
        auth._authenticate_credentials("bad.token.value")

@pytest.mark.parametrize("email_input,password_input,expect_lowercase", [
    ("USER@Example.COM", "s3cr3t", True),
    ("mixed.Case@domain.Org", "p@ss", True),
])
def test_usermanager_create_user_sets_email_and_password(email_input, password_input, expect_lowercase):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = UserManager()
    class FakeUser:
        def __init__(self, email=None, **kwargs):
            self.email = email
            self._saved = False
            # allow arbitrary flags
            for k, v in kwargs.items():
                setattr(self, k, v)
            self.password_set = None
        def set_password(self, raw):
            self.password_set = raw
        def save(self, using=None):
            self._saved = True
    manager.model = FakeUser
    manager._db = None
    # Act
    user = manager.create_user(email_input, password_input)
    # Assert
    if expect_lowercase:
        assert user.email == email_input.lower()
    else:
        assert user.email == email_input
    assert getattr(user, 'password_set') == password_input
    assert getattr(user, '_saved') is True

def test_usermanager_create_superuser_sets_flags_and_validates():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = UserManager()
    class FakeUser:
        def __init__(self, email=None, **kwargs):
            self.email = email
            self.is_staff = kwargs.get('is_staff', False)
            self.is_superuser = kwargs.get('is_superuser', False)
            self._saved = False
        def set_password(self, raw):
            self.password_set = raw
        def save(self, using=None):
            self._saved = True
    manager.model = FakeUser
    manager._db = None
    # Act / Assert: normal creation should set flags True
    superuser = manager.create_superuser("admin@example.com", "adminpass")
    assert superuser.is_staff is True
    assert superuser.is_superuser is True
    assert getattr(superuser, '_saved') is True
    # Act / Assert: passing is_superuser=False should raise ValueError
    with pytest.raises(_exc_lookup("ValueError", Exception)):
        manager.create_superuser("admin2@example.com", "adminpass", is_superuser=False)
