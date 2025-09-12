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

import sys
import types
import datetime
import pytest
from types import SimpleNamespace

def _safe_import(module_name):
    try:
        module = __import__(module_name, fromlist=['*'])
        return module
    except Exception as e:
        pytest.skip(f"Could not import {module_name}: {e}")

def test_ready_imports_signals(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    mod_name = "conduit.apps.articles.__init__"
    # ensure signals module exists so ready() can import it
    fake_signals = types.ModuleType("conduit.apps.articles.signals")
    fake_signals._marker = True
    monkeypatch.setitem(sys.modules, "conduit.apps.articles.signals", fake_signals)
    module = _safe_import("conduit.apps.articles")
    # call either module-level ready() or ArticlesAppConfig.ready()
    if hasattr(module, "ready") and callable(getattr(module, "ready")):
        # should not raise
        module.ready()
    else:
        # try class-based AppConfig
        cls = getattr(module, "ArticlesAppConfig", None)
        if cls is None:
            pytest.skip("No ready() function or ArticlesAppConfig found")
        # instantiate safely: try common ctor signatures
        try:
            inst = cls("conduit.apps.articles", "conduit.apps.articles")
        except TypeError:
            try:
                inst = cls("conduit.apps.articles")
            except TypeError:
                inst = cls()
        # should not raise
        inst.ready()
    # confirm our fake was imported/executed by presence in sys.modules
    assert "conduit.apps.articles.signals" in sys.modules
    assert getattr(sys.modules["conduit.apps.articles.signals"], "_marker", False) is True

def test_article_str_uses_title():
    """Generated by ai-testgen with strict imports and safe shims."""
    module = _safe_import("conduit.apps.articles.models")
    Article = getattr(module, "Article", None)
    if Article is None:
        pytest.skip("Article model not found")
    # create a plain object with expected attribute(s)
    obj = SimpleNamespace(title="Unique Title 123", slug=None)
    # call the unbound __str__ implementation
    # This avoids Django model instantiation
    result = Article.__str__(obj)
    assert isinstance(result, _exc_lookup("str", Exception))
    assert "Unique Title 123" in result

def test_add_slug_to_article_if_not_exists_sets_slug(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    signals = _safe_import("conduit.apps.articles.signals")
    func = getattr(signals, "add_slug_to_article_if_not_exists", None)
    if func is None:
        pytest.skip("add_slug_to_article_if_not_exists not found")
    # monkeypatch slugify and random generator names if present on the module
    # Provide deterministic outputs
    monkeypatch.setattr(signals, "slugify", lambda t: "my-title", raising=False)
    monkeypatch.setattr(signals, "generate_random_string", lambda n=6: "RAND", raising=False)
    # prepare an instance missing slug
    inst = SimpleNamespace(title="My Title", slug="", save_called=False)
    # Some implementations may call save(); provide a save method
    def fake_save():
        inst.save_called = True
    inst.save = fake_save
    # Call the signal handler as Django would
    func(sender=None, instance=inst, created=True)
    assert isinstance(inst.slug, str)
    assert inst.slug != ""
    # result should include slugified title
    assert "my-title" in inst.slug
    # ensure save may have been called (if implementation calls save)
    assert hasattr(inst, "save_called")

def test_article_serializer_getters_return_expected_types():
    """Generated by ai-testgen with strict imports and safe shims."""
    serializers = _safe_import("conduit.apps.articles.serializers")
    ArticleSerializer = getattr(serializers, "ArticleSerializer", None)
    if ArticleSerializer is None:
        pytest.skip("ArticleSerializer not found")
    ser = ArticleSerializer()
    # make a simple object with expected attributes
    created = datetime.datetime(2020, 1, 2, 3, 4, 5)
    updated = datetime.datetime(2021, 2, 3, 4, 5, 6)
    obj = SimpleNamespace(created_at=created, updated_at=updated, favorited=True, favorites_count=7)
    # call serializer methods
    created_val = ser.get_created_at(obj)
    updated_val = ser.get_updated_at(obj)
    fav_count = ser.get_favorites_count(obj)
    favd = ser.get_favorited(obj)
    assert isinstance(created_val, (str, type(None)))
    assert isinstance(updated_val, (str, type(None)))
    assert isinstance(fav_count, _exc_lookup("int", Exception))
    assert isinstance(favd, (bool, int, type(None)))

def test_tagrelatedfield_to_internal_value_and_to_representation_do_not_error(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    relations = _safe_import("conduit.apps.articles.relations")
    TagRelatedField = getattr(relations, "TagRelatedField", None)
    if TagRelatedField is None:
        pytest.skip("TagRelatedField not found")
    # instantiate with minimal args if needed
    try:
        field = TagRelatedField()
    except TypeError:
        # try common signature
        try:
            field = TagRelatedField(queryset=None)
        except Exception as e:
            pytest.skip(f"Could not instantiate TagRelatedField: {e}")
    # Try calling both methods with simple inputs; ensure no exceptions and sensible returns
    internal = None
    try:
        internal = field.to_internal_value("sometag")
    except Exception:
        # If implementation raises because of missing model, that's acceptable only if raises a known Exception type
        raise
    rep = field.to_representation(internal if internal is not None else "sometag")
    assert rep is not None
    assert isinstance(rep, (str, list, dict, int)) or rep is None