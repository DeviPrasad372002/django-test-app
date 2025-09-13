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
    import json
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
except ImportError:
    pytest.skip("conduit.apps.articles.renderers not available", allow_module_level=True)


@pytest.mark.parametrize(
    "input_data, expected_present, expected_absent",
    [
        # single article should be wrapped under "article" and not "articles"
        ({"title": "T", "body": "B"}, ("article",), ("articles",)),
        # paginated style from DRF: results + count -> should produce "articles" and "articlesCount"
        ({"results": [{"title": "A"}, {"title": "B"}], "count": 2}, ("articles", "articlesCount"), ("article",)),
        # errors must not be wrapped but rendered as-is (contain "errors")
        ({"errors": {"title": ["required"]}}, ("errors",), ("article", "articles")),
    ],
)
def test_article_json_renderer_various_inputs(input_data, expected_present, expected_absent):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    renderer = ArticleJSONRenderer()
    data_input = input_data

    # Act
    rendered_bytes = renderer.render(data_input)

    # Assert
    assert isinstance(rendered_bytes, (bytes, str)), "render should return bytes or str"
    rendered_text = rendered_bytes.decode("utf-8") if isinstance(rendered_bytes, _exc_lookup("bytes", Exception)) else rendered_bytes
    parsed = json.loads(rendered_text)
    for key in expected_present:
        assert key in parsed, f"expected key '{key}' present in output for input {data_input}"
    for key in expected_absent:
        assert key not in parsed, f"did not expect key '{key}' in output for input {data_input}"


@pytest.mark.parametrize(
    "input_data, expected_key",
    [
        # single comment rendered under "comment"
        ({"id": 1, "body": "ok"}, "comment"),
        # list of comments rendered under "comments"
        ([{"id": 1, "body": "a"}, {"id": 2, "body": "b"}], "comments"),
    ],
)
def test_comment_json_renderer_single_and_list_behaviour(input_data, expected_key):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    renderer = CommentJSONRenderer()
    data_input = input_data

    # Act
    rendered = renderer.render(data_input)

    # Assert
    assert isinstance(rendered, (bytes, str))
    text = rendered.decode("utf-8") if isinstance(rendered, _exc_lookup("bytes", Exception)) else rendered
    parsed = json.loads(text)
    assert expected_key in parsed
    # ensure the wrapped value has expected structure (list for list case, dict for single case)
    if isinstance(data_input, _exc_lookup("list", Exception)):
        assert isinstance(parsed[expected_key], list)
        assert len(parsed[expected_key]) == len(data_input)
    else:
        assert isinstance(parsed[expected_key], dict)
        # fields from original input must be present
        for k in data_input.keys():
            assert k in parsed[expected_key]


def test_article_and_comment_renderers_produce_valid_json_and_preserve_values():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    article_renderer = ArticleJSONRenderer()
    comment_renderer = CommentJSONRenderer()
    article_payload = {"title": "Edge", "body": "Case", "tags": []}
    comments_payload = [{"id": 10, "body": "Nice"}, {"id": 11, "body": "Good"}]

    # Act
    rendered_article = article_renderer.render(article_payload)
    rendered_comments = comment_renderer.render(comments_payload)

    # Assert
    assert isinstance(rendered_article, (bytes, str))
    assert isinstance(rendered_comments, (bytes, str))

    article_text = rendered_article.decode("utf-8") if isinstance(rendered_article, _exc_lookup("bytes", Exception)) else rendered_article
    comments_text = rendered_comments.decode("utf-8") if isinstance(rendered_comments, _exc_lookup("bytes", Exception)) else rendered_comments

    article_obj = json.loads(article_text)
    comments_obj = json.loads(comments_text)

    # Article renderer should expose the original title and body under some wrapper
    assert any(
        (isinstance(v, _exc_lookup("dict", Exception)) and v.get("title") == "Edge" and v.get("body") == "Case")
        or (isinstance(v, _exc_lookup("list", Exception)) and any(item.get("title") == "Edge" for item in v))
        for v in article_obj.values()
    )

    # Comments renderer should include both comments with original ids and bodies
    all_comment_items = []
    for v in comments_obj.values():
        if isinstance(v, _exc_lookup("list", Exception)):
            all_comment_items.extend(v)
    ids = {c.get("id") for c in all_comment_items}
    bodies = {c.get("body") for c in all_comment_items}
    assert ids == {10, 11}
    assert bodies == {"Nice", "Good"}
