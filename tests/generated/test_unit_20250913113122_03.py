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

import pytest

try:
    import time
    import datetime
    import json
    import string as _string
    import re
    from types import SimpleNamespace

    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication.models import User
    import conduit.apps.authentication.models as auth_models_module
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.signals import create_related_profile
    import conduit.apps.core.exceptions as core_exceptions_module
except ImportError as _err:  # pragma: no cover
    pytest.skip("Required application modules not available: %r" % (_err,), allow_module_level=True)


def _exc_lookup(name, fallback):
    """Attempt to find an exception type by name across common exception modules, fallback otherwise."""
    try:
        import rest_framework.exceptions as rf_exc
        return getattr(rf_exc, name)
    except Exception:
        return fallback


@pytest.mark.parametrize("length", [1, 5, 32])
def test_generate_random_string_length_and_charset(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    allowed_chars = set(_string.ascii_letters + _string.digits + _string.punctuation)
    # Act
    result = generate_random_string(length)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    # All characters should be printable; be lenient to accept ascii letters/digits/punctuation/space
    for ch in result:
        assert ch in allowed_chars or ch in _string.whitespace


def test_user_get_short_name_uses_username_when_present():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_cls = User
    user = object.__new__(user_cls)
    setattr(user, "username", "alice_in_wonderland")
    # Act
    short = user.get_short_name()
    # Assert
    assert isinstance(short, _exc_lookup("str", Exception))
    assert short == "alice_in_wonderland"


def test_user_get_short_name_falls_back_to_full_name_if_username_empty():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_cls = User
    user = object.__new__(user_cls)
    setattr(user, "username", "")
    setattr(user, "first_name", "Alice")
    setattr(user, "last_name", "Liddell")

    # Provide get_full_name if implementation expects it
    if not hasattr(user, "get_full_name"):
        def _get_full_name():
            return "Alice Liddell"
        setattr(user, "get_full_name", _get_full_name)

    # Act
    short = user.get_short_name()
    # Assert
    assert isinstance(short, _exc_lookup("str", Exception))
    assert short in ("Alice Liddell", "Alice")  # accept either full or first name depending on implementation


def test__generate_jwt_token_encodes_expected_payload(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    recorded = {}

    def fake_jwt_encode(payload, secret, algorithm="HS256"):
        recorded['payload'] = payload
        recorded['secret'] = secret
        recorded['algorithm'] = algorithm
        return "SIGNED.TOKEN.STRING"

    # Monkeypatch jwt.encode used in the authentication models module
    monkeypatch.setattr(auth_models_module, "jwt", SimpleNamespace(encode=fake_jwt_encode))

    user_cls = User
    user = object.__new__(user_cls)
    setattr(user, "id", 12345)
    setattr(user, "pk", 12345)
    # Act
    token = user._generate_jwt_token()
    # Assert
    assert isinstance(token, _exc_lookup("str", Exception))
    assert token == "SIGNED.TOKEN.STRING"
    assert 'payload' in recorded
    assert isinstance(recorded['payload'], dict)
    assert recorded['payload'].get('id') in (12345, None) or recorded['payload'].get('pk') in (12345, None)
    # exp should be an int timestamp in the future
    exp = recorded['payload'].get('exp') or recorded['payload'].get('expiry') or recorded['payload'].get('expires')
    if exp is not None:
        assert isinstance(exp, (int, float))
        assert exp > time.time() - 10  # reasonably in the future or near present


def test_user_json_renderer_returns_bytes_and_contains_keys():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = UserJSONRenderer()
    payload = {"user": {"email": "test@example.com", "username": "tester"}}
    # Act
    rendered = renderer.render(payload)
    # Assert
    assert isinstance(rendered, (bytes, str))
    raw = rendered if isinstance(rendered, _exc_lookup("str", Exception)) else rendered.decode("utf-8")
    assert '"user"' in raw
    assert '"email"' in raw
    assert '"username"' in raw
    # Validate valid JSON
    parsed = json.loads(raw)
    assert isinstance(parsed, _exc_lookup("dict", Exception))
    assert "user" in parsed
    assert parsed["user"]["email"] == "test@example.com"


def test_create_related_profile_calls_profile_create_only_when_created(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    calls = {"created": 0}

    class FakeObjects:
        def create(self, **kwargs):
            calls["created"] += 1
            calls["last_kwargs"] = kwargs
            return SimpleNamespace(**kwargs)

    class FakeProfile:
        objects = FakeObjects()

    monkeypatch.setattr("conduit.apps.authentication.signals.Profile", FakeProfile, raising=False)
    dummy_user = SimpleNamespace(id=99, username="bob")

    # Act: when created=True should call create
    create_related_profile(sender=None, instance=dummy_user, created=True)
    # Assert
    assert calls["created"] == 1
    assert calls["last_kwargs"]["user"] is dummy_user

    # Act: when created=False should NOT call create
    create_related_profile(sender=None, instance=dummy_user, created=False)
    # Assert no additional calls
    assert calls["created"] == 1


@pytest.mark.parametrize("exc_instance, expected_min_status", [
    (Exception("generic error"), 400),
])
def test_handle_generic_error_returns_response_like_object(exc_instance, expected_min_status):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    handler = getattr(core_exceptions_module, "_handle_generic_error", None)
    assert handler is not None
    # Act
    resp = handler(exc_instance, {})
    # Assert response-like object: has status_code int >= expected_min_status and contains detail content
    assert hasattr(resp, "status_code")
    assert isinstance(resp.status_code, int)
    assert resp.status_code >= expected_min_status
    # Try to obtain textual content or data
    detail_text = None
    if hasattr(resp, "data"):
        detail_text = json.dumps(resp.data) if not isinstance(resp.data, str) else resp.data
    elif hasattr(resp, "content"):
        try:
            detail_text = resp.content.decode("utf-8") if isinstance(resp.content, (bytes, bytearray)) else str(resp.content)
        except Exception:
            detail_text = str(resp.content)
    assert detail_text is not None
    assert "detail" in detail_text or "error" in detail_text or "message" in detail_text.lower() or "internal" in detail_text.lower() or resp.status_code >= 500
