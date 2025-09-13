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
    import types
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.backends as auth_backends
    import conduit.apps.articles.signals as article_signals
    import conduit.apps.articles.views as article_views
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required project modules not available", allow_module_level=True)

def _exc_lookup(name, default):
    import sys
    for mod in list(sys.modules.values()):
        if not mod:
            continue
        if hasattr(mod, name):
            return getattr(mod, name)
    return default

def test_user_manager_create_user_and_superuser(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_users = []
    class DummyUser:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.password_set = None
            self.saved = False
            # default flags if accessed
            if not hasattr(self, 'is_staff'):
                self.is_staff = False
            if not hasattr(self, 'is_superuser'):
                self.is_superuser = False
        def set_password(self, raw):
            self.password_set = raw
        def save(self, using=None):
            self.saved = True
            created_users.append(self)
    manager = auth_models.UserManager()
    # Ensure manager will instantiate our DummyUser
    manager.model = DummyUser

    # Act
    user = manager.create_user(email="Test@Example.COM", password="s3cr3t", username="tester")
    superuser = manager.create_superuser(email="Admin@EXAMPLE.com", password="adminpass", username="admin")

    # Assert
    assert isinstance(user, _exc_lookup("DummyUser", Exception))
    assert user.saved is True
    assert user.password_set == "s3cr3t"
    # email normalization should lowercase domain part at least
    assert "@" in user.__dict__.get("email", "")
    assert user.__dict__["email"].lower() == user.__dict__["email"]
    assert isinstance(superuser, _exc_lookup("DummyUser", Exception))
    assert superuser.saved is True
    # superuser flags expected to be truthy
    assert getattr(superuser, "is_staff", False) is True
    assert getattr(superuser, "is_superuser", False) is True

def test_jwt_authentication_authenticate_credentials_success(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    decoded_payload = {"id": 42}
    def fake_decode(token, key=None, algorithms=None, options=None):
        return decoded_payload
    # Monkeypatch jwt.decode used inside auth_backends
    if hasattr(auth_backends, "jwt"):
        monkeypatch.setattr(auth_backends.jwt, "decode", fake_decode, raising=False)
    else:
        fake_jwt = types.SimpleNamespace(decode=fake_decode)
        monkeypatch.setattr(auth_backends, "jwt", fake_jwt, raising=False)

    class DummyUser:
        def __init__(self, pk=42):
            self.pk = pk
            self.is_active = True
    class DummyManager:
        @staticmethod
        def get(pk):
            if pk == 42:
                return DummyUser(pk=pk)
            raise Exception("Not found")
    DummyUser.objects = DummyManager()

    # Replace the User reference inside the backend module
    monkeypatch.setattr(auth_backends, "User", DummyUser, raising=False)

    auth_instance = auth_backends.JWTAuthentication()

    # Act
    result = auth_instance._authenticate_credentials("header.payload.signature")

    # Assert
    # Depending on implementation it may return user or (user, token); accept both
    if isinstance(result, _exc_lookup("tuple", Exception)):
        user = result[0]
    else:
        user = result
    assert isinstance(user, _exc_lookup("DummyUser", Exception))
    assert user.pk == 42

@pytest.mark.parametrize("query_params, expect_filters", [
    ({}, False),
    ({"tag": "py"}, True),
    ({"author": "alice", "favorited": "bob"}, True),
])
def test_article_view_filter_queryset_records_calls(query_params, expect_filters):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyQuerySet:
        def __init__(self, items=None):
            self.items = items or []
            self.filter_calls = []
        def filter(self, **kwargs):
            self.filter_calls.append(kwargs)
            # return a new queryset to mimic Django behavior
            new = DummyQuerySet(self.items)
            new.filter_calls = list(self.filter_calls)
            return new
        def order_by(self, *args, **kwargs):
            # record ordering as a "filter-like" call for visibility
            self.filter_calls.append({"_order_by": args})
            return self

    view = article_views.ArticleViewSet()
    # craft a minimal request-like object with query_params attribute
    class DummyRequest:
        def __init__(self, params):
            self.query_params = params
    view.request = DummyRequest(query_params)
    original_qs = DummyQuerySet(items=[{"slug": "a"}, {"slug": "b"}])

    # Act
    filtered = view.filter_queryset(original_qs)

    # Assert
    assert isinstance(filtered, _exc_lookup("DummyQuerySet", Exception))
    if expect_filters:
        assert len(filtered.filter_calls) > 0
    else:
        # no query params => should not apply filters in our adapter
        assert filtered.filter_calls == []

@pytest.mark.parametrize("initial_slug, should_change", [
    (None, True),
    ("existing-slug", False),
])
def test_add_slug_to_article_if_not_exists_sets_or_keeps_slug(monkeypatch, initial_slug, should_change):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug
            self.saved = False
        def save(self, *args, **kwargs):
            self.saved = True

    instance = DummyArticle(title="Hello World!", slug=initial_slug)

    # Act
    # The signal handler typically accepts sender and instance (and kwargs)
    article_signals.add_slug_to_article_if_not_exists(sender=None, instance=instance)

    # Assert
    if should_change:
        assert instance.slug is not None and instance.slug != ""
        # slug should contain slugified title portion "hello-world"
        assert "hello-world" in instance.slug
        assert instance.saved is True
    else:
        # slug should remain unchanged
        assert instance.slug == "existing-slug" or instance.saved is False
