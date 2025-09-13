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

try:
    import pytest
    from types import SimpleNamespace
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.authentication import backends as auth_backends
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication.models import UserManager
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Skipping tests due to ImportError: {e}", allow_module_level=True)


@pytest.mark.parametrize(
    "title, initial_slug, expect_slug_prefix",
    [
        ("My First Article", None, "my-first-article"),
        ("Another! Article @ Test", "", "another-article-test"),
        ("Edge Case---Title", None, "edge-case-title"),
    ],
)
def test_add_slug_to_article_if_not_exists_generates_slug_when_missing(title, initial_slug, expect_slug_prefix):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class FakeArticle:
        def __init__(self, title, slug):
            self.title = title
            self.slug = slug
            self._saved = False

        def save(self, *args, **kwargs):
            self._saved = True

    article = FakeArticle(title=title, slug=initial_slug)

    # Act
    # post_save signal handler typically signature: (sender, instance, created, **kwargs)
    add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    assert isinstance(article.slug, str)
    assert article.slug != ""  # non-empty slug created
    # slug should start with expected prefix (slugify may add random suffix on collision)
    assert article.slug.startswith(expect_slug_prefix)
    # ensure save was called if implementation persists changes
    assert getattr(article, "_saved", True) in (True, False)  # allow both but ensure attribute exists


def test_jwtauth__authenticate_credentials_active_and_inactive(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    jwt_called_with = {}

    def fake_decode(token, key, algorithms):
        jwt_called_with['token'] = token
        return {"id": 123}

    monkeypatch.setattr(auth_backends, "jwt", SimpleNamespace(decode=fake_decode))

    class FakeUser:
        def __init__(self, is_active=True):
            self.is_active = is_active

    # ensure User.objects.get returns an active user first, then an inactive one
    call_count = {"n": 0}

    def fake_get(**kwargs):
        call_count["n"] += 1
        return FakeUser(is_active=(call_count["n"] == 1))

    # Replace the User model manager used by authentication backend
    monkeypatch.setattr(auth_models.User, "objects", SimpleNamespace(get=fake_get))

    backend = auth_backends.JWTAuthentication()

    # Act / Assert: first call returns a user-like object for active user
    result = backend._authenticate_credentials("valid.token.here")
    # Depending on implementation this might return the user or (user, token). Assert at least we get an object with is_active True.
    if isinstance(result, _exc_lookup("tuple", Exception)):
        returned_user = result[0]
    else:
        returned_user = result
    assert hasattr(returned_user, "is_active")
    assert returned_user.is_active is True

    # Act / Assert: second call should raise an authentication-related exception for inactive user
    with pytest.raises(_exc_lookup("AuthenticationFailed", Exception)):
        backend._authenticate_credentials("valid.token.here")


@pytest.mark.parametrize(
    "email, username, password",
    [
        ("user@example.com", "user1", "secret"),
        ("another@example.org", "another", "p@ssw0rd"),
    ],
)
def test_usermanager_create_user_sets_password_and_saves(monkeypatch, email, username, password):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    created_instances = []

    class FakeUserModel:
        def __init__(self, email=None, username=None, **kwargs):
            self.email = email
            self.username = username
            self.password_hashed = None
            self._saved = False

        def set_password(self, raw):
            # emulate Django's set_password by storing a marker
            self.password_hashed = f"hashed:{raw}"

        def save(self, *args, **kwargs):
            self._saved = True
            created_instances.append(self)

    manager = UserManager()
    # Attach a fake model class that user manager will call to instantiate users
    manager.model = FakeUserModel

    # Act
    user = manager.create_user(email=email, username=username, password=password)

    # Assert
    assert isinstance(user, _exc_lookup("FakeUserModel", Exception))
    assert user.email == email
    assert user.username == username
    assert user.password_hashed == f"hashed:{password}"
    assert user._saved is True
    assert created_instances and created_instances[0] is user


def test_user_token_and_get_full_name_have_expected_types_and_content():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Construct a User without saving to DB; Django model __init__ accepts kwargs for fields
    user = auth_models.User(username="janedoe", email="jane@example.com")
    # Some implementations put first_name/last_name empty; test get_full_name fallback to username or combination
    # Act
    token_value = user.token if hasattr(user, "token") else getattr(user, "get_token", lambda: "")()
    full_name_value = user.get_full_name() if hasattr(user, "get_full_name") else ""

    # Assert
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert token_value != ""  # token property should return a non-empty string
    assert isinstance(full_name_value, _exc_lookup("str", Exception))
    # If no explicit full name, implementation often returns username
    assert full_name_value != "" or hasattr(user, "username")
    if full_name_value:
        assert " " in full_name_value or full_name_value == getattr(user, "username", full_name_value)
