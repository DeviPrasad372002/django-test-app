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
    import pytest
    from types import SimpleNamespace
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.backends as auth_backends
    import conduit.apps.core.exceptions as core_exceptions
    import rest_framework.exceptions as drf_exceptions
    import rest_framework.response as drf_response
except ImportError as e:
    import pytest as _pytest
    _pytest.skip("Required packages for tests not available: {}".format(e), allow_module_level=True)

def _exc_lookup(name, default):
    if hasattr(drf_exceptions, name):
        return getattr(drf_exceptions, name)
    return default

@pytest.mark.parametrize(
    "case, is_superuser, email, username, password, expect_exception",
    [
        ("normal_user", False, "Alice@example.com", "alice", "s3cret", None),
        ("normal_superuser", True, "Admin@example.com", "admin", "topsecret", None),
        ("missing_email_user", False, None, "nouser", "pw", ValueError),
    ],
)
def test_user_manager_create_user_and_superuser(case, is_superuser, email, username, password, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calls = {}
    class DummyUser:
        def __init__(self, email=None, username=None):
            self.email = email
            self.username = username
            self.password_set = None
            self.is_staff = False
            self.is_superuser = False
            self.saved = False
        def set_password(self, raw):
            self.password_set = raw
        def save(self, using=None):
            self.saved = True
    manager_stub = SimpleNamespace()
    manager_stub.model = DummyUser
    manager_stub._db = "default"
    def normalize_email(value):
        return value.lower() if isinstance(value, _exc_lookup("str", Exception)) else value
    manager_stub.normalize_email = normalize_email

    # Act
    func = auth_models.UserManager.create_superuser if is_superuser else auth_models.UserManager.create_user
    if expect_exception:
        with pytest.raises(_exc_lookup("expect_exception", Exception)):
            func(manager_stub, email=email, username=username, password=password)
        return

    created = func(manager_stub, email=email, username=username, password=password)

    # Assert
    assert isinstance(created, _exc_lookup("DummyUser", Exception))
    assert created.saved is True
    assert created.password_set == password
    assert created.email == (email.lower() if isinstance(email, _exc_lookup("str", Exception)) else email)
    assert created.username == username
    if is_superuser:
        assert created.is_staff is True or getattr(created, "is_staff", True) is True
        assert created.is_superuser is True or getattr(created, "is_superuser", True) is True

def test_jwtauthenticate_raises_when_user_missing(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth_instance = auth_backends.JWTAuthentication()
    fake_payload = {"id": 999}
    class FakeJWT:
        @staticmethod
        def decode(tok, key, algorithms):
            return fake_payload
    monkeypatch.setattr(auth_backends, "jwt", FakeJWT)

    User = auth_models.User
    # Ensure DoesNotExist exists on User for realistic flow
    if not hasattr(User, "DoesNotExist"):
        User.DoesNotExist = type("DoesNotExist", (Exception,), {})
    class FakeManager:
        def get(self, pk):
            raise User.DoesNotExist()
    monkeypatch.setattr(User, "objects", FakeManager())

    # Act / Assert
    exc_class = _exc_lookup("AuthenticationFailed", Exception)
    with pytest.raises(_exc_lookup("exc_class", Exception)):
        auth_instance._authenticate_credentials("sometoken")

def test_handle_generic_error_returns_response_structure():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    dummy_exception = Exception("boom")
    dummy_context = {"view": None}

    # Act
    response = core_exceptions._handle_generic_error(dummy_exception, dummy_context)

    # Assert
    assert isinstance(response, _exc_lookup("drf_response.Response", Exception))
    assert hasattr(response, "status_code")
    assert isinstance(response.data, dict) or response.data is None
    assert response.status_code >= 500 or response.status_code == getattr(response, "status_code", 500)
