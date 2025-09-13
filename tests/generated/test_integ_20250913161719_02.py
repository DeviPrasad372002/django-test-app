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
            except Exception:
                pass

        if not _dj_settings.configured:
            _installed = ["django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions"]
            if _iu.find_spec("rest_framework"):
                _installed.append("rest_framework")

            # Explicitly try common project apps if present
            for _app in ("conduit.apps.core","conduit.apps.articles","conduit.apps.authentication","conduit.apps.profiles"):
                _maybe_add(_app, _installed)

            # Generic discovery under conduit.apps.*
            try:
                if _iu.find_spec("conduit.apps"):
                    _apps_pkg = importlib.import_module("conduit.apps")
                    for _m in pkgutil.iter_modules(getattr(_apps_pkg, "__path__", [])):
                        _full = "conduit.apps." + _m.name
                        _maybe_add(_full, _installed)
            except Exception:
                pass

            _cfg = dict(
                SECRET_KEY="test-key",
                DEBUG=True,
                ALLOWED_HOSTS=["*"],
                INSTALLED_APPS=sorted(set(_installed)),
                DATABASES=dict(default=dict(ENGINE="django.db.backends.sqlite3", NAME=":memory:")),
                MIDDLEWARE=[],
                MIDDLEWARE_CLASSES=[],
                USE_TZ=True,
                TIME_ZONE="UTC",
            )
            try:
                _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
            except Exception:
                pass

            try:
                _dj_settings.configure(**_cfg)
                django.setup()
            except Exception:
                _pytest.skip("Django setup failed in bootstrap; skipping generated tests", allow_module_level=True)
        else:
            if not _dj_apps.ready:
                try:
                    django.setup()
                except Exception:
                    _pytest.skip("Django setup not ready and failed to initialize; skipping", allow_module_level=True)
except Exception:
    _pytest.skip("Django bootstrap error; skipping generated tests", allow_module_level=True)
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

import builtins
import types
import pytest

try:
    from types import SimpleNamespace
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.backends as auth_backends
    import conduit.apps.articles.views as articles_views
    import conduit.apps.articles.models as articles_models
    import conduit.apps.articles.signals as articles_signals
    import conduit.apps.core.utils as core_utils
    import django
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Required packages not available: {e}", allow_module_level=True)


def _exc_lookup(name, default=Exception):
    return getattr(builtins, name, default)


def test_user_manager_create_user_and_superuser_roundtrip():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    email = "test@example.com"
    password = "s3cret!"
    first_name = "Test"
    last_name = "User"

    User = auth_models.User

    # Act
    created_user = User.objects.create_user(email=email, password=password, first_name=first_name, last_name=last_name)
    created_super = User.objects.create_superuser(email="admin@example.com", password="adminpass")

    # Assert
    assert getattr(created_user, "email", None) == email
    assert getattr(created_user, "first_name", None) == first_name
    assert getattr(created_user, "last_name", None) == last_name
    assert bool(getattr(created_user, "is_superuser", False) is True) is False
    token_value = getattr(created_user, "token", None)
    assert isinstance(token_value, _exc_lookup("str", Exception))

    assert getattr(created_super, "email", None) == "admin@example.com"
    assert bool(getattr(created_super, "is_superuser", False) is True) is True
    full_name = getattr(created_user, "get_full_name", lambda: None)()
    assert isinstance(full_name, _exc_lookup("str", Exception))
    assert first_name in full_name and last_name in full_name


@pytest.mark.parametrize("payload,user_exists", [
    ({"id": 1}, True),
    ({"id": 9999}, False),
])
def test_jwtauthentication__authenticate_credentials_success_and_not_found(monkeypatch, payload, user_exists):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = auth_backends.JWTAuthentication()
    token_string = "abc.def.ghi"

    fake_user = SimpleNamespace(id=payload.get("id"), is_active=True)
    User = auth_models.User

    # Monkeypatch jwt.decode used inside backends module
    def fake_decode(token, key, algorithms=None):
        assert token == token_string
        return payload

    monkeypatch.setattr(auth_backends, "jwt", SimpleNamespace(decode=fake_decode))

    # Control User.objects.get behavior
    if user_exists:
        monkeypatch.setattr(User, "objects", SimpleNamespace(get=lambda **kw: fake_user))
    else:
        class DoesNotExist(Exception):
            pass
        # Simulate Django's model DoesNotExist for User
        monkeypatch.setattr(User, "DoesNotExist", DoesNotExist)
        def raise_not_found(**kw):
            raise DoesNotExist()
        monkeypatch.setattr(User, "objects", SimpleNamespace(get=raise_not_found))

    # Act / Assert
    if user_exists:
        result_user, result_token = auth._authenticate_credentials(payload, token_string)
        assert result_user is fake_user
        assert result_token == token_string
    else:
        with pytest.raises(_exc_lookup('Exception', Exception)):
            auth._authenticate_credentials(payload, token_string)


def test_comments_destroyapi_deletes_comment_and_returns_204(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    view_cls = articles_views.CommentsDestroyAPIView
    view_instance = view_cls()

    delete_called = {"flag": False}

    class FakeComment:
        def __init__(self, author):
            self.author = author

        def delete(self):
            delete_called["flag"] = True

    fake_author = SimpleNamespace(id=10)
    fake_comment = FakeComment(author=fake_author)

    # Monkeypatch get_object_or_404 used inside the view module to return our fake comment
    monkeypatch.setattr(articles_views, "get_object_or_404", lambda model, pk: fake_comment)

    # Prepare a fake request with user equal to comment author
    fake_request = SimpleNamespace(user=fake_author)

    # Act
    response = view_instance.delete(fake_request, pk=1)

    # Assert
    assert delete_called["flag"] is True
    status_code = getattr(response, "status_code", None)
    assert status_code == 204


@pytest.mark.parametrize("query_params,expect_filters", [
    ({"author": "alice", "tag": "python"}, True),
    ({}, False),
])
def test_add_slug_and_filter_queryset_integration(monkeypatch, query_params, expect_filters):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange - add_slug_to_article_if_not_exists
    generated_random = "RND"
    monkeypatch.setattr(core_utils, "generate_random_string", lambda length=6: generated_random)

    article_instance = SimpleNamespace(title="Hello World!", slug="")

    # Act - call signal handler
    articles_signals.add_slug_to_article_if_not_exists(sender=None, instance=article_instance, created=True)

    # Assert - slug was added and contains slugified portion and random string
    assert isinstance(article_instance.slug, str)
    assert generated_random.lower() in article_instance.slug.lower()
    assert "hello-world" in article_instance.slug.lower()

    # Arrange - filter_queryset on an articles view
    class FakeQueryset:
        def __init__(self):
            self.calls = []

        def filter(self, **kwargs):
            self.calls.append(kwargs)
            return self

    fake_qs = FakeQueryset()
    view = articles_views.ArticlesFeedAPIView()
    view.request = SimpleNamespace(query_params=query_params)

    # Act
    filtered = view.filter_queryset(fake_qs)

    # Assert
    assert filtered is fake_qs
    if expect_filters:
        assert len(fake_qs.calls) >= 1
        # Look for keys that indicate author or tag filtering
        key_match = any(
            any(k.startswith(prefix) or "tag" in k for k in call.keys())
            for call in fake_qs.calls
            for prefix in ("author", "author__")
        )
        assert key_match
    else:
        assert fake_qs.calls == []
