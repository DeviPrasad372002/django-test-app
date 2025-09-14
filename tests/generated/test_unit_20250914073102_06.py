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

    
# Replace the Django bootstrap section with this simplified version
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
                    return True
            except Exception:
                pass
            return False

        if not _dj_settings.configured:
            _installed = [
                "django.contrib.auth",
                "django.contrib.contenttypes", 
                "django.contrib.sessions"
            ]
            
            if _iu.find_spec("rest_framework"):
                _installed.append("rest_framework")

            # Try to add conduit apps
            for _app in ("conduit.apps.core", "conduit.apps.articles", "conduit.apps.authentication", "conduit.apps.profiles"):
                _maybe_add(_app, _installed)

            _cfg = dict(
                SECRET_KEY="test-key",
                DEBUG=True,
                ALLOWED_HOSTS=["*"],
                INSTALLED_APPS=sorted(set(_installed)),
                DATABASES=dict(default=dict(ENGINE="django.db.backends.sqlite3", NAME=":memory:")),
                MIDDLEWARE=[
                    'django.middleware.security.SecurityMiddleware',
                    'django.contrib.sessions.middleware.SessionMiddleware',
                    'django.middleware.common.CommonMiddleware',
                ],
                USE_TZ=True,
                TIME_ZONE="UTC",
            )
            
            try:
                _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
            except Exception:
                pass

            try:
                _dj_settings.configure(**_cfg)
            except Exception as e:
                # Don't skip module-level, just continue
                pass

        if not _dj_apps.ready:
            try:
                django.setup()
            except Exception as e:
                # Don't skip module-level, just continue
                pass

except Exception as e:
    # Don't skip at module level - let individual tests handle Django issues
    pass

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

try:
    import pytest
    import json
    from types import SimpleNamespace

    import target.conduit.apps.authentication.backends as backends_module
    from target.conduit.apps.authentication.backends import JWTAuthentication
    import target.conduit.apps.authentication.models as models_module
    from target.conduit.apps.authentication.models import User
    from target.conduit.apps.authentication.renderers import UserJSONRenderer
except ImportError:
    import pytest
    pytest.skip("Skipping tests due to missing target modules", allow_module_level=True)


def _exc_lookup(name, default=Exception):
    try:
        import rest_framework.exceptions as rf_ex
        return getattr(rf_ex, name, default)
    except Exception:
        return default


def make_request_with_header(header_value):
    class DummyRequest:
        pass

    req = DummyRequest()
    # Some implementations access META['HTTP_AUTHORIZATION'] and/or headers.get('Authorization')
    req.META = {'HTTP_AUTHORIZATION': header_value} if header_value is not None else {}
    req.headers = {'Authorization': header_value} if header_value is not None else {}
    return req


def test_authenticate_returns_none_when_no_authorization_header():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = JWTAuthentication()
    request = make_request_with_header(None)

    # Act
    result = auth.authenticate(request)

    # Assert
    assert result is None


@pytest.mark.parametrize(
    "auth_header,expected_token",
    [
        ("Token abc123", "abc123"),
        ("Bearer xyz.789", "xyz.789"),
        ("token mixedCASE", "mixedCASE"),
    ],
)
def test_authenticate_parses_token_and_delegates_to_credentials(auth_header, expected_token, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = JWTAuthentication()
    request = make_request_with_header(auth_header)

    captured = {}

    def fake_authenticate_credentials(self, token):
        captured['token'] = token
        return ("fake_user_obj", token)

    monkeypatch.setattr(JWTAuthentication, "_authenticate_credentials", fake_authenticate_credentials)

    # Act
    result = auth.authenticate(request)

    # Assert
    assert result == ("fake_user_obj", expected_token)
    assert captured.get('token') == expected_token


def test__authenticate_credentials_raises_authentication_failed_when_user_missing(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    backend = JWTAuthentication()

    # Make jwt.decode return a payload with an id
    def fake_decode(token, key, algorithms):
        return {"id": 999}

    monkeypatch.setattr(backends_module, "jwt", SimpleNamespace(decode=fake_decode))

    # Ensure User.objects.get raises to simulate missing user
    class DummyManager:
        def get(self, *args, **kwargs):
            raise Exception("not found")

    # Patch the User reference used in the backend module
    monkeypatch.setattr(backends_module, "User", SimpleNamespace(objects=DummyManager()))

    # Act / Assert
    with pytest.raises(_exc_lookup("AuthenticationFailed")):
        backend._authenticate_credentials("doesnotmatter")


def test_user_token_and_name_and_renderer(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_instance = User(username="tester", email="tester@example.com")

    # Monkeypatch jwt.encode in the models module so token generation is deterministic
    def fake_encode(payload, key, algorithm):
        return "signed-token-for-{}".format(payload.get("id", "noid"))

    monkeypatch.setattr(models_module, "jwt", SimpleNamespace(encode=fake_encode))

    # Act
    token_value = user_instance.token
    full_name = user_instance.get_full_name()
    short_name = user_instance.get_short_name()

    # Assert token format and type
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert "signed-token-for" in token_value

    # For this user model the full and short name typically use username or email fallback
    assert isinstance(full_name, _exc_lookup("str", Exception))
    assert isinstance(short_name, _exc_lookup("str", Exception))
    assert full_name == short_name or full_name == user_instance.username

    # Renderer should wrap user representation under top-level "user" key
    renderer = UserJSONRenderer()
    rendered_bytes = renderer.render({"username": "tester", "email": "tester@example.com"})
    assert isinstance(rendered_bytes, (bytes, str))
    if isinstance(rendered_bytes, _exc_lookup("bytes", Exception)):
        rendered_str = rendered_bytes.decode("utf-8")
    else:
        rendered_str = rendered_bytes
    parsed = json.loads(rendered_str)
    assert "user" in parsed
    assert parsed["user"]["username"] == "tester"
    assert parsed["user"]["email"] == "tester@example.com"
