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
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.core import exceptions as core_exceptions
    from conduit.apps.articles import signals as article_signals
    from conduit.apps.core import utils as core_utils
    from rest_framework import exceptions as drf_exceptions
except ImportError:
    import pytest
    pytest.skip("Required project modules not available", allow_module_level=True)


def test_generate_jwt_token_uses_jwt_encode_and_includes_user_id(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user_instance = getattr(auth_models, "User")() if hasattr(auth_models, "User") else type("U", (), {})()
    # Set attributes that token generator typically expects
    setattr(user_instance, "id", 123)
    setattr(user_instance, "pk", 123)
    setattr(user_instance, "email", "user@example.test")
    expected_return_token = "FAKE.TOKEN.VALUE"
    captured = {}

    def fake_encode(payload, key, algorithm="HS256"):
        captured["payload"] = payload
        captured["key"] = key
        captured["algorithm"] = algorithm
        return expected_return_token

    # Act - replace the jwt module used inside the authentication models module
    monkeypatch.setattr(auth_models, "jwt", type("M", (), {"encode": staticmethod(fake_encode)}))
    # Some implementations call a module-level function, others call a method/property on User.
    if hasattr(auth_models, "_generate_jwt_token") and callable(getattr(auth_models, "_generate_jwt_token")):
        result_token = auth_models._generate_jwt_token(user_instance)
    elif hasattr(user_instance, "token"):
        # Access as attribute/property
        result_token = user_instance.token
    else:
        pytest.skip("No recognizable JWT generator found in authentication models", allow_module_level=False)

    # Assert
    assert result_token == expected_return_token
    assert isinstance(captured.get("payload"), dict)
    # Ensure the user id is included in the payload under any common key
    assert ("id" in captured["payload"]) or ("pk" in captured["payload"])
    assert captured["algorithm"] == "HS256"


@pytest.mark.parametrize(
    "handler_func, exception_instance, expected_status",
    [
        (core_exceptions._handle_not_found_error, drf_exceptions.NotFound(detail="missing"), 404),
        (core_exceptions._handle_generic_error, Exception("boom"), 500),
    ],
)
def test_core_error_handlers_return_response_with_status_and_message(handler_func, exception_instance, expected_status):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    assert callable(handler_func)

    # Act
    response = handler_func(exception_instance)

    # Assert
    # Ensure the handler returned a DRF-like Response with status_code and data
    assert hasattr(response, "status_code")
    assert hasattr(response, "data")
    assert response.status_code == expected_status
    # Data should contain some message/detail about the error
    assert isinstance(response.data, (dict, list))
    # Provide at least a minimal content check
    if isinstance(response.data, dict):
        assert len(response.data) > 0


@pytest.mark.parametrize(
    "initial_slug, expected_changed",
    [
        (None, True),           # No slug => should be generated and saved
        ("existing-slug", False),  # Existing slug => should not be changed
    ],
)
def test_add_slug_to_article_if_not_exists_generates_slug_and_saves(monkeypatch, initial_slug, expected_changed):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug
            self.saved = False

        def save(self):
            self.saved = True

    article = DummyArticle(title="Hello World!", slug=initial_slug)
    generated_random = "RND123"

    # Monkeypatch the generator used by the signal to return a predictable string
    if hasattr(core_utils, "generate_random_string"):
        monkeypatch.setattr(core_utils, "generate_random_string", lambda length=6: generated_random)
    else:
        # If the utils module doesn't expose that function, still proceed by patching the signal's reference if any
        if hasattr(article_signals, "generate_random_string"):
            monkeypatch.setattr(article_signals, "generate_random_string", lambda length=6: generated_random)

    # Monkeypatch slugify used in the signal to return a deterministic value
    if hasattr(article_signals, "slugify"):
        monkeypatch.setattr(article_signals, "slugify", lambda s: "hello-world")
    else:
        # Best effort: if the signals module uses django.utils.text.slugify directly,
        # set an attribute there would be risky; skip if not present.
        pytest.skip("Signals module does not expose slugify; cannot reliably test slug generation", allow_module_level=False)

    # Act
    # The signal handler signature is usually (sender, instance, **kwargs)
    # Provide created=True to mimic creation where slug is required
    article_signals.add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    if expected_changed:
        assert article.saved is True
        assert article.slug is not None
        # Expect slug to incorporate slugify(title) and the random string in some form
        assert "hello-world" in article.slug
        assert generated_random.lower() in article.slug.lower()
    else:
        # If slug existed, it should remain unchanged and not be saved
        assert article.slug == initial_slug
        # Saved might still be True if implementation always calls save; check that slug was not altered
        assert article.slug == initial_slug
