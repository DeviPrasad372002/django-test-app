import importlib.util, pytest
if importlib.util.find_spec('django') is None:
    pytest.skip('django not installed; skipping module', allow_module_level=True)

# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib as _importlib, importlib.util as _iu, importlib.machinery as _im, types as _types, pytest as _pytest, builtins as _builtins
import warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
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
    try:
        import collections as _collections, collections.abc as _abc
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container',
                   'MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
            if not hasattr(_collections, _n) and hasattr(_abc, _n):
                setattr(_collections, _n, getattr(_abc, _n))
    except Exception:
        pass
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

# Disable import adapter entirely if Django is present to avoid metaclass issues.
_DJ_PRESENT = _iu.find_spec("django") is not None
if not STRICT and not _DJ_PRESENT:
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

# Handle Django configuration for tests
try:
    import django
    from django.conf import settings
    from django import apps as _dj_apps
    
    if not settings.configured:
        _cfg = dict(
            DEBUG=True,
            SECRET_KEY='test-secret-key-for-pytest',
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
            ],
            MIDDLEWARE=[
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
            ],
            USE_TZ=True,
            TIME_ZONE="UTC",
        )
        try:
            _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
        except Exception:
            pass
        try:
            settings.configure(**_cfg)
        except Exception as e:
            pass
    
    if not _dj_apps.ready:
        try:
            django.setup()
        except Exception as e:
            pass
            
except Exception as e:
    pass



# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

try:
    import pytest
    import json
    import string
    from conduit.apps.core.utils import generate_random_string
    import conduit.apps.core.exceptions as core_excs
    from conduit.apps.authentication.signals import create_related_profile
    import conduit.apps.authentication.signals as auth_signals
    from conduit.apps.authentication.renderers import UserJSONRenderer
    import rest_framework.exceptions as drf_exceptions
except ImportError as e:
    import pytest
    pytest.skip("Required modules not available: " + str(e), allow_module_level=True)


@pytest.mark.parametrize("length", [0, 1, 8, 50])
def test_generate_random_string_length_and_characters(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    requested_length = length

    # Act
    result = generate_random_string(requested_length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == requested_length
    assert all(c.isalnum() for c in result)


def test_core_exception_handler_delegates_to_specific_handlers(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    recorded = {"generic": 0, "notfound": 0}

    def generic_stub(exc, context):
        recorded["generic"] += 1
        return {"handled_by": "generic", "detail": str(exc)}

    def notfound_stub(exc, context):
        recorded["notfound"] += 1
        return {"handled_by": "notfound", "detail": str(exc)}

    monkeypatch.setattr(core_excs, "_handle_generic_error", generic_stub)
    monkeypatch.setattr(core_excs, "_handle_not_found_error", notfound_stub)

    # Act - generic exception
    generic_result = core_excs.core_exception_handler(Exception("boom"), {})

    # Assert - generic path
    assert generic_result == {"handled_by": "generic", "detail": "boom"}
    assert recorded["generic"] == 1
    assert recorded["notfound"] == 0

    # Act - not found exception
    nf = drf_exceptions.NotFound("missing")
    notfound_result = core_excs.core_exception_handler(nf, {})

    # Assert - not found path
    assert notfound_result == {"handled_by": "notfound", "detail": "missing"}
    assert recorded["notfound"] == 1


def test_create_related_profile_creates_profile_when_created(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyManager:
        def __init__(self):
            self.created_kwargs = None

        def create(self, **kwargs):
            self.created_kwargs = kwargs
            return {"created": True, "kwargs": kwargs}

    class DummyProfile:
        objects = DummyManager()

    dummy_user = type("U", (), {"id": 42, "username": "tester"})()

    # Patch the Profile reference inside the authentication.signals module
    monkeypatch.setattr(auth_signals, "Profile", DummyProfile)

    # Act - created=True should create profile
    result_when_created = create_related_profile(sender=None, instance=dummy_user, created=True, **{})

    # Assert
    assert DummyProfile.objects.created_kwargs == {"user": dummy_user}
    # Some signal handlers return None; if a value is returned ensure it's the created marker
    if result_when_created is not None:
        assert isinstance(result_when_created, _exc_lookup("dict", Exception)) or result_when_created == {"created": True, "kwargs": {"user": dummy_user}}

    # Reset manager state
    DummyProfile.objects.created_kwargs = None

    # Act - created=False should NOT create profile
    result_when_not_created = create_related_profile(sender=None, instance=dummy_user, created=False, **{})

    # Assert no creation occurred
    assert DummyProfile.objects.created_kwargs is None
    if result_when_not_created is not None:
        assert result_when_not_created != {"created": True, "kwargs": {"user": dummy_user}}


def test_userjsonrenderer_render_outputs_expected_json_structure():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = UserJSONRenderer()
    user_payload = {"username": "alice", "email": "alice@example.test"}
    input_data = {"user": user_payload}

    # Act
    rendered = renderer.render(input_data, accepted_media_type=None, renderer_context=None)

    # Assert
    assert isinstance(rendered, (bytes, str))
    text = rendered.decode("utf-8") if isinstance(rendered, _exc_lookup("bytes", Exception)) else rendered
    parsed = json.loads(text)
    assert "user" in parsed
    assert isinstance(parsed["user"], dict)
    assert parsed["user"].get("username") == "alice"
    assert parsed["user"].get("email") == "alice@example.test"
