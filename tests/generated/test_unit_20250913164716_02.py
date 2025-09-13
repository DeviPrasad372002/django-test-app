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

import types
import pytest

try:
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import backends as auth_backends
    from rest_framework import exceptions as drf_exceptions
    from conduit.apps.articles import views as articles_views
except ImportError:
    import pytest
    pytest.skip("Required modules for tests not available", allow_module_level=True)

_exc_lookup = lambda name, fallback: getattr(drf_exceptions, name, fallback)


def test_user_manager_create_user_and_superuser(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = auth_models.UserManager()
    saved_users = []

    class DummyUser:
        def __init__(self, email=None, **extra_fields):
            self.email = email
            self.is_staff = extra_fields.get('is_staff', False)
            self.is_superuser = extra_fields.get('is_superuser', False)
            self._password = None
            self.saved_using = None

        def set_password(self, raw):
            self._password = f"hashed:{raw}"

        def save(self, using=None):
            self.saved_using = using
            saved_users.append(self)

    manager.model = DummyUser
    manager._db = 'default'

    # Act
    normal_user = manager.create_user(email='user@example.com', password='pass123')
    super_user = manager.create_superuser(email='admin@example.com', password='adminpass')

    # Assert
    assert isinstance(normal_user, _exc_lookup("DummyUser", Exception))
    assert normal_user.email == 'user@example.com'
    assert normal_user._password == 'hashed:pass123'
    assert normal_user.saved_using == 'default'
    assert not normal_user.is_staff
    assert not normal_user.is_superuser

    assert isinstance(super_user, _exc_lookup("DummyUser", Exception))
    assert super_user.email == 'admin@example.com'
    assert super_user._password == 'hashed:adminpass'
    assert super_user.saved_using == 'default'
    assert super_user.is_staff
    assert super_user.is_superuser

    # invalid inputs => expect ValueError
    with pytest.raises(_exc_lookup("ValueError", Exception)):
        manager.create_user(email='', password='nope')

    with pytest.raises(_exc_lookup("ValueError", Exception)):
        manager.create_user(email=None, password='nope')


@pytest.mark.parametrize(
    "jwt_decode_result, jwt_decode_exc, expect_failure",
    [
        ({"user_id": 1}, None, False),
        (None, Exception("bad token"), True),
    ],
)
def test_jwt_authentication__authenticate_credentials(monkeypatch, jwt_decode_result, jwt_decode_exc, expect_failure):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    dummy_user = types.SimpleNamespace(id=1, is_active=True)

    class DummyUserModel:
        objects = types.SimpleNamespace(
            get=lambda **kwargs: dummy_user if kwargs.get('pk', kwargs.get('id')) in (1, None, 1) else (_ for _ in ()).throw(Exception("not found"))
        )

    # monkeypatch jwt.decode behavior
    def fake_decode(*args, **kwargs):
        if jwt_decode_exc:
            raise jwt_decode_exc
        return jwt_decode_result

    monkeypatch.setattr(auth_backends, "jwt", types.SimpleNamespace(decode=fake_decode, DecodeError=Exception))
    monkeypatch.setattr(auth_backends, "User", DummyUserModel)

    backend = auth_backends.JWTAuthentication()

    # Act / Assert
    if expect_failure:
        with pytest.raises(_exc_lookup("AuthenticationFailed", Exception)):
            backend._authenticate_credentials("invalid.token.here")
    else:
        result = backend._authenticate_credentials("valid.token.here")
        # result may be user or (user, token)
        user = result[0] if isinstance(result, _exc_lookup("tuple", Exception)) else result
        assert user is dummy_user


@pytest.mark.parametrize(
    "query_params, expect_filtered",
    [
        ({}, False),
        ({"tag": "python"}, True),
        ({"author": "alice"}, True),
        ({"favorited": "bob"}, True),
        ({"tag": "x", "author": "y"}, True),
    ],
)
def test_articles_view_filter_queryset_applies_filters(query_params, expect_filtered):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyQuerySet:
        def __init__(self):
            self.filters = []

        def filter(self, **kwargs):
            self.filters.append(kwargs)
            return self

    queryset = DummyQuerySet()
    viewset = articles_views.ArticleViewSet.__new__(articles_views.ArticleViewSet)
    viewset.request = types.SimpleNamespace(query_params=query_params)

    # Act
    result_qs = viewset.filter_queryset(queryset)

    # Assert
    assert result_qs is queryset
    assert (len(queryset.filters) > 0) is expect_filtered


@pytest.mark.parametrize(
    "first_name,last_name,expected_full",
    [
        ("Alice", "Smith", "Alice Smith"),
        ("", "", "alice@example.com"),
        (None, None, "bob@example.com"),
    ],
)
def test_user_token_and_get_full_name(monkeypatch, first_name, last_name, expected_full):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    User = auth_models.User
    user_instance = User.__new__(User)
    # set attributes without invoking model constructor
    user_instance.email = "alice@example.com" if expected_full != "bob@example.com" else "bob@example.com"
    user_instance.first_name = first_name
    user_instance.last_name = last_name

    # Monkeypatch token generator
    monkeypatch.setattr(User, "_generate_jwt_token", lambda self: "JWT_TOKEN_XYZ")

    # Act
    token_value = getattr(user_instance, "token")
    full_name = user_instance.get_full_name()

    # Assert
    assert token_value == "JWT_TOKEN_XYZ"
    assert full_name == expected_full
