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
import random

try:
    import pytest
    from rest_framework.test import APIClient
except ImportError:
    import pytest  # type: ignore
    pytest.skip("pytest and djangorestframework required for these tests", allow_module_level=True)

random.seed(0)

def _post_try_both(client, path, payload):
    """
    Try posting to path and path with/without trailing slash to be tolerant of URL configs.
    Returns the first non-404 response.
    """
    resp = client.post(path, payload, format="json")
    if resp.status_code == 404:
        alt = path.rstrip("/") if path.endswith("/") else path + "/"
        resp = client.post(alt, payload, format="json")
    return resp

def _get_try_both(client, path, headers=None):
    if headers:
        for k, v in headers.items():
            client.credentials(**{k: v})
    resp = client.get(path, format="json")
    if resp.status_code == 404:
        alt = path.rstrip("/") if path.endswith("/") else path + "/"
        resp = client.get(alt, format="json")
    client.credentials()  # clear
    return resp

def _login_and_get_token(client, email, password):
    login_payload = {"user": {"email": email, "password": password}}
    resp = _post_try_both(client, "/api/users/login", login_payload)
    if resp.status_code == 404:
        
        resp = _post_try_both(client, "/api/users/login/", login_payload)
    return resp

def _attempt_auth_prefixes_and_get_user(client, token):
    """
    Try common Authorization header prefixes and return the first successful response.
    """
    prefixes = ("Token", "JWT", "Bearer")
    for p in prefixes:
        hdr = {"HTTP_AUTHORIZATION": f"{p} {token}"}
        # DRF APIClient accepts credentials via .credentials, but we can also pass HTTP_ headers
        client.credentials(HTTP_AUTHORIZATION=f"{p} {token}")
        resp = client.get("/api/user", format="json")
        client.credentials()  # clear
        if resp.status_code == 200:
            return p, resp
    return None, None

def _unique_user_credentials():
    n = random.randint(1000, 9999)
    email = f"alice{n}@example.com"
    username = f"alice{n}"
    password = "strong-password-123"
    return email, username, password

def test_registration_login_and_user_retrieve_success():
    
    # Arrange
    client = APIClient()
    email, username, password = _unique_user_credentials()
    registration_payload = {"user": {"username": username, "email": email, "password": password}}

    # Act - register
    resp = _post_try_both(client, "/api/users", registration_payload)

    # Assert - registration created and response shape
    assert resp.status_code == 201, f"expected 201 Created, got {resp.status_code} body={resp.content!r}"
    body = resp.json()
    assert isinstance(body, dict)
    assert "user" in body, "registration response must contain 'user' key"
    user_obj = body["user"]
    assert user_obj.get("email") == email
    assert "token" in user_obj and isinstance(user_obj["token"], str) and len(user_obj["token"]) > 10

    # Act - login
    login_resp = _login_and_get_token(client, email, password)

    # Assert - login success shape and status
    assert login_resp.status_code == 200, f"expected 200 OK on login, got {login_resp.status_code}"
    login_body = login_resp.json()
    assert "user" in login_body and "token" in login_body["user"]
    token = login_body["user"]["token"]

    # Act & Assert - try common auth header prefixes to retrieve /api/user
    prefix, user_resp = _attempt_auth_prefixes_and_get_user(client, token)
    assert prefix is not None, "none of the common auth header prefixes succeeded"
    assert user_resp.status_code == 200
    user_body = user_resp.json()
    assert "user" in user_body
    assert user_body["user"].get("email") == email
    # Critical business invariant: token returned at login matches token in registration response (if any)
    assert token == user_obj["token"]

def test_user_endpoint_requires_authentication():
    
    # Arrange
    client = APIClient()

    # Act - unauthenticated request to user endpoint
    resp = _get_try_both(client, "/api/user")

    # Assert - must be unauthorized (401)
    assert resp.status_code == 401, f"expected 401 Unauthorized for unauthenticated /api/user, got {resp.status_code}"

@pytest.mark.parametrize("wrong_password", ["badpass", "", "123"])
def test_login_with_invalid_credentials_returns_400(wrong_password):
    
    # Arrange
    client = APIClient()
    email, username, password = _unique_user_credentials()
    # Create the user via registration endpoint first
    reg_payload = {"user": {"username": username, "email": email, "password": password}}
    reg_resp = _post_try_both(client, "/api/users", reg_payload)
    assert reg_resp.status_code == 201

    # Act - attempt login with wrong password
    login_payload = {"user": {"email": email, "password": wrong_password}}
    login_resp = _post_try_both(client, "/api/users/login", login_payload)

    # Assert - expect 400 Bad Request for invalid credentials and no 'user' key
    assert login_resp.status_code == 400, f"expected 400 Bad Request for invalid login, got {login_resp.status_code}"
    body = login_resp.json()
    # Either explicit 'errors' structure or no 'user' key is acceptable, but must not include 'user'
    assert "user" not in body, "invalid login must not return a 'user' key"
    # Some implementations return an 'errors' object; if present, it should be a dict
    if "errors" in body:
        assert isinstance(body["errors"], dict) or isinstance(body["errors"], list) or isinstance(body["errors"], str)
