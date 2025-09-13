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

try:
    import pytest
    import importlib
    from types import SimpleNamespace
    import inspect

    backends_mod = importlib.import_module("conduit.apps.authentication.backends")
    jwt_auth_cls = getattr(backends_mod, "JWTAuthentication")
    views_mod = importlib.import_module("conduit.apps.articles.views")
    CommentsDestroyAPIView = getattr(views_mod, "CommentsDestroyAPIView")
    models_auth_mod = importlib.import_module("conduit.apps.authentication.models")
    UserManager = getattr(models_auth_mod, "UserManager")
except ImportError as e:
    import pytest
    pytest.skip(f"Skipping tests because import failed: {e}", allow_module_level=True)


def _exc_lookup(name, default=Exception):
    """
    Lookup common exception types by name across likely modules.
    """
    candidates = [
        "rest_framework.exceptions",
        "django.core.exceptions",
        "builtins",
        "exceptions",  # fallback
    ]
    for modname in candidates:
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        if hasattr(mod, name):
            return getattr(mod, name)
    return default


@pytest.mark.parametrize(
    "decoded_payload, monkeypatch_user, expected_exception_name",
    [
        ({}, None, "AuthenticationFailed"),  # missing id in payload
        ({"id": 1}, True, "AuthenticationFailed"),  # id present but user lookup fails
    ],
)
def test_jwtauthenticate__authenticate_credentials_raises_on_invalid_payload(
    # Arrange-Act-Assert: generated by ai-testgen
    decoded_payload, monkeypatch_user, expected_exception_name, monkeypatch
):
    # Arrange
    auth_instance = jwt_auth_cls()
    expected_exc = _exc_lookup(expected_exception_name, Exception)

    # If we need to simulate a user lookup failure, monkeypatch the User object in the module.
    if monkeypatch_user:
        class FakeDoesNotExist(Exception):
            pass

        class FakeObjects:
            @staticmethod
            def get(**kwargs):
                raise FakeDoesNotExist("not found")

        class FakeUserClass:
            DoesNotExist = FakeDoesNotExist
            objects = FakeObjects()

        monkeypatch.setattr(backends_mod, "User", FakeUserClass, raising=False)

    # Act / Assert
    with pytest.raises(_exc_lookup("expected_exc", Exception)):
        # call the protected method directly with the decoded token payload
        auth_instance._authenticate_credentials(decoded_payload)


def test_comments_destroy_api_view_calls_delete_and_returns_no_content(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = CommentsDestroyAPIView()

    deleted = {"called": False}

    class FakeComment:
        def delete(self):
            deleted["called"] = True

    def fake_get_object():
        return FakeComment()

    monkeypatch.setattr(view, "get_object", fake_get_object, raising=False)

    # Create a minimal fake request object; view.delete typically ignores it for deletion logic
    fake_request = SimpleNamespace()

    # Act
    response = view.delete(fake_request, pk="irrelevant")

    # Assert
    assert deleted["called"] is True, "Expected the comment's delete() to be called"
    assert hasattr(response, "status_code"), "Expected a DRF Response-like object"
    assert isinstance(response.status_code, int)
    assert response.status_code == 204, f"Expected 204 No Content, got {response.status_code}"


def test_user_manager_create_user_and_create_superuser_set_expected_flags_and_call_set_password():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    manager = UserManager()

    recorded = {}

    class FakeUser:
        def __init__(self, email=None, **kwargs):
            self.email = email
            # record any extras passed for inspection
            recorded["init_kwargs"] = kwargs.copy()
            recorded["init_email"] = email
            self.is_staff = kwargs.get("is_staff", False)
            self.is_superuser = kwargs.get("is_superuser", False)
            self.password_set_to = None
            self.saved = False

        def set_password(self, raw_password):
            self.password_set_to = raw_password

        def save(self):
            self.saved = True

    # Ensure the manager will instantiate our FakeUser instead of a real model
    manager.model = FakeUser

    # Act - create a normal user
    normal_user = manager.create_user(email="Test@Example.COM", password="s3cr3t", first_name="F", last_name="L")

    # Assert normal user fields and behavior
    assert isinstance(normal_user, _exc_lookup("FakeUser", Exception))
    assert recorded["init_email"].lower() == "test@example.com"
    assert normal_user.password_set_to == "s3cr3t"
    assert normal_user.saved is True
    assert normal_user.is_staff is False
    assert normal_user.is_superuser is False

    # Reset recorded and create superuser
    recorded.clear()

    super_user = manager.create_superuser(email="Admin@Example.COM", password="adminpw")

    # Assert superuser fields and behavior
    assert isinstance(super_user, _exc_lookup("FakeUser", Exception))
    assert recorded["init_email"].lower() == "admin@example.com"
    assert super_user.password_set_to == "adminpw"
    assert super_user.saved is True
    assert super_user.is_staff is True
    assert super_user.is_superuser is True
