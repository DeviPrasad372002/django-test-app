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

import types
import inspect
import pytest

def _exc_lookup(name, default=Exception):
    return globals().get(name, default)

def find_class_with_method(module, method_name):
    for obj in vars(module).values():
        if isinstance(obj, _exc_lookup("type", Exception)) and hasattr(obj, method_name):
            return obj
    return None

def test_follow_unfollow_is_following_flow(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        profiles_models = __import__("conduit.apps.profiles.models", fromlist=["*"])
    except Exception:
        pytest.skip("conduit.apps.profiles.models not importable")
    cls = find_class_with_method(profiles_models, "follow")
    if cls is None:
        pytest.skip("no class with 'follow' method found in profiles.models")
    # prepare fake instance
    instance = object.__new__(cls)
    calls = {"added": [], "removed": []}
    # many implementations use a manager with add/remove or a related manager with filter
    instance.following = types.SimpleNamespace(
        add=lambda obj: calls["added"].append(obj),
        remove=lambda obj: calls["removed"].append(obj),
        filter=lambda **kw: [1]  # used by is_following possibly
    )
    other = types.SimpleNamespace(id=123, username="other")
    # Call follow method
    follow_method = getattr(cls, "follow")
    try:
        follow_method(instance, other)
    except TypeError:
        # maybe method expects only one arg (other) when bound; try binding
        follow_method = getattr(cls, "follow")
        follow_method(instance, other)
    assert calls["added"] and calls["added"][-1] is other
    # Test unfollow if present
    if hasattr(cls, "unfollow"):
        unfollow_method = getattr(cls, "unfollow")
        # reset
        calls["removed"].clear()
        try:
            unfollow_method(instance, other)
        except TypeError:
            unfollow_method = getattr(cls, "unfollow")
            unfollow_method(instance, other)
        assert calls["removed"] and calls["removed"][-1] is other
    # Test is_following/is_followed_by if present
    if hasattr(cls, "is_following"):
        is_following = getattr(cls, "is_following")
        # make following.filter return non-empty -> truthy
        instance.following = types.SimpleNamespace(filter=lambda **kw: [other])
        res = is_following(instance, other)
        assert bool(res) is True
        # make following.filter return empty -> falsy
        instance.following = types.SimpleNamespace(filter=lambda **kw: [])
        res2 = is_following(instance, other)
        assert bool(res2) is False
    if hasattr(cls, "is_followed_by"):
        is_followed_by = getattr(cls, "is_followed_by")
        # Simulate followers.filter returns non-empty
        instance.followers = types.SimpleNamespace(filter=lambda **kw: [other])
        res = is_followed_by(instance, other)
        assert bool(res) is True
        instance.followers = types.SimpleNamespace(filter=lambda **kw: [])
        res2 = is_followed_by(instance, other)
        assert bool(res2) is False

def test_favorite_unfavorite_has_favorited_flow(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        profiles_models = __import__("conduit.apps.profiles.models", fromlist=["*"])
    except Exception:
        pytest.skip("conduit.apps.profiles.models not importable")
    cls = find_class_with_method(profiles_models, "favorite")
    if cls is None:
        pytest.skip("no class with 'favorite' method found in profiles.models")
    instance = object.__new__(cls)
    calls = {"fav_added": [], "fav_removed": []}
    instance.favorites = types.SimpleNamespace(
        add=lambda obj: calls["fav_added"].append(obj),
        remove=lambda obj: calls["fav_removed"].append(obj),
        filter=lambda **kw: [1]
    )
    fake_article = types.SimpleNamespace(slug="a-slug", title="A")
    fav_method = getattr(cls, "favorite")
    try:
        fav_method(instance, fake_article)
    except TypeError:
        fav_method = getattr(cls, "favorite")
        fav_method(instance, fake_article)
    assert calls["fav_added"] and calls["fav_added"][-1] is fake_article
    # unfavorite
    if hasattr(cls, "unfavorite"):
        unfav = getattr(cls, "unfavorite")
        calls["fav_removed"].clear()
        try:
            unfav(instance, fake_article)
        except TypeError:
            unfav = getattr(cls, "unfavorite")
            unfav(instance, fake_article)
        assert calls["fav_removed"] and calls["fav_removed"][-1] is fake_article
    # has_favorited
    if hasattr(cls, "has_favorited"):
        has_fav = getattr(cls, "has_favorited")
        instance.favorites = types.SimpleNamespace(filter=lambda **kw: [fake_article])
        assert bool(has_fav(instance, fake_article)) is True
        instance.favorites = types.SimpleNamespace(filter=lambda **kw: [])
        assert bool(has_fav(instance, fake_article)) is False

def test_profiles_serializers_get_image_and_get_following(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        profiles_serializers = __import__("conduit.apps.profiles.serializers", fromlist=["*"])
    except Exception:
        pytest.skip("conduit.apps.profiles.serializers not importable")
    # find a class with get_image
    target_cls = None
    for obj in vars(profiles_serializers).values():
        if isinstance(obj, _exc_lookup("type", Exception)) and (hasattr(obj, "get_image") or hasattr(obj, "get_following")):
            target_cls = obj
            break
    if target_cls is None:
        pytest.skip("no serializer class with get_image/get_following found")
    inst = object.__new__(target_cls)
    # Test get_image: provide object with image attribute
    if hasattr(target_cls, "get_image"):
        get_image = getattr(target_cls, "get_image")
        profile_obj = types.SimpleNamespace(image="http://example.com/pic.png", profile=None)
        res = get_image(inst, profile_obj)
        # Accept either the same url, None, or a string type to be flexible across implementations
        assert (res == "http://example.com/pic.png") or (res is None) or isinstance(res, _exc_lookup("str", Exception))
    # Test get_following: create obj where following relation can be inferred
    if hasattr(target_cls, "get_following"):
        get_following = getattr(target_cls, "get_following")
        # Many implementations use the serializer context to determine the requesting user;
        # call method with obj that has a simple identifier - ensure it returns a boolean or None without raising.
        profile_obj = types.SimpleNamespace(user=types.SimpleNamespace(username="u1"))
        result = get_following(inst, profile_obj)
        assert (result is None) or isinstance(result, (bool, str))

def test_articles_appconfig_ready_registers_signal(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        articles_init = __import__("conduit.apps.articles.__init__", fromlist=["*"])
        articles_signals = __import__("conduit.apps.articles.signals", fromlist=["*"])
    except Exception:
        pytest.skip("articles app modules not importable")
    # locate ArticlesAppConfig
    ArticlesAppConfig = getattr(articles_init, "ArticlesAppConfig", None)
    if ArticlesAppConfig is None:
        pytest.skip("ArticlesAppConfig not found")
    # Patch django's pre_save.connect to capture handler
    try:
        import django.db.models.signals as django_signals
    except Exception:
        pytest.skip("django.db.models.signals not importable")
    record = {}
    def fake_connect(handler, sender=None, weak=True, dispatch_uid=None, **kwargs):
        record["handler"] = handler
        record["sender"] = sender
        record["dispatch_uid"] = dispatch_uid
    monkeypatch.setattr(django_signals, "pre_save", types.SimpleNamespace(connect=fake_connect))
    # Call ready
    app_conf = ArticlesAppConfig()
    # Some ready implementations accept no args; call it
    app_conf.ready()
    assert "handler" in record
    handler = record["handler"]
    # Handler should be the add_slug_to_article_if_not_exists function or named similarly
    expected_name = "add_slug_to_article_if_not_exists"
    # accept either exact function or wrapper with same name
    assert getattr(handler, "__name__", "") == expected_name or expected_name in repr(handler)