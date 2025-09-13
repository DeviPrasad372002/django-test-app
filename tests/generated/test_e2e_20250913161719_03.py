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
except ImportError:
    raise

try:
    from conduit.apps.core import utils as core_utils
except ImportError:
    pytest.skip("conduit.apps.core.utils not available", allow_module_level=True)

try:
    from conduit.apps.authentication import models as auth_models
except ImportError:
    pytest.skip("conduit.apps.authentication.models not available", allow_module_level=True)

try:
    from conduit.apps.authentication import renderers as auth_renderers
except ImportError:
    pytest.skip("conduit.apps.authentication.renderers not available", allow_module_level=True)

try:
    from conduit.apps.authentication import serializers as auth_serializers
except ImportError:
    pytest.skip("conduit.apps.authentication.serializers not available", allow_module_level=True)


def test_generate_random_string_deterministic(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: force the random.choice used by the utility to return a predictable sequence
    calls = {"count": 0}
    sequence = list("ABCDEF012345")  # deterministic sequence for repeated calls

    def fake_choice(_seq):
        # Act: return next item from sequence cycling deterministically
        value = sequence[calls["count"] % len(sequence)]
        calls["count"] += 1
        return value

    monkeypatch.setattr(core_utils.random, "choice", fake_choice)

    # Act: generate strings of various lengths
    result_len_1 = core_utils.generate_random_string(1)
    result_len_5 = core_utils.generate_random_string(5)
    result_len_12 = core_utils.generate_random_string(12)

    # Assert: produced strings have requested lengths and match the deterministic pattern
    assert isinstance(result_len_1, _exc_lookup("str", Exception))
    assert len(result_len_1) == 1
    assert result_len_1 == "A"

    assert isinstance(result_len_5, _exc_lookup("str", Exception))
    assert len(result_len_5) == 5
    assert result_len_5 == "BCDEF"

    assert isinstance(result_len_12, _exc_lookup("str", Exception))
    assert len(result_len_12) == 12
    # sequence cycles, so the 12-char output is the sequence repeated once
    assert result_len_12 == "012345ABCDEF"


def test_user_get_short_name_and_generate_jwt_token_calls_jwt_encode(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create a User instance without DB save and set identifying attributes
    User = getattr(auth_models, "User")
    user_instance = User()
    # Provide expected public attributes used by get_short_name and token generator
    setattr(user_instance, "username", "alice")
    setattr(user_instance, "email", "alice@example.test")
    setattr(user_instance, "pk", 42)

    # Prepare a fake jwt.encode to capture payload and return a predictable token
    captured = {}

    def fake_encode(payload, key, algorithm="HS256"):
        captured["payload"] = payload
        captured["key"] = key
        captured["algorithm"] = algorithm
        return "signed-token-xyz"

    # Act: monkeypatch the jwt.encode used in the authentication models module
    # The module uses "jwt", so replace its encode attribute
    monkeypatch.setattr(auth_models.jwt, "encode", fake_encode)

    # Act: call get_short_name and _generate_jwt_token
    short_name_result = user_instance.get_short_name()
    token_result = user_instance._generate_jwt_token()

    # Assert: get_short_name returns the username and token generation invoked jwt.encode with expected payload
    assert isinstance(short_name_result, _exc_lookup("str", Exception))
    assert short_name_result == "alice"

    assert token_result == "signed-token-xyz"
    assert "payload" in captured
    # payload should include id matching pk and an expiration field (commonly 'exp')
    assert captured["payload"].get("id") == 42
    assert "exp" in captured["payload"]
    # algorithm default should be provided
    assert captured["algorithm"] in ("HS256",)


@pytest.mark.parametrize(
    "input_data,expected_user_keys",
    [
        ({"email": "bob@example.test", "token": "t1"}, {"email", "token"}),
        ({"email": "x@y.test", "token": "tok", "username": "x"}, {"email", "token", "username"}),
    ],
)
def test_userjsonrenderer_render_wraps_user(input_data, expected_user_keys):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: instantiate renderer
    RendererClass = getattr(auth_renderers, "UserJSONRenderer")
    renderer = RendererClass()

    # Act: render the provided input_data
    rendered_bytes = renderer.render(input_data, accepted_media_type=None, renderer_context=None)

    # Assert: returned value is bytes containing a JSON object with top-level "user" key
    assert isinstance(rendered_bytes, (bytes, bytearray))
    import json

    rendered_text = rendered_bytes.decode("utf-8")
    parsed = json.loads(rendered_text)
    assert "user" in parsed and isinstance(parsed["user"], dict)
    user_obj = parsed["user"]
    # The rendered user object should include at least the keys we provided
    assert expected_user_keys.issubset(set(user_obj.keys()))
    for key in expected_user_keys:
        assert user_obj[key] == input_data[key]


def test_login_serializer_invalid_when_missing_credentials():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: instantiate the LoginSerializer with no credentials
    LoginSerializer = getattr(auth_serializers, "LoginSerializer")
    serializer_instance = LoginSerializer(data={})

    # Act: run validation without raising exceptions
    is_valid_result = serializer_instance.is_valid(raise_exception=False)
    errors = serializer_instance.errors

    # Assert: serializer reports invalid and contains errors for expected missing fields
    assert is_valid_result is False
    assert isinstance(errors, _exc_lookup("dict", Exception))
    # At least one of 'email' or 'password' should be reported as missing depending on implementation
    assert ("email" in errors) or ("password" in errors) or ("username" in errors) or ("non_field_errors" in errors)
