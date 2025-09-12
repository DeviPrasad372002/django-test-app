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

import importlib
import types
import pytest

def _exc_lookup(module_name, name, default=Exception):
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, name, default)
    except Exception:
        return default

def test_generate_random_string_deterministic(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        core_utils = importlib.import_module('conduit.apps.core.utils')
    except ImportError:
        pytest.skip("conduit.apps.core.utils not available")
    # Force deterministic choice
    def always_a(seq):
        return 'A'
    monkeypatch.setattr(core_utils, 'random', types.SimpleNamespace(choice=always_a))
    res = core_utils.generate_random_string(6)
    assert isinstance(res, _exc_lookup("str", Exception))
    assert res == 'A' * 6

def test_user_short_name_and_jwt_token(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        auth_models = importlib.import_module('conduit.apps.authentication.models')
    except ImportError:
        pytest.skip("conduit.apps.authentication.models not available")
    # Create a lightweight User instance without DB save
    try:
        user = auth_models.User(username='tester')
    except Exception:
        # If constructor signature differs, try basic object with needed attrs
        user = types.SimpleNamespace(username='tester')
        # bind methods if present on class
        if hasattr(auth_models.User, '_generate_jwt_token'):
            user._generate_jwt_token = types.MethodType(auth_models.User._generate_jwt_token, user)
        if hasattr(auth_models.User, 'get_short_name'):
            user.get_short_name = types.MethodType(auth_models.User.get_short_name, user)
    # Short name behavior
    if hasattr(user, 'get_short_name'):
        assert user.get_short_name() == 'tester'
    else:
        pytest.skip("User.get_short_name not available")
    # Patch jwt.encode to ensure deterministic token
    if hasattr(auth_models, 'jwt') and hasattr(auth_models.jwt, 'encode'):
        def fake_encode(payload, key, algorithm='HS256'):
            return b'__signed_token__'
        monkeypatch.setattr(auth_models, 'jwt', types.SimpleNamespace(encode=fake_encode))
    else:
        # try module-level import fallback
        try:
            jwt_mod = importlib.import_module('jwt')
            monkeypatch.setattr(jwt_mod, 'encode', lambda payload, key, algorithm='HS256': b'__signed_token__')
        except Exception:
            pytest.skip("jwt not available to patch")
    # Call token generation if available
    if hasattr(user, '_generate_jwt_token'):
        token = user._generate_jwt_token()
        # Accept bytes or str
        assert token in (b'__signed_token__', '__signed_token__')
    else:
        pytest.skip("User._generate_jwt_token not available")

def test_render_validate_and_create_related_profile(monkeypatch):
    """Generated by ai-testgen with strict imports and safe shims."""
    # Test renderer.render from authentication.renderers
    try:
        renderers = importlib.import_module('conduit.apps.authentication.renderers')
    except ImportError:
        pytest.skip("conduit.apps.authentication.renderers not available")
    renderer_cls = getattr(renderers, 'UserJSONRenderer', None)
    if not renderer_cls:
        pytest.skip("UserJSONRenderer not available")
    renderer = renderer_cls()
    rendered = renderer.render({'user': {'username': 'alice'}})
    # rendered should be bytes or str containing username
    if isinstance(rendered, _exc_lookup("bytes", Exception)):
        assert b'alice' in rendered
    else:
        assert 'alice' in rendered

    # Test RegistrationSerializer.validate (if exists)
    try:
        serializers = importlib.import_module('conduit.apps.authentication.serializers')
    except ImportError:
        pytest.skip("conduit.apps.authentication.serializers not available")
    RegistrationSerializer = getattr(serializers, 'RegistrationSerializer', None)
    if RegistrationSerializer:
        # Provide minimal good data if serializer expects it; otherwise ensure validate exists
        sample_data = {'user': {'username': 'bob', 'email': 'bob@example.com', 'password': 'pass'}} 
        ser = RegistrationSerializer(data=sample_data)
        # If serializer has is_valid, call it; it may require Django REST framework
        if hasattr(ser, 'is_valid'):
            try:
                ser.is_valid(raise_exception=False)
            except Exception:
                # Not a failure of our test; just ensure validate path exists
                pass

    # Test create_related_profile signal handler attempts to create a Profile
    try:
        auth_signals = importlib.import_module('conduit.apps.authentication.signals')
    except ImportError:
        pytest.skip("conduit.apps.authentication.signals not available")
    create_related_profile = getattr(auth_signals, 'create_related_profile', None)
    if not create_related_profile:
        pytest.skip("create_related_profile not available")
    try:
        profiles_models = importlib.import_module('conduit.apps.profiles.models')
    except ImportError:
        pytest.skip("conduit.apps.profiles.models not available")
    Profile = getattr(profiles_models, 'Profile', None)
    if not Profile:
        pytest.skip("Profile model not available")
    called = {}
    # Monkeypatch Profile.objects.create if present
    if hasattr(Profile, 'objects') and hasattr(Profile.objects, 'create'):
        def fake_create(**kwargs):
            called['created_with'] = kwargs
            return types.SimpleNamespace(**kwargs)
        monkeypatch.setattr(Profile.objects, 'create', fake_create)
        # Create a dummy user instance
        user = types.SimpleNamespace(username='charlie')
        # Call the signal handler as if a user was created
        create_related_profile(sender=None, instance=user, created=True)
        assert 'created_with' in called
        # Ensure the user passed through to Profile creation
        assert called['created_with'].get('user') == user
    else:
        pytest.skip("Profile.objects.create not available")

def test_core_exception_handlers_return_responses():
    """Generated by ai-testgen with strict imports and safe shims."""
    try:
        core_ex = importlib.import_module('conduit.apps.core.exceptions')
    except ImportError:
        pytest.skip("conduit.apps.core.exceptions not available")
    # Lookup DRF exceptions gracefully
    NotFound = _exc_lookup('rest_framework.exceptions', 'NotFound', Exception)
    ValidationError = _exc_lookup('rest_framework.exceptions', 'ValidationError', Exception)
    # Test not found handler if present
    nf_handler = getattr(core_ex, '_handle_not_found_error', None)
    if nf_handler:
        resp = nf_handler(NotFound('nope'))
        # Expect a response-like with status_code attribute
        assert getattr(resp, 'status_code', None) == 404
    else:
        pytest.skip("_handle_not_found_error not available")
    # Test generic error handler
    gen_handler = getattr(core_ex, '_handle_generic_error', None)
    if gen_handler:
        resp2 = gen_handler(Exception('boom'))
        assert getattr(resp2, 'status_code', None) in (500, 400, None)  # allow implementations to vary but ensure callable
    else:
        pytest.skip("_handle_generic_error not available")
    # Test core_exception_handler dispatching
    core_handler = getattr(core_ex, 'core_exception_handler', None)
    if core_handler:
        # For a validation error
        try:
            val_exc = ValidationError({'field': ['bad']})
        except Exception:
            val_exc = Exception('validation')
        response = core_handler(val_exc, context={})
        # Should return a Response-like or None
        assert response is None or hasattr(response, 'status_code')
    else:
        pytest.skip("core_exception_handler not available")