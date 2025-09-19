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

import types
import datetime as real_datetime
from unittest import mock

import pytest

try:
    from conduit.apps.core import utils as core_utils
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication.models import _generate_jwt_token
    from conduit.apps.core import exceptions as core_exceptions
    from conduit.apps.authentication import signals as auth_signals
    from rest_framework import exceptions as drf_exceptions
except ImportError as e:
    pytest.skip(f"Skipping integration tests; missing project modules: {e}", allow_module_level=True)

def test_generate_random_string_length_and_charset(monkeypatch):
    # Arrange
    # Force a deterministic sequence of choices by cycling through a known list
    sequence = list("abc123")
    seq_iter = iter(sequence * 5)

    def fake_choice(_seq):
        try:
            return next(seq_iter)
        except StopIteration:
            return sequence[0]

    monkeypatch.setattr(core_utils.random, "choice", fake_choice)

    # Act
    result = core_utils.generate_random_string(8)

    # Assert
    assert isinstance(result, str)
    assert len(result) == 8
    
    assert all(ch in "abc123" for ch in result)

def test__generate_jwt_token_calls_jwt_with_expected_payload(monkeypatch):
    # Arrange
    # Create a dummy user-like object
    DummyUser = types.SimpleNamespace
    user = DummyUser(pk=42)

    captured = {}

    def fake_encode(payload, secret, algorithm=None):
        # capture arguments for assertions
        captured["payload"] = payload
        captured["secret"] = secret
        captured["algorithm"] = algorithm
        # return a deterministic token-like value
        return "fake.jwt.token"

    # Patch the jwt.encode used in the authentication.models module
    monkeypatch.setattr(auth_models, "jwt", types.SimpleNamespace(encode=fake_encode))

    # Also ensure SECRET_KEY exists on module (models may reach into settings via module-level import)
    # If auth_models references django settings, patch attribute SECRET_KEY on module as fallback
    monkeypatch.setattr(auth_models, "SECRET_KEY", "testing-secret", raising=False)

    # Act
    token = _generate_jwt_token(user)

    # Assert
    assert token == "fake.jwt.token"
    assert "payload" in captured
    payload = captured["payload"]
    
    assert payload.get("id") == 42
    assert "exp" in payload
    # algorithm typically passed; allow None or explicit HS256 depending on implementation
    assert captured["algorithm"] in (None, "HS256")
    # secret should match what we patched or be a string
    assert isinstance(captured["secret"], str)

def test_core_exception_handler_delegates_to_not_found_handler(monkeypatch):
    # Arrange
    sentinel = object()

    # Spy for not-found handler
    called = {"args": None}

    def fake_not_found(exc, context=None):
        called["args"] = (exc, context)
        return sentinel

    # Replace the internal handler used by core_exception_handler
    monkeypatch.setattr(core_exceptions, "_handle_not_found_error", fake_not_found)

    # Create a DRF NotFound exception instance
    exc = drf_exceptions.NotFound(detail="missing")

    # Act
    result = core_exceptions.core_exception_handler(exc, context={"view": "test"})

    # Assert
    assert result is sentinel
    assert isinstance(called["args"][0], drf_exceptions.NotFound)
    assert called["args"][1] == {"view": "test"}

def test_core_exception_handler_delegates_to_generic_handler_for_unexpected(monkeypatch):
    # Arrange
    sentinel = {"handled": "generic"}

    called = {"args": None}

    def fake_generic(exc, context=None):
        called["args"] = (exc, context)
        return sentinel

    monkeypatch.setattr(core_exceptions, "_handle_generic_error", fake_generic)

    exc = RuntimeError("boom")

    # Act
    result = core_exceptions.core_exception_handler(exc, context={"info": 1})

    # Assert
    assert result is sentinel
    assert isinstance(called["args"][0], RuntimeError)
    assert called["args"][1] == {"info": 1}

def test_create_related_profile_creates_profile_when_user_created(monkeypatch):
    # Arrange
    created_calls = {}

    class DummyProfile:
        def __init__(self, user):
            self.user = user

    class DummyManager:
        def get_or_create(self, user):
            created_calls["user"] = user
            return (DummyProfile(user), True)

    DummyProfileClass = types.SimpleNamespace(objects=DummyManager())

    # Patch the Profile symbol inside the signals module
    monkeypatch.setattr(auth_signals, "Profile", DummyProfileClass)

    # Create a dummy user-like instance expected by the signal handler
    user_instance = types.SimpleNamespace(username="alice", email="alice@example.com")

    # Act
    # The signal handler signature is typically (sender, instance, created, **kwargs)
    auth_signals.create_related_profile(sender=object(), instance=user_instance, created=True)

    # Assert
    assert created_calls.get("user") is user_instance

@pytest.mark.parametrize("created_flag", [False, True])
def test_create_related_profile_noop_when_not_created(monkeypatch, created_flag):
    # Arrange
    
    def will_fail_get_or_create(user):
        raise AssertionError("Should not be called when created is False")

    DummyProfileClass = types.SimpleNamespace(objects=types.SimpleNamespace(get_or_create=will_fail_get_or_create))
    monkeypatch.setattr(auth_signals, "Profile", DummyProfileClass)

    user_instance = types.SimpleNamespace(username="bob")

    # Act / Assert
    
    if not created_flag:
        
        auth_signals.create_related_profile(sender=object(), instance=user_instance, created=False)
    else:
        with pytest.raises(AssertionError):
            auth_signals.create_related_profile(sender=object(), instance=user_instance, created=True)
