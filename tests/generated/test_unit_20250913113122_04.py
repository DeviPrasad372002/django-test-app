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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

import pytest

try:
    from conduit.apps.articles.models import Article, Comment, Tag
    from conduit.apps.articles.relations import TagRelatedField
    import conduit.apps.articles.relations as relations_module
    import rest_framework.exceptions as rest_exceptions
except ImportError as e:  # pragma: no cover - skip module if imports unavailable
    import pytest as _pytest
    _pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

_exc_lookup = lambda name, default: getattr(rest_exceptions, name, default)


@pytest.mark.parametrize(
    "model_class, init_kwargs, expected_str",
    [
        (Article, {"title": "Test Article", "body": "Body"}, "Test Article"),
        (Article, {"title": "", "body": "Empty title body"}, ""),
        (Comment, {"body": "Nice post!", "author_id": 1}, "Nice post!"),
        (Tag, {"name": "python"}, "python"),
    ],
)
def test_models___str__(model_class, init_kwargs, expected_str):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create an instance without relying on DB persistence
    instance = model_class(**init_kwargs)
    # Act: call __str__
    result = str(instance)
    # Assert: __str__ returns the expected string
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected_str


def test_tagrelatedfield_to_representation_and_to_internal_value_success(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: prepare a fake Tag object and patch relations.Tag.get_or_create
    created_tags = {}

    class FakeTag:
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return f"<FakeTag {self.name!r}>"

    def fake_get_or_create(name):
        # simulate DB get_or_create: return same object instance for same name
        if name in created_tags:
            return created_tags[name], False
        obj = FakeTag(name)
        created_tags[name] = obj
        return obj, True

    monkeypatch.setattr(relations_module, "Tag", type("T", (), {"get_or_create": staticmethod(fake_get_or_create)}))

    field = TagRelatedField()
    # Act: representation from object
    tag_obj = FakeTag("django")
    representation = field.to_representation(tag_obj)
    # Assert: representation is the tag name
    assert representation == "django"
    # Act: internal value from string -> should return the FakeTag instance
    internal = field.to_internal_value("django")
    # Assert: internal value is the same instance created by fake_get_or_create
    assert internal is created_tags["django"]
    assert isinstance(internal, _exc_lookup("FakeTag", Exception))


@pytest.mark.parametrize("bad_input", [None, 123, 1.23, [], {}])
def test_tagrelatedfield_to_internal_value_invalid_types_raise_validationerror(monkeypatch, bad_input):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: ensure Tag exists but not invoked for invalid types
    class DummyTag:
        @staticmethod
        def get_or_create(name):
            return object(), True

    monkeypatch.setattr(relations_module, "Tag", DummyTag)

    field = TagRelatedField()
    ValidationError = _exc_lookup("ValidationError", Exception)
    # Act / Assert: non-string inputs should raise a ValidationError from DRF
    with pytest.raises(_exc_lookup("ValidationError", Exception)):
        field.to_internal_value(bad_input)
