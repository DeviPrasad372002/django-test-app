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

import inspect
import types
import random
from types import SimpleNamespace

import pytest

try:
    # Authentication models and utilities
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication import serializers as auth_serializers
    from conduit.apps.authentication import signals as auth_signals

    # Core utilities and exceptions
    from conduit.apps.core import utils as core_utils
    from conduit.apps.core import exceptions as core_exceptions

    # Profiles (for follow/unfollow)
    from conduit.apps.profiles import models as profiles_models

    # DRF exceptions / serializers / response for assertions
    from rest_framework import serializers as drf_serializers
    from rest_framework import exceptions as drf_exceptions
    from rest_framework.response import Response

except Exception as exc:  # pragma: no cover - environment may not have Django
    pytest.skip(f"Skipping tests because imports failed: {exc}", allow_module_level=True)

def _call_adaptively(func, *args):
    """
    Helper: try to call func with given args; if it raises TypeError from missing/extra self,
    attempt to prepend None as self and call again.
    """
    try:
        return func(*args)
    except TypeError:
        # try adding dummy self
        return func(None, *args)

def test_get_short_name_username_and_email_variants():
    # Arrange
    get_short_name = getattr(auth_models, "get_short_name", None)
    assert callable(get_short_name), "get_short_name not found"

    class FakeUser:
        def __init__(self, username=None, email=None):
            self.username = username
            self.email = email

    cases = [
        (FakeUser(username="alice", email="a@e.com"), "alice"),
        (FakeUser(username="", email="bob@e.com"), "bob@e.com"),
        (FakeUser(username=None, email="c@e.com"), "c@e.com"),
    ]

    for user, expected in cases:
        # Act
        result = _call_adaptively(get_short_name, user)
        # Assert
        assert isinstance(result, str)
        assert result == expected

def test__generate_jwt_token_calls_jwt_encode_and_sets_exp(monkeypatch):
    _generate_jwt_token = getattr(auth_models, "_generate_jwt_token", None)
    assert callable(_generate_jwt_token), "_generate_jwt_token not found"

    captured = {}

    def fake_encode(payload, secret, algorithm="HS256"):
        captured["payload"] = payload
        captured["secret"] = secret
        captured["algorithm"] = algorithm
        return "FAKE_TOKEN"

    # Monkeypatch jwt.encode used inside function
    import jwt as real_jwt  # ensure module exists; will be skipped earlier if missing
    monkeypatch.setattr(real_jwt, "encode", fake_encode)

    class FakeUser:
        def __init__(self, pk):
            self.pk = pk
            self.id = pk

    user = FakeUser(42)

    # Act
    token = _call_adaptively(_generate_jwt_token, user)

    # Assert
    assert token == "FAKE_TOKEN"
    assert isinstance(captured.get("payload"), dict)
    # payload should include an id field and expiration
    assert ("user_id" in captured["payload"]) or ("id" in captured["payload"])
    assert "exp" in captured["payload"]
    assert captured["algorithm"] == "HS256"
    assert isinstance(captured["payload"]["exp"], (int, float))

def test_userjsonrenderer_render_wraps_under_user_key_and_returns_bytes():
    # Arrange
    renderer = UserJSONRenderer()
    data = {"username": "bob", "email": "bob@example.com"}

    # Act
    out = renderer.render(data)

    # Assert
    assert isinstance(out, (bytes, str))
    text = out.decode() if isinstance(out, bytes) else out
    assert '"user"' in text or "'user'" in text
    assert "bob@example.com" in text

@pytest.mark.parametrize(
    "attrs,should_raise",
    [
        ({"email": "x@x.com", "password": "pw", "password2": "pw"}, False),
        ({"email": "x@x.com", "password": "pw", "password2": "different"}, True),
    ],
)
def test_validate_password_confirmation_behavior(attrs, should_raise):
    validate = getattr(auth_serializers, "RegistrationSerializer", None)
    # The serializer may implement validate as an instance method; adapt accordingly.
    if validate is None:
        pytest.skip("RegistrationSerializer missing; cannot test validate behavior")

    # Create a dummy serializer instance if needed
    ser_instance = validate()
    func = getattr(ser_instance, "validate", None)
    assert callable(func), "validate method not found on RegistrationSerializer"

    if should_raise:
        with pytest.raises(drf_serializers.ValidationError):
            func(attrs)
    else:
        result = func(attrs)
        assert isinstance(result, dict)
        assert result.get("email") == attrs["email"]

