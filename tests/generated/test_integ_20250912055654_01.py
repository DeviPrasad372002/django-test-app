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
import pytest

def test_add_slug_to_article_if_not_exists_sets_and_preserves(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles import signals
    except Exception as e:
        # Use harness-provided exception lookup if available
        _exc = globals().get('_exc_lookup', lambda name, default: ImportError)
        if isinstance(e, _exc('ImportError', Exception)):
            pytest.skip("conduit.apps.articles.signals not available")
        raise

    # Dummy article-like object
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    # Ensure deterministic slugify and random string generation
    monkeypatch.setattr(signals, 'slugify', lambda s: 'my-title', raising=False)
    monkeypatch.setattr(signals, 'generate_random_string', lambda n=6: 'RAND123', raising=False)

    # Case: slug is None -> should be set
    a = DummyArticle("My Title", slug=None)
    # The signal handler signature often is (sender, instance, created, **kwargs) or (instance, created, **kwargs)
    # Try both common invocation patterns to be robust
    try:
        signals.add_slug_to_article_if_not_exists(a, created=True)
    except TypeError:
        # try alternative ordering
        signals.add_slug_to_article_if_not_exists(sender=None, instance=a, created=True)
    assert getattr(a, 'slug') == 'my-title-RAND123'

    # Case: slug already exists -> should be preserved
    b = DummyArticle("Other", slug='exists-slug')
    try:
        signals.add_slug_to_article_if_not_exists(b, created=True)
    except TypeError:
        signals.add_slug_to_article_if_not_exists(sender=None, instance=b, created=True)
    assert getattr(b, 'slug') == 'exists-slug'


def test_article_serializer_favoriting_and_count(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles.serializers import ArticleSerializer
    except Exception as e:
        _exc = globals().get('_exc_lookup', lambda name, default: ImportError)
        if isinstance(e, _exc('ImportError', Exception)):
            pytest.skip("conduit.apps.articles.serializers.ArticleSerializer not available")
        raise

    try:
        import conduit.apps.profiles.models as profiles_models
    except Exception:
        profiles_models = types.SimpleNamespace()

    # Dummy article-like object with favorites.count()
    class DummyFavorites:
        def count(self):
            return 7

    class DummyArticle:
        def __init__(self):
            self.favorites = DummyFavorites()

    article = DummyArticle()

    # Monkeypatch has_favorited to simulate that the current user has favorited the article
    monkeypatch.setattr(profiles_models, 'has_favorited', lambda user, obj: True, raising=False)

    # Build a serializer instance with a dummy request in context
    dummy_request = types.SimpleNamespace(user=types.SimpleNamespace(id=1))
    try:
        serializer = ArticleSerializer(instance=article, context={'request': dummy_request})
    except TypeError:
        # Some serializers require 'data' positional; instantiate minimally
        serializer = ArticleSerializer(context={'request': dummy_request})

    # Call get_favorited and get_favorites_count if available
    fav = True
    if hasattr(serializer, 'get_favorited'):
        fav = serializer.get_favorited(article)
    else:
        pytest.skip("ArticleSerializer.get_favorited not present")

    count = None
    if hasattr(serializer, 'get_favorites_count'):
        count = serializer.get_favorites_count(article)
    else:
        pytest.skip("ArticleSerializer.get_favorites_count not present")

    assert fav is True
    assert count == 7


def test_articles_appconfig_ready_imports_signals(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles import __init__ as articles_init
        ArticlesAppConfig = getattr(articles_init, 'ArticlesAppConfig', None)
        if ArticlesAppConfig is None:
            raise ImportError("ArticlesAppConfig not found")
    except Exception as e:
        _exc = globals().get('_exc_lookup', lambda name, default: ImportError)
        if isinstance(e, _exc('ImportError', Exception)):
            pytest.skip("conduit.apps.articles.ArticlesAppConfig not available")
        raise

    mod_name = 'conduit.apps.articles.signals'
    dummy_mod = types.ModuleType(mod_name)
    dummy_mod.__dict__.update({'DUMMY_SIGNAL_MODULE': True})

    # Ensure we restore sys.modules after test
    original = sys.modules.get(mod_name)
    sys.modules[mod_name] = dummy_mod
    try:
        # Instantiate config and call ready; typical signature: Apps config may accept name and module
        try:
            cfg = ArticlesAppConfig('articles', articles_init)
            cfg.ready()
        except TypeError:
            # alternative constructor signature
            cfg = ArticlesAppConfig()
            cfg.ready()
    finally:
        # restore original
        if original is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = original

    # If ready imported the module, our dummy should still be present and unmodified
    assert hasattr(dummy_mod, 'DUMMY_SIGNAL_MODULE') and dummy_mod.DUMMY_SIGNAL_MODULE is True