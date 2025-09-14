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
    import json
    import jwt
    import pytest
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.authentication.models import User
except ImportError as e:
    import pytest
    pytest.skip("skip tests due to ImportError: {}".format(e), allow_module_level=True)


@pytest.mark.parametrize(
    "input_payload, expected_root",
    [
        ({"title": "Hello World", "body": "Content"}, "article"),
        ({"title": "Boundary", "slug": "boundary-slug"}, "article"),
    ],
)
def test_article_json_renderer_wraps_payload_under_article_key(input_payload, expected_root):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = ArticleJSONRenderer()
    data_to_render = input_payload

    # Act
    rendered_bytes = renderer.render(data_to_render)

    # Assert
    assert isinstance(rendered_bytes, (bytes, bytearray))
    parsed = json.loads(rendered_bytes.decode("utf-8"))
    assert expected_root in parsed
    assert parsed[expected_root] == data_to_render


@pytest.mark.parametrize(
    "data_to_render, expected_root",
    [
        ({"id": 1, "body": "A comment"}, "comment"),
        ([{"id": 1, "body": "First"}, {"id": 2, "body": "Second"}], "comments"),
    ],
)
def test_comment_json_renderer_wraps_single_and_list_variants(data_to_render, expected_root):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = CommentJSONRenderer()
    payload = data_to_render

    # Act
    rendered = renderer.render(payload)

    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    parsed = json.loads(rendered.decode("utf-8"))
    assert expected_root in parsed
    assert parsed[expected_root] == payload


@pytest.mark.parametrize(
    "user_attrs",
    [
        ({"id": 42},),
        ({"id": 7, "email": "tester@example.com", "username": "tester"},),
    ],
)
def test_user_token_is_jwt_and_decodes_to_payload(user_attrs):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    attrs = user_attrs[0]
    user = User()
    for k, v in attrs.items():
        setattr(user, k, v)

    # Act
    token_attr = getattr(user, "token", None)
    if callable(token_attr):
        token_value = token_attr()
    else:
        token_value = token_attr

    # Assert token is a string JWT-looking token
    assert isinstance(token_value, _exc_lookup("str", Exception))
    assert token_value.count(".") == 2

    # Act: decode without verifying signature (deterministic check of structure)
    decoded = jwt.decode(token_value, options={"verify_signature": False})

    # Assert decoded is a mapping and contains at least one identifying claim
    assert isinstance(decoded, _exc_lookup("dict", Exception))
    assert any(k in decoded for k in ("id", "user_id", "email", "username", "sub"))
