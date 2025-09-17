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

try:
    import pytest
    import random
    from rest_framework.test import APIClient
except ImportError:
    import pytest as _pytest
    _pytest.skip("Django/DRF not available", allow_module_level=True)

random.seed(0)

def _register_user(client, username, email, password="password123"):
    """Helper to register a user via public registration endpoint."""
    payload = {"user": {"username": username, "email": email, "password": password}}
    resp = client.post("/api/users/", payload, format="json")
    return resp

def _login_user(client, email, password="password123"):
    payload = {"user": {"email": email, "password": password}}
    resp = client.post("/api/users/login/", payload, format="json")
    return resp

def _auth_client_for_token(client, token):
    client.credentials(HTTP_AUTHORIZATION="Token " + token)
    return client

@pytest.mark.django_db
def test_articles_favorite_unfavorite_by_different_users():
    
    # Arrange
    client = APIClient()

    # Create author A
    username_a = f"author_a_{random.randint(1000,9999)}"
    email_a = username_a + "@example.com"
    r = _register_user(client, username_a, email_a)
    assert r.status_code == 201
    token_a = r.json()["user"]["token"]

    # Create user B who will favorite/unfavorite
    username_b = f"user_b_{random.randint(1000,9999)}"
    email_b = username_b + "@example.com"
    r = _register_user(client, username_b, email_b)
    assert r.status_code == 201
    token_b = r.json()["user"]["token"]

    # Author A creates article
    _auth_client_for_token(client, token_a)
    article_payload = {
        "article": {
            "title": "Deterministic Title",
            "description": "desc",
            "body": "body",
            "tagList": ["test"],
        }
    }
    create_resp = client.post("/api/articles/", article_payload, format="json")
    assert create_resp.status_code == 201
    article = create_resp.json()["article"]
    slug = article["slug"]
    # Business invariant: creator is not automatically marked as having favorited by another user
    assert article["favoritesCount"] == 0
    assert article["favorited"] is False

    # Act: user B favorites the article
    client = APIClient()  # fresh client for user B
    _auth_client_for_token(client, token_b)
    fav_resp = client.post(f"/api/articles/{slug}/favorite/", format="json")
    
    assert fav_resp.status_code == 200
    fav_article = fav_resp.json()["article"]
    assert fav_article["slug"] == slug
    assert fav_article["favorited"] is True
    assert isinstance(fav_article["favoritesCount"], int) and fav_article["favoritesCount"] == 1

    # Act: user B unfavorites the article (DELETE)
    unfav_resp = client.delete(f"/api/articles/{slug}/favorite/", format="json")
    # Assert: unfavorite succeeded and counts updated
    assert unfav_resp.status_code in (200, 204)
    # GET the article to confirm state (some APIs return 200 on delete with body, some 204)
    get_resp = client.get(f"/api/articles/{slug}/", format="json")
    assert get_resp.status_code == 200
    got = get_resp.json()["article"]
    assert got["slug"] == slug
    assert got["favorited"] is False
    assert isinstance(got["favoritesCount"], int) and got["favoritesCount"] == 0

@pytest.mark.django_db
def test_follow_and_comment_delete_permissions_and_unauthenticated_follow_denied():
    
    # Arrange
    client = APIClient()

    # Create profile owner user C
    username_c = f"user_c_{random.randint(1000,9999)}"
    email_c = username_c + "@example.com"
    r = _register_user(client, username_c, email_c)
    assert r.status_code == 201
    token_c = r.json()["user"]["token"]

    # Create other user D
    username_d = f"user_d_{random.randint(1000,9999)}"
    email_d = username_d + "@example.com"
    r = _register_user(client, username_d, email_d)
    assert r.status_code == 201
    token_d = r.json()["user"]["token"]

    # User C creates an article
    _auth_client_for_token(client, token_c)
    article_payload = {
        "article": {
            "title": "Owner Article",
            "description": "desc",
            "body": "body",
            "tagList": [],
        }
    }
    create_resp = client.post("/api/articles/", article_payload, format="json")
    assert create_resp.status_code == 201
    slug = create_resp.json()["article"]["slug"]

    # User C posts a comment
    comment_payload = {"comment": {"body": "A protective comment"}}
    comment_resp = client.post(f"/api/articles/{slug}/comments/", comment_payload, format="json")
    assert comment_resp.status_code == 201
    comment = comment_resp.json()["comment"]
    comment_id = comment["id"]
    assert comment["body"] == "A protective comment"
    # Business invariant: comment author.username equals user C
    assert comment["author"]["username"] == username_c

    # Act: user D attempts to delete C's comment
    client_d = APIClient()
    _auth_client_for_token(client_d, token_d)
    del_resp = client_d.delete(f"/api/articles/{slug}/comments/{comment_id}/", format="json")
    # Assert: deletion by non-author should be forbidden (403) or unauthorized (403 is expected for object-permissions)
    assert del_resp.status_code in (403, 404)

    # Act: user D follows user C
    follow_resp = client_d.post(f"/api/profiles/{username_c}/follow/", format="json")
    # Assert: following succeeded and profile payload shows following True
    assert follow_resp.status_code == 200
    profile = follow_resp.json()["profile"]
    assert profile["username"] == username_c
    assert profile["following"] is True

    # Negative case: unauthenticated attempt to follow should be denied
    anon = APIClient()
    anon_follow = anon.post(f"/api/profiles/{username_c}/follow/", format="json")
    assert anon_follow.status_code in (401, 403)
