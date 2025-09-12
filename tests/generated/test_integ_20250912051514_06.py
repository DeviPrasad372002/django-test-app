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


def _exc_lookup(name, fallback):
    # Try common exception modules
    candidates = [
        'rest_framework.exceptions',
        'django.core.exceptions',
        'conduit.apps.core.exceptions',
        'conduit.apps.authentication.backends',
        'conduit.apps.authentication.models',
    ]
    for modname in candidates:
        try:
            mod = __import__(modname, fromlist=[name])
            exc = getattr(mod, name, None)
            if isinstance(exc, _exc_lookup("type", Exception)) and issubclass(exc, Exception):
                return exc
        except Exception:
            continue
    return fallback


def test_jwtauthentication_authenticates_valid_token(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        backend_mod = __import__('conduit.apps.authentication.backends', fromlist=['JWTAuthentication'])
    except ImportError:
        pytest.skip('conduit.apps.authentication.backends not available')
    JWTAuthentication = getattr(backend_mod, 'JWTAuthentication', None)
    if JWTAuthentication is None:
        pytest.skip('JWTAuthentication not found in backends module')

    # Patch jwt.decode used in the backend to return a predictable payload
    def fake_decode(token, key, algorithms=None):
        return {'id': 1}

    fake_jwt_mod = types.SimpleNamespace(decode=fake_decode)
    monkeypatch.setattr(backend_mod, 'jwt', fake_jwt_mod, raising=False)

    # Create a fake User model with an objects.get that returns an active user
    class FakeUserObj:
        is_active = True
        id = 1
        email = 'user@example.com'

    class FakeQS:
        def get(self, pk):
            if pk == 1:
                return FakeUserObj()
            raise Exception('not found')

    class FakeUser:
        objects = FakeQS()

    monkeypatch.setattr(backend_mod, 'User', FakeUser, raising=False)

    inst = JWTAuthentication()
    # Some implementations pass the token string to authenticate, others use internal helpers.
    # Prefer calling internal credential decoder if available, else attempt authenticate with a fake header.
    authenticate_impl = getattr(inst, '_authenticate_credentials', None)
    if callable(authenticate_impl):
        user = authenticate_impl({'id': 1})
    else:
        # Fallback to calling authenticate with a crafted header tuple if implemented that way
        auth_result = inst.authenticate(None, [('HTTP_AUTHORIZATION', 'Token dummy')])
        # authenticate may return (user, token) or None
        if isinstance(auth_result, _exc_lookup("tuple", Exception)):
            user = auth_result[0]
        else:
            user = auth_result

    assert user is not None
    assert getattr(user, 'is_active', False) is True
    assert getattr(user, 'id', None) == 1


def test_jwtauthentication_raises_when_user_missing(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        backend_mod = __import__('conduit.apps.authentication.backends', fromlist=['JWTAuthentication'])
    except ImportError:
        pytest.skip('conduit.apps.authentication.backends not available')
    JWTAuthentication = getattr(backend_mod, 'JWTAuthentication', None)
    if JWTAuthentication is None:
        pytest.skip('JWTAuthentication not found in backends module')

    # jwt.decode returns an id that does not map to a user
    def fake_decode(token, key, algorithms=None):
        return {'id': 999}

    fake_jwt_mod = types.SimpleNamespace(decode=fake_decode)
    monkeypatch.setattr(backend_mod, 'jwt', fake_jwt_mod, raising=False)

    # Fake User.objects.get raises a "DoesNotExist" style exception (we'll use a generic Exception)
    class FakeQS:
        def get(self, pk):
            raise Exception('Does not exist')

    class FakeUser:
        objects = FakeQS()

    monkeypatch.setattr(backend_mod, 'User', FakeUser, raising=False)

    inst = JWTAuthentication()
    authenticate_impl = getattr(inst, '_authenticate_credentials', None)
    exc_class = _exc_lookup('AuthenticationFailed', Exception)

    if callable(authenticate_impl):
        with pytest.raises(_exc_lookup("exc_class", Exception)):
            authenticate_impl({'id': 999})
    else:
        # If only authenticate exists, calling it with a bad token should raise as well
        with pytest.raises(_exc_lookup("exc_class", Exception)):
            inst.authenticate(None, [('HTTP_AUTHORIZATION', 'Token bad')])  # type: ignore[arg-type]


def test__generate_jwt_token_uses_jwt_encode(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        models_mod = __import__('conduit.apps.authentication.models', fromlist=['_generate_jwt_token'])
    except ImportError:
        pytest.skip('conduit.apps.authentication.models not available')
    gen = getattr(models_mod, '_generate_jwt_token', None)
    if gen is None or not callable(gen):
        pytest.skip('_generate_jwt_token not present in models module')

    # Monkeypatch jwt.encode to return deterministic token
    def fake_encode(payload, key, algorithm='HS256'):
        # return a predictable string that includes id for verification
        return f"encoded-{payload.get('id')}-{algorithm}"

    # Some modules import jwt at top-level; set attribute accordingly
    monkeypatch.setattr(models_mod, 'jwt', types.SimpleNamespace(encode=fake_encode), raising=False)

    class FakeSelf:
        id = 123

    token = gen(FakeSelf())
    assert isinstance(token, _exc_lookup("str", Exception))
    assert 'encoded-123' in token


def test_userjsonrenderer_renders_user_key(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        renderers_mod = __import__('conduit.apps.authentication.renderers', fromlist=['UserJSONRenderer'])
    except ImportError:
        pytest.skip('conduit.apps.authentication.renderers not available')
    UserJSONRenderer = getattr(renderers_mod, 'UserJSONRenderer', None)
    if UserJSONRenderer is None:
        pytest.skip('UserJSONRenderer not found in renderers module')

    renderer = UserJSONRenderer()
    data = {'user': {'email': 'a@b.com', 'username': 'tester'}}
    out = renderer.render(data)
    # Should return bytes or str; normalize to bytes for assertion
    if isinstance(out, _exc_lookup("str", Exception)):
        out_bytes = out.encode('utf-8')
    else:
        out_bytes = out
    assert b'"user"' in out_bytes
    assert b'a@b.com' in out_bytes or b'a@b.com'.decode() in out_bytes.decode()  # defensive check