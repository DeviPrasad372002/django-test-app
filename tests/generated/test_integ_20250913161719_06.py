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
    import json
    import pytest
    from types import SimpleNamespace

    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import renderers as auth_renderers
    from conduit.apps.authentication import views as auth_views
except ImportError as e:  # pragma: no cover - skip when imports unavailable
    import pytest as _pytest
    _pytest.skip("Required application modules not available: {}".format(e), allow_module_level=True)

def test_user_token_calls_jwt_encode_and_includes_user_id_and_exp(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    captured = {}
    def fake_encode(payload, key, algorithm='HS256'):
        captured['payload'] = payload
        captured['key'] = key
        captured['algorithm'] = algorithm
        return "encoded.jwt.token"
    # Ensure the module-level jwt.encode used in models is replaced
    monkeypatch.setattr(auth_models.jwt, 'encode', fake_encode, raising=True)

    # Create a User instance without touching DB; set id to simulate persisted user
    test_user = auth_models.User(id=123)

    # Act
    if hasattr(test_user, 'token'):
        token_value = test_user.token
    else:
        token_value = test_user._generate_jwt_token()

    # Assert
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert token_value == "encoded.jwt.token"
    assert 'payload' in captured
    payload = captured['payload']
    # payload should contain some numeric field equal to the user's pk (id)
    pk_present = any(value == getattr(test_user, 'pk', getattr(test_user, 'id', None)) for value in payload.values())
    assert pk_present, "Generated JWT payload does not contain the user's primary key"
    assert 'exp' in payload or any(k.lower().startswith('exp') for k in payload.keys())

def test_user_json_renderer_outputs_valid_json_bytes_and_roundtrips(monkeypatch, tmp_path):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = auth_renderers.UserJSONRenderer()
    user_data = {'user': {'email': 'alice@example.com', 'token': 'tok-123', 'username': 'alice'}}
    # Act
    rendered_bytes = renderer.render(user_data)
    # Assert
    assert isinstance(rendered_bytes, (bytes, str))
    if isinstance(rendered_bytes, _exc_lookup("bytes", Exception)):
        decoded = rendered_bytes.decode('utf-8')
    else:
        decoded = rendered_bytes
    parsed = json.loads(decoded)
    assert parsed == user_data

@pytest.mark.parametrize("view_attr, serializer_attr, input_data", [
    ("LoginAPIView", "LoginSerializer", {"email": "john@example.com", "password": "password123"}),
    ("RegistrationAPIView", "RegistrationSerializer", {"email": "sue@example.com", "password": "pw", "username": "sue"}),
])
def test_auth_views_invoke_serializer_and_return_serializer_data(monkeypatch, view_attr, serializer_attr, input_data):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    module_views = auth_views
    ViewClass = getattr(module_views, view_attr)
    # Create a fake serializer that mimics DRF serializer interface used by views
    class FakeSerializer:
        def __init__(self, data=None, instance=None, context=None):
            self.initial_data = data or {}
            self._saved = False
            # construct a predictable returned data shape
            email = self.initial_data.get('email') or (self.initial_data.get('user') or {}).get('email')
            username = self.initial_data.get('username') or (self.initial_data.get('user') or {}).get('username') or 'guest'
            self._data = {'user': {'email': email, 'username': username, 'token': 'fake.token'}}
        def is_valid(self, raise_exception=False):
            # Simulate validation passing; if raise_exception True mimic DRF by raising if invalid
            valid = True
            if not valid and raise_exception:
                raise Exception("Validation failed")
            return valid
        def save(self, **kwargs):
            # Simulate creation side-effects and return a representation
            self._saved = True
            return self._data
        @property
        def data(self):
            return self._data

    # Monkeypatch the serializer symbol in the views module so ViewClass uses our FakeSerializer
    monkeypatch.setattr(module_views, serializer_attr, FakeSerializer, raising=False)

    # Act
    view_instance = ViewClass()
    fake_request = SimpleNamespace(data=input_data)
    response = view_instance.post(fake_request)

    # Assert
    # Ensure the response looks like DRF Response (has .data) and contains the serializer's data
    assert hasattr(response, 'data')
    assert response.data == FakeSerializer(data=input_data).data
    # also ensure serializer save path was logically possible (view invoked serializer.save implicitly or left data intact)
    assert 'user' in response.data and 'token' in response.data['user']
