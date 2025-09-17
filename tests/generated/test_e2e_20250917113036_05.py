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
    import random
    from rest_framework.test import APIClient
    from django.utils import timezone
except ImportError as e:
    import pytest
    pytest.skip("Required test dependencies not available: {}".format(e), allow_module_level=True)

import datetime

# Freeze time for deterministic tokens/timestamps used by the app
_FIXED_NOW = datetime.datetime(2020, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

@pytest.fixture(autouse=True)
def freeze_time(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: _FIXED_NOW)
    # seed randomness used by any slug/random helpers
    random.seed(0)

def _register_and_get_token(client: APIClient, email: str, username: str, password: str = "password123"):
    # Arrange
    payload = {"user": {"username": username, "email": email, "password": password}}
    # Act
    resp = client.post("/api/users/", payload, format="json")
    assert resp.status_code == 201, "Registration failed: {}".format(resp.content)
    body = resp.json()
    token = body["user"].get("token")
    assert isinstance(token, str) and token, "No token returned on registration"
    return token, body["user"]

@pytest.mark.django_db
def test_articles_favorite_flow_increments_and_reflects_favorited_state():
    
    # Arrange
    client = APIClient()
    token_author, author_user = _register_and_get_token(client, "author@example.com", "author_user")
    token_user2, user2 = _register_and_get_token(client, "reader@example.com", "reader_user")

    # Author creates an article
    article_payload = {
        "article": {
            "title": "Deterministic Title",
            "description": "desc",
            "body": "content",
            "tagList": ["testing", "deterministic"]
        }
    }
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_author}")
    post_resp = client.post("/api/articles/", article_payload, format="json")
    assert post_resp.status_code == 201
    article = post_resp.json()["article"]
    slug = article["slug"]
    assert article["title"] == "Deterministic Title"
    assert set(article.get("tagList", [])) == {"testing", "deterministic"}
    assert article.get("favoritesCount", 0) == 0

    # Act: user2 favorites the article
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_user2}")
    fav_resp = client.post(f"/api/articles/{slug}/favorite", {}, format="json")
    
    assert fav_resp.status_code in (200, 201)
    fav_body = fav_resp.json()
    assert "article" in fav_body
    article_after_fav = fav_body["article"]

    # Assert: favorited state and count reflect the action
    assert article_after_fav["favorited"] is True
    assert article_after_fav["favoritesCount"] == 1

    # GET article as author should show favoritesCount == 1 but favorited False for author
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_author}")
    get_resp = client.get(f"/api/articles/{slug}", format="json")
    assert get_resp.status_code == 200
    get_article = get_resp.json()["article"]
    assert get_article["favoritesCount"] == 1
    assert get_article["favorited"] is False

@pytest.mark.django_db
def test_comments_create_and_delete_permission_enforced():
    
    # Arrange
    client = APIClient()
    token_author, author_user = _register_and_get_token(client, "c_author@example.com", "c_author")
    token_other, other_user = _register_and_get_token(client, "c_other@example.com", "c_other")

    # Author creates an article
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_author}")
    art_payload = {"article": {"title": "Commented Article", "description": "d", "body": "b"}}
    art_resp = client.post("/api/articles/", art_payload, format="json")
    assert art_resp.status_code == 201
    slug = art_resp.json()["article"]["slug"]

    # Author posts a comment
    comment_payload = {"comment": {"body": "This is an author comment"}}
    com_post = client.post(f"/api/articles/{slug}/comments", comment_payload, format="json")
    assert com_post.status_code == 201
    comment = com_post.json()["comment"]
    comment_id = comment["id"]
    assert comment["body"] == "This is an author comment"
    assert "createdAt" in comment and "updatedAt" in comment

    # Act: other user attempts to delete the author's comment
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_other}")
    delete_resp = client.delete(f"/api/articles/{slug}/comments/{comment_id}", format="json")

    # Assert: permission denied (403) or 404 depending on implementation — prefer 403 for explicit permission
    assert delete_resp.status_code in (403, 404), f"Unexpected status code deleting other's comment: {delete_resp.status_code}"

    # Author deletes their comment successfully
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_author}")
    delete_auth_resp = client.delete(f"/api/articles/{slug}/comments/{comment_id}", format="json")
    assert delete_auth_resp.status_code in (200, 204), "Author should be able to delete own comment"
    # Verify comment no longer appears
    list_resp = client.get(f"/api/articles/{slug}/comments", format="json")
    assert list_resp.status_code == 200
    comments = list_resp.json().get("comments", [])
    assert all(c["id"] != comment_id for c in comments)

@pytest.mark.django_db
def test_feed_and_tags_list_respect_following_relationship_and_tag_listing():
    
    # Arrange
    client = APIClient()
    token_author, author_user = _register_and_get_token(client, "feed_author@example.com", "feed_author")
    token_follower, follower_user = _register_and_get_token(client, "follower@example.com", "follower")

    # Author creates two articles with distinct tags
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_author}")
    a1 = {"article": {"title": "Feed Article One", "description": "d1", "body": "b1", "tagList": ["alpha", "common"]}}
    a2 = {"article": {"title": "Feed Article Two", "description": "d2", "body": "b2", "tagList": ["beta", "common"]}}
    r1 = client.post("/api/articles/", a1, format="json")
    r2 = client.post("/api/articles/", a2, format="json")
    assert r1.status_code == 201 and r2.status_code == 201

    # Follower follows author via public profile endpoint (common RealWorld: POST /api/profiles/:username/follow)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_follower}")
    follow_resp = client.post(f"/api/profiles/{author_user['username']}/follow", {}, format="json")
    assert follow_resp.status_code in (200, 201)
    follow_body = follow_resp.json()
    assert "profile" in follow_body and follow_body["profile"]["username"] == author_user["username"]
    assert follow_body["profile"].get("following") is True

    # Act: follower requests feed; should include author's articles
    feed_resp = client.get("/api/articles/feed", format="json")
    assert feed_resp.status_code == 200
    feed_body = feed_resp.json()
    assert "articles" in feed_body and isinstance(feed_body["articles"], list)
    titles = {a["title"] for a in feed_body["articles"]}
    assert "Feed Article One" in titles and "Feed Article Two" in titles

    # Tag list endpoint returns tags including ones we used
    tags_resp = client.get("/api/tags", format="json")
    assert tags_resp.status_code == 200
    tags_body = tags_resp.json()
    assert "tags" in tags_body and isinstance(tags_body["tags"], list)
    assert "alpha" in tags_body["tags"]
    assert "beta" in tags_body["tags"]
    assert "common" in tags_body["tags"]
