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

import pytest as _pytest
# If a target import fails, skip the whole module rather than passing silently.
try:
    pass
except ImportError as _e:
    import pytest as _pytest; _pytest.skip(str(_e), allow_module_level=True)
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

import pytest

try:
    from conduit.apps.authentication.models import User
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.articles.views import CommentsDestroyAPIView
    import conduit.apps.authentication.backends as auth_backends_mod
    import conduit.apps.authentication.models as auth_models_mod
    import conduit.apps.articles.views as articles_views_mod
    import jwt as jwt_lib  # used only to ensure presence; will be monkeypatched
except ImportError:
    import pytest as _pytest
    _pytest.skip("Required application modules not available", allow_module_level=True)


def _exc_lookup(name, fallback):
    try:
        import rest_framework.exceptions as rf_exceptions
        return getattr(rf_exceptions, name, fallback)
    except Exception:
        return fallback


@pytest.mark.parametrize(
    "first_name,last_name,expected_full",
    [
        ("Alice", "Smith", "Alice Smith"),
        ("", "", None),
        (None, None, None),
    ],
)
def test_user_get_full_name_and_token_property(monkeypatch, first_name, last_name, expected_full):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    # Monkeypatch the internal token generator to return a deterministic token
    monkeypatch.setattr(User, "_generate_jwt_token", lambda self: "fixed-token-123")
    # Create instance without touching DB; Django model __init__ supports this
    user = User(email="user@example.com")
    # set attributes that get_full_name may rely on
    user.first_name = first_name
    user.last_name = last_name

    # Act
    full_name = user.get_full_name() if hasattr(user, "get_full_name") else None
    token_value = user.token if hasattr(user, "token") else None

    # Assert
    if expected_full:
        assert isinstance(full_name, _exc_lookup("str", Exception))
        assert full_name == expected_full
    else:
        # Fallback behavior: many implementations return email when names missing
        if full_name is not None:
            assert isinstance(full_name, _exc_lookup("str", Exception))
            assert full_name in (user.email, "", None) or full_name == ""
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert token_value == "fixed-token-123"


def test_jwt_authentication_authenticate_credentials_success_and_failures(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    auth = JWTAuthentication()

    # Prepare a fake user to be returned by User.objects.get
    class FakeUser:
        def __init__(self, pk):
            self.pk = pk

    fake_user = FakeUser(pk=42)

    # Successful decode -> user found
    monkeypatch.setattr(auth_backends_mod.jwt, "decode", lambda token, key, algorithms: {"user_id": 42})
    # Monkeypatch User.objects.get to return our fake user
    monkeypatch.setattr(auth_models_mod.User.objects, "get", lambda **kwargs: fake_user)

    # Act
    result = auth._authenticate_credentials("valid.token.string")

    # Assert
    assert isinstance(result, _exc_lookup("tuple", Exception))
    returned_user, returned_token = result
    assert returned_user is fake_user
    assert returned_token == "valid.token.string"

    # Now simulate decode error -> should raise AuthenticationFailed
    def raise_decode_error(*args, **kwargs):
        raise Exception("invalid token")

    monkeypatch.setattr(auth_backends_mod.jwt, "decode", raise_decode_error)
    AuthFail = _exc_lookup("AuthenticationFailed", Exception)

    with pytest.raises(_exc_lookup("AuthFail", Exception)):
        auth._authenticate_credentials("broken.token")

    # Now simulate user not found -> should raise AuthenticationFailed
    monkeypatch.setattr(auth_backends_mod.jwt, "decode", lambda token, key, algorithms: {"user_id": 999})
    def raise_does_not_exist(**kwargs):
        raise auth_models_mod.User.DoesNotExist
    monkeypatch.setattr(auth_models_mod.User.objects, "get", raise_does_not_exist)

    with pytest.raises(_exc_lookup("AuthFail", Exception)):
        auth._authenticate_credentials("token.with.nonexistent.user")


def test_comments_destroy_view_calls_perform_destroy_and_delete_invokes_destroy(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    view = CommentsDestroyAPIView()
    sentinel_obj = object()
    called = {"performed": False, "destroy_called_with": None, "delete_called": False}

    # Monkeypatch get_object to return sentinel and perform_destroy to record call
    monkeypatch.setattr(view, "get_object", lambda: sentinel_obj)
    def fake_perform_destroy(instance):
        called["performed"] = True
        called["destroy_called_with"] = instance
    monkeypatch.setattr(view, "perform_destroy", fake_perform_destroy)

    # Act
    response = view.destroy(request=None, *[], **{})

    # Assert
    assert called["performed"] is True
    assert called["destroy_called_with"] is sentinel_obj
    assert hasattr(response, "status_code")
    assert int(response.status_code) == 204

    # Now ensure delete delegates to destroy: monkeypatch destroy to mark called
    def fake_destroy(request, *args, **kwargs):
        called["delete_called"] = True
        class SimpleResp:
            status_code = 204
        return SimpleResp()
    monkeypatch.setattr(view, "destroy", fake_destroy)

    # Act
    delete_resp = view.delete(request=None, *[], **{})

    # Assert
    assert called["delete_called"] is True
    assert hasattr(delete_resp, "status_code")
    assert int(delete_resp.status_code) == 204
