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

import random
import pytest

try:
    from rest_framework.test import APIClient
    from django.contrib.auth import get_user_model
except ImportError:
    pytest.skip("Django REST framework or Django not available", allow_module_level=True)

random.seed(0)

def register_user(client, username, email, password):
    # Arrange
    payload = {"user": {"username": username, "email": email, "password": password}}
    # Act
    resp = client.post("/api/users", payload, format="json")
    # Assert minimal expectations for registration
    assert resp.status_code in (200, 201), f"unexpected status for register: {resp.status_code}, body: {getattr(resp, 'data', resp.content)}"
    data = resp.data
    assert "user" in data and "token" in data["user"], "registration response missing token"
    token = data["user"]["token"]
    return token, data["user"]

def create_article(client, token, title, description, body, tags=None):
    payload = {
        "article": {
            "title": title,
            "description": description,
            "body": body,
            "tagList": tags or [],
        }
    }
    resp = client.post("/api/articles", payload, format="json", HTTP_AUTHORIZATION=f"Token {token}")
    assert resp.status_code == 201, f"article creation failed: {resp.status_code}, {getattr(resp, 'data', resp.content)}"
    return resp.data["article"]

def post_comment(client, token, slug, body_text):
    payload = {"comment": {"body": body_text}}
    resp = client.post(f"/api/articles/{slug}/comments", payload, format="json", HTTP_AUTHORIZATION=f"Token {token}")
    return resp

def get_comments(client, slug):
    return client.get(f"/api/articles/{slug}/comments", format="json")

def favorite_article(client, token, slug):
    return client.post(f"/api/articles/{slug}/favorite", format="json", HTTP_AUTHORIZATION=f"Token {token}")

def unfavorite_article(client, token, slug):
    return client.delete(f"/api/articles/{slug}/favorite", format="json", HTTP_AUTHORIZATION=f"Token {token}")

def follow_profile(client, token, username):
    return client.post(f"/api/profiles/{username}/follow", format="json", HTTP_AUTHORIZATION=f"Token {token}")

def unfollow_profile(client, token, username):
    return client.delete(f"/api/profiles/{username}/follow", format="json", HTTP_AUTHORIZATION=f"Token {token}")

def get_article(client, slug, token=None):
    headers = {}
    if token:
        headers["HTTP_AUTHORIZATION"] = f"Token {token}"
    return client.get(f"/api/articles/{slug}", format="json", **headers)

def assert_article_schema(article):
    # Basic schema checks for article object
    keys = {"slug", "title", "description", "body", "tagList", "createdAt", "updatedAt", "favorited", "favoritesCount", "author"}
    assert keys.issubset(set(article.keys())), f"article keys missing, have: {list(article.keys())}"
    assert isinstance(article["favorited"], bool)
    assert isinstance(article["favoritesCount"], int)
    author = article["author"]
    assert "username" in author and "following" in author
    assert isinstance(author["following"], bool)

def assert_comment_schema(comment):
    keys = {"id", "createdAt", "updatedAt", "body", "author"}
    assert keys.issubset(set(comment.keys()))
    author = comment["author"]
    assert "username" in author and "following" in author
    assert isinstance(comment["id"], int)
    assert isinstance(comment["body"], str)

@pytest.mark.django_db
def test_comments_list_create_and_delete_permission():
    
    # Arrange
    client = APIClient()
    # Create article author
    token_author, author_info = register_user(client, "author_user", "author@example.com", "password123")
    # Create commenter user
    token_commenter, commenter_info = register_user(client, "commenter_user", "commenter@example.com", "password123")
    # Author creates an article
    article = create_article(client, token_author, "Test Title", "desc", "body", tags=["test"])
    slug = article["slug"]

    # Act: commenter posts a comment
    post_resp = post_comment(client, token_commenter, slug, "Nice article!")
    assert post_resp.status_code == 201, f"failed to post comment: {post_resp.status_code}"
    comment = post_resp.data["comment"]

    # Assert: comment schema, content, author linkage
    assert_comment_schema(comment)
    assert comment["body"] == "Nice article!"
    assert comment["author"]["username"] == commenter_info["username"]
    # By default, commenter is not following the author
    assert comment["author"]["following"] is False

    # Act: list comments
    list_resp = get_comments(client, slug)
    assert list_resp.status_code == 200
    assert "comments" in list_resp.data and isinstance(list_resp.data["comments"], list)
    listed = list_resp.data["comments"]
    assert any(c["id"] == comment["id"] for c in listed)

    # Act: another logged-in user (not the comment author) attempts to delete the comment
    token_other, _ = register_user(client, "other_user", "other@example.com", "password123")
    del_resp = client.delete(f"/api/articles/{slug}/comments/{comment['id']}", format="json", HTTP_AUTHORIZATION=f"Token {token_other}")
    # Assert: permission denied (403) for non-author
    assert del_resp.status_code in (403, 401), "non-author should not be allowed to delete the comment"

    # Act: comment author deletes their comment
    del_by_author = client.delete(f"/api/articles/{slug}/comments/{comment['id']}", format="json", HTTP_AUTHORIZATION=f"Token {token_commenter}")
    # Assert: delete success (204 or 200 depending on implementation)
    assert del_by_author.status_code in (200, 204)
    # Verify comment no longer appears
    list_after = get_comments(client, slug)
    assert all(c["id"] != comment["id"] for c in list_after.data["comments"])

