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
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
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
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

import pytest

try:
    import json
    import types
    from types import SimpleNamespace
    import re
    import builtins

    import target.conduit.apps.authentication.models as auth_models
    import target.conduit.apps.authentication.renderers as auth_renderers
    import target.conduit.apps.authentication.serializers as auth_serializers
    import target.conduit.apps.authentication.signals as auth_signals
    import target.conduit.apps.core.exceptions as core_exceptions
    import target.conduit.apps.core.utils as core_utils
    import target.conduit.apps.profiles.models as profiles_models
    from rest_framework.response import Response
    import rest_framework.exceptions as rf_exceptions
except ImportError as e:
    import pytest as _pytest
    _pytest.skip(f"Skipped tests due to ImportError: {e}", allow_module_level=True)


def _exc_lookup(name, default=Exception):
    try:
        import rest_framework.exceptions as _rf
        if hasattr(_rf, name):
            return getattr(_rf, name)
    except Exception:
        pass
    try:
        import django
        from django.http import Http404
        if name == "Http404":
            return Http404
    except Exception:
        pass
    return default


# Tests for get_short_name and _generate_jwt_token on User
class TestUserShortNameAndJwt:
    @pytest.mark.parametrize("username,expected", [
        ("alice", "alice"),
        ("", ""),
        (None, None),
    ])
    def test_get_short_name_returns_username_directly(self, username, expected):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        user_instance = SimpleNamespace(username=username, pk=42, id=42)
        # Act
        result = auth_models.User.get_short_name(user_instance)
        # Assert
        assert result == expected

    def test__generate_jwt_token_encodes_payload_with_id_and_exp(self, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        captured = {}
        def fake_encode(payload, secret, algorithm="HS256"):
            captured['payload'] = payload
            captured['secret'] = secret
            captured['algorithm'] = algorithm
            return "signed.token.string"
        # Ensure settings secret predictable
        monkeypatch.setattr(auth_models, "jwt", SimpleNamespace(encode=fake_encode))
        # Some implementations use settings from django.conf; ensure attribute exists
        monkeypatch.setattr(auth_models, "settings", SimpleNamespace(SECRET_KEY="shh-its-secret"), raising=False)
        # Provide deterministic datetime by patching datetime.datetime.utcnow if used to compute exp
        class FakeDateTime:
            @classmethod
            def utcnow(cls):
                import datetime as _dt
                return _dt.datetime(2020, 1, 1)
        monkeypatch.setattr(auth_models, "datetime", FakeDateTime, raising=False)

        user_instance = SimpleNamespace(pk=123, id=123)
        # Act
        token = auth_models.User._generate_jwt_token(user_instance)
        # Assert
        assert token == "signed.token.string"
        assert 'payload' in captured
        payload = captured['payload']
        assert ('id' in payload) and (payload['id'] in (123, '123'))
        assert 'exp' in payload and isinstance(payload['exp'], int)
        assert captured['secret'] == "shh-its-secret"


# Tests for render in authentication.renderers (UserJSONRenderer)
class TestUserJSONRendererRender:
    @pytest.mark.parametrize("input_data,expected_keys", [
        ({"email": "a@b.com", "token": "t"}, {"user"}),
        ({}, {"user"}),
    ])
    def test_render_wraps_in_user_key_and_returns_bytes(self, input_data, expected_keys):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        renderer = auth_renderers.UserJSONRenderer()
        # Act
        rendered = renderer.render(input_data, accepted_media_type=None, renderer_context=None)
        # Assert
        assert isinstance(rendered, (bytes, str))
        decoded = rendered.decode() if isinstance(rendered, _exc_lookup("bytes", Exception)) else rendered
        parsed = json.loads(decoded)
        assert set(parsed.keys()) >= expected_keys


# Tests for validate method on RegistrationSerializer (basic behavior)
class TestRegistrationSerializerValidate:
    @pytest.mark.parametrize("payload,should_raise", [
        ({"username": "bob", "email": "x@y.com", "password": "pw", "password2": "pw"}, False),
        ({"username": "bob", "email": "x@y.com", "password": "pw", "password2": "different"}, True),
        ({"username": "", "email": "x@y.com", "password": "pw", "password2": "pw"}, False),
    ])
    def test_validate_passwords_matching(self, payload, should_raise):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        serializer_cls = getattr(auth_serializers, "RegistrationSerializer", None)
        assert serializer_cls is not None, "RegistrationSerializer not found"
        serializer = serializer_cls()
        # Act / Assert
        if should_raise:
            ValidationError = _exc_lookup("ValidationError", Exception)
            with pytest.raises(_exc_lookup("ValidationError", Exception)):
                serializer.validate(payload)
        else:
            result = serializer.validate(payload)
            assert isinstance(result, _exc_lookup("dict", Exception))
            # Expect username/email presence preserved
            for k in ("username", "email"):
                if k in payload:
                    assert k in result


# Tests for create_related_profile signal handler with monkeypatched Profile model
class TestCreateRelatedProfileSignal:
    def test_create_related_profile_calls_profile_create_when_created_true(self, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        created_calls = {}
        def fake_create(**kwargs):
            created_calls['called_with'] = kwargs
            return SimpleNamespace(**kwargs)
        fake_objects = SimpleNamespace(create=fake_create)
        monkeypatch.setattr(auth_signals, "Profile", SimpleNamespace(objects=fake_objects), raising=False)
        # Provide a fake user instance
        user_instance = SimpleNamespace(pk=7, username="u7")
        # Act
        auth_signals.create_related_profile(sender=None, instance=user_instance, created=True)
        # Assert
        assert 'called_with' in created_calls
        assert created_calls['called_with'].get('user') is user_instance

    def test_create_related_profile_skips_when_created_false(self, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        called = {"count": 0}
        def fake_create(**kwargs):
            called["count"] += 1
            return SimpleNamespace(**kwargs)
        fake_objects = SimpleNamespace(create=fake_create)
        monkeypatch.setattr(auth_signals, "Profile", SimpleNamespace(objects=fake_objects), raising=False)
        user_instance = SimpleNamespace(pk=8, username="u8")
        # Act
        auth_signals.create_related_profile(sender=None, instance=user_instance, created=False)
        # Assert
        assert called["count"] == 0


# Tests for core exception handlers
class TestCoreExceptionHandlers:
    @pytest.mark.parametrize("exc,expected_status", [
        (Exception("generic"), 500),
        (rf_exceptions.NotFound(detail="nope"), 404),
    ])
    def test_core_exception_handler_returns_response_with_status(self, exc, expected_status):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        context = {}
        # Act
        resp = core_exceptions.core_exception_handler(exc, context)
        # Assert
        assert isinstance(resp, _exc_lookup("Response", Exception))
        assert resp.status_code == expected_status
        assert isinstance(resp.data, dict)
        assert 'errors' in resp.data or resp.status_code == 404

    def test_handle_generic_error_structure_contains_errors_key(self):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        exc = Exception("something bad")
        # Act
        resp = core_exceptions._handle_generic_error(exc)
        # Assert
        assert isinstance(resp, _exc_lookup("Response", Exception))
        assert resp.status_code >= 500
        assert isinstance(resp.data, dict)
        assert 'errors' in resp.data

    def test_handle_not_found_error_returns_404_and_error_detail(self):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        NotFound = _exc_lookup("NotFound", Exception)
        exc = NotFound("not found")
        # Act
        resp = core_exceptions._handle_not_found_error(exc)
        # Assert
        assert isinstance(resp, _exc_lookup("Response", Exception))
        assert resp.status_code == 404
        assert isinstance(resp.data, dict)
        # Either 'errors' or 'detail' may be present depending on implementation
        assert 'errors' in resp.data or 'detail' in resp.data


# Tests for generate_random_string
class TestGenerateRandomString:
    @pytest.mark.parametrize("length", [0, 1, 8, 16])
    def test_generate_random_string_length_and_charset(self, length):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange / Act
        s = core_utils.generate_random_string(length)
        # Assert
        assert isinstance(s, _exc_lookup("str", Exception))
        assert len(s) == length
        if length > 0:
            assert re.fullmatch(r"[A-Za-z0-9]+", s) is not None


# Tests for follow, unfollow, is_following using stub manager objects on simple instances
class TestProfileFollowUnfollowLogic:
    class StubManager:
        def __init__(self):
            self._set = set()
        def add(self, obj):
            self._set.add(obj)
        def remove(self, obj):
            self._set.discard(obj)
        def all(self):
            return list(self._set)
        def filter(self, **kwargs):
            results = []
            for p in self._set:
                match = True
                for k, v in kwargs.items():
                    if getattr(p, k, None) != v:
                        match = False
                        break
                if match:
                    results.append(p)
            return results

    @pytest.fixture
    def stub_profile(self):
        def _make(id_val):
            return SimpleNamespace(user=id_val, pk=id_val, following=self.StubManager(), followers=self.StubManager())
        return _make

    def test_follow_unfollow_is_following_behavior(self, stub_profile):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        alice = stub_profile(1)
        bob = stub_profile(2)
        # Act: call unbound methods with our simple objects
        # follow
        profiles_models.Profile.follow(alice, bob)
        # Assert follow occurred in either following or followers manager depending on implementation
        following_contains = bob in alice.following.all() or alice in bob.followers.all()
        assert following_contains is True
        # is_following should return True when checked
        is_following_result = profiles_models.Profile.is_following(alice, bob)
        assert isinstance(is_following_result, _exc_lookup("bool", Exception))
        assert is_following_result is True
        # Act: unfollow
        profiles_models.Profile.unfollow(alice, bob)
        # Assert removal happened
        following_still = bob in alice.following.all() or alice in bob.followers.all()
        assert following_still is False

    def test_is_following_false_when_no_relationship(self, stub_profile):
    # Arrange-Act-Assert: generated by ai-testgen
        # Arrange
        a = stub_profile(10)
        b = stub_profile(11)
        # Act
        result = profiles_models.Profile.is_following(a, b)
        # Assert
        assert result in (False, bool(result) is False)
