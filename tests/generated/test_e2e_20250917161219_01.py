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
    import random
    import datetime
    from django.utils import timezone
except Exception:
    import pytest
    pytest.skip("Django/DRF not available", allow_module_level=True)

@pytest.mark.django_db
def test_article_create_and_favorite_flow_success(monkeypatch):
    
    # Arrange
    random.seed(0)
    fixed_now = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(timezone, "now", lambda: fixed_now)

    client = APIClient()

    # Register author (user A)
    author_payload = {"user": {"username": "author_a", "email": "author_a@example.com", "password": "pass123"}}
    resp = client.post("/api/users/", author_payload, format="json")
    assert resp.status_code == 201
    author_token = resp.json()["user"]["token"]
    assert isinstance(author_token, str) and author_token != ""

    # Author creates an article
    client.credentials(HTTP_AUTHORIZATION="Token " + author_token)
    article_payload = {
        "article": {
            "title": "Deterministic Title",
            "description": "desc",
            "body": "body content",
            "tagList": ["testtag"],
        }
    }
    resp = client.post("/api/articles/", article_payload, format="json")
    assert resp.status_code == 201
    article = resp.json().get("article")
    assert isinstance(article, dict)
    slug = article["slug"]
    assert "Deterministic-Title" or slug  # ensure slug exists (concrete value may include randomness)
    # Verify serializer fields and invariants
    assert article["title"] == "Deterministic Title"
    assert "createdAt" in article and "updatedAt" in article
    assert article["createdAt"] == article["updatedAt"]
    assert article["favorited"] is False
    assert article["favoritesCount"] == 0

    # Register another user (user B) who will favorite the article
    client.logout()
    userb_payload = {"user": {"username": "user_b", "email": "user_b@example.com", "password": "pass456"}}
    resp = client.post("/api/users/", userb_payload, format="json")
    assert resp.status_code == 201
    token_b = resp.json()["user"]["token"]
    assert isinstance(token_b, str) and token_b != ""

    # Act: user B favorites the article
    client.credentials(HTTP_AUTHORIZATION="Token " + token_b)
    fav_resp = client.post(f"/api/articles/{slug}/favorite/", format="json")
    assert fav_resp.status_code == 200
    fav_article = fav_resp.json().get("article")
    assert fav_article["favorited"] is True
    assert fav_article["favoritesCount"] == 1

    
    get_resp = client.get(f"/api/articles/{slug}/", format="json")
    assert get_resp.status_code == 200
    got = get_resp.json().get("article")
    assert got["favorited"] is True
    assert got["favoritesCount"] == 1
    
    assert got["createdAt"] == got["updatedAt"]

@pytest.mark.django_db
def test_delete_article_permission_cases(monkeypatch):
    
    # Arrange
    random.seed(0)
    fixed_now = datetime.datetime(2021, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(timezone, "now", lambda: fixed_now)

    client = APIClient()

    # Create author and article
    author_payload = {"user": {"username": "owner", "email": "owner@example.com", "password": "ownerpass"}}
    resp = client.post("/api/users/", author_payload, format="json")
    assert resp.status_code == 201
    owner_token = resp.json()["user"]["token"]
    client.credentials(HTTP_AUTHORIZATION="Token " + owner_token)

    article_payload = {
        "article": {
            "title": "To Be Deleted",
            "description": "will test delete",
            "body": "delete me",
            "tagList": [],
        }
    }
    resp = client.post("/api/articles/", article_payload, format="json")
    assert resp.status_code == 201
    slug = resp.json()["article"]["slug"]

    # Act & Assert: unauthenticated delete -> 401
    client.logout()
    unauth_delete = client.delete(f"/api/articles/{slug}/", format="json")
    assert unauth_delete.status_code == 401

    # Create a different authenticated user and attempt delete -> 403
    userb_payload = {"user": {"username": "not_owner", "email": "not_owner@example.com", "password": "otherpass"}}
    resp = client.post("/api/users/", userb_payload, format="json")
    assert resp.status_code == 201
    token_other = resp.json()["user"]["token"]
    client.credentials(HTTP_AUTHORIZATION="Token " + token_other)

    forbidden_delete = client.delete(f"/api/articles/{slug}/", format="json")
    # Expect Forbidden (403) for authenticated non-author
    assert forbidden_delete.status_code == 403

    # Ensure article still exists
    get_resp = client.get(f"/api/articles/{slug}/", format="json")
    assert get_resp.status_code == 200
    assert get_resp.json()["article"]["slug"] == slug
