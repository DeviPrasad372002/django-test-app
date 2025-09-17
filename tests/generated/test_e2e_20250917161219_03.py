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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

import pytest

try:
    from rest_framework.test import APIClient
    from django.contrib.auth import get_user_model
except Exception:
    import pytest as _pytest
    _pytest.skip("Django or DRF not available", allow_module_level=True)

@pytest.mark.django_db
def test_registration_creates_user_and_profile_and_returns_jwt():
    
    # Arrange
    client = APIClient()
    username = "alice_e2e"
    email = "alice_e2e@example.com"
    password = "s3cretpass"
    payload = {"user": {"username": username, "email": email, "password": password}}

    # Act
    resp = client.post("/api/users", payload, format="json")

    # Assert
    assert resp.status_code == 201
    data = resp.json()
    assert "user" in data and isinstance(data["user"], dict)
    userobj = data["user"]
    # required keys on user payload
    for key in ("email", "username", "token"):
        assert key in userobj
    assert userobj["email"] == email
    assert userobj["username"] == username
    # token shape: JWT-like three parts
    token = userobj["token"]
    assert isinstance(token, str) and token.count(".") == 2

    # Act: retrieve created profile via public profile endpoint
    resp_profile = client.get(f"/api/profiles/{username}")

    # Assert profile exists and has expected schema and invariants
    assert resp_profile.status_code == 200
    p = resp_profile.json()
    assert "profile" in p and isinstance(p["profile"], dict)
    profile = p["profile"]
    assert profile["username"] == username
    # new user should not be followed by default
    assert profile.get("following") is False

@pytest.mark.django_db
def test_follow_and_unfollow_authenticated_user_changes_following_flag():
    
    # Arrange
    client = APIClient()
    # create user A
    a_name = "follow_a"
    a_email = "follow_a@example.com"
    a_pass = "apass"
    client.post("/api/users", {"user": {"username": a_name, "email": a_email, "password": a_pass}}, format="json")
    # create user B
    b_name = "follow_b"
    b_email = "follow_b@example.com"
    b_pass = "bpass"
    client.post("/api/users", {"user": {"username": b_name, "email": b_email, "password": b_pass}}, format="json")

    # Act: log in as A
    login_resp = client.post("/api/users/login", {"user": {"email": a_email, "password": a_pass}}, format="json")
    assert login_resp.status_code == 200
    token = login_resp.json()["user"]["token"]
    # authenticate client for user A
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    # Act: follow B
    follow_resp = client.post(f"/api/profiles/{b_name}/follow")
    # Assert follow succeeded and following=True
    assert follow_resp.status_code == 200
    follow_data = follow_resp.json()
    assert "profile" in follow_data
    assert follow_data["profile"]["username"] == b_name
    assert follow_data["profile"]["following"] is True

    # Act: unfollow B
    unfollow_resp = client.delete(f"/api/profiles/{b_name}/follow")
    # Assert unfollow succeeded and following=False
    assert unfollow_resp.status_code == 200
    unf_data = unfollow_resp.json()
    assert "profile" in unf_data
    assert unf_data["profile"]["username"] == b_name
    assert unf_data["profile"]["following"] is False

@pytest.mark.django_db
def test_follow_endpoint_requires_authentication_and_returns_401_for_anon():
    
    # Arrange
    client = APIClient()
    # create target user B
    b_name = "noauth_b"
    b_email = "noauth_b@example.com"
    b_pass = "bpass"
    client.post("/api/users", {"user": {"username": b_name, "email": b_email, "password": b_pass}}, format="json")

    # Act: anonymous client tries to follow B
    anon_client = APIClient()
    resp = anon_client.post(f"/api/profiles/{b_name}/follow")

    # Assert unauthorized
    assert resp.status_code in (401, 403)
    body = resp.json()
    
    assert any(k in body for k in ("detail", "errors"))

@pytest.mark.django_db
def test_nonexistent_article_returns_404_with_error_shape():
    
    # Arrange
    client = APIClient()
    nonexist_slug = "this-article-does-not-exist-12345"

    # Act
    resp = client.get(f"/api/articles/{nonexist_slug}")

    # Assert 404 and expected error schema keys
    assert resp.status_code == 404
    body = resp.json()
    
    assert isinstance(body, dict)
    assert "errors" in body or "detail" in body
