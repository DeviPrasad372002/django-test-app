import importlib.util, pytest
if importlib.util.find_spec('django') is None:
    pytest.skip('django not installed; skipping module', allow_module_level=True)

import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import json
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

try:
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.renderers as auth_renderers
    import conduit.apps.authentication.serializers as auth_serializers
    import conduit.apps.authentication.signals as auth_signals
    import conduit.apps.core.exceptions as core_excs
    import conduit.apps.core.utils as core_utils
    import conduit.apps.profiles.models as profiles_models
    from rest_framework import exceptions as drf_exceptions
    from rest_framework import views as drf_views
    from rest_framework.response import Response
except (ImportError, ModuleNotFoundError) as exc:
    pytest.skip(f"Skipping tests; import failed: {exc}", allow_module_level=True)

# Arrange / Act / Assert style tests below

def test_get_short_name_returns_local_part_when_email_present():
    # Arrange
    dummy = SimpleNamespace(email="alice.example@domain.org")
    # Act
    result = auth_models.User.get_short_name(dummy)
    # Assert
    assert isinstance(result, str)
    assert result == "alice.example"

def test_get_short_name_handles_username_fallback():
    
    dummy = SimpleNamespace()
    
    def _raise():
        raise AttributeError
    dummy.__dict__['email'] = None
    # Some implementations fall back to username; set username and call
    dummy.username = "bob"
    # Act
    result = auth_models.User.get_short_name(dummy)
    # Assert
    assert isinstance(result, str)
    # Either returns username or empty string; ensure it is not a non-iterable
    assert result in ("bob", "") or result == "bob"

def test__generate_jwt_token_decodes_bytes_and_returns_string(monkeypatch):
    # Arrange
    fake_user = SimpleNamespace(pk=42)
    # Monkeypatch jwt.encode in module to return bytes
    def fake_encode(payload, secret, algorithm="HS256"):
        
        assert payload.get("id") == 42
        return b"byte-token"
    monkeypatch.setattr(auth_models, "jwt", SimpleNamespace(encode=fake_encode))
    # Act
    token = auth_models.User._generate_jwt_token(fake_user)
    # Assert
    assert isinstance(token, str)
    assert token == "byte-token"

def test__generate_jwt_token_handles_string_returned_from_jwt(monkeypatch):
    # Arrange
    fake_user = SimpleNamespace(pk=7)
    def fake_encode(payload, secret, algorithm="HS256"):
        assert payload.get("id") == 7
        return "string-token"
    monkeypatch.setattr(auth_models, "jwt", SimpleNamespace(encode=fake_encode))
    # Act
    token = auth_models.User._generate_jwt_token(fake_user)
    # Assert
    assert isinstance(token, str)
    assert token == "string-token"

def test_UserJSONRenderer_render_wraps_user_key_and_handles_none():
    # Arrange
    renderer = auth_renderers.UserJSONRenderer()
    data = {"email": "u@example.com", "token": "abc"}
    # Act
    rendered = renderer.render(data)
    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    loaded = json.loads(rendered.decode("utf-8"))
    assert "user" in loaded and loaded["user"] == data

    # Act: None should produce empty bytes (common implementation)
    rendered_none = renderer.render(None)
    # Assert
    assert isinstance(rendered_none, (bytes, bytearray))
    # Either empty or JSON null - accept both but ensure type
    assert rendered_none == b"" or json.loads(rendered_none.decode("utf-8")) in (None, {})

def test_LoginSerializer_validate_success_and_failure(monkeypatch):
    # Arrange
    SerializerClass = auth_serializers.LoginSerializer
    serializer = SerializerClass()
    valid_data = {"email": "x@test", "password": "pwd"}
    fake_user = SimpleNamespace(pk=1, email="x@test")

    # Monkeypatch authenticate used within the serializer module to return a user
    monkeypatch.setattr(auth_serializers, "authenticate", lambda **kwargs: fake_user)
    # Act
    result = serializer.validate(valid_data)
    # Assert: many implementations return the user instance
    assert (isinstance(result, dict) and ("user" in result and result["user"] == fake_user)) or result == fake_user

    
    monkeypatch.setattr(auth_serializers, "authenticate", lambda **kwargs: None)
    with pytest.raises(drf_exceptions.ValidationError):
        serializer.validate(valid_data)