@pytest.mark.django_db
def test_favorite_and_unfavorite_article_affects_favorited_flag_and_count():
    
    # Arrange
    client = APIClient()
    token_author, author_info = register_user(client, "fav_author", "fav_author@example.com", "password123")
    token_user, user_info = register_user(client, "fav_user", "fav_user@example.com", "password123")
    article = create_article(client, token_author, "Fav Title", "desc", "content", tags=["fav"])
    slug = article["slug"]

    # Sanity check article schema via unauthenticated get
    unauth_get = get_article(client, slug)
    assert unauth_get.status_code == 200
    article_public = unauth_get.data["article"]
    assert_article_schema(article_public)
    # Initially not favorited
    assert article_public["favorited"] is False
    base_count = article_public["favoritesCount"]
    assert isinstance(base_count, int)

    # Act: user favorites the article
    fav_resp = favorite_article(client, token_user, slug)
    assert fav_resp.status_code in (200, 201)
    fav_article = fav_resp.data["article"]
    # Assert: favorited flag true and count incremented by 1
    assert fav_article["favorited"] is True
    assert fav_article["favoritesCount"] == base_count + 1

    # Act: fetch article as this user and verify fields
    get_as_user = get_article(client, slug, token=token_user)
    assert get_as_user.status_code == 200
    article_as_user = get_as_user.data["article"]
    assert article_as_user["favorited"] is True
    assert article_as_user["favoritesCount"] == base_count + 1
    # Author should show whether this user is following the author (False)
    assert article_as_user["author"]["username"] == author_info["username"]
    assert article_as_user["author"]["following"] is False

    # Act: user unfavorites
    unfav_resp = unfavorite_article(client, token_user, slug)
    # Assert: unfavorite success and favorited false and count back to base
    assert unfav_resp.status_code in (200, 204)
    # GET to verify consistent state
    after_get = get_article(client, slug, token=token_user)
    assert after_get.status_code == 200
    after_article = after_get.data["article"]
    assert after_article["favorited"] is False
    assert after_article["favoritesCount"] == base_count

@pytest.mark.django_db
def test_follow_unfollow_changes_author_following_field_on_article_author():
    
    # Arrange
    client = APIClient()
    token_author, author_info = register_user(client, "follow_author", "follow_author@example.com", "password123")
    token_follower, follower_info = register_user(client, "follower_user", "follower@example.com", "password123")
    article = create_article(client, token_author, "Follow Title", "desc", "body", tags=[])
    slug = article["slug"]

    # Initially article's author.following is False for the follower
    get_before = get_article(client, slug, token=token_follower)
    assert get_before.status_code == 200
    assert get_before.data["article"]["author"]["following"] is False

    # Act: follower follows the author
    follow_resp = follow_profile(client, token_follower, author_info["username"])
    assert follow_resp.status_code in (200, 201)
    profile = follow_resp.data.get("profile") or follow_resp.data.get("user") or {}
    # The API should return profile with following True or the article endpoint will reflect it
    # Assert using article endpoint that the author is now followed
    get_after = get_article(client, slug, token=token_follower)
    assert get_after.status_code == 200
    assert get_after.data["article"]["author"]["following"] is True

    # Act: unfollow and verify following becomes False
    unfollow_resp = unfollow_profile(client, token_follower, author_info["username"])
    assert unfollow_resp.status_code in (200, 204)
    get_after_unfollow = get_article(client, slug, token=token_follower)
    assert get_after_unfollow.status_code == 200
    assert get_after_unfollow.data["article"]["author"]["following"] is False
