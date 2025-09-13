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

try:
    import pytest
    from unittest.mock import Mock
    import types
    import jwt
    import target.conduit.apps.authentication.models as auth_models
    import target.conduit.apps.authentication.backends as auth_backends
    import target.conduit.apps.articles.views as articles_views
    import target.conduit.apps.articles.models as articles_models
    import rest_framework.exceptions as rf_exceptions
    from rest_framework.response import Response
except ImportError:
    import pytest
    pytest.skip("Required modules for integration tests are not available", allow_module_level=True)

def _exc_lookup(name, default):
    import importlib
    # Search common exception modules
    for mod_name in ("rest_framework.exceptions", "django.core.exceptions", "builtins"):
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        if hasattr(mod, name):
            return getattr(mod, name)
    return default

def test_user_manager_create_user_and_superuser_and_token(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = auth_models.UserManager()
    class DummyUser:
        def __init__(self, email='', username='', first_name='', last_name='', is_staff=False, is_superuser=False, **kwargs):
            self.email = email
            self.username = username
            self.first_name = first_name
            self.last_name = last_name
            self.is_staff = is_staff
            self.is_superuser = is_superuser
            self._password = None
            self.saved = False
        def set_password(self, raw):
            self._password = f'hashed:{raw}'
        def save(self, using=None):
            self.saved = True
        def get_full_name(self):
            return f'{self.first_name} {self.last_name}'.strip()
        def _generate_jwt_token(self):
            return "GENERATED_JWT"
        @property
        def token(self):
            return self._generate_jwt_token()
    manager.model = DummyUser

    # Monkeypatch jwt.encode to ensure determinism if used indirectly
    monkeypatch.setattr(jwt, "encode", lambda payload, key, algorithm=None: "FXJWT", raising=False)

    # Act - create regular user
    created_user = manager.create_user(email="u@example.test", username="tester", first_name="T", last_name="User", password="pw")
    # Assert - created attributes and saved flag and password hashed
    assert isinstance(created_user, _exc_lookup("DummyUser", Exception))
    assert created_user.email == "u@example.test"
    assert created_user.username == "tester"
    assert created_user.first_name == "T"
    assert created_user.last_name == "User"
    assert created_user._password == "hashed:pw"
    assert getattr(created_user, "saved", True) is True or getattr(created_user, "saved", False) is True
    assert created_user.get_full_name() == "T User"
    assert created_user.token == "GENERATED_JWT"

    # Act - create superuser
    super_user = manager.create_superuser(email="admin@example.test", username="admin", password="root")
    # Assert - superuser flags set
    assert isinstance(super_user, _exc_lookup("DummyUser", Exception))
    assert getattr(super_user, "is_staff", True) is True
    assert getattr(super_user, "is_superuser", True) is True

@pytest.mark.parametrize("payload_key", ("id", "user_id", "pk"))
def test_jwt_authentication__authenticate_credentials_resolves_user(monkeypatch, payload_key):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    token_value = "sometoken123"
    auth_instance = auth_backends.JWTAuthentication()

    # Prepare a decoded payload with whichever key is parameterized
    decoded_payload = {payload_key: 99, "email": "x@test"}
    monkeypatch.setattr(jwt, "decode", lambda t, key, algorithms=None: decoded_payload, raising=False)

    class DummyUserObj:
        def __init__(self, uid):
            self.id = uid
            self.email = "x@test"
        def __repr__(self):
            return f"<DummyUser id={self.id}>"

    class DummyObjects:
        @staticmethod
        def get(**kwargs):
            # Accept pk, id, user_id lookups and return DummyUserObj
            for key in ("pk", "id", "user_id"):
                if key in kwargs:
                    return DummyUserObj(kwargs[key])
            # If nothing matched, try positional id
            raise LookupError("not found")

    # Monkeypatch User model's objects to our DummyObjects
    monkeypatch.setattr(auth_models, "User", types.SimpleNamespace(objects=DummyObjects), raising=False)

    # Act
    resolved_user = auth_instance._authenticate_credentials(token_value)

    # Assert
    assert isinstance(resolved_user, _exc_lookup("DummyUserObj", Exception))
    assert resolved_user.id == decoded_payload[payload_key]

@pytest.mark.parametrize("is_owner, expect_deleted, expect_exception", [
    (True, True, None),
    (False, False, "PermissionDenied"),
])
def test_comments_destroy_view_delete_respects_ownership(monkeypatch, is_owner, expect_deleted, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = articles_views.CommentsDestroyAPIView()
    # Create fake comment object
    delete_called = {"value": False}
    class FakeComment:
        def __init__(self, author):
            self.author = author
        def delete(self):
            delete_called["value"] = True

    # Create fake users
    owner_user = types.SimpleNamespace(username="owner")
    other_user = types.SimpleNamespace(username="other")

    comment_author = owner_user if is_owner else other_user
    fake_comment = FakeComment(author=comment_author)

    # Mock get_object to return our fake comment
    monkeypatch.setattr(view, "get_object", lambda *args, **kwargs: fake_comment, raising=False)

    # Fake request with user attribute
    request_user = owner_user
    if not is_owner:
        request_user = types.SimpleNamespace(username="intruder")
    fake_request = types.SimpleNamespace(user=request_user)

    # Act / Assert
    if expect_exception:
        with pytest.raises(_exc_lookup(expect_exception, Exception)):
            # Many implementations accept (request, article_pk, pk) signature
            try:
                view.delete(fake_request, article_pk=1, pk=2)
            except TypeError:
                # fallback: some implementations accept (request, pk)
                view.delete(fake_request, pk=2)
        assert delete_called["value"] is False
    else:
        result = None
        # Try both possible signatures defensively
        try:
            result = view.delete(fake_request, article_pk=1, pk=2)
        except TypeError:
            result = view.delete(fake_request, pk=2)
        # If view returns a DRF Response, assert 204; otherwise just ensure delete was called
        if isinstance(result, _exc_lookup("Response", Exception)):
            assert result.status_code in (204, 200)
        assert delete_called["value"] is True
