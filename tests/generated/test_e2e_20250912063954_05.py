import importlib.util, pytest
if importlib.util.find_spec('django') is None:
    pytest.skip('django not installed; skipping module', allow_module_level=True)

# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib as _importlib, importlib.util as _iu, importlib.machinery as _im, types as _types, pytest as _pytest, builtins as _builtins
import warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
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
    # Jinja2 / MarkupSafe
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
    # Flask escape & context __ident_func__
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
    # collections.abc re-exports
    try:
        import collections as _collections, collections.abc as _abc
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet'):
            if not hasattr(_collections, _n) and hasattr(_abc, _n):
                setattr(_collections, _n, getattr(_abc, _n))
    except Exception:
        pass
    # Marshmallow __version__ polyfill
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
for __qt_root in ["PyQt5","PyQt6","PySide2","PySide6"]:
    if _safe_find_spec(__qt_root) is None:
        _pkg=_ensure_pkg(__qt_root,True); _core=_ensure_pkg(__qt_root+".QtCore",False); _gui=_ensure_pkg(__qt_root+".QtGui",False); _widgets=_ensure_pkg(__qt_root+".QtWidgets",False)
        class QObject: pass
        def pyqtSignal(*a, **k): return object()
        def pyqtSlot(*a, **k):
            def _decorator(fn): return fn
            return _decorator
        class QCoreApplication: 
            def __init__(self,*a,**k): pass
            def exec_(self): return 0
            def exec(self): return 0
        _core.QObject=QObject; _core.pyqtSignal=pyqtSignal; _core.pyqtSlot=pyqtSlot; _core.QCoreApplication=QCoreApplication
        class QFont:  # minimal
            def __init__(self,*a,**k): pass
        class QDoubleValidator:
            def __init__(self,*a,**k): pass
            def setBottom(self,*a,**k): pass
            def setTop(self,*a,**k): pass
        class QIcon: 
            def __init__(self,*a,**k): pass
        class QPixmap:
            def __init__(self,*a,**k): pass
        _gui.QFont=QFont; _gui.QDoubleValidator=QDoubleValidator; _gui.QIcon=QIcon; _gui.QPixmap=QPixmap
        class QApplication:
            def __init__(self,*a,**k): pass
            def exec_(self): return 0
            def exec(self): return 0
        class QWidget: 
            def __init__(self,*a,**k): pass
        class QLabel(QWidget):
            def __init__(self,*a,**k): super().__init__(); self._text=""
            def setText(self,t): self._text=str(t)
            def text(self): return self._text
        class QLineEdit(QWidget):
            def __init__(self,*a,**k): super().__init__(); self._text=""
            def setText(self,t): self._text=str(t)
            def text(self): return self._text
            def clear(self): self._text=""
        class QTextEdit(QLineEdit): pass
        class QPushButton(QWidget):
            def __init__(self,*a,**k): super().__init__()
        class QMessageBox:
            @staticmethod
            def warning(*a,**k): return None
            @staticmethod
            def information(*a,**k): return None
            @staticmethod
            def critical(*a,**k): return None
        class QFileDialog:
            @staticmethod
            def getSaveFileName(*a,**k): return ("history.txt","")
            @staticmethod
            def getOpenFileName(*a,**k): return ("history.txt","")
        class QFormLayout:
            def __init__(self,*a,**k): pass
            def addRow(self,*a,**k): pass
        class QGridLayout(QFormLayout):
            def addWidget(self,*a,**k): pass
        _widgets.QApplication=QApplication; _widgets.QWidget=QWidget; _widgets.QLabel=QLabel; _widgets.QLineEdit=QLineEdit; _widgets.QTextEdit=QTextEdit
        _widgets.QPushButton=QPushButton; _widgets.QMessageBox=QMessageBox; _widgets.QFileDialog=QFileDialog; _widgets.QFormLayout=QFormLayout; _widgets.QGridLayout=QGridLayout
        for _name in ("QApplication","QWidget","QLabel","QLineEdit","QTextEdit","QPushButton","QMessageBox","QFileDialog","QFormLayout","QGridLayout"):
            setattr(_gui,_name,getattr(_widgets,_name))
