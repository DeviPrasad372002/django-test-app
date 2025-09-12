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

def test_user_token_generation(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    import pytest
    try:
        import conduit.apps.authentication.models as auth_models
    except ImportError:
        pytest.skip("authentication.models not available")
    # Ensure jwt.encode used inside the module is deterministic
    def fake_encode(payload, key, algorithm='HS256'):
        # return bytes as jwt.encode often does in pyjwt<2 or bytes-like in places
        return b"fixed-token-bytes"
    monkeypatch.setattr(auth_models.jwt, "encode", fake_encode, raising=False)

    # Create a lightweight User instance without DB operations
    User = auth_models.User
    # instantiate model-like object; Django model __init__ usually accepts kwargs
    try:
        user = User(email="tester@example.com", username="tester", id=42)
    except TypeError:
        # fallback: construct via types.SimpleNamespace if instantiation fails
        user = types.SimpleNamespace(email="tester@example.com", username="tester", id=42)
        # attach module method if token property expects instance methods
        if hasattr(User, "_generate_jwt_token"):
            # bind function to our simple namespace
            func = getattr(User, "_generate_jwt_token")
            user._generate_jwt_token = types.MethodType(func, user)

    # Access token attribute or method
    token_attr = getattr(user, "token", None)
    if callable(token_attr):
        token_val = token_attr()
    else:
        token_val = token_attr

    # If token property delegates to _generate_jwt_token
    if token_val is None and hasattr(user, "_generate_jwt_token"):
        token_val = user._generate_jwt_token()

    assert token_val is not None
    # Accept bytes or str
    token_str = token_val.decode() if isinstance(token_val, (bytes, bytearray)) else str(token_val)
    assert "fixed-token-bytes" in token_str


def test_jwt_authentication_success(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    import pytest
    try:
        import conduit.apps.authentication.backends as backends
        import conduit.apps.authentication.models as auth_models
    except ImportError:
        pytest.skip("authentication backend or models not available")

    # Prepare a dummy user object to be returned by queryset lookup
    class DummyUser:
        def __init__(self):
            self.id = 5
            self.email = "d@example.com"
    dummy = DummyUser()

    # Patch jwt.decode used in backend to return expected payload
    def fake_decode(token, key, algorithms=None):
        return {"id": dummy.id}
    monkeypatch.setattr(backends, "jwt", backends.jwt, raising=False)
    monkeypatch.setattr(backends.jwt, "decode", fake_decode, raising=False)

    # Patch User.objects.get to return our dummy user when looked up by id
    # Try to set on the actual model if present; otherwise patch the reference in backend
    try:
        # If backend imports User from models, patch models' User.objects
        class FakeManager:
            def get(self, **kwargs):
                return dummy
        monkeypatch.setattr(auth_models.User, "objects", FakeManager(), raising=False)
    except Exception:
        # Fallback: patch the User referenced inside backend module if present
        if hasattr(backends, "User"):
            class FakeManager2:
                def get(self, **kwargs):
                    return dummy
            try:
                monkeypatch.setattr(backends.User, "objects", FakeManager2(), raising=False)
            except Exception:
                pytest.skip("Unable to patch User.objects for authentication test")

    # Build a minimal request-like object with headers/meta expected by backend
    class Req:
        META = {"HTTP_AUTHORIZATION": "Token sometoken", "Authorization": "Token sometoken"}
    request = Req()

    auth = backends.JWTAuthentication()
    result = auth.authenticate(request)
    # authentication backends may return None on failure or (user, token) on success
    assert result is not None, "Expected authentication to return a (user, token) tuple"
    assert isinstance(result, _exc_lookup("tuple", Exception)) and len(result) == 2
    returned_user, returned_token = result
    assert returned_user is dummy
    # Ensure token returned is the provided token string or similar
    assert returned_token is not None
    # token could be str or bytes; normalize and check substring
    rt = returned_token.decode() if isinstance(returned_token, (bytes, bytearray)) else str(returned_token)
    assert "sometoken" in rt


def test_user_json_renderer_renders_expected_structure():
    """Generated by ai-testgen with strict imports and safe shims."""
    import pytest
    try:
        from conduit.apps.authentication.renderers import UserJSONRenderer
    except ImportError:
        pytest.skip("authentication.renderers not available")

    renderer = UserJSONRenderer()
    sample = {"user": {"email": "alice@example.com", "username": "alice"}}
    rendered = renderer.render(sample, renderer_context={})
    # renderer should produce bytes or str containing the keys and values
    assert rendered is not None
    rendered_bytes = rendered if isinstance(rendered, (bytes, bytearray)) else str(rendered).encode()
    assert b'"user"' in rendered_bytes or b"user" in rendered_bytes
    assert b"alice@example.com" in rendered_bytes
    assert b"alice" in rendered_bytes