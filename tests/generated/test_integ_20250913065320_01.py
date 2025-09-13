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
    from conduit.apps.articles import signals as article_signals
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.profiles import serializers as profiles_serializers
except ImportError:
    pytest.skip("required application modules not found", allow_module_level=True)


def test_add_slug_to_article_if_not_exists_creates_slug_and_saves(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: prepare deterministic slugify and random generator and a dummy article instance
    monkeypatch.setattr(article_signals, "generate_random_string", lambda n: "RND")
    monkeypatch.setattr(article_signals, "slugify", lambda text: "my-title")
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug
            self._saved_called = False
        def save(self, *args, **kwargs):
            self._saved_called = True
    dummy_article = DummyArticle(title="My Title", slug=None)

    # Act: invoke the signal handler as Django would on post-save for created instance
    # signature: (sender, instance, created, **kwargs)
    article_signals.add_slug_to_article_if_not_exists(sender=None, instance=dummy_article, created=True)

    # Assert: slug added and save was called
    assert isinstance(dummy_article.slug, str)
    assert dummy_article.slug == "my-title-RND"
    assert dummy_article._saved_called is True


def test__generate_jwt_token_uses_jwt_encode_and_returns_string(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: ensure jwt.encode returns a deterministic string and create a User instance
    def fake_encode(payload, secret, algorithm="HS256"):
        # verify payload contains an 'id' key (may be None) and standard claims possibly
        assert isinstance(payload, _exc_lookup("dict", Exception))
        assert "exp" in payload or "id" in payload
        return "FAKE.TOKEN.VALUE"
    # monkeypatch the jwt.encode used in the authentication models module
    monkeypatch.setattr(auth_models.jwt, "encode", fake_encode, raising=True)

    # Create a User instance without saving to DB; Django model __init__ supports this
    user_instance = auth_models.User()

    # Act: call the internal token generation method
    token_value = user_instance._generate_jwt_token()

    # Assert: returns the exact fake token and is a string
    assert token_value == "FAKE.TOKEN.VALUE"
    assert isinstance(token_value, _exc_lookup("str", Exception))


@pytest.mark.parametrize("is_following_result, expected", [(True, True), (False, False)])
def test_profileserializer_get_following_uses_is_following(monkeypatch, is_following_result, expected):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: create dummy current_user and target_user objects and a dummy serializer self
    current_user = SimpleNamespace(username="current")
    target_user = SimpleNamespace(username="target")

    dummy_request = SimpleNamespace(user=current_user)
    dummy_self = SimpleNamespace(context={"request": dummy_request})

    # Monkeypatch the is_following used in the profiles.serializers module
    monkeypatch.setattr(profiles_serializers, "is_following", lambda a, b: is_following_result, raising=False)

    # Act: call the class-bound method unbound via the serializer class (works if method defined on class)
    result = None
    # Attempt to call ProfileSerializer.get_following if defined; otherwise, call function if present.
    if hasattr(profiles_serializers, "ProfileSerializer"):
        serializer_cls = profiles_serializers.ProfileSerializer
        result = serializer_cls.get_following(dummy_self, target_user)
    else:
        # fallback: try direct function name in module
        get_following_func = getattr(profiles_serializers, "get_following")
        result = get_following_func(dummy_self, target_user)

    # Assert: result matches the monkeypatched is_following outcome and is boolean
    assert result == expected
    assert isinstance(result, _exc_lookup("bool", Exception))


def test_profileserializer_get_following_returns_false_without_request_context():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: prepare dummy_self without request in context and a target user
    dummy_self = SimpleNamespace(context={})
    target_user = SimpleNamespace(username="target")

    # Act: call the method/function
    if hasattr(profiles_serializers, "ProfileSerializer"):
        serializer_cls = profiles_serializers.ProfileSerializer
        result = serializer_cls.get_following(dummy_self, target_user)
    else:
        get_following_func = getattr(profiles_serializers, "get_following")
        result = get_following_func(dummy_self, target_user)

    # Assert: with no request context present the following status is False (safe default)
    assert result is False
    assert isinstance(result, _exc_lookup("bool", Exception))