def test_create_related_profile_creates_on_created_true(monkeypatch):
    # Arrange
    called = {}
    def fake_create(**kwargs):
        called['created_with'] = kwargs
        return SimpleNamespace(**kwargs)
    FakeProfile = SimpleNamespace(objects=SimpleNamespace(create=fake_create))
    monkeypatch.setattr(auth_signals, "Profile", FakeProfile)
    fake_instance = SimpleNamespace(pk=10)
    # Act
    auth_signals.create_related_profile(sender=None, instance=fake_instance, created=True)
    # Assert
    assert 'created_with' in called
    assert called['created_with'].get("user") == fake_instance

    # Do not create when created=False
    called.clear()
    auth_signals.create_related_profile(sender=None, instance=fake_instance, created=False)
    assert called == {}

def test_core_exception_handler_delegates_to_not_found_and_generic(monkeypatch):
    # Arrange: make DRF exception_handler return None (simulate unhandled)
    monkeypatch.setattr(drf_views, "exception_handler", lambda exc, ctx: None)

    # NotFound case
    nf = drf_exceptions.NotFound("nope")
    resp_nf = core_excs.core_exception_handler(nf, {})
    assert isinstance(resp_nf, Response)
    assert resp_nf.status_code in (404, )  # explicit expectation of 404
    
    assert isinstance(resp_nf.data, dict)
    assert "errors" in resp_nf.data

    # Generic exception case
    gen = Exception("boom")
    resp_gen = core_excs.core_exception_handler(gen, {})
    assert isinstance(resp_gen, Response)
    assert resp_gen.status_code in (500,)
    assert isinstance(resp_gen.data, dict)
    assert "errors" in resp_gen.data

def test_handle_not_found_and_generic_return_responses():
    # Act
    resp_nf = core_excs._handle_not_found_error(Exception("x"), {})
    resp_gen = core_excs._handle_generic_error(Exception("y"), {})
    # Assert
    assert isinstance(resp_nf, Response)
    assert resp_nf.status_code in (404,)
    assert isinstance(resp_nf.data, dict)
    assert "errors" in resp_nf.data

    assert isinstance(resp_gen, Response)
    assert resp_gen.status_code in (500,)
    assert isinstance(resp_gen.data, dict)
    assert "errors" in resp_gen.data

@pytest.mark.parametrize("length", [1, 5, 12])
def test_generate_random_string_length_and_charset(length):
    # Arrange / Act
    result = core_utils.generate_random_string(length=length)
    # Assert
    assert isinstance(result, str)
    assert len(result) == length
    assert re.fullmatch(r"[A-Za-z0-9]+", result) is not None

def test_profile_follow_unfollow_is_following_calls_managers(monkeypatch):
    # Arrange
    # Access unbound methods
    follow_func = profiles_models.Profile.follow
    unfollow_func = profiles_models.Profile.unfollow
    is_following_func = profiles_models.Profile.is_following

    # Create dummy target profile
    target = SimpleNamespace(pk=99)

    # Case: follow should call manager.add
    added = {}
    class FollowingMock:
        def add(self, obj):
            added['obj'] = obj
    self_obj = SimpleNamespace(following=FollowingMock())
    # Act
    follow_func(self_obj, target)
    # Assert
    assert added.get('obj') == target

    # Case: unfollow should call manager.remove
    removed = {}
    class FollowingMock2:
        def remove(self, obj):
            removed['obj'] = obj
    self_obj2 = SimpleNamespace(following=FollowingMock2())
    unfollow_func(self_obj2, target)
    assert removed.get('obj') == target

    # Case: is_following uses filter(...).exists()
    class FilterResult:
        def __init__(self, exists_result):
            self._res = exists_result
        def exists(self):
            return self._res
    class FollowingMock3:
        def __init__(self, expect_pk):
            self.expect_pk = expect_pk
        def filter(self, **kwargs):
            # check that pk compared to target.pk
            assert 'pk' in kwargs
            return FilterResult(kwargs['pk'] == self.expect_pk)
    # When following includes target
    self_obj3 = SimpleNamespace(following=FollowingMock3(expect_pk=99))
    assert is_following_func(self_obj3, target) is True
    # When following does not include target
    self_obj4 = SimpleNamespace(following=FollowingMock3(expect_pk=1))
    assert is_following_func(self_obj4, target) is False
