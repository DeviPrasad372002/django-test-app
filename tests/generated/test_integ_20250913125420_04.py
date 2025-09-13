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
    from types import SimpleNamespace
    from conduit.apps.articles.relations import TagRelatedField
    from conduit.apps.articles.models import Tag
    from conduit.apps.articles import signals as article_signals
    from conduit.apps.profiles import serializers as profiles_serializers
    from conduit.apps.profiles import models as profiles_models
except ImportError as e:
    import pytest
    pytest.skip("Required modules not available: {}".format(e), allow_module_level=True)


@pytest.mark.parametrize(
    "case_name, tag_name, expected",
    [
        ("normal", "pytest-tag", "pytest-tag"),
        ("empty", "", ""),
    ],
)
def test_tagrelatedfield_to_representation_returns_name(case_name, tag_name, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    field = TagRelatedField()
    tag_instance = Tag()
    tag_instance.name = tag_name

    # Act
    representation = field.to_representation(tag_instance)

    # Assert
    assert isinstance(representation, _exc_lookup("str", Exception))
    assert representation == expected


def test_tagrelatedfield_to_internal_value_gets_or_creates_tag(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    captured = {}

    def fake_get_or_create(**kwargs):
        captured['called_with'] = kwargs
        fake_tag = Tag()
        fake_tag.name = kwargs.get('name')
        return (fake_tag, True)

    monkeypatch.setattr(Tag, "objects", SimpleNamespace(get_or_create=fake_get_or_create))
    field = TagRelatedField()
    input_value = "new-tag"

    # Act
    internal = field.to_internal_value(input_value)

    # Assert
    assert isinstance(internal, _exc_lookup("Tag", Exception))
    assert getattr(internal, "name", None) == input_value
    assert captured.get("called_with") == {"name": input_value}


def test_add_slug_to_article_if_not_exists_sets_slug(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    title_value = "An Example Title"
    expected_slug = "an-example-title"
    monkeypatch.setattr(article_signals, "slugify", lambda v: expected_slug)
    article_obj = SimpleNamespace(slug=None, title=title_value)

    # Act
    # handler signature expected: (sender, instance, created, **kwargs)
    article_signals.add_slug_to_article_if_not_exists(None, article_obj, True)

    # Assert
    assert getattr(article_obj, "slug", None) == expected_slug


def test_get_following_uses_is_following(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    recorded = {}

    def fake_is_following(current_user, target_user):
        recorded["args"] = (current_user, target_user)
        return True

    monkeypatch.setattr(profiles_models, "is_following", fake_is_following)

    request_user = SimpleNamespace(username="alice")
    target_user = SimpleNamespace(username="bob")
    fake_self = SimpleNamespace(context={"request": SimpleNamespace(user=request_user)})

    # Try module-level function first, fallback to serializer method on a class
    if hasattr(profiles_serializers, "get_following") and callable(getattr(profiles_serializers, "get_following")):
        func = getattr(profiles_serializers, "get_following")
        # Act
        result = func(fake_self, target_user)
    else:
        found = None
        for attr_name in dir(profiles_serializers):
            attr = getattr(profiles_serializers, attr_name)
            if isinstance(attr, _exc_lookup("type", Exception)) and hasattr(attr, "get_following"):
                found = getattr(attr, "get_following")
                break
        assert found is not None, "get_following not found in module or serializer classes"
        # Act
        result = found(fake_self, target_user)

    # Assert
    assert result is True
    assert "args" in recorded
    assert recorded["args"][0].username == "alice"
    assert recorded["args"][1].username == "bob"
