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
    import types
    import inspect
    import json
    import pytest

    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.renderers as auth_renderers
    import conduit.apps.authentication.serializers as auth_serializers
    import conduit.apps.authentication.signals as auth_signals
    import conduit.apps.core.exceptions as core_exceptions
    import conduit.apps.core.utils as core_utils
    import conduit.apps.profiles.models as profiles_models
    import rest_framework.exceptions as rest_exceptions
except ImportError as e:
    import pytest
    pytest.skip("Skipping tests due to ImportError: %s" % e, allow_module_level=True)


def test_get_short_name_and_generate_jwt_token(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    dummy_user = types.SimpleNamespace(pk=42, username="alice")
    # Ensure jwt.encode used inside _generate_jwt_token returns a predictable value
    def fake_encode(payload, key, algorithm="HS256"):
        # return bytes to emulate common jwt implementations
        return b"fake.jwt.token"
    monkeypatch.setattr(auth_models, "jwt", types.SimpleNamespace(encode=fake_encode))
    # Act
    get_short_name_fn = getattr(auth_models.User, "get_short_name")
    short_name = get_short_name_fn(dummy_user)
    token_fn = getattr(auth_models.User, "_generate_jwt_token")
    token = token_fn(dummy_user)
    # Assert
    assert isinstance(short_name, _exc_lookup("str", Exception))
    assert short_name == "alice"
    assert isinstance(token, (str, bytes))
    token_str = token.decode() if isinstance(token, _exc_lookup("bytes", Exception)) else token
    assert "fake.jwt.token" in token_str


def test_userjsonrenderer_render_roundtrip():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = auth_renderers.UserJSONRenderer()
    payload = {"user": {"email": "u@example.com", "username": "bob", "token": "T"}}
    # Act
    rendered = renderer.render(payload, media_type="application/json", renderer_context={})
    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    decoded = rendered.decode("utf-8")
    parsed = json.loads(decoded)
    assert parsed == payload


@pytest.mark.parametrize(
    "input_data",
    [
        ({"email": "x@y.com", "username": "x", "password": "secure"}),
        ({"email": "test@domain.com", "username": "tester", "password": "p@55W0rd"}),
    ],
)
def test_registration_serializer_validate_returns_dict(input_data):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer_cls = auth_serializers.RegistrationSerializer
    serializer = serializer_cls()
    # Act
    validated = serializer.validate(input_data.copy())
    # Assert
    assert isinstance(validated, _exc_lookup("dict", Exception))
    # essential keys preserved
    assert "email" in validated and validated["email"] == input_data["email"]
    assert "username" in validated and validated["username"] == input_data["username"]


def test_create_related_profile_calls_profile_create(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    called = {}
    def fake_create(**kwargs):
        called["kwargs"] = kwargs
        return types.SimpleNamespace(**kwargs)
    # Ensure Profile.objects.create exists and is patched
    profile_mod = profiles_models
    if not hasattr(profile_mod, "Profile"):
        pytest.fail("profiles.models.Profile not present")
    # patch the manager create method
    manager = types.SimpleNamespace(create=fake_create)
    monkeypatch.setattr(profile_mod.Profile, "objects", manager, raising=False)
    dummy_user = types.SimpleNamespace(pk=77)
    handler = auth_signals.create_related_profile
    # Act
    handler(sender=auth_models.User, instance=dummy_user, created=True)
    # Assert
    assert "kwargs" in called
    # typical signal creates profile with user association
    assert any(v is dummy_user for v in called["kwargs"].values())


@pytest.mark.parametrize("exc_instance, expected_status_range", [
    (rest_exceptions.NotFound("missing"), (400, 499)),
    (rest_exceptions.PermissionDenied("nope"), (400, 599)),
    (Exception("server"), (500, 599)),
])
def test_core_exception_handler_and_internal_handlers(exc_instance, expected_status_range):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    context = {}
    # Act
    resp = core_exceptions.core_exception_handler(exc_instance, context)
    # Assert
    # Response-like object should have status_code and data
    assert hasattr(resp, "status_code")
    assert hasattr(resp, "data")
    status = resp.status_code
    lo, hi = expected_status_range
    assert lo <= status <= hi
    # generic internal handlers produce response-like object
    generic_resp = core_exceptions._handle_generic_error(Exception("x"))
    notfound_resp = core_exceptions._handle_not_found_error(rest_exceptions.NotFound("y"))
    assert hasattr(generic_resp, "status_code") and hasattr(generic_resp, "data")
    assert hasattr(notfound_resp, "status_code") and hasattr(notfound_resp, "data")
    assert isinstance(generic_resp.status_code, int)
    assert isinstance(notfound_resp.status_code, int)
    assert generic_resp.status_code >= 400
    assert notfound_resp.status_code == 404 or (400 <= notfound_resp.status_code < 500)


@pytest.mark.parametrize("length", [1, 5, 12, 32])
def test_generate_random_string_lengths(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange / Act
    result = core_utils.generate_random_string(length)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    # characters are alphanumeric (common expectation)
    import string as _string
    allowed = set(_string.ascii_letters + _string.digits)
    assert set(result).issubset(allowed)


@pytest.mark.parametrize("bad_length", [-1, 0])
def test_generate_random_string_invalid_lengths(bad_length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange / Act / Assert
    with pytest.raises(_exc_lookup("Exception", Exception)):
        core_utils.generate_random_string(bad_length)


class _RelSet:
    def __init__(self):
        self._s = set()
    def add(self, item):
        self._s.add(item)
    def remove(self, item):
        self._s.discard(item)
    def all(self):
        return list(self._s)
    def __contains__(self, item):
        return item in self._s

class FakeProfile:
    def __init__(self, identifier):
        self.id = identifier
        self.following = _RelSet()
        self.followers = _RelSet()
    def save(self):
        pass
    def __repr__(self):
        return f"<FakeProfile {self.id}>"

def _get_callable_for(name):
    # Prefer method on Profile class, fall back to module-level function
    if hasattr(profiles_models, "Profile") and hasattr(profiles_models.Profile, name):
        return lambda a, b: getattr(profiles_models.Profile, name)(a, b)
    if hasattr(profiles_models, name):
        return getattr(profiles_models, name)
    raise AttributeError(f"No callable {name} found in profiles module or Profile class")


def test_follow_unfollow_and_is_following_behavior():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    follower = FakeProfile("A")
    followee = FakeProfile("B")
    follow_callable = _get_callable_for("follow")
    unfollow_callable = _get_callable_for("unfollow")
    is_following_callable = _get_callable_for("is_following")
    # Act: follow
    follow_callable(follower, followee)
    # Assert follow relationship established at least on follower.following
    assert followee in follower.following or followee in follower.following._s or any(followee is p for p in follower.following.all())
    # Act: is_following should be True
    assert is_following_callable(follower, followee) is True
    # Act: unfollow
    unfollow_callable(follower, followee)
    # Assert: no longer following
    assert not is_following_callable(follower, followee)
    # Edge: cannot follow self (should not add)
    follow_callable(follower, follower)
    assert not is_following_callable(follower, follower) or (follower in follower.following and False), "Self-follow should be either no-op or explicitly disallowed"
