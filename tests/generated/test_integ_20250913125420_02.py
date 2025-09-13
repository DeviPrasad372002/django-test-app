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

import pytest

try:
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.articles.views import CommentsDestroyAPIView
    from django.utils.text import slugify
    import rest_framework.exceptions as _rf_exceptions
except ImportError as e:
    pytest.skip(f"Required project modules not available: {e}", allow_module_level=True)


def _exc_lookup(name, fallback):
    return getattr(_rf_exceptions, name, fallback)


@pytest.mark.parametrize(
    "initial_slug, created, expected_changed",
    [
        (None, True, True),           # new instance, slug should be added
        ("existing-slug", True, False),  # has slug already, should remain unchanged
        (None, False, False),         # not created event, should not add slug
    ],
)
def test_add_slug_to_article_if_not_exists_sets_slug_and_saves(monkeypatch, initial_slug, created, expected_changed):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    generated_token = "RND123"
    monkeypatch.setattr("conduit.apps.core.utils.generate_random_string", lambda *a, **k: generated_token)

    class DummyArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug
            self._saved = False

        def save(self):
            self._saved = True

    instance = DummyArticle(title="My First Post!", slug=initial_slug)

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=instance, created=created, **{})

    # Assert
    if expected_changed:
        expected_slug_prefix = slugify(instance.title)
        assert instance.slug is not None and instance.slug.startswith(expected_slug_prefix)
        assert instance.slug.endswith(generated_token)
        assert instance._saved is True
    else:
        # slug should remain as initial value (including None) and save should not be called
        assert instance.slug == initial_slug
        assert instance._saved is False


@pytest.mark.parametrize(
    "auth_header, expected_result",
    [
        ("Token abc.def.ghi", ("user_obj", "abc.def.ghi")),  # standard token header -> authenticate returns tuple
        ("Bearer abc.def.ghi", ("user_obj", "abc.def.ghi")),  # bearer accepted similarly
        (None, None),  # missing header -> authenticate returns None
        ("", None),    # empty header -> authenticate returns None
    ],
)
def test_jwt_authenticate_delegates_to__authenticate_credentials(monkeypatch, auth_header, expected_result):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    backend = JWTAuthentication()

    class FakeRequest:
        def __init__(self, header_value):
            # DRF typically inspects META['HTTP_AUTHORIZATION']
            self.META = {}
            if header_value is not None:
                self.META["HTTP_AUTHORIZATION"] = header_value

    captured = {}

    def fake__authenticate_credentials(token):
        captured['token'] = token
        return ("user_obj", token)

    monkeypatch.setattr(backend, "_authenticate_credentials", fake__authenticate_credentials)

    request = FakeRequest(auth_header)

    # Act
    result = backend.authenticate(request)

    # Assert
    if expected_result is None:
        assert result is None
        assert 'token' not in captured
    else:
        expected_user, expected_token = expected_result
        assert result[0] == expected_user
        assert result[1] == expected_token
        assert captured['token'] == expected_token


@pytest.mark.parametrize("raise_not_found", [False, True])
def test_comments_destroy_view_calls_delete_or_raises(monkeypatch, raise_not_found):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view = CommentsDestroyAPIView()

    class FakeRequest:
        pass

    class FakeComment:
        def __init__(self):
            self.deleted = False

        def delete(self):
            self.deleted = True

    fake_comment = FakeComment()

    if raise_not_found:
        def fake_get_object():
            raise _exc_lookup("NotFound", Exception)()
    else:
        def fake_get_object():
            return fake_comment

    monkeypatch.setattr(view, "get_object", fake_get_object)

    request = FakeRequest()

    # Act / Assert
    if raise_not_found:
        with pytest.raises(_exc_lookup("NotFound", Exception)):
            view.delete(request, pk=1)
    else:
        response = view.delete(request, pk=1)
        # DRF delete handlers typically return Response(status=204) or similar
        # We check that object delete was called and that a response-like object is returned with status_code attribute
        assert fake_comment.deleted is True
        assert hasattr(response, "status_code")
        assert response.status_code in (200, 204, 202)  # accept common successful status codes for deletion
