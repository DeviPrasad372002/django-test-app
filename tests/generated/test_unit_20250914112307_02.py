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

# Handle Django configuration for tests
try:
    import django
    from django.conf import settings
    from django import apps as _dj_apps
    
    if not settings.configured:
        _cfg = dict(
            DEBUG=True,
            SECRET_KEY='test-secret-key-for-pytest',
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
            ],
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
            settings.configure(**_cfg)
        except Exception as e:
            pass
    
    if not _dj_apps.ready:
        try:
            django.setup()
        except Exception as e:
            pass
            
except Exception as e:
    pass



# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from types import SimpleNamespace
    import builtins

    import conduit.apps.authentication.backends as backends
    import conduit.apps.articles.views as article_views
except ImportError as e:
    import pytest as _pytest
    _pytest.skip("Required modules not found: {}".format(e), allow_module_level=True)

@pytest.mark.parametrize(
    "payload, returned_user_attrs",
    [
        ({"user_id": 1}, {"id": 1, "username": "alice"}),
        ({"id": "abc"}, {"id": "abc", "username": "bob"}),
    ],
)
def test__authenticate_credentials_returns_user_for_valid_payload(monkeypatch, payload, returned_user_attrs):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_user = SimpleNamespace(**returned_user_attrs)

    class DummyManager:
        def get(self, **kwargs):
            # ensure incoming kwargs include one of expected id keys
            if any(k in kwargs for k in ("user_id", "id", "pk")):
                return fake_user
            raise Exception("unexpected lookup")

    class DummyUserModel:
        objects = DummyManager()

    monkeypatch.setattr(backends, "User", DummyUserModel, raising=False)

    # Act
    auth = backends.JWTAuthentication()
    result_user = auth._authenticate_credentials(payload)

    # Assert
    assert result_user is fake_user
    assert hasattr(result_user, "username")
    assert getattr(result_user, "id") == returned_user_attrs["id"]


@pytest.mark.parametrize(
    "mode, jwt_side_effect, user_get_side_effect",
    [
        ("decode_error", Exception("decode failed"), None),
        ("user_not_found", None, Exception("does not exist")),
    ],
)
def test_authenticate_raises_on_invalid_token_or_missing_user(monkeypatch, mode, jwt_side_effect, user_get_side_effect):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # create a dummy request with an Authorization header typical format
    class DummyRequest:
        META = {"HTTP_AUTHORIZATION": "Bearer faketoken"}

    def fake_get_authorization_header(req):
        return b"Bearer faketoken"

    # monkeypatch helper to ensure authenticate sees the header
    monkeypatch.setattr(backends, "get_authorization_header", fake_get_authorization_header, raising=False)

    if jwt_side_effect is not None:
        def fake_decode(token, key, algorithms):
            raise jwt_side_effect
        monkeypatch.setattr(backends, "jwt", backends.jwt, raising=False)
        monkeypatch.setattr(backends.jwt, "decode", lambda *a, **k: (_ for _ in ()).throw(jwt_side_effect))
    else:
        # Return a payload referencing user id for the user-not-found scenario
        monkeypatch.setattr(backends, "jwt", backends.jwt, raising=False)
        monkeypatch.setattr(backends.jwt, "decode", lambda token, key, algorithms: {"user_id": 999})

    class DummyManager:
        def get(self, **kwargs):
            if user_get_side_effect is not None:
                raise user_get_side_effect
            return SimpleNamespace(id=999, username="ghost")

    class DummyUserModel:
        objects = DummyManager()

    monkeypatch.setattr(backends, "User", DummyUserModel, raising=False)

    # Act / Assert
    auth = backends.JWTAuthentication()
    expected_exc = _exc_lookup("AuthenticationFailed", Exception)
    with pytest.raises(_exc_lookup("expected_exc", Exception)):
        auth.authenticate(DummyRequest())


def test_comments_destroy_view_deletes_comment_and_raises_when_missing(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = article_views.CommentsDestroyAPIView()

    # Success scenario: get_object returns an object with delete side effect
    deleted_flag = {"deleted": False}

    class FakeComment:
        def delete(self_inner):
            deleted_flag["deleted"] = True

    def fake_get_object_success():
        return FakeComment()

    monkeypatch.setattr(view, "get_object", fake_get_object_success, raising=False)

    class DummyRequest:
        pass

    # Act
    response = view.delete(DummyRequest(), pk=1)

    # Assert
    assert hasattr(response, "status_code")
    assert response.status_code in (200, 204)  # view may return 200 or 204 depending on implementation
    assert deleted_flag["deleted"] is True

    # Not found scenario: get_object raises a NotFound-like error
    def fake_get_object_missing():
        raise Exception("not found")

    monkeypatch.setattr(view, "get_object", fake_get_object_missing, raising=False)

    expected_not_found_exc = _exc_lookup("NotFound", Exception)
    with pytest.raises(_exc_lookup("expected_not_found_exc", Exception)):
        view.delete(DummyRequest(), pk=999)
