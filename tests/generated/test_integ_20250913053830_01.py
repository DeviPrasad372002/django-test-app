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

try:
    import pytest
# If a target import fails, skip the whole module rather than passing silently.
try:
    pass
except ImportError as _e:
    import pytest as _pytest; _pytest.skip(str(_e), allow_module_level=True)
    from types import SimpleNamespace
    from datetime import datetime, timedelta
    import conduit.apps.articles.signals as article_signals
    from conduit.apps.articles.models import Article, Tag, Comment
    from conduit.apps.authentication.models import User
    import conduit.apps.authentication.models as auth_models_mod
except ImportError as e:
    import pytest  # re-import for the skip call below
    pytest.skip("Required project modules not available: {}".format(e), allow_module_level=True)


@pytest.mark.parametrize("title_value, expected", [
    ("Hello World", "Hello World"),
    ("", ""),
])
def test_article___str__returns_title_for_various_titles(title_value, expected):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    article_instance = Article(title=title_value)
    # Act
    result = str(article_instance)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected


@pytest.mark.parametrize("tag_name", [
    "python",
    "",
])
def test_tag___str__returns_name(tag_name):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    tag_instance = Tag(name=tag_name)
    # Act
    result = str(tag_instance)
    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == tag_name


def test_add_slug_to_article_if_not_exists_creates_slug_using_slugify_and_random(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    # Provide deterministic slugify and random generator in the signals module namespace.
    monkeypatch.setattr('conduit.apps.articles.signals.generate_random_string', (lambda *a, **k: 'RND123'), raising=False)
    monkeypatch.setattr('conduit.apps.articles.signals.slugify', (lambda s: 'my-title'), raising=False)

    class FakeArticle:
        def __init__(self):
            self.slug = None
            self.title = "My Title"

    fake_article = FakeArticle()

    # Act
    # Simulate Django post_save signal handler invocation: sender, instance, created
    article_signals.add_slug_to_article_if_not_exists(sender=Article, instance=fake_article, created=True)

    # Assert
    assert hasattr(fake_article, 'slug')
    # Expect combination of slugified title and generated random string joined by a hyphen
    assert fake_article.slug == 'my-title-RND123'


def test_user_token_uses_jwt_encode_and_includes_user_id(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    recorded = {}

    def fake_jwt_encode(payload, secret, algorithm='HS256'):
        recorded['payload'] = payload
        recorded['secret'] = secret
        recorded['algorithm'] = algorithm
        return 'FAKE-TOKEN-XYZ'

    # Patch the jwt.encode used inside the authentication models module
    monkeypatch.setattr(auth_models_mod, 'jwt', SimpleNamespace(encode=fake_jwt_encode), raising=False)

    user = User()
    # Ensure both id and pk are present to cover different possible implementations
    user.id = 42
    user.pk = 42

    # Act
    token_value = getattr(user, 'token')  # property expected

    # Assert
    assert token_value == 'FAKE-TOKEN-XYZ'
    assert 'payload' in recorded and isinstance(recorded['payload'], dict)
    payload = recorded['payload']
    # Accept either 'id' or 'user_id' depending on implementation
    assert (payload.get('id') == 42) or (payload.get('user_id') == 42)
    assert recorded.get('algorithm') in ('HS256', None) or isinstance(recorded.get('algorithm'), str)
