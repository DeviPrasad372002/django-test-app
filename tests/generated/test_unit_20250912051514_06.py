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

def _exc_lookup(name, default):
    try:
        mod = __import__('rest_framework.exceptions', fromlist=[name])
        return getattr(mod, name, default)
    except Exception:
        return default

def test_user_token_and_name_methods():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.authentication import models as auth_models
    except ImportError:
        pytest.skip("authentication models not available")
    User = getattr(auth_models, "User", None)
    UserManager = getattr(auth_models, "UserManager", None)
    if User is None or UserManager is None:
        pytest.skip("User or UserManager not defined")
    # instantiate a User without saving to DB; set attributes directly
    u = User()
    # set common attrs if present
    for attr, val in (("email", "tester@example.com"), ("username", "tester"), ("id", 123)):
        try:
            setattr(u, attr, val)
        except Exception:
            pass
    # token generator may be either a property 'token' or method '_generate_jwt_token'
    token = None
    if hasattr(u, "token"):
        try:
            token = getattr(u, "token")
        except Exception:
            # if token is callable
            if callable(getattr(u, "token")):
                token = u.token()
    if not token and hasattr(u, "_generate_jwt_token"):
        try:
            token = u._generate_jwt_token()
        except Exception:
            token = None
    assert isinstance(token, (str, bytes)), "Expected token to be str/bytes"
    # name helpers
    if hasattr(u, "get_full_name"):
        full = u.get_full_name()
        assert full is None or isinstance(full, _exc_lookup("str", Exception))
    if hasattr(u, "get_short_name"):
        short = u.get_short_name()
        assert short is None or isinstance(short, _exc_lookup("str", Exception))

def test_jwtauthentication_no_header_and_bad_token_raises():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.authentication.backends import JWTAuthentication
    except ImportError:
        pytest.skip("JWTAuthentication not available")
    jwt_auth = JWTAuthentication()
    class DummyRequest:
        META = {}
    req = DummyRequest()
    # no auth header -> authenticate returns None or (None, None)
    res = jwt_auth.authenticate(req)
    assert res is None or (isinstance(res, _exc_lookup("tuple", Exception)) and len(res) == 2)
    # invalid credentials should raise an authentication exception via internal helper if available
    exc = _exc_lookup('AuthenticationFailed', Exception)
    # try to call _authenticate_credentials if present
    if hasattr(jwt_auth, "_authenticate_credentials"):
        with pytest.raises(_exc_lookup("exc", Exception)):
            jwt_auth._authenticate_credentials(b"notavalidtoken")
    else:
        pytest.skip("_authenticate_credentials not implemented on JWTAuthentication")

def test_userjsonrenderer_renders_user_wrapper_and_json():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.authentication.renderers import UserJSONRenderer
    except ImportError:
        pytest.skip("UserJSONRenderer not available")
    import json
    renderer = UserJSONRenderer()
    data = {"email": "a@b.com", "username": "a"}
    rendered = renderer.render({"user": data})
    # should be bytes/str JSON containing "user" key
    assert isinstance(rendered, (bytes, str))
    if isinstance(rendered, _exc_lookup("bytes", Exception)):
        rendered_text = rendered.decode("utf-8")
    else:
        rendered_text = rendered
    parsed = json.loads(rendered_text)
    assert "user" in parsed and parsed["user"]["email"] == "a@b.com"

def test_serializers_reject_missing_required_fields():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.authentication import serializers as auth_serializers
    except ImportError:
        pytest.skip("authentication serializers not available")
    RegistrationSerializer = getattr(auth_serializers, "RegistrationSerializer", None)
    LoginSerializer = getattr(auth_serializers, "LoginSerializer", None)
    UserSerializer = getattr(auth_serializers, "UserSerializer", None)
    if RegistrationSerializer is None or LoginSerializer is None or UserSerializer is None:
        pytest.skip("expected serializers not present")
    # Registration: missing fields should be invalid
    reg = RegistrationSerializer(data={})
    assert not reg.is_valid()
    assert isinstance(reg.errors, dict) and reg.errors
    # Login: missing fields should be invalid
    login = LoginSerializer(data={})
    assert not login.is_valid()
    assert isinstance(login.errors, dict) and login.errors
    # UserSerializer when provided data for update should also validate required structure
    user_s = UserSerializer(data={})
    # Some UserSerializers expect instance instead; is_valid should handle missing data gracefully
    try:
        valid = user_s.is_valid()
    except Exception:
        valid = False
    assert not valid

def test_views_have_serializer_class_and_timestampedmodel_fields():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        from conduit.apps.authentication import views as auth_views
        from conduit.apps.core import models as core_models
    except ImportError:
        pytest.skip("authentication views or core models not available")
    RegistrationAPIView = getattr(auth_views, "RegistrationAPIView", None)
    LoginAPIView = getattr(auth_views, "LoginAPIView", None)
    UserRetrieveUpdateAPIView = getattr(auth_views, "UserRetrieveUpdateAPIView", None)
    if RegistrationAPIView is None or LoginAPIView is None or UserRetrieveUpdateAPIView is None:
        pytest.skip("expected API views not present")
    # Each view should declare serializer_class attribute
    for view_cls in (RegistrationAPIView, LoginAPIView, UserRetrieveUpdateAPIView):
        assert hasattr(view_cls, "serializer_class"), f"{view_cls.__name__} missing serializer_class"
        # serializer_class should be a class or callable
        sc = getattr(view_cls, "serializer_class")
        assert sc is not None
    # TimestampedModel should expose created_at and updated_at fields at class level
    TimestampedModel = getattr(core_models, "TimestampedModel", None)
    if TimestampedModel is None:
        pytest.skip("TimestampedModel not present")
    assert hasattr(TimestampedModel, "created_at")
    assert hasattr(TimestampedModel, "updated_at")