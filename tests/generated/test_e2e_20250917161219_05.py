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
import datetime

try:
    from rest_framework.test import APIClient
except ImportError:
    pytest.skip("rest_framework not available", allow_module_level=True)

try:
    import conduit.apps.core.utils as core_utils
    import django.utils.timezone as dj_tz
except Exception:
    pytest.skip("Required project modules not available", allow_module_level=True)

@pytest.mark.django_db
def test_article_create_and_retrieve_roundtrip(monkeypatch):
    
    # Arrange
    fixed_dt = datetime.datetime(2020, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(dj_tz, "now", lambda: fixed_dt)
    monkeypatch.setattr(core_utils, "generate_random_string", lambda n=6: "FIXED")

    client = APIClient()

    # Register user
    reg_payload = {"user": {"username": "alice", "email": "alice@example.com", "password": "password123"}}
    r = client.post("/api/users/", reg_payload, format="json")
    assert r.status_code == 201
    assert "user" in r.data and "email" in r.data["user"]
    # Login to get token
    login_payload = {"user": {"email": "alice@example.com", "password": "password123"}}
    r = client.post("/api/users/login/", login_payload, format="json")
    assert r.status_code == 200
    token = r.data["user"]["token"]
    auth_header = {"HTTP_AUTHORIZATION": f"Token {token}"}

    # Act: create article
    article_payload = {
        "article": {
            "title": "Test Article",
            "description": "desc",
            "body": "body text",
            "tagList": ["tag1", "tag2"],
        }
    }
    r = client.post("/api/articles/", article_payload, format="json", **auth_header)

    # Assert create response
    assert r.status_code == 201
    assert "article" in r.data
    art = r.data["article"]
    assert art["title"] == "Test Article"
    assert art["description"] == "desc"
    assert isinstance(art["tagList"], list) and set(art["tagList"]) == {"tag1", "tag2"}
    # slug expected to include slugified title and our fixed random suffix
    assert "FIXED" in art["slug"]
    assert art["favorited"] is False
    assert art["favoritesCount"] == 0
    assert art["author"]["username"] == "alice"
    # createdAt/updatedAt should reflect our frozen time in ISO format start
    assert art["createdAt"].startswith("2020-01-01T12:00:00")
    assert art["updatedAt"].startswith("2020-01-01T12:00:00")

    slug = art["slug"]

    # Act: retrieve the article
    r = client.get(f"/api/articles/{slug}/", format="json")

    # Assert retrieval matches
    assert r.status_code == 200
    got = r.data["article"]
    assert got["slug"] == art["slug"]
    assert got["title"] == "Test Article"
    assert got["author"]["username"] == "alice"

@pytest.mark.django_db
def test_comment_delete_permission_enforced(monkeypatch):
    
    # Arrange
    fixed_dt = datetime.datetime(2020, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(dj_tz, "now", lambda: fixed_dt)
    monkeypatch.setattr(core_utils, "generate_random_string", lambda n=6: "FIXED")

    client = APIClient()

    # Create author and article
    client.post("/api/users/", {"user": {"username": "author", "email": "author@example.com", "password": "pw"}}, format="json")
    r = client.post("/api/users/login/", {"user": {"email": "author@example.com", "password": "pw"}}, format="json")
    token_author = r.data["user"]["token"]
    auth_author = {"HTTP_AUTHORIZATION": f"Token {token_author}"}

    art_payload = {"article": {"title": "Authored", "description": "d", "body": "b"}}
    r = client.post("/api/articles/", art_payload, format="json", **auth_author)
    assert r.status_code == 201
    slug = r.data["article"]["slug"]

    # Author posts a comment
    r = client.post(f"/api/articles/{slug}/comments", {"comment": {"body": "a comment"}}, format="json", **auth_author)
    assert r.status_code == 201
    comment = r.data["comment"]
    comment_id = comment["id"]
    assert comment["body"] == "a comment"
    assert comment["author"]["username"] == "author"

    # Create another user (attacker)
    client.post("/api/users/", {"user": {"username": "hacker", "email": "hacker@example.com", "password": "pw"}}, format="json")
    r = client.post("/api/users/login/", {"user": {"email": "hacker@example.com", "password": "pw"}}, format="json")
    token_hacker = r.data["user"]["token"]
    auth_hacker = {"HTTP_AUTHORIZATION": f"Token {token_hacker}"}

    # Act: hacker attempts to delete author's comment
    r = client.delete(f"/api/articles/{slug}/comments/{comment_id}", format="json", **auth_hacker)

    # Assert: forbidden
    assert r.status_code == 403

    # Act: author deletes their own comment
    r = client.delete(f"/api/articles/{slug}/comments/{comment_id}", format="json", **auth_author)

    # Assert: successful deletion (204 No Content expected)
    assert r.status_code == 204

    # Confirm comment no longer retrievable via list
    r = client.get(f"/api/articles/{slug}/comments", format="json")
    assert r.status_code == 200
    
    ids = [c["id"] for c in r.data.get("comments", [])]
    assert comment_id not in ids

@pytest.mark.django_db
def test_favorite_toggle_updates_counts_and_flags(monkeypatch):
    
    # Arrange
    fixed_dt = datetime.datetime(2020, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(dj_tz, "now", lambda: fixed_dt)
    monkeypatch.setattr(core_utils, "generate_random_string", lambda n=6: "FIXED")

    client = APIClient()

    # Create article author and their article
    client.post("/api/users/", {"user": {"username": "author2", "email": "author2@example.com", "password": "pw"}}, format="json")
    r = client.post("/api/users/login/", {"user": {"email": "author2@example.com", "password": "pw"}}, format="json")
    token_author = r.data["user"]["token"]
    auth_author = {"HTTP_AUTHORIZATION": f"Token {token_author}"}

    r = client.post("/api/articles/", {"article": {"title": "FavMe", "description": "d", "body": "b"}}, format="json", **auth_author)
    assert r.status_code == 201
    slug = r.data["article"]["slug"]

    # Create user who will favorite
    client.post("/api/users/", {"user": {"username": "fave_user", "email": "fave@example.com", "password": "pw"}}, format="json")
    r = client.post("/api/users/login/", {"user": {"email": "fave@example.com", "password": "pw"}}, format="json")
    token_fave = r.data["user"]["token"]
    auth_fave = {"HTTP_AUTHORIZATION": f"Token {token_fave}"}

    # Act: favorite the article
    r = client.post(f"/api/articles/{slug}/favorite", format="json", **auth_fave)

    # Assert: favorited and count incremented
    assert r.status_code == 200
    art = r.data["article"]
    assert art["favorited"] is True
    assert art["favoritesCount"] == 1

    # Act: unfavorite the article
    r = client.delete(f"/api/articles/{slug}/favorite", format="json", **auth_fave)

    # Assert: unfavorited and count decremented
    assert r.status_code == 200
    art = r.data["article"]
    assert art["favorited"] is False
    assert art["favoritesCount"] == 0