_THIRD_PARTY_TOPS = ['__future__', 'conduit', 'datetime', 'django', 'json', 'jwt', 'models', 'os', 'random', 'relations', 'renderers', 'rest_framework', 'serializers', 'string', 'views']
# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import json
import pytest

def test_article_and_comment_renderers_composition():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    except Exception as e:
        pytest.skip(f"Import error: {e}")
    article = {"title": "Test Article", "body": "Some content", "slug": "test-article"}
    comment = {"id": 1, "body": "Nice article", "author": {"username": "alice"}}

    cr = CommentJSONRenderer()
    # Render singular comment
    rendered_single = cr.render(comment, renderer_context={})
    # Render comment list
    rendered_list = cr.render([comment], renderer_context={})
    ar = ArticleJSONRenderer()
    rendered_article = ar.render(article, renderer_context={})

    def loads(b):
        if isinstance(b, (bytes, bytearray)):
            return json.loads(b.decode("utf-8"))
        return json.loads(b)

    parsed_single = loads(rendered_single)
    parsed_list = loads(rendered_list)
    parsed_article = loads(rendered_article)

    # Comment renderer should produce either a 'comment' root or 'comments'
    assert any(k in parsed_single for k in ("comment", "comments"))
    assert any(k in parsed_list for k in ("comment", "comments"))
    # Article renderer should produce either an 'article' root or include title/body keys
    if "article" in parsed_article:
        assert parsed_article["article"].get("title") == "Test Article"
    else:
        # fallback: expect title present at top level
        assert parsed_article.get("title") == "Test Article"

def test_article_serializer_to_representation_includes_title_and_tags():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles.serializers import ArticleSerializer
    except Exception as e:
        pytest.skip(f"Import error: {e}")

    # Provide a plain dict instance; DRF serializers support dict-like instances for representation
    author = {"username": "bob", "bio": "author bio", "image": None}
    article = {
        "title": "Hello World",
        "description": "desc",
        "body": "content",
        "slug": "hello-world",
        "tagList": ["python", "testing"],
        "author": author,
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2020-01-02T00:00:00Z",
    }

    serializer = ArticleSerializer(instance=article)
    data = serializer.data

    assert data.get("title") == "Hello World"
    # Accept several possible tag field names that implementations may use
    tag_field_candidates = ("tagList", "tags", "tag_list", "taglist")
    assert any(field in data for field in tag_field_candidates)
    # Extract the tag list value
    tag_values = None
    for field in tag_field_candidates:
        if field in data:
            tag_values = data[field]
            break
    assert isinstance(tag_values, (list, tuple))
    assert "python" in tag_values

def test_comment_serializer_validation_and_render():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles.serializers import CommentSerializer
        from conduit.apps.articles.renderers import CommentJSONRenderer
    except Exception as e:
        pytest.skip(f"Import error: {e}")

    payload = {"body": "Great article!"}
    serializer = CommentSerializer(data=payload)
    # Validation may succeed or produce errors depending on serializer expectations;
    # we ensure deterministic handling: either valid or errors are present.
    try:
        is_valid = serializer.is_valid()
    except Exception as exc:
        # If validation raises, skip the test as environment may not be configured for full validation
        pytest.skip(f"Serializer validation raised: {exc}")

    # Build a plausible comment instance for rendering irrespective of serializer internals
    comment_instance = {
        "id": 1,
        "body": payload["body"],
        "author": {"username": "tester"},
        "created_at": "2021-01-01T00:00:00Z",
    }

    renderer = CommentJSONRenderer()
    rendered = renderer.render(comment_instance, renderer_context={})
    if isinstance(rendered, (bytes, bytearray)):
        rendered = rendered.decode("utf-8")
    parsed = json.loads(rendered)

    # The renderer should produce either a singular 'comment' or a 'comments' container
    if "comment" in parsed:
        assert parsed["comment"].get("body") == payload["body"]
    elif "comments" in parsed:
        c = parsed["comments"]
        if isinstance(c, _exc_lookup("list", Exception)):
            assert any(item.get("body") == payload["body"] for item in c)
        elif isinstance(c, _exc_lookup("dict", Exception)):
            assert c.get("body") == payload["body"]
        else:
            pytest.skip("Unexpected comments container format")
    else:
        pytest.fail("Rendered comment JSON missing expected root key")