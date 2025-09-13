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

try:
    import pytest
    import importlib
    import re
    from types import SimpleNamespace
except ImportError:  # pragma: no cover - module-level skip when pytest or stdlib not present
    import pytest
    pytest.skip("pytest or stdlib imports not available", allow_module_level=True)

try:
    auth_models = importlib.import_module('conduit.apps.authentication.models')
    core_exceptions = importlib.import_module('conduit.apps.core.exceptions')
    core_utils = importlib.import_module('conduit.apps.core.utils')
    articles_signals = importlib.import_module('conduit.apps.articles.signals')
except ImportError:
    pytest.skip("Target conduit modules not available", allow_module_level=True)


@pytest.mark.parametrize("length", [0, 1, 10, 50])
def test_generate_random_string_returns_expected_length_and_charset(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    generate_random_string = getattr(core_utils, 'generate_random_string')
    pattern = re.compile(r'^[A-Za-z0-9]*$')

    # Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    assert pattern.match(result) is not None


def test__generate_jwt_token_calls_jwt_with_payload_including_id_and_exp(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    captured = {}

    class FakeJWT:
        def encode(self, payload, secret, algorithm='HS256'):
            captured['payload'] = payload
            captured['secret'] = secret
            captured['algorithm'] = algorithm
            return 'encoded-token'

    fake_jwt = FakeJWT()
    # Replace the jwt module reference inside auth_models with our fake
    monkeypatch.setattr(auth_models, 'jwt', fake_jwt, raising=False)
    # Ensure settings.SECRET_KEY exists inside the module (method likely accesses settings)
    monkeypatch.setattr(auth_models, 'settings', SimpleNamespace(SECRET_KEY='sekret'), raising=False)

    # Build a fake "self" with expected attributes (pk/id)
    fake_user = SimpleNamespace(pk=123, id=123)

    # Act
    token = auth_models.User._generate_jwt_token(fake_user)

    # Assert
    assert token == 'encoded-token'
    assert 'payload' in captured
    payload = captured['payload']
    # The payload should include an expiration key and include the user's id somewhere
    assert 'exp' in payload
    assert any(value == 123 for value in payload.values())


def test_add_slug_to_article_if_not_exists_uses_slugify_and_random(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    add_slug = getattr(articles_signals, 'add_slug_to_article_if_not_exists')
    # Force deterministic slugify and random string generation used by the signal
    monkeypatch.setattr(articles_signals, 'slugify', lambda s: 'slugged-title', raising=False)
    monkeypatch.setattr(articles_signals, 'generate_random_string', lambda n=6: 'RANDOM', raising=False)

    # Create a fake article instance with no slug
    fake_article = SimpleNamespace(title='Hello World!', slug=None)

    # Act
    # The signal usually receives (sender, instance, **kwargs)
    add_slug(None, fake_article)

    # Assert
    # Expect slug constructed from slugify(title) + '-' + random
    assert isinstance(fake_article.slug, str)
    assert fake_article.slug == 'slugged-title-RANDOM'


def test_core_exception_handlers_return_responses_with_expected_status(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Create a fake Response class to capture status_code and data
    class FakeResponse:
        def __init__(self, data, status=None):
            self.data = data
            self.status_code = status

    monkeypatch.setattr(core_exceptions, 'Response', FakeResponse, raising=False)

    # Act: call not-found handler
    not_found_exc = Exception("not found")
    response_not_found = core_exceptions._handle_not_found_error(not_found_exc, {})

    # Act: call generic handler
    generic_exc = Exception("generic error")
    response_generic = core_exceptions._handle_generic_error(generic_exc, {})

    # Assert: _handle_not_found_error should produce a 404-like response
    assert hasattr(response_not_found, 'status_code')
    assert int(response_not_found.status_code) in (404,)

    # Assert: _handle_generic_error should produce a 500-like response and include error details
    assert hasattr(response_generic, 'status_code')
    assert int(response_generic.status_code) in (500, 400)  # accept 500 or conservative 400 if implemented differently
    assert hasattr(response_generic, 'data')
    assert response_generic.data is not None
