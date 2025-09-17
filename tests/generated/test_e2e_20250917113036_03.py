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

import json
import random

try:
    import pytest
    from rest_framework.test import APIClient
    from django.urls import reverse  
except Exception as e:  # pragma: no cover - skip module if framework not present
    import pytest as _pytest
    _pytest.skip(f"DRF/Django not available: {e}", allow_module_level=True)

# Make randomness deterministic for any code paths that may use it
random.seed(0)

def _register_user(client: APIClient, username: str, email: str, password: str):
    """
    Helper to register a user via public registration endpoint.
    Returns the response JSON and status_code.
    """
    payload = {"user": {"username": username, "email": email, "password": password}}
    resp = client.post("/api/users/", data=payload, format="json")
    return resp

def _login_user(client: APIClient, email: str, password: str):
    """
    Helper to login and extract token and username.
    Returns tuple (status_code, token, username, raw_json)
    """
    payload = {"user": {"email": email, "password": password}}
    resp = client.post("/api/users/login", data=payload, format="json")
    data = resp.json() if resp.content else {}
    token = None
    username = None
    if isinstance(data, dict):
        user = data.get("user") or {}
        token = user.get("token")
        username = user.get("username")
    return resp.status_code, token, username, data

@pytest.mark.django_db
def test_registration_creates_related_profile_and_profile_endpoint_returns_expected_schema():
    
    # Arrange
    client = APIClient()
    username = "charlie"
    email = "charlie@example.com"
    password = "safepassword123"

    # Act: register user
    resp = _register_user(client, username=username, email=email, password=password)

    # Assert: registration succeeded and expected shape
    assert resp.status_code in (200, 201), f"unexpected status {resp.status_code} body={resp.content}"
    resp_json = resp.json()
    assert "user" in resp_json, "registration did not return 'user' key"
    user_obj = resp_json["user"]
    assert user_obj.get("email") == email
    assert user_obj.get("username") == username
    assert "token" in user_obj and isinstance(user_obj["token"], str) and len(user_obj["token"]) > 0

    # Act: fetch profile via public profile endpoint
    profile_resp = client.get(f"/api/profiles/{username}")

    # Assert: profile endpoint returns expected schema and business invariants
    assert profile_resp.status_code == 200, f"profile GET failed: {profile_resp.content}"
    profile_json = profile_resp.json()
    assert "profile" in profile_json
    profile = profile_json["profile"]
    expected_keys = {"username", "bio", "image", "following"}
    assert expected_keys.issubset(set(profile.keys()))
    assert profile["username"] == username
    # A freshly created user should not be being followed by the requester (anonymous)
    assert profile["following"] is False

@pytest.mark.django_db
def test_follow_unfollow_flow_and_unauthenticated_follow_blocked():
    
    # Arrange
    client = APIClient()

    # Create two users: alice (follower) and bob (target)
    alice_resp = _register_user(client, username="alice", email="alice@example.com", password="alicepass")
    bob_resp = _register_user(client, username="bob", email="bob@example.com", password="bobpass")

    assert alice_resp.status_code in (200, 201)
    assert bob_resp.status_code in (200, 201)

    # Act & Assert: unauthenticated attempt to follow should be rejected (permission)
    unauth_follow_resp = client.post("/api/profiles/bob/follow", format="json")
    assert unauth_follow_resp.status_code in (401, 403), "Unauthenticated follow must be forbidden"

    # Arrange: login as alice to get token
    status, token, username, _ = _login_user(client, email="alice@example.com", password="alicepass")
    assert status == 200
    assert token is not None
    # Attach auth header for subsequent requests
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    # Act: alice follows bob
    follow_resp = client.post("/api/profiles/bob/follow", format="json")
    assert follow_resp.status_code in (200, 201), f"follow failed: {follow_resp.content}"
    follow_json = follow_resp.json()
    assert "profile" in follow_json
    assert follow_json["profile"]["username"] == "bob"
    assert follow_json["profile"]["following"] is True

    # Act: alice unfollows bob
    unfollow_resp = client.delete("/api/profiles/bob/follow", format="json")
    assert unfollow_resp.status_code in (200, 204), f"unfollow failed: {unfollow_resp.content}"
    # Some APIs return 204 with empty body, handle both
    if unfollow_resp.status_code == 204:
        # Re-fetch profile to validate state
        reget = client.get("/api/profiles/bob")
        assert reget.status_code == 200
        prof = reget.json().get("profile", {})
        assert prof.get("following") is False
    else:
        unfollow_json = unfollow_resp.json()
        assert "profile" in unfollow_json
        assert unfollow_json["profile"]["following"] is False

@pytest.mark.django_db
def test_create_article_with_tags_populates_global_tag_list():
    
    # Arrange
    client = APIClient()
    username = "tagger"
    email = "tagger@example.com"
    password = "taggerpass"
    reg_resp = _register_user(client, username=username, email=email, password=password)
    assert reg_resp.status_code in (200, 201)
    status, token, _, _ = _login_user(client, email=email, password=password)
    assert status == 200 and token

    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    # Act: create an article with two deterministic tags
    tags = ["alpha", "beta"]
    article_payload = {
        "article": {
            "title": "Tag Test Article",
            "description": "Testing tags endpoint",
            "body": "Some content here",
            "tagList": tags,
        }
    }
    create_resp = client.post("/api/articles", data=article_payload, format="json")

    # Assert: article created successfully and returns expected fields
    assert create_resp.status_code in (200, 201), f"article creation failed: {create_resp.content}"
    article_json = create_resp.json()
    assert "article" in article_json
    created = article_json["article"]
    assert set(["title", "description", "body", "tagList", "slug"]).issubset(set(created.keys()))
    assert set(tags).issubset(set(created.get("tagList", [])))

    # Act: fetch tags list (public)
    tags_resp = client.get("/api/tags")
    assert tags_resp.status_code == 200, f"tags endpoint failed: {tags_resp.content}"
    tags_json = tags_resp.json()
    assert "tags" in tags_json and isinstance(tags_json["tags"], list)

    # Assert: the tags we created are present in the global tag list
    returned_tags = set(tags_json["tags"])
    for t in tags:
        assert t in returned_tags, f"expected tag '{t}' missing from global tags"
