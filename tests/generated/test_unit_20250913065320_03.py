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
# If a target import fails, skip the whole module rather than passing silently.
try:
    pass
except ImportError as _e:
    import pytest as _pytest; _pytest.skip(str(_e), allow_module_level=True)
from types import SimpleNamespace

try:
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.core import exceptions as core_exceptions
    from conduit.apps.authentication import renderers as auth_renderers
    from conduit.apps.authentication import signals as auth_signals
except ImportError:
    pytest.skip("Required target modules not available", allow_module_level=True)


@pytest.mark.parametrize("length", [0, 1, 8, 64])
def test_generate_random_string_returns_expected_length_and_chars(length):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    requested_length = length
    # Act
    result = generate_random_string(requested_length)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == requested_length
    # All characters must be alphanumeric (letters or digits)
    assert all(ch.isalnum() for ch in result)


def test__generate_jwt_token_uses_jwt_encode_with_user_id_and_returns_token(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    called = {}
    def fake_encode(payload, key, algorithm="HS256"):
        called['payload'] = payload
        called['key'] = key
        called['algorithm'] = algorithm
        return "FAKE.JWT.TOKEN"

    # monkeypatch jwt in the module where function is defined
    monkeypatch.setattr(auth_models, "jwt", SimpleNamespace(encode=fake_encode), raising=False)

    # Create a dummy user-like object with a primary key attribute used for token payload
    dummy_user = SimpleNamespace(pk=123, id=123, email="u@example.test")

    # Act
    # _generate_jwt_token may be a standalone function or a method on User class.
    if hasattr(auth_models, "_generate_jwt_token"):
        token = auth_models._generate_jwt_token(dummy_user)
    else:
        # try as attribute on User class
        token = auth_models.User._generate_jwt_token(dummy_user)

    # Assert
    assert token == "FAKE.JWT.TOKEN"
    assert 'payload' in called
    # Expect the payload to include some user identifier - either id or pk
    payload = called['payload']
    assert isinstance(payload, _exc_lookup("dict", Exception))
    assert any(key in payload for key in ("id", "user_id", "pk"))
    assert called['algorithm'] in ("HS256", None,)


def test_get_short_name_prefers_username_and_fallbacks_to_email_or_repr():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    # The get_short_name might be implemented as a method on the User class or a module-level function.
    # Prepare a simple object with attributes to exercise the method.
    short_name_obj = SimpleNamespace(username="shorty", email="x@y.test")
    no_username_obj = SimpleNamespace(username="", email="z@y.test")
    no_identifiers = SimpleNamespace()

    # Determine callable to test
    if hasattr(auth_models, "get_short_name"):
        getter = auth_models.get_short_name
    else:
        # Use User.get_short_name bound function from the User class
        getter = auth_models.User.get_short_name

    # Act / Assert - with username
    result_with_username = getter(short_name_obj)
    assert isinstance(result_with_username, _exc_lookup("str", Exception))
    assert result_with_username == "shorty"

    # Act / Assert - without username but with email
    result_with_email = getter(no_username_obj)
    assert isinstance(result_with_email, _exc_lookup("str", Exception))
    assert "@" in result_with_email or result_with_email == "z@y.test"

    # Act / Assert - with no identifying attrs should return string representation
    result_repr = getter(no_identifiers)
    assert isinstance(result_repr, _exc_lookup("str", Exception))


@pytest.mark.parametrize("exc_instance,expected_handler_attr", [
    (type("NotFoundLike", (Exception,), {"status_code": 404})(), "_handle_not_found_error"),
    (Exception("generic"), "_handle_generic_error"),
])
def test_core_exception_handler_delegates_to_specific_handlers(monkeypatch, exc_instance, expected_handler_attr):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    called = {"not_found": False, "generic": False}
    def fake_not_found(exc, context):
        called["not_found"] = True
        return {"handled": "not_found"}
    def fake_generic(exc, context):
        called["generic"] = True
        return {"handled": "generic"}

    # Patch the internal handler functions
    monkeypatch.setattr(core_exceptions, "_handle_not_found_error", fake_not_found, raising=False)
    monkeypatch.setattr(core_exceptions, "_handle_generic_error", fake_generic, raising=False)

    # Act
    response = core_exceptions.core_exception_handler(exc_instance, context={})

    # Assert
    assert isinstance(response, _exc_lookup("dict", Exception))
    if expected_handler_attr == "_handle_not_found_error":
        assert called["not_found"] is True
        assert response.get("handled") == "not_found"
    else:
        assert called["generic"] is True
        assert response.get("handled") == "generic"


def test_auth_render_renders_user_structure():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    renderer = auth_renderers.UserJSONRenderer()
    payload = {"user": {"email": "a@b.test", "username": "u"}}
    # Act
    rendered = renderer.render(payload, accepted_media_type=None, renderer_context=None)
    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    assert b'"user"' in rendered or b"'user'" in rendered
    assert b"email" in rendered


def test_create_related_profile_creates_profile_when_created_true(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    created_calls = {}
    class FakeProfileManager:
        def create(self, **kwargs):
            created_calls['called'] = True
            created_calls['kwargs'] = kwargs
            return "PROFILE"

    fake_profile_model = SimpleNamespace(objects=FakeProfileManager())

    # Monkeypatch the Profile reference inside the signals module to our fake
    monkeypatch.setattr(auth_signals, "Profile", fake_profile_model, raising=False)

    fake_user = SimpleNamespace(pk=77)
    # Act
    auth_signals.create_related_profile(sender=object, instance=fake_user, created=True)
    # Assert
    assert created_calls.get('called', False) is True
    assert created_calls['kwargs'].get('user') == fake_user
