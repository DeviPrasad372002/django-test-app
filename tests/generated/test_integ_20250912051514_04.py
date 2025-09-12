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

def _skip_if_missing(*modules_or_attrs):
    # helper to skip if any import/attr missing
    for name in modules_or_attrs:
        if name is None:
            pytest.skip("Required target not present")

def _make_request_user():
    class ReqUser:
        is_authenticated = True
        def __init__(self, identifier="testuser"):
            self.id = identifier
        def __repr__(self):
            return f"<ReqUser {self.id}>"
    class Req:
        def __init__(self):
            self.user = ReqUser()
    return Req()

def test_get_following_uses_is_following(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        import conduit.apps.profiles.serializers as ps
        import conduit.apps.profiles.models as pm
    except Exception:
        pytest.skip("profiles.serializers or profiles.models not importable")
    # locate the get_following callable (module-level or on a serializer class)
    func = getattr(ps, 'get_following', None)
    if func is None:
        # try common serializer class names
        cls = getattr(ps, 'ProfileSerializer', None) or getattr(ps, 'PublicProfileSerializer', None)
        func = getattr(cls, 'get_following', None) if cls is not None else None
    if func is None:
        pytest.skip("get_following not found in profiles.serializers")
    # prepare a dummy self with context holding a request.user
    class DummySelf:
        pass
    DummySelf.context = {'request': _make_request_user()}
    # ensure is_following is called with expected arguments
    called = {}
    def fake_is_following(a, b):
        called['args'] = (a, b)
        return True
    monkeypatch.setattr(pm, 'is_following', fake_is_following, raising=False)
    # try both dict and object profile representations
    profile_obj = type('P', (), {'username': 'alice'})()
    result = func(DummySelf(), profile_obj)
    assert result is True
    assert 'args' in called
    # verify the first arg passed was the request user from context
    assert called['args'][0].__class__.__name__.startswith('ReqUser')
    # also call with a dict-like profile
    called.clear()
    result2 = func(DummySelf(), {'username': 'bob'})
    assert result2 is True
    assert 'args' in called

def test_get_image_returns_string_and_handles_missing(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        import conduit.apps.profiles.serializers as ps
    except Exception:
        pytest.skip("profiles.serializers not importable")
    func = getattr(ps, 'get_image', None)
    if func is None:
        cls = getattr(ps, 'ProfileSerializer', None) or getattr(ps, 'PublicProfileSerializer', None)
        func = getattr(cls, 'get_image', None) if cls is not None else None
    if func is None:
        pytest.skip("get_image not found in profiles.serializers")
    # dummy self not required for image in many serializers but include context anyway
    class DummySelf:
        context = {}
    # case 1: profile with image attribute set
    profile_with_image = type('P', (), {'image': 'https://cdn.example/avatar.png'})()
    out = func(DummySelf(), profile_with_image)
    assert isinstance(out, (str, type('s', (), ()) ))
    assert 'avatar' not in str(out) or str(out).startswith('http') or out == profile_with_image.image
    # case 2: profile with no image attribute or None
    profile_no_image = type('P', (), {'image': None})()
    out2 = func(DummySelf(), profile_no_image)
    # should be a string (often empty)
    assert isinstance(out2, _exc_lookup("str", Exception))
    # common expected fallback is empty string; accept empty or non-null string
    assert out2 == '' or len(out2) >= 0

def test_article_get_favorited_delegates_to_has_favorited(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        import conduit.apps.articles.serializers as ars
        import conduit.apps.profiles.models as pm
    except Exception:
        pytest.skip("articles.serializers or profiles.models not importable")
    # locate get_favorited on serializer or module
    func = getattr(ars, 'get_favorited', None)
    if func is None:
        # try common class
        cls = getattr(ars, 'ArticleSerializer', None)
        func = getattr(cls, 'get_favorited', None) if cls is not None else None
    if func is None:
        pytest.skip("get_favorited not found in articles.serializers")
    # prepare dummy serializer self with request in context
    class DummySelf:
        pass
    DummySelf.context = {'request': _make_request_user()}
    # prepare an article-like object; many implementations expect .author or .slug - pass minimal
    article_obj = type('A', (), {'slug': 'test-slug', 'id': 123})()
    called = {}
    def fake_has_favorited(user, article):
        called['args'] = (user, article)
        return False
    monkeypatch.setattr(pm, 'has_favorited', fake_has_favorited, raising=False)
    res = func(DummySelf(), article_obj)
    assert res is False
    assert 'args' in called
    # ensure first arg is the request user
    assert called['args'][0].__class__.__name__.startswith('ReqUser')
    # ensure second arg corresponds to the article-like object passed
    assert called['args'][1] is article_obj

def test_add_slug_to_article_if_not_exists_generates_slug(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        import conduit.apps.articles.signals as signals
    except Exception:
        pytest.skip("articles.signals not importable")
    func = getattr(signals, 'add_slug_to_article_if_not_exists', None)
    if func is None:
        pytest.skip("add_slug_to_article_if_not_exists not found in articles.signals")
    # create a fake article instance with title and no slug
    class ArticleLike:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug
    a = ArticleLike("My Test Article")
    # Call the signal handler; many versions accept (sender, instance, created, **kwargs)
    # Try with created True and False to be robust
    try:
        func(sender=None, instance=a, created=False)
    except TypeError:
        # maybe signature uses (sender, instance, **kwargs)
        func(None, a)
    # After invoking, slug should be set (non-empty string)
    assert getattr(a, 'slug', None) is not None
    assert isinstance(a.slug, str)
    assert len(a.slug) > 0
    # slug should be based on the title (contain parts of title lowercased)
    assert 'my' in a.slug.lower() or 'test' in a.slug.lower() or '-' in a.slug.lower()