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
import pytest

try:
    import jwt
    from django.conf import settings
    from rest_framework.exceptions import AuthenticationFailed
    from conduit.apps.authentication.models import User
    from conduit.apps.authentication.backends import JWTAuthentication
except ImportError:
    pytest.skip("Django or required packages not available", allow_module_level=True)

@pytest.mark.django_db
def test_create_user_and_create_superuser_flags():
    
    # Arrange
    manager = User.objects
    create_user = getattr(manager, "create_user")
    create_superuser = getattr(manager, "create_superuser")

    # Prepare flexible kwargs based on signature
    cu_sig = inspect.signature(create_user)
    cs_sig = inspect.signature(create_superuser)

    cu_kwargs = {}
    if "email" in cu_sig.parameters:
        cu_kwargs["email"] = "TEST@Example.COM"
    if "username" in cu_sig.parameters:
        cu_kwargs["username"] = "tester"
    if "password" in cu_sig.parameters:
        cu_kwargs["password"] = "password123"

    cs_kwargs = {}
    if "email" in cs_sig.parameters:
        cs_kwargs["email"] = "ADMIN@Example.COM"
    if "username" in cs_sig.parameters:
        cs_kwargs["username"] = "admin"
    if "password" in cs_sig.parameters:
        cs_kwargs["password"] = "adminpass"

    # Act
    user = create_user(**cu_kwargs)
    superuser = create_superuser(**cs_kwargs)

    # Assert
    
    assert isinstance(user, User)
    assert user.email == user.email.lower()
    assert "@" in user.email and user.email.endswith("example.com")

    assert isinstance(superuser, User)
    # superuser should have elevated flags
    assert getattr(superuser, "is_staff", True) is True
    assert getattr(superuser, "is_superuser", True) is True

@pytest.mark.django_db
def test_user_token_decodable_contains_user_id(monkeypatch):
    
    # Arrange
    manager = User.objects
    create_user = getattr(manager, "create_user")
    sig = inspect.signature(create_user)
    kwargs = {}
    if "email" in sig.parameters:
        kwargs["email"] = "tokenuser@example.com"
    if "username" in sig.parameters:
        kwargs["username"] = "tokenuser"
    if "password" in sig.parameters:
        kwargs["password"] = "tokensecret"

    user = create_user(**kwargs)

    # Use a deterministic secret for decoding
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key", raising=False)

    # Act
    token = getattr(user, "token", None)
    # Allow property or method
    if callable(token):
        token = token()

    # Assert
    assert isinstance(token, str)
    # decode without verifying exp to avoid timing dependence
    payload = jwt.decode(token, "test-secret-key", algorithms=["HS256"], options={"verify_exp": False})
    assert isinstance(payload, dict)
    # payload should include user id
    assert "user_id" in payload
    assert int(payload["user_id"]) == int(user.pk)

@pytest.mark.django_db
def test_jwtauth__authenticate_credentials_valid_and_invalid():
    
    # Arrange
    manager = User.objects
    create_user = getattr(manager, "create_user")
    sig = inspect.signature(create_user)
    kwargs = {}
    if "email" in sig.parameters:
        kwargs["email"] = "authuser@example.com"
    if "username" in sig.parameters:
        kwargs["username"] = "authuser"
    if "password" in sig.parameters:
        kwargs["password"] = "authpass"

    user = create_user(**kwargs)
    backend = JWTAuthentication()
    auth_method = getattr(backend, "_authenticate_credentials", None)
    assert callable(auth_method)

    # Act / Assert: valid payload returns user (or (user, token))
    payload = {"user_id": user.pk}
    result = auth_method(payload)

    # Accept either user or (user, token)
    if isinstance(result, tuple):
        returned_user = result[0]
        assert returned_user.pk == user.pk
        # second element should be token-like str if present
        if len(result) > 1:
            assert isinstance(result[1], str)
    else:
        assert getattr(result, "pk", None) == user.pk

    
    bad_payload = {"user_id": -999999}
    with pytest.raises(AuthenticationFailed):
        auth_method(bad_payload)
