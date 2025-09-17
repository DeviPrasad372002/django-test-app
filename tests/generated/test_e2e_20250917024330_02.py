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
    import json
    from datetime import datetime
    import pytest
    from rest_framework.test import APIClient
except Exception:
    import pytest
    pytest.skip("pytest, rest_framework or stdlib modules are required", allow_module_level=True)

pytestmark = [pytest.mark.django_db]

def _register(client, username, email, password):
    payload = {"user": {"username": username, "email": email, "password": password}}
    resp = client.post("/api/users/", data=json.dumps(payload), content_type="application/json")
    return resp

def _login(client, email, password):
    payload = {"user": {"email": email, "password": password}}
    resp = client.post("/api/users/login", data=json.dumps(payload), content_type="application/json")
    return resp

def _create_article(client, token, title="T", description="D", body="B", tags=None):
    if tags is None:
        tags = []
    if token is not None:
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    payload = {"article": {"title": title, "description": description, "body": body, "tagList": tags}}
    resp = client.post("/api/articles/", data=json.dumps(payload), content_type="application/json")
    return resp

def _post_comment(client, token, slug, body):
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    payload = {"comment": {"body": body}}
    resp = client.post(f"/api/articles/{slug}/comments", data=json.dumps(payload), content_type="application/json")
    return resp

def _get_comments(client, slug):
    return client.get(f"/api/articles/{slug}/comments")

def _delete_comment(client, token, slug, comment_id):
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client.delete(f"/api/articles/{slug}/comments/{comment_id}")

def test_users_register_login_and_user_endpoint_returns_token_and_email():
    
    # Arrange
    client = APIClient()
    username = "alice_e2e"
    email = "alice_e2e@example.com"
    password = "strongpassword123"

    # Act - register
    resp_reg = _register(client, username, email, password)

    # Assert - registration
    assert resp_reg.status_code == 201, f"expected 201 created, got {resp_reg.status_code} body={resp_reg.content!r}"
    data = resp_reg.json()
    assert isinstance(data, dict)
    assert "user" in data
    user_block = data["user"]
    assert user_block["email"] == email
    assert user_block["username"] == username
    assert isinstance(user_block.get("token"), str) and len(user_block["token"]) > 10

    # Act - login
    resp_login = _login(client, email, password)

    # Assert - login
    assert resp_login.status_code == 200, f"expected 200 ok on login, got {resp_login.status_code}"
    login_data = resp_login.json()
    assert "user" in login_data
    token = login_data["user"].get("token")
    assert isinstance(token, str) and len(token) > 10

    # Act - get current user using token
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    resp_me = client.get("/api/user")

    
    assert resp_me.status_code == 200, f"expected 200 ok on /api/user, got {resp_me.status_code}"
    me_data = resp_me.json()
    assert "user" in me_data
    assert me_data["user"]["email"] == email
    assert me_data["user"]["username"] == username

def test_comments_create_list_and_delete_lifecycle():
    
    # Arrange
    client = APIClient()

    # create author (article owner)
    author_un = "author_e2e"
    author_email = "author_e2e@example.com"
    author_pw = "pw_author_123"
    resp = _register(client, author_un, author_email, author_pw)
    assert resp.status_code == 201
    author_token = resp.json()["user"]["token"]

    # create article by author
    article_title = "E2E Article"
    resp_article = _create_article(client, author_token, title=article_title, description="desc", body="body", tags=["x"])
    assert resp_article.status_code == 201, f"article creation failed: {resp_article.status_code} {resp_article.content!r}"
    article = resp_article.json().get("article")
    assert isinstance(article, dict)
    slug = article.get("slug")
    assert isinstance(slug, str) and len(slug) > 0

    # create commenter user
    commenter_un = "commenter_e2e"
    commenter_email = "commenter_e2e@example.com"
    commenter_pw = "pw_commenter_123"
    resp_commenter = _register(client, commenter_un, commenter_email, commenter_pw)
    assert resp_commenter.status_code == 201
    commenter_token = resp_commenter.json()["user"]["token"]

    # Act - commenter posts a comment
    comment_body = "This is a deterministic comment."
    resp_post = _post_comment(client, commenter_token, slug, comment_body)

    # Assert - posting comment
    assert resp_post.status_code == 201, f"expected 201 on comment create, got {resp_post.status_code} body={resp_post.content!r}"
    comment_obj = resp_post.json().get("comment")
    assert isinstance(comment_obj, dict)
    assert comment_obj["body"] == comment_body
    assert isinstance(comment_obj.get("id"), int)
    assert isinstance(comment_obj.get("author"), dict)
    assert comment_obj["author"].get("username") == commenter_un
    # createdAt should be a non-empty ISO-like string
    created_at = comment_obj.get("createdAt")
    assert isinstance(created_at, str) and len(created_at) > 10
    
    created_to_parse = created_at.rstrip("Z")
    
    assert "T" in created_to_parse

    comment_id = comment_obj["id"]

    # Act - list comments
    resp_list = _get_comments(client, slug)

    
    assert resp_list.status_code == 200, f"expected 200 on comment list, got {resp_list.status_code}"
    list_data = resp_list.json()
    assert "comments" in list_data
    comments = list_data["comments"]
    assert isinstance(comments, list)
    assert any(c["id"] == comment_id and c["body"] == comment_body for c in comments)

    # Act - delete comment as the commenter
    resp_del = _delete_comment(client, commenter_token, slug, comment_id)

    # Assert - deletion succeeded (204 No Content or 200 OK accepted)
    assert resp_del.status_code in (200, 204), f"unexpected delete status {resp_del.status_code} body={resp_del.content!r}"

    # Act - list comments after deletion
    resp_list_after = _get_comments(client, slug)

    # Assert - comment removed
    assert resp_list_after.status_code == 200
    comments_after = resp_list_after.json().get("comments", [])
    assert all(c["id"] != comment_id for c in comments_after), "deleted comment still present in list"
