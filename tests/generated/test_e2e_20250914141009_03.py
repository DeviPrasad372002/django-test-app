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

import pytest

try:
    import conduit.apps.core.utils as core_utils
    import conduit.apps.core.exceptions as core_exceptions
    import conduit.apps.authentication.models as auth_models
    from rest_framework.exceptions import NotFound
    from rest_framework.response import Response
    import jwt
    import time
except ImportError as e:
    pytest.skip(f"Skipping tests due to ImportError: {e}", allow_module_level=True)

import types

@pytest.mark.parametrize("length", [0, 1, 16, 64])
def test_generate_random_string_returns_expected_length_and_deterministic_chars(monkeypatch, length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    captured_seqs = []
    def fake_choice(seq):
        captured_seqs.append(seq)
        return seq[0]
    def fake_choices(seq, k=1):
        captured_seqs.append(seq)
        return [seq[0]] * k

    monkeypatch.setattr(core_utils.random, "choice", fake_choice, raising=False)
    monkeypatch.setattr(core_utils.random, "choices", fake_choices, raising=False)

    # Act
    result = core_utils.generate_random_string(length)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length
    if length == 0:
        assert result == ""
    else:
        assert captured_seqs, "random.choice/choices was not called at all"
        first_seq = captured_seqs[0]
        assert first_seq, "sequence passed to random choice was empty"
        expected_char = first_seq[0]
        assert result == expected_char * length

@pytest.mark.parametrize("exc, expected_status", [
    (NotFound("missing resource"), 404),
    (Exception("unexpected"), 500),
])
def test_core_exception_handler_and_helpers_return_response_with_errors(exc, expected_status):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    context = {"view": None, "request": None}

    # Act
    if isinstance(exc, _exc_lookup("NotFound", Exception)):
        response = core_exceptions._handle_not_found_error(exc, context)
    else:
        response = core_exceptions._handle_generic_error(exc, context)

    # Assert
    assert isinstance(response, _exc_lookup("Response", Exception))
    assert hasattr(response, "status_code")
    assert response.status_code == expected_status
    assert isinstance(response.data, dict)
    assert "errors" in response.data

def test_user_generate_jwt_token_and_get_short_name(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyUser:
        pass
    dummy = DummyUser()
    dummy.pk = 42
    dummy.id = 42
    dummy.username = "bob"
    dummy.email = "bob@example.org"

    # Ensure module has settings attribute and set SECRET_KEY deterministically
    if not hasattr(auth_models, "settings"):
        # create a lightweight fake settings object used by the method if absent
        auth_models.settings = types.SimpleNamespace(SECRET_KEY="tests-secret-key")
    else:
        # monkeypatch existing settings.SECRET_KEY
        monkeypatch.setattr(auth_models.settings, "SECRET_KEY", "tests-secret-key", raising=False)

    # Act
    token = auth_models.User._generate_jwt_token(dummy)

    # Some jwt implementations return bytes
    if isinstance(token, _exc_lookup("bytes", Exception)):
        token = token.decode("utf-8")

    # Decode token to verify payload and expiration
    decoded = jwt.decode(token, auth_models.settings.SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})

    # Assert token payload contains id and exp
    assert isinstance(decoded, _exc_lookup("dict", Exception))
    assert "id" in decoded
    assert int(decoded["id"]) == dummy.pk
    assert "exp" in decoded
    assert isinstance(decoded["exp"], int)
    assert decoded["exp"] > int(time.time())

    # Act - get_short_name
    short_name = auth_models.User.get_short_name(dummy)

    # Assert - expecting username to be returned as short name
    assert isinstance(short_name, _exc_lookup("str", Exception))
    assert short_name == "bob"
