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

try:
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.articles.views import CommentsDestroyAPIView
    from conduit.apps.core import exceptions as core_exceptions
except ImportError:
    pytest.skip("Required application modules not available", allow_module_level=True)


class _exc_lookup:
    def __init__(self, name, default=Exception):
        self.name = name
        self.default = default

    def __call__(self):
        return globals().get(self.name, self.default)


@pytest.mark.parametrize(
    "created, initial_slug, expected_changed, expected_slug_suffix",
    [
        (True, "", True, "-abc"),
        (False, "", False, None),
        (True, "existing-slug", False, None),
    ],
)
def test_add_slug_to_article_if_not_exists_generates_and_saves(monkeypatch, created, initial_slug, expected_changed, expected_slug_suffix):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: fake article instance and monkeypatch helpers used by the signal
    class FakeArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug
            self.save_called = False

        def save(self):
            self.save_called = True

    article = FakeArticle(title="Hello World", slug=initial_slug)

    # Patch slugify used by the signals module and the random generator
    monkeypatch.setattr("conduit.apps.articles.signals.slugify", lambda s: "hello-world")
    monkeypatch.setattr("conduit.apps.core.utils.generate_random_string", lambda length=6: "abc")

    # Act: call the signal handler as Django would on post-save
    add_slug_to_article_if_not_exists(sender=None, instance=article, created=created)

    # Assert: if created and no initial slug -> slug updated and saved
    if expected_changed:
        assert article.slug.startswith("hello-world"), "slug should start with slugified title"
        assert article.slug.endswith(expected_slug_suffix), "slug should include generated suffix"
        assert article.save_called is True, "save should have been called when adding slug"
    else:
        assert article.slug == initial_slug, "slug should remain unchanged"
        assert article.save_called is False, "save must not be called when not changing slug"


@pytest.mark.parametrize(
    "auth_header, should_authenticate, expected_token_value",
    [
        ("Token abc.def", True, "abc.def"),
        ("Bearer xyz.123", True, "xyz.123"),
        (None, False, None),
        ("Token", False, None),
        ("Random abc", False, None),
    ],
)
def test_jwt_authentication_authenticate_parses_header_and_calls_credentials(monkeypatch, auth_header, should_authenticate, expected_token_value):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: fake request with or without Authorization header
    class FakeRequest:
        def __init__(self, header):
            self.META = {}
            if header is not None:
                self.META["HTTP_AUTHORIZATION"] = header

    request = FakeRequest(auth_header)

    called = {"called": False, "received_token": None}

    # Replace the internal _authenticate_credentials to observe/how it's called
    def fake_authenticate_credentials(self, token):
        called["called"] = True
        called["received_token"] = token
        # Return a tuple like (user, token) as some authenticate implementations do
        return ("fake_user_object", token)

    monkeypatch.setattr(JWTAuthentication, "_authenticate_credentials", fake_authenticate_credentials, raising=False)

    jwt_auth = JWTAuthentication()

    # Act: call authenticate
    result = jwt_auth.authenticate(request)

    # Assert
    if should_authenticate:
        assert called["called"] is True, "Expected _authenticate_credentials to be called for valid header"
        assert called["received_token"] == expected_token_value, "Token extracted from header should match expected"
        assert isinstance(result, _exc_lookup("tuple", Exception)), "authenticate should return a tuple (user, token) when successful"
        assert result[1] == expected_token_value
    else:
        assert called["called"] is False, "No credential call should be made for missing/invalid header"
        assert result is None, "authenticate should return None when no valid Authorization header"


@pytest.mark.parametrize("raise_on_delete, handler_returns", [(False, None), (True, "handled")])
def test_comments_destroy_api_view_deletes_or_handles_errors(monkeypatch, raise_on_delete, handler_returns):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: Fake comment object and view; monkeypatch get_object on the view to return it
    class FakeComment:
        def __init__(self):
            self.delete_called = False

        def delete(self):
            if raise_on_delete:
                raise RuntimeError("delete failed")
            self.delete_called = True

        def __str__(self):
            return "Comment(id=1)"

    fake_comment = FakeComment()

    # Instantiate the view
    view = CommentsDestroyAPIView()

    # Monkeypatch get_object to ensure view obtains our fake comment
    def fake_get_object(*args, **kwargs):
        return fake_comment

    monkeypatch.setattr(view, "get_object", fake_get_object, raising=False)

    # If deletion raises, patch the core exception handler to return a sentinel
    if raise_on_delete:
        def fake_handle_generic_error(exc):
            return handler_returns
        monkeypatch.setattr(core_exceptions, "_handle_generic_error", fake_handle_generic_error, raising=False)

    # Minimal fake request object
    class FakeRequest:
        def __init__(self):
            self.user = None

    request = FakeRequest()

    # Act: call the view's deletion entrypoint (try 'delete' then 'destroy' fallback)
    response = None
    if hasattr(view, "delete"):
        response = view.delete(request, pk=1)
    elif hasattr(view, "destroy"):
        response = view.destroy(request, pk=1)
    else:
        pytest.fail("CommentsDestroyAPIView has neither delete nor destroy method")

    # Assert: on normal path the comment's delete must have been called
    if not raise_on_delete:
        assert fake_comment.delete_called is True, "delete must be called on the comment when no exception occurs"
        # If a DRF Response is returned, it should indicate no content
        if hasattr(response, "status_code"):
            assert int(response.status_code) in (200, 204), "expected 200/204 status on successful delete"
    else:
        # When delete raises, our patched handler should have been returned by the view
        assert response == handler_returns, "When delete raises, view should delegate to _handle_generic_error"
        assert fake_comment.delete_called is False, "delete flag should remain False when exception raised"
