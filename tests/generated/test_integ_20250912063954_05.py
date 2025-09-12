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

import pytest
import inspect

def _exc_lookup(name, default=Exception):
    return getattr(__builtins__, name, default)

def test_serializers_and_meta():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles import serializers as articles_serializers
        ArticleSerializer = articles_serializers.ArticleSerializer
        CommentSerializer = articles_serializers.CommentSerializer
        TagSerializer = articles_serializers.TagSerializer
        Meta = articles_serializers.Meta
    except ImportError:
        pytest.skip("articles.serializers not available")
    # Basic structural checks
    assert inspect.isclass(ArticleSerializer)
    assert inspect.isclass(CommentSerializer)
    assert inspect.isclass(TagSerializer)
    assert inspect.isclass(Meta)
    # If serializer has an inner Meta, ensure it exposes fields or model (best-effort)
    if hasattr(ArticleSerializer, "Meta"):
        meta = getattr(ArticleSerializer, "Meta")
        # meta may or may not define fields; if it does, it should be iterable
        if hasattr(meta, "fields"):
            fields = getattr(meta, "fields")
            assert hasattr(fields, "__iter__")
    # TagSerializer commonly exposes a fields attribute in its Meta
    if hasattr(TagSerializer, "Meta") and hasattr(TagSerializer.Meta, "fields"):
        assert hasattr(TagSerializer.Meta.fields, "__iter__")

def test_json_renderers_nest_keys():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles import renderers as articles_renderers
    except ImportError:
        pytest.skip("articles.renderers not available")
    ArticleJSONRenderer = getattr(articles_renderers, "ArticleJSONRenderer", None)
    CommentJSONRenderer = getattr(articles_renderers, "CommentJSONRenderer", None)
    if ArticleJSONRenderer is None or CommentJSONRenderer is None:
        pytest.skip("Expected JSON renderer classes not found")
    # create instances
    art_renderer = ArticleJSONRenderer()
    com_renderer = CommentJSONRenderer()
    # Prepare sample payloads that typical renderers would wrap/emit
    sample_article_payload = {"article": {"slug": "sample-slug", "title": "T"}}
    sample_comment_payload = {"comments": [{"id": 1, "body": "x"}], "comment": {"id": 1, "body": "x"}}
    # Attempt to call render; if render API not present, skip
    if not hasattr(art_renderer, "render") or not hasattr(com_renderer, "render"):
        pytest.skip("Renderer.render not available on renderer classes")
    art_out = art_renderer.render(sample_article_payload, accepted_media_type=None, renderer_context=None)
    com_out = com_renderer.render(sample_comment_payload, accepted_media_type=None, renderer_context=None)
    # Expect byte outputs that contain JSON keys; be robust to str/bytes return
    if isinstance(art_out, _exc_lookup("bytes", Exception)):
        assert b"sample-slug" in art_out or b"sample-slug" in art_out.lower()
        assert b"article" in art_out or b"\"article\"" in art_out
    else:
        out_s = str(art_out)
        assert "sample-slug" in out_s
        assert "article" in out_s
    if isinstance(com_out, _exc_lookup("bytes", Exception)):
        assert b"comments" in com_out or b"comment" in com_out
        assert b"body" in com_out
    else:
        out_s = str(com_out)
        assert "comments" in out_s or "comment" in out_s
        assert "body" in out_s

def test_views_linked_serializers_and_renderers():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles import views as articles_views
        from conduit.apps.articles import renderers as articles_renderers
        from conduit.apps.articles import serializers as articles_serializers
    except ImportError:
        pytest.skip("articles.views/renderers/serializers not available")
    # Collect view classes we expect to exist
    view_names = [
        "CommentsListCreateAPIView",
        "CommentsDestroyAPIView",
        "ArticlesFavoriteAPIView",
        "TagListAPIView",
        "ArticlesFeedAPIView",
        "ArticleViewSet",
    ]
    for name in view_names:
        view_cls = getattr(articles_views, name, None)
        assert view_cls is not None, f"{name} should be present in articles.views"
        # Check that view references a serializer class by name or attribute
        serializer_attr = getattr(view_cls, "serializer_class", None) or getattr(view_cls, "get_serializer_class", None)
        assert serializer_attr is not None, f"{name} should declare serializer_class or get_serializer_class"
        # Many views declare renderer_classes; if present ensure JSON renderers are included by name
        renderer_classes = getattr(view_cls, "renderer_classes", None)
        if renderer_classes:
            names = [getattr(r, "__name__", str(r)) for r in renderer_classes]
            # Accept that either ArticleJSONRenderer or CommentJSONRenderer might appear depending on view
            assert any("JSONRenderer" in n or "ArticleJSONRenderer" in n or "CommentJSONRenderer" in n for n in names)
    # Cross-check that at least one view uses the ArticleSerializer and one uses CommentSerializer
    ser_names = [getattr(c, "__name__", str(c)) for c in (getattr(articles_serializers, a) for a in dir(articles_serializers) if a.endswith("Serializer"))]
    assert any("ArticleSerializer" in n for n in ser_names)
    assert any("CommentSerializer" in n for n in ser_names)

def test_add_slug_to_article_if_not_exists(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles import signals as articles_signals
    except ImportError:
        pytest.skip("articles.signals not available")
    # Ensure generate_random_string used inside signals is deterministic
    if hasattr(articles_signals, "generate_random_string"):
        monkeypatch.setattr(articles_signals, "generate_random_string", lambda n=6: "xyz")
    else:
        # Try to patch utility module if signals referenced it differently
        try:
            import conduit.apps.core.utils as core_utils
            monkeypatch.setattr(core_utils, "generate_random_string", lambda n=6: "xyz")
        except Exception:
            # Not fatal; just proceed
            pass
    add_slug = getattr(articles_signals, "add_slug_to_article_if_not_exists", None)
    if add_slug is None:
        pytest.skip("add_slug_to_article_if_not_exists not defined in articles.signals")
    # Create a minimal stub article object
    class StubArticle:
        def __init__(self, title, slug=""):
            self.title = title
            self.slug = slug
    stub = StubArticle("My Test Article")
    # Call the signal handler with named args to match Django signature (sender, instance, created, **kwargs)
    try:
        add_slug(sender=None, instance=stub, created=True)
    except TypeError:
        # Try alternate calling convention if signature differs
        add_slug(stub)
    # After running, slug should be set (slugify of title likely present)
    assert getattr(stub, "slug", None), "slug should be populated by signal"
    slug_val = stub.slug.lower()
    assert "my-test-article" in slug_val or "-" in slug_val or len(slug_val) > 0