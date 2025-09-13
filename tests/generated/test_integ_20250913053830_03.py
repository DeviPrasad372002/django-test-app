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
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet'):
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
_THIRD_PARTY_TOPS = ['__future__', 'conduit', 'datetime', 'django', 'json', 'jwt', 'models', 'os', 'random', 'relations', 'renderers', 'rest_framework', 'serializers', 'string', 'views']

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest as _pytest
# If a target import fails, skip the whole module rather than passing silently.
try:
    pass
except ImportError as _e:
    import pytest as _pytest; _pytest.skip(str(_e), allow_module_level=True)
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

import pytest
from types import SimpleNamespace

try:
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.core.utils as core_utils
    import conduit.apps.core.exceptions as core_exc
    import conduit.apps.authentication.signals as auth_signals
    import conduit.apps.profiles.models as profiles_models
    import rest_framework.exceptions as drf_exceptions
    import string
except ImportError as e:  # pragma: no cover - skip tests when imports unavailable
    import pytest as _pytest
    _pytest.skip(f"Skipping tests due to ImportError: {e}", allow_module_level=True)


def test_generate_jwt_token_encodes_payload_and_returns_token(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    captured = {}
    fake_self = SimpleNamespace(id=123)
    def fake_encode(payload, key=None, algorithm=None):
        captured['payload'] = payload
        captured['key'] = key
        captured['algorithm'] = algorithm
        return "FAKE_TOKEN"
    # Monkeypatch the jwt.encode used in the module under test
    monkeypatch.setattr(auth_models.jwt, "encode", fake_encode, raising=True)

    # Act
    token = auth_models._generate_jwt_token(fake_self)

    # Assert
    assert token == "FAKE_TOKEN"
    assert isinstance(captured.get('payload'), dict)
    assert captured['payload'].get('id') == 123
    assert 'exp' in captured['payload']


@pytest.mark.parametrize("length", [0, 1, 8, 32])
def test_generate_random_string_returns_requested_length_and_charset(length):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    allowed_chars = set(string.ascii_letters + string.digits)

    # Act
    result = core_utils.generate_random_string(length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    if length > 0:
        assert set(result).issubset(allowed_chars)
    else:
        assert result == ""


def test_core_exception_handler_delegates_to_specific_handlers(monkeypatch):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    called = {"not_found": False, "generic": False}

    def fake_not_found_handler(exc, context):
        called["not_found"] = True
        return {"handled": "not_found", "detail": getattr(exc, "detail", None)}

    def fake_generic_handler(exc, context):
        called["generic"] = True
        return {"handled": "generic", "detail": str(exc)}

    monkeypatch.setattr(core_exc, "_handle_not_found_error", fake_not_found_handler, raising=True)
    monkeypatch.setattr(core_exc, "_handle_generic_error", fake_generic_handler, raising=True)

    # Act - NotFound (should call not_found handler)
    not_found_exc = drf_exceptions.NotFound(detail="missing resource")
    result_not_found = core_exc.core_exception_handler(not_found_exc, context={})

    # Assert - NotFound path
    assert called["not_found"] is True
    assert result_not_found == {"handled": "not_found", "detail": getattr(not_found_exc, "detail", None)}

    # Reset and test generic exception
    called["not_found"] = False
    called["generic"] = False

    # Act - generic Exception (should call generic handler)
    generic_exc = Exception("unexpected")
    result_generic = core_exc.core_exception_handler(generic_exc, context={})

    # Assert - Generic path
    assert called["generic"] is True
    assert result_generic == {"handled": "generic", "detail": str(generic_exc)}


@pytest.mark.parametrize("created_flag,should_call", [(True, True), (False, False)])
def test_create_related_profile_calls_profile_create_only_when_created(monkeypatch, created_flag, should_call):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    calls = []
    def fake_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(**kwargs)

    # Monkeypatch Profile.objects.create to capture calls
    # It is common for Django models to have an 'objects' manager; guard attribute access
    profile_model = getattr(profiles_models, "Profile", None)
    assert profile_model is not None, "Profile model must be present for this integration test"
    monkeypatch.setattr(profile_model.objects, "create", fake_create, raising=False)

    fake_user = SimpleNamespace(pk=999, username="tester")

    # Act
    auth_signals.create_related_profile(sender=None, instance=fake_user, created=created_flag, **{})

    # Assert
    if should_call:
        assert len(calls) == 1
        # Expect the profile to be created with user passed through kwargs
        assert calls[0].get("user") is fake_user
    else:
        assert calls == []
