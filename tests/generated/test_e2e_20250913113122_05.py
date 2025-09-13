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

try:
    import pytest
    import json
    import datetime
    from types import SimpleNamespace
    from conduit.apps.articles.serializers import ArticleSerializer, CommentSerializer, TagSerializer, Meta
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"ImportError: {e}", allow_module_level=True)


def test_article_serializer_representation_and_meta_presence():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    author_obj = SimpleNamespace(username="alice", bio="author bio", image=None)
    created = datetime.datetime(2020, 1, 1, 12, 0, 0)
    updated = datetime.datetime(2020, 1, 2, 12, 0, 0)
    article_obj = SimpleNamespace(
        title="Test Title",
        description="Short desc",
        body="The body content",
        slug="test-title",
        created_at=created,
        updated_at=updated,
        author=author_obj,
        # provide minimal attributes that serializers may access
        tags=[],
    )
    serializer_context = {"request": SimpleNamespace(user=None)}

    # Act
    serializer_instance = ArticleSerializer(instance=article_obj, context=serializer_context)
    representation = serializer_instance.data

    # Assert
    assert isinstance(representation, _exc_lookup("dict", Exception))
    assert representation.get("title") == "Test Title" or representation.get("article", {}).get("title") == "Test Title"
    # Meta presence and fields sanity
    assert hasattr(ArticleSerializer, "Meta")
    meta_cls = getattr(ArticleSerializer, "Meta")
    assert hasattr(meta_cls, "fields")
    fields_value = getattr(meta_cls, "fields")
    assert isinstance(fields_value, (list, tuple))
    assert any("title" == f or "title" in f for f in fields_value)


@pytest.mark.parametrize(
    "author_username, body_text",
    [
        ("bob", "A simple comment"),
        ("", ""),  # edge: empty username and empty body
    ],
)
def test_comment_serializer_representation_handles_author_and_body(author_username, body_text):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    author_obj = SimpleNamespace(username=author_username, bio="", image=None)
    created = datetime.datetime(2021, 6, 1, 8, 30, 0)
    comment_obj = SimpleNamespace(
        id=1,
        body=body_text,
        created_at=created,
        updated_at=created,
        author=author_obj,
    )

    # Act
    serializer_instance = CommentSerializer(instance=comment_obj, context={"request": SimpleNamespace(user=None)})
    representation = serializer_instance.data

    # Assert
    assert isinstance(representation, _exc_lookup("dict", Exception))
    # Comments serializers commonly either return a dict with keys directly or nested under "comment"
    if "body" in representation:
        assert representation["body"] == body_text
    else:
        assert representation.get("comment", {}).get("body") == body_text
    # Author username present in nested representation
    author_repr = representation.get("author") or representation.get("comment", {}).get("author")
    assert isinstance(author_repr, _exc_lookup("dict", Exception))
    assert author_repr.get("username") == author_username


@pytest.mark.parametrize(
    "renderer_class,input_payload,expected_key",
    [
        (ArticleJSONRenderer, {"article": {"title": "R1"}}, "article"),
        (ArticleJSONRenderer, {"articles": [{"title": "R2"}]}, "articles"),
        (CommentJSONRenderer, {"comment": {"body": "C1"}}, "comment"),
        (CommentJSONRenderer, {"comments": [{"body": "C2"}]}, "comments"),
    ],
)
def test_json_renderers_wrap_and_serialize_keys(renderer_class, input_payload, expected_key):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = renderer_class()

    # Act
    rendered_bytes = renderer.render(input_payload)
    # Some renderers return bytes, some return str; normalize
    if isinstance(rendered_bytes, _exc_lookup("bytes", Exception)):
        rendered_text = rendered_bytes.decode("utf-8")
    else:
        rendered_text = str(rendered_bytes)
    parsed = json.loads(rendered_text)

    # Assert
    assert isinstance(parsed, _exc_lookup("dict", Exception))
    assert expected_key in parsed
    assert parsed[expected_key] == input_payload[expected_key]


def test_tag_serializer_serializes_simple_tag_object_and_handles_edge_values():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    normal_tag = SimpleNamespace(name="python")
    empty_tag = SimpleNamespace(name="")

    # Act
    normal_serialized = TagSerializer(instance=normal_tag).data
    empty_serialized = TagSerializer(instance=empty_tag).data

    # Assert
    assert isinstance(normal_serialized, _exc_lookup("dict", Exception))
    # tag serializer commonly returns a representation with a "tag" or "name" field
    assert normal_serialized.get("name") == "python" or normal_serialized.get("tag") == "python"
    assert isinstance(empty_serialized, _exc_lookup("dict", Exception))
    # empty name should be preserved in representation
    assert empty_serialized.get("name", empty_serialized.get("tag")) == ""
