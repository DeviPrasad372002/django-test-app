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
    from types import SimpleNamespace
    from conduit.apps.articles import relations as articles_relations
    from conduit.apps.profiles import serializers as profiles_serializers
except ImportError:
    import pytest
    pytest.skip("Required modules for tests are not importable", allow_module_level=True)

@pytest.mark.parametrize(
    "input_name,expected_name",
    [
        ("python", "python"),
        ("unit-test", "unit-test"),
    ],
)
def test_tagrelatedfield_to_internal_value_calls_get_or_create(monkeypatch, input_name, expected_name):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    recorded = {}
    class DummyObjects:
        def get_or_create(self, name):
            recorded['name'] = name
            return (SimpleNamespace(name=name, created=True), True)
    DummyTag = SimpleNamespace(objects=DummyObjects())
    monkeypatch.setattr(articles_relations, "Tag", DummyTag, raising=False)
    field = articles_relations.TagRelatedField()

    # Act
    result = field.to_internal_value(input_name)

    # Assert
    assert hasattr(result, "name")
    assert result.name == expected_name
    assert recorded.get('name') == expected_name

def test_tagrelatedfield_to_representation_uses_name_attribute():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    field = articles_relations.TagRelatedField()
    fake_tag = SimpleNamespace(name="integration")

    # Act
    output = field.to_representation(fake_tag)

    # Assert
    assert isinstance(output, _exc_lookup("str", Exception))
    assert output == "integration"

@pytest.mark.parametrize(
    "image_value,expected",
    [
        ("https://example.com/img.png", "https://example.com/img.png"),
        (None, ""),  # boundary: missing image
    ],
)
def test_profile_serializer_get_image_handles_present_and_missing_images(image_value, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer_cls = getattr(profiles_serializers, "ProfileSerializer", None)
    assert serializer_cls is not None, "ProfileSerializer expected in profiles.serializers"
    request_stub = SimpleNamespace(user=SimpleNamespace(is_anonymous=True))
    serializer = serializer_cls(context={"request": request_stub})
    user_obj = SimpleNamespace(image=image_value)

    # Act
    result = serializer.get_image(user_obj)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    assert result == expected

@pytest.mark.parametrize("is_following_return", [True, False])
def test_profile_serializer_get_following_respects_request_user_follow_state(is_following_return):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer_cls = getattr(profiles_serializers, "ProfileSerializer", None)
    assert serializer_cls is not None, "ProfileSerializer expected in profiles.serializers"
    # request.user may call is_following(obj) or have profile.is_following(obj); provide both
    def is_following_method(target):
        recorded['target'] = target
        return is_following_return
    recorded = {}
    request_user = SimpleNamespace(
        is_anonymous=False,
        is_following=is_following_method,
        profile=SimpleNamespace(is_following=is_following_method),
    )
    request_stub = SimpleNamespace(user=request_user)
    serializer = serializer_cls(context={"request": request_stub})
    target_obj = SimpleNamespace(username="alice")

    # Act
    result = serializer.get_following(target_obj)

    # Assert
    assert isinstance(result, _exc_lookup("bool", Exception))
    assert result == is_following_return
    # ensure the target was passed through to at least one is_following callable
    assert recorded.get('target') is target_obj
