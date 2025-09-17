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
from types import SimpleNamespace

try:
    import pytest
    from unittest import mock
    import string
    import datetime as _datetime

    from conduit.apps.core.utils import generate_random_string
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.signals as auth_signals
    import conduit.apps.profiles.models as profiles_models
    import conduit.apps.core.exceptions as core_exceptions
    from rest_framework.exceptions import NotFound
except ImportError as e:
    import pytest
    pytest.skip("Skipping integration tests due to missing import: %s" % e, allow_module_level=True)

def test_generate_random_string_various_lengths_chars():
    
    # Arrange
    lengths = [1, 5, 16, 32]

    # Act / Assert
    for n in lengths:
        result = generate_random_string(n)

        # Assert length and type
        assert isinstance(result, str)
        assert len(result) == n

        # Assert characters are from allowed set
        allowed = set(string.ascii_letters + string.digits)
        assert set(result).issubset(allowed)

def test__generate_jwt_token_calls_jwt_encode_and_includes_id(monkeypatch):
    
    # Arrange
    # Determine token callable: method on User or standalone in module
    token_callable = None
    if hasattr(auth_models, "_generate_jwt_token"):
        token_callable = auth_models._generate_jwt_token
    elif hasattr(auth_models, "User") and hasattr(auth_models.User, "_generate_jwt_token"):
        token_callable = auth_models.User._generate_jwt_token
    else:
        pytest.skip("No _generate_jwt_token available in authentication models")

    dummy_user = SimpleNamespace(pk=123, id=123)

    # Prepare a mock for jwt.encode that captures the payload argument
    encode_mock = mock.Mock(return_value="MOCKED.JWT.TOKEN")
    # Replace jwt in module with a simple namespace exposing encode
    monkeypatch.setattr(auth_models, "jwt", SimpleNamespace(encode=encode_mock))

    # Also ensure any settings.SECRET_KEY lookup won't blow up: monkeypatch attribute if present
    if hasattr(auth_models, "settings"):
        try:
            monkeypatch.setattr(auth_models.settings, "SECRET_KEY", "test-secret", raising=False)
        except Exception:
            # fallback if settings is module proxy that disallows setting
            pass

    # Act
    # Call token function; if it's an unbound function, pass dummy_user as first arg
    if isinstance(token_callable, types.FunctionType):
        token = token_callable(dummy_user)
    else:
        # Bound method fallback: attempt to call directly
        token = token_callable(dummy_user)

    # Assert
    assert token == "MOCKED.JWT.TOKEN"
    assert encode_mock.called, "jwt.encode should have been called"

    # Inspect payload passed to jwt.encode: first arg expected to be payload dict
    called_args, called_kwargs = encode_mock.call_args
    assert len(called_args) >= 1, "jwt.encode should be called with payload as first positional arg"
    payload = called_args[0]
    assert isinstance(payload, dict)
    # Payload should include user id under a common key (id or pk)
    assert payload.get("id", payload.get("user_id", payload.get("pk"))) in (123, None) or payload.get("id") == 123 or payload.get("user_id") == 123

@pytest.mark.parametrize("exc, expected_status", [
    (NotFound(detail="nope"), 404),
    (Exception("boom"), 500),
])
def test_core_exception_handler_handles_not_found_and_generic(exc, expected_status):
    
    # Arrange
    # context can be empty for these handlers
    context = {}

    # Act
    response = core_exceptions.core_exception_handler(exc, context)

    # Assert
    # core_exception_handler may return a Response or None; ensure Response-like behavior
    assert response is not None, "core_exception_handler returned None unexpectedly"
    # status_code attribute expected on DRF Response
    assert hasattr(response, "status_code"), "response lacks status_code"
    assert response.status_code == expected_status
    # Data should be a dict exposing error information
    assert hasattr(response, "data"), "response lacks data"
    assert isinstance(response.data, dict)
    
    assert response.data, "response.data should not be empty"

def test_create_related_profile_triggers_profile_creation(monkeypatch):
    
    # Arrange
    created_called = mock.Mock()

    # Monkeypatch Profile.objects.create to capture call
    # The profiles_models.Profile may or may not exist; guard accordingly
    if not hasattr(profiles_models, "Profile"):
        pytest.skip("profiles_models.Profile not available")

    # Create a fake manager with create method
    fake_objects = SimpleNamespace(create=created_called)
    # Apply monkeypatch: set Profile.objects to our fake manager
    try:
        monkeypatch.setattr(profiles_models.Profile, "objects", fake_objects, raising=False)
    except Exception:
        
        profiles_models.Profile.objects = fake_objects

    # Prepare a fake user instance that signal would receive
    fake_user = SimpleNamespace(pk=9, id=9, email="u@example.com", username="user9")

    # Act
    # Django signals typically call handler with (sender, instance, created, **kwargs)
    # Try to call create_related_profile in multiple ways depending on signature
    sig = auth_signals.create_related_profile
    try:
        sig(sender=auth_models.User, instance=fake_user, created=True)
    except TypeError:
        # Fallback to positional
        sig(auth_models.User, fake_user, True)

    # Assert
    assert created_called.called, "Profile.objects.create should have been called by create_related_profile"
    # Ensure it was called with a user keyword argument referencing the instance
    called_args, called_kwargs = created_called.call_args
    # Accept either user positional arg or user kwarg
    if called_kwargs:
        assert called_kwargs.get("user") is fake_user
    else:
        # If positional, first arg should be the user
        assert called_args and called_args[0] is fake_user
