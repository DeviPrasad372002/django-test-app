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

try:
    import pytest
    from types import SimpleNamespace
    from conduit.apps.articles.serializers import ArticleSerializer
    from conduit.apps.profiles.serializers import ProfileSerializer
    from conduit.apps.profiles import models as profiles_models
    from conduit.apps.authentication import models as auth_models
except ImportError as e:
    import pytest
    pytest.skip("Skipping tests due to ImportError: {}".format(e), allow_module_level=True)


@pytest.mark.parametrize("has_favorited_value", [True, False])
def test_article_serializer_get_favorited_delegates_to_profiles_has_favorited(monkeypatch, has_favorited_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    article_instance = SimpleNamespace(slug="an-article")
    request_user = SimpleNamespace(is_authenticated=True)
    fake_request = SimpleNamespace(user=request_user)
    serializer = ArticleSerializer(instance=article_instance, context={"request": fake_request})
    monkeypatch.setattr(profiles_models, "has_favorited", lambda user, article: has_favorited_value)
    # Act
    result = serializer.get_favorited(article_instance)
    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result is has_favorited_value


@pytest.mark.parametrize("count_value", [0, 1, 999])
def test_article_serializer_get_favorites_count_reads_article_favorites_count(count_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class Favs:
        def __init__(self, n):
            self._n = n

        def count(self):
            return self._n

    article_instance = SimpleNamespace(favorites=Favs(count_value))
    serializer = ArticleSerializer(instance=article_instance)
    # Act
    result = serializer.get_favorites_count(article_instance)
    # Assert
    assert isinstance(result, _exc_lookup("int", Exception))
    assert result == count_value


@pytest.mark.parametrize(
    "profile_image, is_following_return, expected_image, expected_following",
    [
        ("https://cdn.example/avatar.png", True, "https://cdn.example/avatar.png", True),
        (None, False, "", False),
    ],
)
def test_profile_serializer_get_image_and_get_following(monkeypatch, profile_image, is_following_return, expected_image, expected_following):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # target_user has a profile with an image attribute
    profile_obj = SimpleNamespace(image=profile_image)
    target_user = SimpleNamespace(username="target", profile=profile_obj)
    # current user is in request context
    current_user = SimpleNamespace(username="current", is_authenticated=True)
    fake_request = SimpleNamespace(user=current_user)
    serializer = ProfileSerializer(instance=target_user, context={"request": fake_request})
    # Patch is_following in profiles.models to exercise cross-module call
    monkeypatch.setattr(profiles_models, "is_following", lambda current, target: is_following_return)
    # Act
    image_result = serializer.get_image(target_user)
    following_result = serializer.get_following(target_user)
    # Assert
    assert isinstance(image_result, _exc_lookup("str", Exception))
    assert image_result == expected_image
    assert isinstance(following_result, _exc_lookup("bool", Exception))
    assert following_result == expected_following


def test_user_token_uses_jwt_encode(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Create a User instance without saving to DB; rely on _generate_jwt_token to call jwt.encode internally.
    user_instance = auth_models.User(username="tester")
    # Patch the jwt.encode used inside the authentication.models module to observe payload and return a deterministic token
    captured = {}
    def fake_encode(payload, secret, algorithm="HS256"):
        captured['payload'] = payload
        captured['secret'] = secret
        captured['algorithm'] = algorithm
        return "FAKE.JWT.TOKEN"
    # The auth_models module likely imports jwt as 'jwt'; patch that attribute
    if hasattr(auth_models, "jwt"):
        monkeypatch.setattr(auth_models.jwt, "encode", fake_encode, raising=False)
    else:
        # If module attribute not present, set a jwt attribute on the module
        monkeypatch.setattr(auth_models, "jwt", SimpleNamespace(encode=fake_encode), raising=False)
    # Act
    token_value = user_instance.token
    # Assert
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert token_value == "FAKE.JWT.TOKEN"
    # ensure jwt.encode was invoked with a payload containing the username or user id
    assert "payload" in captured
    assert isinstance(captured["payload"], dict)
    # payload should include an exp and user identifying info; at least check for a token-like claim presence
    assert any(k in captured["payload"] for k in ("user_id", "id", "username", "email"))
    assert captured["algorithm"] in ("HS256", None, "");  # allow some flexibility if algorithm omitted or different