def test_create_related_profile_calls_profile_create_when_created(monkeypatch):
    create_related_profile = getattr(auth_signals, "create_related_profile", None)
    assert callable(create_related_profile), "create_related_profile not found"

    created_calls = {}

    class FakeProfileManager:
        def create(self, **kwargs):
            created_calls["called_with"] = kwargs
            return SimpleNamespace(**kwargs)

    class FakeProfileModel:
        objects = FakeProfileManager()

    # Monkeypatch Profile in signals module to our fake
    monkeypatch.setattr(auth_signals, "Profile", FakeProfileModel, raising=False)

    fake_user = SimpleNamespace(username="john", pk=7)
    # Act
    create_related_profile(sender=None, instance=fake_user, created=True)

    # Assert
    assert "called_with" in created_calls
    assert created_calls["called_with"].get("user") == fake_user

    # If not created, should not call create
    created_calls.clear()
    create_related_profile(sender=None, instance=fake_user, created=False)
    assert created_calls == {}

def test_core_exception_handler_and_helpers_return_structured_responses():
    handler = getattr(core_exceptions, "core_exception_handler", None)
    gen = getattr(core_exceptions, "_handle_generic_error", None)
    nf = getattr(core_exceptions, "_handle_not_found_error", None)
    assert callable(handler)
    assert callable(gen)
    assert callable(nf)

    # Generic error
    exc = Exception("boom")
    generic_resp = gen(exc)
    assert isinstance(generic_resp, dict)
    assert "errors" in generic_resp
    # expect message present
    assert any("boom" in str(v) for v in generic_resp["errors"].values())

    # Not found error: use DRF NotFound
    nf_exc = drf_exceptions.NotFound("nope")
    nf_resp = nf(nf_exc)
    assert isinstance(nf_resp, dict)
    assert "errors" in nf_resp
    assert any("nope" in str(v) for v in nf_resp["errors"].values())

    # core_exception_handler should return a DRF Response and status mapping
    resp = handler(nf_exc, context={})
    assert isinstance(resp, Response)
    assert resp.status_code == 404
    assert isinstance(resp.data, dict)
    assert "errors" in resp.data

    resp2 = handler(Exception("crash"), context={})
    assert isinstance(resp2, Response)
    assert resp2.status_code == 500
    assert "errors" in resp2.data

def test_generate_random_string_is_deterministic_with_monkeypatched_choice(monkeypatch):
    gen = getattr(core_utils, "generate_random_string", None)
    assert callable(gen)

    # Patch random.choice to always return 'z'
    monkeypatch.setattr(random, "choice", lambda seq: "z")
    s = gen(5)
    assert isinstance(s, str)
    assert s == "z" * 5

    # Edge: length 0
    s0 = gen(0)
    assert s0 == ""

def test_follow_unfollow_and_is_following_behavior():
    follow_func = getattr(profiles_models, "follow", None)
    unfollow_func = getattr(profiles_models, "unfollow", None)
    is_following_func = getattr(profiles_models, "is_following", None)

    assert callable(follow_func)
    assert callable(unfollow_func)
    assert callable(is_following_func)

    class FakeFollowingCollection:
        def __init__(self):
            self._data = set()

        def add(self, item):
            self._data.add(item)

        def remove(self, item):
            self._data.discard(item)

        # simulate filter(pk=...).exists() pattern
        def filter(self, **kwargs):
            pk = kwargs.get("pk")
            matching = [x for x in self._data if getattr(x, "pk", None) == pk]
            return SimpleNamespace(exists=lambda: bool(matching))

        def __contains__(self, item):
            return item in self._data

    class FakeProfile:
        def __init__(self, pk):
            self.pk = pk
            self.following = FakeFollowingCollection()

    a = FakeProfile(1)
    b = FakeProfile(2)

    # Act - follow
    _call_adaptively(follow_func, a, b)
    # Assert - now a is following b
    assert b in a.following._data or is_following_func(a, b) is True

    # Act - is_following
    res = _call_adaptively(is_following_func, a, b)
    assert res is True

    # Act - unfollow
    _call_adaptively(unfollow_func, a, b)
    # Assert - no longer following
    res2 = _call_adaptively(is_following_func, a, b)
    assert res2 is False or b not in a.following._data
