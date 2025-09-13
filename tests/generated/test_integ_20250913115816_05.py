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

try:
    import pytest
    import jwt
    import json
    import time
    from datetime import datetime, timedelta
    from types import SimpleNamespace

    from django.conf import settings
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
except ImportError:
    import pytest
    pytest.skip("Required modules for integration tests are not available", allow_module_level=True)


def test_user_generate_jwt_token_and_decodable(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create a fake user-like object and set a predictable SECRET_KEY
    fake_user = SimpleNamespace(pk=123)
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key", raising=False)

    # Act: call the User._generate_jwt_token implementation with the fake user
    token = auth_models.User._generate_jwt_token(fake_user)

    # Assert: token decodes and contains expected id and a future exp timestamp
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert isinstance(decoded, _exc_lookup("dict", Exception))
    assert decoded.get("id") == 123
    exp_ts = decoded.get("exp")
    assert isinstance(exp_ts, _exc_lookup("int", Exception))
    assert exp_ts > int(time.time())


def test_jwt_authentication_authenticates_request_and_returns_user(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: prepare secret and fake user; monkeypatch User.objects.get to return fake user
    monkeypatch.setattr(settings, "SECRET_KEY", "another-test-secret", raising=False)
    fake_user = SimpleNamespace(pk=777, username="testuser")
    # Build token for the fake user using the model implementation
    token = auth_models.User._generate_jwt_token(fake_user)

    # Monkeypatch the User.objects.get to simulate DB lookup by pk
    class FakeManager:
        @staticmethod
        def get(**kwargs):
            # Accept lookups like pk=... or id=...
            if kwargs.get("pk") == fake_user.pk or kwargs.get("id") == fake_user.pk:
                return fake_user
            raise auth_models.User.DoesNotExist  # let it raise the real exception type if present

    monkeypatch.setattr(auth_models.User, "objects", FakeManager, raising=False)

    # Create a fake request object with the Authorization header
    fake_request = SimpleNamespace(META={"HTTP_AUTHORIZATION": f"Token {token}"})

    # Act: run the authentication routine
    auth_backend = JWTAuthentication()
    result = auth_backend.authenticate(fake_request)

    # Assert: backend returned the fake user and the token, in expected tuple structure
    assert isinstance(result, _exc_lookup("tuple", Exception)) and len(result) == 2
    returned_user, returned_token = result
    assert returned_user is fake_user
    assert returned_token == token


@pytest.mark.parametrize(
    "renderer_class,input_data,expected_key",
    [
        (ArticleJSONRenderer, {"title": "Hello", "body": "World"}, "article"),
        (CommentJSONRenderer, {"body": "Nice post!"}, "comment"),
        # Edge case: None data should still produce a JSON object (renderers often handle None)
        (ArticleJSONRenderer, None, "article"),
        (CommentJSONRenderer, None, "comment"),
    ],
)
def test_article_and_comment_renderers_wrap_payload_correctly(renderer_class, input_data, expected_key):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: instantiate renderer and prepare data
    renderer = renderer_class()

    # Act: render the input data (could be bytes or str depending on implementation)
    rendered = renderer.render(input_data)

    # Assert: rendered output is JSON containing the expected top-level key
    if isinstance(rendered, _exc_lookup("bytes", Exception)):
        rendered_text = rendered.decode("utf-8")
    else:
        rendered_text = rendered
    parsed = json.loads(rendered_text)
    assert expected_key in parsed
    # For non-None payloads, ensure original data appears under the key
    if input_data is not None:
        assert parsed[expected_key] == input_data
    else:
        # If input was None, renderer should still provide a value (often None or empty)
        assert expected_key in parsed
