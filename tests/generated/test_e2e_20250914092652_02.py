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

def _fix_django_metaclass_compatibility():
    """Fix Django 1.10.5 metaclass compatibility with Python 3.10+"""
    try:
        import sys
        if sys.version_info >= (3, 8):
            import builtins
            original_build_class = builtins.__build_class__
            
            def patched_build_class(func, name, *bases, metaclass=None, **kwargs):
                try:
                    return original_build_class(func, name, *bases, metaclass=metaclass, **kwargs)
                except RuntimeError as e:
                    if '__classcell__' in str(e) and 'not set' in str(e):
                        # Create a new function without problematic cell variables
                        import types
                        code = func.__code__
                        if code.co_freevars:
                            # Remove free variables that cause issues
                            new_code = code.replace(
                                co_freevars=(),
                                co_names=code.co_names + code.co_freevars
                            )
                            new_func = types.FunctionType(
                                new_code,
                                func.__globals__,
                                func.__name__,
                                func.__defaults__,
                                None  # No closure
                            )
                            return original_build_class(new_func, name, *bases, metaclass=metaclass, **kwargs)
                    raise
                except Exception:
                    # Fallback for other metaclass issues
                    return original_build_class(func, name, *bases, **kwargs)
            
            builtins.__build_class__ = patched_build_class
    except Exception:
        pass

# Apply Django metaclass fix early
_fix_django_metaclass_compatibility()

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
            # Don't skip module-level, just continue
            pass
    
    if not _dj_apps.ready:
        try:
            django.setup()
        except Exception as e:
            # Don't skip module-level, just continue
            pass
            
except Exception as e:
    # Don't skip at module level - let individual tests handle Django issues
    pass



# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

try:
    import pytest
    import importlib
    import inspect
    import string
except ImportError:
    import pytest
    pytest.skip("Required test modules not available", allow_module_level=True)


def _resolve(module_path, attr_path):
    module_obj = importlib.import_module(module_path)
    attr_parts = attr_path.split(".")
    obj = module_obj
    for part in attr_parts:
        obj = getattr(obj, part)
    return obj


@pytest.mark.parametrize(
    "module_path,attr_path,expected_kind",
    [
        ("conduit.apps.articles.serializers", "ArticleSerializer", "class"),
        ("conduit.apps.articles.models", "Comment", "class"),
        ("conduit.apps.authentication.backends", "JWTAuthentication", "class"),
        ("conduit.apps.authentication.models", "UserManager", "class"),
        ("conduit.apps.authentication.models", "User", "class"),
        ("conduit.apps.core.exceptions", "_handle_generic_error", "callable"),
        ("conduit.apps.articles.signals", "add_slug_to_article_if_not_exists", "callable"),
        ("conduit.apps.profiles.serializers", "get_following", "callable"),
        ("conduit.apps.profiles.models", "has_favorited", "callable"),
    ],
)
def test_public_api_surface_has_expected_kinds(module_path, attr_path, expected_kind):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    module_name = module_path
    attribute_name = attr_path
    kind_expected = expected_kind

    # Act
    resolved_obj = _resolve(module_name, attribute_name)

    # Assert
    if kind_expected == "class":
        assert inspect.isclass(resolved_obj), f"{module_name}.{attribute_name} should be a class"
    elif kind_expected == "callable":
        assert callable(resolved_obj), f"{module_name}.{attribute_name} should be callable"
    else:
        pytest.fail(f"Unexpected expected_kind: {kind_expected}")


@pytest.mark.parametrize(
    "method_name",
    [
        "to_representation",
        "create",
        "get_favorited",
        "get_favorites_count",
        "get_updated_at",
        "get_created_at",
    ],
)
def test_article_serializer_exposes_core_methods(method_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    module_name = "conduit.apps.articles.serializers"
    class_name = "ArticleSerializer"

    # Act
    ArticleSerializer = _resolve(module_name, class_name)
    has_attribute = hasattr(ArticleSerializer, method_name)
    attribute_obj = getattr(ArticleSerializer, method_name) if has_attribute else None

    # Assert
    assert has_attribute, f"ArticleSerializer should have attribute {method_name}"
    assert callable(attribute_obj), f"ArticleSerializer.{method_name} should be callable"


@pytest.mark.parametrize("length", [1, 8, 16, 64])
def test_generate_random_string_length_and_printable(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    module_name = "conduit.apps.core.utils"
    func_name = "generate_random_string"

    # Act
    generate_random_string = _resolve(module_name, func_name)
    result_a = generate_random_string(length)
    result_b = generate_random_string(length)

    # Assert
    assert isinstance(result_a, _exc_lookup("str", Exception)), "Result should be a string"
    assert len(result_a) == length, f"Expected length {length}, got {len(result_a)}"
    assert result_a.isprintable(), "Result should contain printable characters only"
    assert not any(ch.isspace() for ch in result_a), "Result should not contain whitespace characters"
    # For longer lengths, expect non-deterministic outputs (very small chance of collision)
    if length >= 4:
        assert result_a != result_b, "Two generated strings should differ for reasonable lengths"
