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

try:
    import pytest
    from rest_framework.test import APIClient
except ImportError:
    import pytest
    pytest.skip("Django REST framework is required for these tests", allow_module_level=True)

@pytest.mark.django_db
def test_registration_creates_user_and_returns_token():
    
    # Arrange
    client = APIClient()
    payload = {
        "user": {
            "username": "test_register_user",
            "email": "register@example.com",
            "password": "strong-password-123"
        }
    }

    # Act
    resp = client.post("/api/users", payload, format="json")

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert isinstance(data, dict)
    assert "user" in data and isinstance(data["user"], dict)
    user = data["user"]
    # expected schema keys
    for key in ("email", "username", "token", "bio", "image"):
        assert key in user
    assert user["email"] == "register@example.com"
    assert user["username"] == "test_register_user"
    assert isinstance(user["token"], str) and len(user["token"]) > 0

@pytest.mark.django_db
def test_login_and_get_profile_with_token_auth():
    
    # Arrange
    client = APIClient()
    reg_payload = {
        "user": {
            "username": "test_login_user",
            "email": "login@example.com",
            "password": "login-pass-456"
        }
    }
    client.post("/api/users", reg_payload, format="json")

    login_payload = {
        "user": {
            "email": "login@example.com",
            "password": "login-pass-456"
        }
    }

    # Act - login
    login_resp = client.post("/api/users/login", login_payload, format="json")

    # Assert login response
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "user" in login_data and isinstance(login_data["user"], dict)
    token = login_data["user"].get("token")
    assert isinstance(token, str) and token != ""

    # Act - use token to access protected endpoint
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    profile_resp = client.get("/api/user")

    # Assert profile response
    assert profile_resp.status_code == 200
    profile_data = profile_resp.json()
    assert "user" in profile_data and isinstance(profile_data["user"], dict)
    assert profile_data["user"]["email"] == "login@example.com"
    assert profile_data["user"]["username"] == "test_login_user"
    # token returned on profile should be presente (may match or be refreshed)
    assert "token" in profile_data["user"]

@pytest.mark.django_db
def test_user_update_requires_authentication():
    
    # Arrange
    client = APIClient()
    update_payload = {"user": {"bio": "malicious update"}}

    # Act
    resp = client.put("/api/user", update_payload, format="json")

    # Assert
    assert resp.status_code == 401
    body = resp.json()
    
    assert isinstance(body, dict)
    assert "detail" in body

@pytest.mark.django_db
def test_login_with_invalid_credentials_returns_400():
    
    # Arrange
    client = APIClient()
    reg_payload = {
        "user": {
            "username": "test_invalid_login",
            "email": "invalid@example.com",
            "password": "valid-pass-789"
        }
    }
    client.post("/api/users", reg_payload, format="json")

    bad_login_payload = {
        "user": {
            "email": "invalid@example.com",
            "password": "wrong-password"
        }
    }

    # Act
    resp = client.post("/api/users/login", bad_login_payload, format="json")

    # Assert
    assert resp.status_code == 400
    body = resp.json()
    assert isinstance(body, dict)
    # ensure login did not return a user object
    assert "user" not in body
    
    assert any(k in body for k in ("errors", "detail", "non_field_errors"))
