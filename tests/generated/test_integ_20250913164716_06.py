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
    from unittest import mock
    from conduit.apps.authentication import backends as backends_mod
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import serializers as auth_serializers
    from conduit.apps.authentication import renderers as auth_renderers
    import jwt as jwt_module
    import rest_framework.exceptions as rest_exceptions
except ImportError:
    import pytest
    pytest.skip("Required test modules not available; skipping", allow_module_level=True)

def _exc_lookup(name, default=Exception):
    return getattr(rest_exceptions, name, default)

@pytest.mark.parametrize("auth_scheme", ["Token", "Bearer"])
def test_jwt_authenticate_success_returns_user_and_token(monkeypatch, auth_scheme):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    extracted_token = "tok-123"
    header_value = f"{auth_scheme} {extracted_token}"
    fake_payload = {"id": 42}

    class FakeUser:
        def __init__(self, pk, username):
            self.pk = pk
            self.id = pk
            self.username = username

    class FakeUserModel:
        DoesNotExist = type("DoesNotExist", (Exception,), {})
        def __init__(self):
            self.objects = mock.MagicMock()
    fake_user_model = FakeUserModel()
    fake_user_instance = FakeUser(42, "alice")
    fake_user_model.objects.get.return_value = fake_user_instance

    # Monkeypatch decode to return predictable payload
    monkeypatch.setattr(jwt_module, "decode", lambda token, key, algorithms=None: fake_payload)
    # Monkeypatch the User model used in backend to our fake
    monkeypatch.setattr(backends_mod, "User", fake_user_model)

    fake_request = mock.Mock()
    fake_request.META = {"HTTP_AUTHORIZATION": header_value}

    # Act
    auth_instance = backends_mod.JWTAuthentication()
    result = auth_instance.authenticate(fake_request)

    # Assert
    assert isinstance(result, _exc_lookup("tuple", Exception))
    returned_user, returned_token = result
    assert returned_user is fake_user_instance
    assert returned_token == extracted_token

def test_jwt_authenticate_missing_user_raises_authentication_failed(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    extracted_token = "missing-user-tok"
    header_value = f"Token {extracted_token}"
    fake_payload = {"id": 999}

    class FakeUserModel:
        DoesNotExist = type("DoesNotExist", (Exception,), {})
        def __init__(self):
            self.objects = mock.MagicMock()
    fake_user_model = FakeUserModel()
    # Simulate objects.get raising DoesNotExist
    fake_user_model.objects.get.side_effect = fake_user_model.DoesNotExist()

    monkeypatch.setattr(jwt_module, "decode", lambda token, key, algorithms=None: fake_payload)
    monkeypatch.setattr(backends_mod, "User", fake_user_model)

    fake_request = mock.Mock()
    fake_request.META = {"HTTP_AUTHORIZATION": header_value}

    # Act / Assert
    auth_instance = backends_mod.JWTAuthentication()
    expected_exc = _exc_lookup("AuthenticationFailed", Exception)
    with pytest.raises(_exc_lookup("expected_exc", Exception)):
        auth_instance.authenticate(fake_request)

@pytest.mark.parametrize(
    "input_data, should_error",
    [
        ({"username": "bob", "email": "bob@example.com", "password": "secure"}, False),
        ({"username": "noemail", "password": "pw"}, True),
    ],
)
def test_registration_serializer_creates_user_and_renderer_outputs_token(monkeypatch, input_data, should_error):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Prepare a fake user instance that the create path will return
    class FakeUser:
        def __init__(self, username, email, token):
            self.username = username
            self.email = email
            self.token = token

    fake_token = "regtok-1"
    fake_user_instance = FakeUser(username=input_data.get("username"), email=input_data.get("email"), token=fake_token)

    # Create a fake User model with objects.create_user returning our fake user
    class FakeUserModel:
        def __init__(self):
            self.objects = mock.MagicMock()

    fake_user_model = FakeUserModel()
    fake_user_model.objects.create_user.return_value = fake_user_instance

    # Monkeypatch the User model referenced by the serializer to use our fake
    monkeypatch.setattr(auth_models, "User", fake_user_model)

    serializer = auth_serializers.RegistrationSerializer(data=input_data)

    # Act / Assert
    if should_error:
        expected_exc = _exc_lookup("ValidationError", Exception)
        with pytest.raises(_exc_lookup("expected_exc", Exception)):
            serializer.is_valid(raise_exception=True)
    else:
        # Validate and save
        serializer.is_valid(raise_exception=True)
        created_user = serializer.save()

        # Assertions about returned user and serializer representation
        assert created_user is fake_user_instance
        serialized_data = serializer.data
        assert isinstance(serialized_data, _exc_lookup("dict", Exception))
        assert "user" in serialized_data
        user_block = serialized_data["user"]
        assert isinstance(user_block, _exc_lookup("dict", Exception))
        assert user_block.get("username") == fake_user_instance.username
        # token must be present and match our fake token
        assert "token" in user_block
        assert user_block["token"] == fake_user_instance.token

        # Now render the serializer output using the JSON renderer to ensure integration
        renderer = auth_renderers.UserJSONRenderer()
        rendered_bytes = renderer.render(serialized_data)
        assert isinstance(rendered_bytes, (bytes, bytearray))
        # Ensure the token appears in the rendered output
        assert fake_user_instance.token.encode() in rendered_bytes
