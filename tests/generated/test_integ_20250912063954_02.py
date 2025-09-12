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
import pytest

def test_create_superuser_calls_create_user_with_super_flags(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.authentication import models as auth_models
    except ImportError:
        pytest.skip("conduit.apps.authentication.models not available")
    # Instantiate a UserManager and ensure create_superuser delegates to create_user with proper flags
    manager = auth_models.UserManager()
    called = {}
    def fake_create_user(self, email, password=None, **extra_fields):
        called['email'] = email
        called['password'] = password
        called['extra_fields'] = extra_fields.copy()
        class DummyUser:
            pass
        u = DummyUser()
        # reflect flags back on returned object for assertions
        u.is_staff = extra_fields.get('is_staff', False)
        u.is_superuser = extra_fields.get('is_superuser', False)
        return u
    # Patch the instance method on the class so bound method works
    monkeypatch.setattr(auth_models.UserManager, 'create_user', fake_create_user, raising=False)
    # Call create_superuser; signatures may vary, but typically take email and password
    try:
        superuser = manager.create_superuser('admin@example.test', 'pw123')
    except TypeError:
        # try alternative signature with username/email keyword
        superuser = manager.create_superuser(email='admin@example.test', password='pw123')
    assert called, "create_user was not called by create_superuser"
    assert called['email'] == 'admin@example.test'
    assert superuser.is_staff is True
    assert superuser.is_superuser is True

def test_jwt_authentication__authenticate_credentials_returns_user(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.authentication import backends as auth_backends
    except ImportError:
        pytest.skip("conduit.apps.authentication.backends not available")
    # Prepare a fake user model and patch get_user_model used inside backend
    class FakeObjects:
        def __init__(self, instance):
            self._instance = instance
        def get(self, **kwargs):
            # Accept common lookup keys id or pk or user_id
            if any(k in kwargs for k in ('id', 'pk', 'user_id')):
                return self._instance
            raise LookupError("not found")
    class FakeUser:
        def __init__(self, uid=1, email='u@test'):
            self.id = uid
            self.email = email
            self.is_active = True
    fake_user = FakeUser(uid=42, email='decoded@test')
    class FakeModel:
        objects = FakeObjects(fake_user)
    # Patch get_user_model in the backend module to return our FakeModel
    monkeypatch.setattr(auth_backends, 'get_user_model', lambda: FakeModel, raising=False)
    # Construct a JWTAuthentication instance and call _authenticate_credentials with a payload
    backend = auth_backends.JWTAuthentication()
    # Common payload key could be 'id' or 'user_id'; provide both to be tolerant
    payload = {'id': 42, 'email': 'decoded@test'}
    user = backend._authenticate_credentials(payload)
    assert user is fake_user
    assert getattr(user, 'email', None) == 'decoded@test'

def test_add_slug_to_article_if_not_exists_generates_and_saves(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles import signals as article_signals
    except ImportError:
        pytest.skip("conduit.apps.articles.signals not available")
    # Prepare deterministic slug generator
    def fake_generate_random_string(length=6):
        return 'fixedslug'
    # Attempt to monkeypatch where the signal function expects it
    if hasattr(article_signals, 'generate_random_string'):
        monkeypatch.setattr(article_signals, 'generate_random_string', fake_generate_random_string, raising=False)
    else:
        # fallback to core utils if signals import from there
        try:
            from conduit.apps.core import utils as core_utils
            monkeypatch.setattr(core_utils, 'generate_random_string', fake_generate_random_string, raising=False)
        except Exception:
            # if not present, continue; the signal may not call it
            pass
    # Fake article instance
    saved = {}
    class FakeArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug
        def save(self, *args, **kwargs):
            saved['called'] = True
    article = FakeArticle(title="My Test Title", slug=None)
    # Call the signal handler as Django would: sender, instance, created, **kwargs
    try:
        article_signals.add_slug_to_article_if_not_exists(sender=object, instance=article, created=True)
    except Exception as exc:
        # If the function raises due to environment, fail the test with a helpful message
        raise
    assert getattr(article, 'slug', None) is not None, "Slug was not set on the article"
    assert saved.get('called', False) is True

def test_comments_destroy_api_view_deletes_comment_and_returns_response(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.articles import views as articles_views
    except ImportError:
        pytest.skip("conduit.apps.articles.views not available")
    # Instantiate the view and monkeypatch get_object to return a fake comment
    view = articles_views.CommentsDestroyAPIView()
    deleted = {}
    class FakeComment:
        def delete(self_inner):
            deleted['called'] = True
    fake_comment = FakeComment()
    # Replace view.get_object to return our fake comment regardless of kwargs
    monkeypatch.setattr(view, 'get_object', lambda *args, **kwargs: fake_comment, raising=False)
    # Create a minimal request-like object; some views may expect request.user
    request = types.SimpleNamespace(user=None)
    # Call delete; many DRF views accept (request, *args, **kwargs)
    response = view.delete(request, pk=1)
    # If the view returned a Response, check status_code; otherwise ensure deletion occurred
    if hasattr(response, 'status_code'):
        assert response.status_code in (200, 204)
    assert deleted.get('called', False) is True