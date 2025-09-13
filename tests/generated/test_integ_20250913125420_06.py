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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from unittest.mock import Mock

    from conduit.apps.authentication.models import User
    from conduit.apps.authentication.serializers import RegistrationSerializer, UserSerializer
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication import backends as auth_backends
    from conduit.apps.authentication import signals as auth_signals
except ImportError as _err:
    import pytest as _pytest
    _pytest.skip(f"Skipping tests: ImportError: {_err}", allow_module_level=True)


@pytest.mark.parametrize("generated_token", ["fixed-token-123", ""])
def test_user_token_property_returns_generated_token(monkeypatch, generated_token):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_instance = User(username="alice", email="alice@example.com")
    monkeypatch.setattr(User, "_generate_jwt_token", lambda self: generated_token)

    # Act
    result_token = user_instance.token

    # Assert
    assert isinstance(result_token, _exc_lookup("str", Exception))
    assert result_token == generated_token


@pytest.mark.parametrize("token_value", ["serializer-token", ""])
def test_user_serializer_to_representation_and_renderer(monkeypatch, token_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    monkeypatch.setattr(User, "_generate_jwt_token", lambda self: token_value)
    fake_user = User(username="bob", email="bob@example.com", bio="bio", image="http://img")
    serializer = UserSerializer(fake_user)

    # Act
    serialized_data = serializer.data
    rendered_bytes = UserJSONRenderer().render({"user": serialized_data})
    rendered_text = rendered_bytes.decode("utf-8")

    # Assert
    assert isinstance(serialized_data, _exc_lookup("dict", Exception))
    assert "email" in serialized_data
    assert "username" in serialized_data
    assert "token" in serialized_data
    assert serialized_data["token"] == token_value
    assert '"user"' in rendered_text
    assert '"token"' in rendered_text
    assert serialized_data["email"] == "bob@example.com"


@pytest.mark.parametrize(
    "payload_map,should_raise",
    [
        ({"id": 10}, False),
        ({"user_id": 20}, False),
        (None, True),
    ],
)
def test_jwtauthentication_authenticate_credentials_variants(monkeypatch, payload_map, should_raise):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    jwt_module_in_backend = auth_backends.jwt

    if payload_map is None:
        def decode_raise(token, key, algorithms):
            raise Exception("invalid token")
        monkeypatch.setattr(auth_backends, "jwt", jwt_module_in_backend)
        monkeypatch.setattr(auth_backends.jwt, "decode", decode_raise)
    else:
        def decode_return(token, key, algorithms):
            return payload_map
        monkeypatch.setattr(auth_backends, "jwt", jwt_module_in_backend)
        monkeypatch.setattr(auth_backends.jwt, "decode", decode_return)

    fake_user = Mock()
    fake_user.is_active = True
    # The backend likely calls User.objects.get; monkeypatch that manager method
    monkeypatch.setattr(auth_backends.User.objects, "get", Mock(return_value=fake_user))

    auth = auth_backends.JWTAuthentication()

    # Act / Assert
    if should_raise:
        with pytest.raises(_exc_lookup("Exception", Exception)):
            auth._authenticate_credentials("sometoken")
    else:
        result = auth._authenticate_credentials("validtoken")
        # method may return tuple (user, token) or user; handle both
        if isinstance(result, _exc_lookup("tuple", Exception)):
            returned_user = result[0]
            returned_token = result[1] if len(result) > 1 else None
            assert returned_user is fake_user
        else:
            assert result is fake_user


@pytest.mark.parametrize(
    "input_data",
    [
        {"username": "charlie", "email": "charlie@example.com", "password": "pass123"},
        {"username": "dave", "email": "dave@example.com", "password": "strong"},
    ],
)
def test_registration_serializer_create_triggers_profile_signal(monkeypatch, input_data):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_user = Mock()
    fake_user.username = input_data["username"]
    fake_user.email = input_data["email"]
    # Patch User.objects.create_user to return our fake user instance
    monkeypatch.setattr(User.objects, "create_user", Mock(return_value=fake_user))
    # Patch signal handler to observe calls
    called = {"count": 0, "args": None, "kwargs": None}

    def fake_create_related_profile(sender, instance=None, created=False, **kwargs):
        called["count"] += 1
        called["args"] = (sender, instance, created)
        called["kwargs"] = kwargs

    monkeypatch.setattr(auth_signals, "create_related_profile", fake_create_related_profile)

    serializer = RegistrationSerializer()

    # Act
    created_user = serializer.create(input_data)

    # Assert
    assert created_user is fake_user
    assert User.objects.create_user.called
    assert called["count"] == 1
    # Ensure the signal handler was called with the created user as instance
    assert called["args"][1] is fake_user
    assert called["args"][2] is True or called["args"][2] is False or isinstance(called["args"][2], bool) is True
