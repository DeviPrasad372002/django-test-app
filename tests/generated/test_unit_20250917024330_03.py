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

import pytest
from unittest.mock import MagicMock

try:
    import jwt
    from django.conf import settings
    from rest_framework import exceptions as drf_exceptions
    from rest_framework.response import Response

    from conduit.apps.authentication.models import User
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication.signals import create_related_profile
    import conduit.apps.authentication.signals as auth_signals
    from conduit.apps.core.exceptions import core_exception_handler, _handle_generic_error, _handle_not_found_error
except ImportError as e:
    pytest.skip(f"Skipping tests because required imports are not available: {e}", allow_module_level=True)

def test_generate_random_string_deterministic(monkeypatch):
    
    # Arrange
    length = 6
    # Ensure the implementation's random.choice is patched deterministically
    monkeypatch.setattr("conduit.apps.core.utils.random.choice", lambda seq: "X")

    # Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, str)
    assert len(result) == length
    assert result == "X" * length

def test_create_related_profile_calls_profile_create(monkeypatch):
    
    # Arrange
    user = User(username="tester")
    # Ensure the signals module's Profile.objects.create is observed
    assert hasattr(auth_signals, "Profile"), "auth_signals module must expose Profile for this test"
    original_objects = auth_signals.Profile.objects
    mock_create = MagicMock(return_value="created_profile")
    # Replace the objects attribute with a mock that has create
    monkeypatch.setattr(auth_signals.Profile, "objects", MagicMock(create=mock_create))

    # Act
    # Simulate post_save signal handler invocation when a user is created
    create_related_profile(sender=User, instance=user, created=True)

    # Assert
    assert mock_create.called, "Profile.objects.create was not called"
    # Ensure the created user instance was passed through in keywords if implementation uses that
    called_kwargs = mock_create.call_args.kwargs
    assert any(user is v for v in called_kwargs.values()) or "user" in called_kwargs

def test_user_get_short_name_and_jwt_token_structure(monkeypatch):
    
    # Arrange
    # Provide a stable secret key for token verification
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key")
    user = User(id=42, username="alice")

    # Act
    short = user.get_short_name()
    token = user._generate_jwt_token()

    # Assert
    assert isinstance(short, str)
    # Typical get_short_name returns username; verify consistency
    assert short == "alice"

    assert isinstance(token, str)
    # Token should be a JWT (three segments separated by dots)
    assert token.count(".") == 2

    # Decode token to verify payload structure and signing
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert isinstance(payload, dict)
    assert payload.get("id") == 42
    assert "exp" in payload
    assert isinstance(payload["exp"], int)

def test_core_exception_handler_maps_not_found_to_404():
    
    # Arrange
    exc = drf_exceptions.NotFound(detail="not here")
    context = {}

    # Act
    response = core_exception_handler(exc, context)

    # Assert
    assert isinstance(response, Response)
    assert response.status_code == 404

def test_handle_generic_and_not_found_error_helpers():
    
    # Arrange
    generic_exc = Exception("boom")
    not_found_exc = drf_exceptions.NotFound(detail="missing")

    # Act
    generic_resp = _handle_generic_error(generic_exc, {})
    nf_resp = _handle_not_found_error(not_found_exc, {})

    # Assert generic error yields 500
    assert isinstance(generic_resp, Response)
    assert generic_resp.status_code == 500

    # Assert not found helper yields 404
    assert isinstance(nf_resp, Response)
    assert nf_resp.status_code == 404
