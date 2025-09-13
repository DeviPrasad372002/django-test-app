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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import pytest
    from types import SimpleNamespace
    from unittest.mock import Mock
    import importlib

    auth_models = importlib.import_module("target.conduit.apps.authentication.models")
    backends = importlib.import_module("target.conduit.apps.authentication.backends")
    article_serializers = importlib.import_module("target.conduit.apps.articles.serializers")
    article_views = importlib.import_module("target.conduit.apps.articles.views")
    article_models = importlib.import_module("target.conduit.apps.articles.models")
    rest_exceptions = importlib.import_module("rest_framework.exceptions")
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Skipping tests due to import error: {e}", allow_module_level=True)


@pytest.mark.parametrize(
    "first,last,expected_full",
    [
        ("Alice", "Smith", "Alice Smith"),
        ("", "", ""),  # edge: no names provided
    ],
)
def test_user_token_and_get_full_name(monkeypatch, first, last, expected_full):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = auth_models.User()
    user.first_name = first
    user.last_name = last
    user.email = "alice@example.com"
    monkeypatch.setattr(
        auth_models.User,
        "_generate_jwt_token",
        lambda self: "JWT-MOCK-TOKEN",
        raising=False,
    )

    # Act
    token_value = user.token
    full_name = user.get_full_name()

    # Assert
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert token_value == "JWT-MOCK-TOKEN"
    assert isinstance(full_name, _exc_lookup("str", Exception))
    assert full_name == expected_full


@pytest.mark.parametrize(
    "exists,should_be_active,expect_exception",
    [
        (True, True, False),   # normal: user found and active
        (True, False, True),   # edge: user found but inactive -> auth failure
        (False, False, True),  # error: user not found -> auth failure
    ],
)
def test_jwtauthentication_authenticate_credentials(monkeypatch, exists, should_be_active, expect_exception):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    backend = backends.JWTAuthentication()
    payload = {"user_id": 1}

    class DummyObjects:
        def __init__(self, exists, active):
            self._exists = exists
            self._active = active

        def get(self, pk):
            if not self._exists:
                # try to mimic typical Django DoesNotExist behavior if available on the model
                model = getattr(backends, "User", None)
                exc = getattr(model, "DoesNotExist", Exception)
                raise exc("not found")
            return SimpleNamespace(is_active=self._active, pk=pk)

    dummy_objects = DummyObjects(exists, should_be_active)
    dummy_user_model = SimpleNamespace(objects=dummy_objects)

    monkeypatch.setattr(backends, "User", dummy_user_model, raising=False)

    # Act / Assert
    if expect_exception:
        with pytest.raises(_exc_lookup("rest_exceptions.AuthenticationFailed", Exception)):
            backend._authenticate_credentials(payload)
    else:
        result_user = backend._authenticate_credentials(payload)
        assert hasattr(result_user, "is_active")
        assert result_user.is_active is True
        assert getattr(result_user, "pk", None) == 1


@pytest.mark.parametrize(
    "get_object_raises",
    [
        None,  # normal deletion
        rest_exceptions.NotFound("no comment"),  # edge: not found -> propagate
    ],
)
def test_comments_destroy_api_calls_delete(monkeypatch, get_object_raises):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = article_views.CommentsDestroyAPIView()
    deleted_mock = Mock()
    comment_obj = Mock(delete=deleted_mock)

    def _get_object_success():
        return comment_obj

    def _get_object_error():
        raise get_object_raises

    if get_object_raises is None:
        monkeypatch.setattr(view, "get_object", _get_object_success, raising=False)
    else:
        monkeypatch.setattr(view, "get_object", _get_object_error, raising=False)

    request = SimpleNamespace(user=None)

    # Act / Assert
    if get_object_raises is None:
        response = view.delete(request, pk=1)
        # Assert that delete was called on the model instance
        assert deleted_mock.called is True
    else:
        with pytest.raises(type(get_object_raises)):
            view.delete(request, pk=1)


@pytest.mark.parametrize(
    "favorited_value,author_following",
    [
        (True, False),   # typical: favorited by current user, author not followed
        (False, True),   # edge: not favorited, but author is followed
    ],
)
def test_article_serializer_includes_favorited_and_author_following(monkeypatch, favorited_value, author_following):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    author = SimpleNamespace(username="bob")
    article = SimpleNamespace(title="T", body="B", author=author)
    request = SimpleNamespace(user=SimpleNamespace(pk=1))
    # Monkeypatch serializer helper methods that compute favorited and author info
    monkeypatch.setattr(
        article_serializers.ArticleSerializer,
        "get_favorited",
        lambda self, obj: favorited_value,
        raising=False,
    )
    # Some implementations expose get_author or get_profile_related; attempt to patch common name 'get_author'
    monkeypatch.setattr(
        article_serializers.ArticleSerializer,
        "get_author",
        lambda self, obj: {"username": obj.author.username, "following": author_following},
        raising=False,
    )

    serializer = article_serializers.ArticleSerializer(article, context={"request": request})

    # Act
    data = serializer.data

    # Assert
    assert "favorited" in data
    assert data["favorited"] is favorited_value
    assert "author" in data
    assert isinstance(data["author"], dict)
    assert data["author"].get("username") == "bob"
    assert data["author"].get("following") is author_following
