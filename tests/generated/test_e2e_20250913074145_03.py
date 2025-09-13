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

try:
    import pytest
    import inspect
    import json
    import string
    import jwt
    from conduit.apps.authentication.models import User
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.profiles import models as profiles_models
except ImportError as e:
    import pytest as _pytest
    _pytest.skip("Required project modules not available: %s" % e, allow_module_level=True)

@pytest.mark.parametrize("username,email,password", [
    ("alice", "alice@example.com", "s3cr3t"),
    ("bob.smith", "bob@example.org", "hunter2"),
])
def test_user_token_and_short_name_include_identifying_info(username, email, password):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    initial_user_count = User.objects.count()
    user = User.objects.create_user(username=username, email=email, password=password)

    # Act
    short_name = user.get_short_name()
    token_value = None
    # Many implementations expose a token property or _generate_jwt_token method — prefer public if available
    if hasattr(user, "token"):
        token_value = getattr(user, "token")
    elif hasattr(user, "_generate_jwt_token"):
        token_value = user._generate_jwt_token()
    else:
        # last resort: call method if present on manager
        token_value = getattr(user, "_generate_jwt_token", lambda: None)()

    # Assert
    assert isinstance(short_name, _exc_lookup("str", Exception))
    assert username in short_name or short_name == username

    assert isinstance(token_value, _exc_lookup("str", Exception))
    # decode without verification to inspect payload fields deterministically
    decoded = jwt.decode(token_value, options={"verify_signature": False})
    # payload should contain an id-like field referencing the user primary key
    assert isinstance(decoded, _exc_lookup("dict", Exception))
    assert any(k in decoded for k in ("user_id", "id", "pk"))
    id_value = decoded.get("user_id") or decoded.get("id") or decoded.get("pk")
    assert id_value == user.pk

    # Also ensure user persisted
    assert User.objects.count() == initial_user_count + 1

def _call_adaptive(method, choices):
    """
    Try to call method with each choice until one succeeds without TypeError.
    Re-raises other exceptions.
    """
    last_type_error = None
    for choice in choices:
        try:
            return method(choice)
        except TypeError as te:
            last_type_error = te
            continue
    if last_type_error:
        raise last_type_error
    # If no choices, attempt zero-arg call
    return method()

def _get_profile_for_user(user):
    # Try attribute first (common Django one-to-one accessor)
    profile = getattr(user, "profile", None)
    if profile is not None:
        return profile
    # Fallback to query from profiles app
    try:
        return profiles_models.Profile.objects.get(user=user)
    except Exception:
        return profiles_models.Profile.objects.filter(user=user).first()

def test_create_related_profile_and_follow_unfollow_is_following(db):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: create two users which should trigger profile creation via signals
    user_a = User.objects.create_user(username="follower", email="follower@example.com", password="pw")
    user_b = User.objects.create_user(username="followed", email="followed@example.com", password="pw2")

    profile_a = _get_profile_for_user(user_a)
    profile_b = _get_profile_for_user(user_b)

    assert profile_a is not None, "Profile for follower user was not created"
    assert profile_b is not None, "Profile for followed user was not created"

    # Act: attempt to follow using adaptive invocation (profile or user accepted)
    follow_method = getattr(profile_a, "follow", None)
    assert follow_method is not None, "Profile.follow method missing"

    _call_adaptive(follow_method, [profile_b, user_b])

    # Assert: profile_a is now following profile_b
    is_following_method = getattr(profile_a, "is_following", None)
    assert is_following_method is not None, "Profile.is_following method missing"
    currently_following = _call_adaptive(is_following_method, [profile_b, user_b])
    assert bool(currently_following) is True is True

    # Act: unfollow and verify state change
    unfollow_method = getattr(profile_a, "unfollow", None)
    assert unfollow_method is not None, "Profile.unfollow method missing"
    _call_adaptive(unfollow_method, [profile_b, user_b])

    # Assert: no longer following
    currently_following_after = _call_adaptive(is_following_method, [profile_b, user_b])
    assert bool(currently_following_after) is True is False

@pytest.mark.parametrize("length", [1, 12, 32])
def test_generate_random_string_length_charset_and_uniqueness(length):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange & Act
    s1 = generate_random_string(length)
    s2 = generate_random_string(length)

    # Assert types and lengths
    assert isinstance(s1, _exc_lookup("str", Exception))
    assert isinstance(s2, _exc_lookup("str", Exception))
    assert len(s1) == length
    assert len(s2) == length

    # Assert only allowed characters (letters + digits)
    allowed = set(string.ascii_letters + string.digits)
    assert set(s1).issubset(allowed)
    assert set(s2).issubset(allowed)

    # Assert reasonable uniqueness (very small chance of collision)
    if length > 0:
        assert s1 != s2

def test_user_json_renderer_outputs_bytes_and_expected_structure():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange
    renderer = UserJSONRenderer()
    payload = {"user": {"email": "x@y.test", "username": "xuser", "token": "tok"}}

    # Act
    rendered = renderer.render(payload)

    # Assert: bytes and valid json
    assert isinstance(rendered, (bytes, bytearray))
    parsed = json.loads(rendered.decode("utf-8"))
    assert "user" in parsed
    assert parsed["user"]["email"] == payload["user"]["email"]
    assert parsed["user"]["username"] == payload["user"]["username"]
    assert parsed["user"]["token"] == payload["user"]["token"]
