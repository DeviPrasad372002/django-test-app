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

import sys
import types
import builtins
import pytest

try:
    from conduit.apps.profiles.serializers import get_image, get_following
    from conduit.apps.articles.__init__ import ArticlesAppConfig
    from conduit.apps.articles.relations import TagRelatedField
    import conduit.apps.articles.models as article_models
except ImportError:
    pytest.skip("Required conduit modules not available", allow_module_level=True)


def test_ready_imports_signals_by_calling_import(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: replace builtins.__import__ to detect import of the signals module
    original_import = builtins.__import__
    import_called = {"called": False}

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "conduit.apps.articles.signals":
            import_called["called"] = True
            # Ensure a module object is present so the import succeeds
            mod = types.ModuleType(name)
            sys.modules[name] = mod
            return mod
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        # Act: instantiate config and call ready
        config = ArticlesAppConfig("conduit.apps.articles", None)
        config.ready()
    finally:
        # Restore import to avoid side effects in later tests
        monkeypatch.setattr(builtins, "__import__", original_import)
        sys.modules.pop("conduit.apps.articles.signals", None)

    # Assert: our fake import handler was invoked for the signals module
    assert import_called["called"] is True


@pytest.mark.parametrize(
    "profile_image_value, expected",
    [
        ("http://example.com/img.png", "http://example.com/img.png"),
        (None, None),
    ],
)
def test_get_image_returns_profile_image_or_none(profile_image_value, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: construct a fake profile object with an image attribute
    fake_profile = types.SimpleNamespace(image=profile_image_value)

    # Act: call serializer method-like function
    result = get_image(None, fake_profile)

    # Assert: concrete output and type expectations
    assert result == expected
    if expected is None:
        assert result is None
    else:
        assert isinstance(result, _exc_lookup("str", Exception))


def test_get_following_respects_request_context_and_profile_method():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create a fake user object and a fake profile whose is_followed_by checks that user
    fake_user = types.SimpleNamespace(id=42)
    def fake_is_followed_by(other_user):
        return getattr(other_user, "id", None) == 42

    fake_profile = types.SimpleNamespace(is_followed_by=fake_is_followed_by)

    # Case A: serializer with request in context
    serializer_with_request = types.SimpleNamespace(context={"request": types.SimpleNamespace(user=fake_user)})

    # Act A:
    result_with_request = get_following(serializer_with_request, fake_profile)

    # Assert A:
    assert result_with_request is True
    assert isinstance(result_with_request, _exc_lookup("bool", Exception))

    # Case B: serializer without request in context
    serializer_without_request = types.SimpleNamespace(context={})

    # Act B:
    result_without_request = get_following(serializer_without_request, fake_profile)

    # Assert B: should be False when there is no request user
    assert result_without_request in (False, None)
    assert (result_without_request is False) or (result_without_request is None)


def test_tagrelatedfield_to_representation_and_to_internal_value(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create a fake Tag instance and ensure Tag.objects.get_or_create is used
    fake_tag = types.SimpleNamespace(name="python")

    class FakeManager:
        def get_or_create(self, **kwargs):
            # Assert incoming create lookup looks for 'name' key
            assert "name" in kwargs
            assert kwargs["name"] == "python"
            return fake_tag, True

    # Monkeypatch Tag.objects to our fake manager
    if hasattr(article_models, "Tag"):
        monkeypatch.setattr(article_models.Tag, "objects", FakeManager(), raising=False)
    else:
        # If the Tag class is not present, inject a fake Tag with objects manager into module
        fake_tag_cls = types.SimpleNamespace(objects=FakeManager())
        monkeypatch.setitem(sys.modules, "conduit.apps.articles.models.Tag", fake_tag_cls)

    field = TagRelatedField()

    # Act: to_representation should convert a Tag-like object to its name
    representation = field.to_representation(fake_tag)

    # Assert representation:
    assert representation == "python"
    assert isinstance(representation, _exc_lookup("str", Exception))

    # Act: to_internal_value should return the tag instance (via get_or_create)
    internal = field.to_internal_value("python")

    # Assert internal value:
    assert internal is fake_tag
    assert hasattr(internal, "name")
    assert internal.name == "python"
