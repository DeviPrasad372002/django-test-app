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
    from rest_framework.test import APIClient
except ImportError:  # pragma: no cover
    import pytest as _pytest
    _pytest.skip("Django REST framework or pytest not available", allow_module_level=True)

import random
import json

# Keep randomness deterministic for any internal random string generation fallback
random.seed(0)

def _register_user(client, username, email, password):
    """Helper: register and return parsed JSON response."""
    payload = {"user": {"username": username, "email": email, "password": password}}
    resp = client.post("/api/users", data=payload, format="json")
    return resp

def _login_user(client, email, password):
    payload = {"user": {"email": email, "password": password}}
    resp = client.post("/api/users/login", data=payload, format="json")
    return resp

def _auth_header(token):
    return {"HTTP_AUTHORIZATION": f"Token {token}"}

def _create_article(client, token, title, description, body, tags=None):
    data = {"article": {"title": title, "description": description, "body": body, "tagList": tags or []}}
    return client.post("/api/articles", data=data, format="json", **_auth_header(token))

def _get_article(client, slug, token=None):
    headers = _auth_header(token) if token else {}
    return client.get(f"/api/articles/{slug}", format="json", **headers)

def _delete_article(client, slug, token):
    return client.delete(f"/api/articles/{slug}", format="json", **_auth_header(token))

def _favorite_article(client, slug, token):
    return client.post(f"/api/articles/{slug}/favorite", data={}, format="json", **_auth_header(token))

@pytest.mark.django_db
def test_auth_register_login_get_user():
    
    # Arrange
    client = APIClient()

    username = "alice"
    email = "alice@example.com"
    password = "safepass123"

    # Act - register
    reg_resp = _register_user(client, username, email, password)

    # Assert registration
    assert reg_resp.status_code == 201
    reg_json = reg_resp.json()
    assert "user" in reg_json and isinstance(reg_json["user"], dict)
    assert reg_json["user"]["email"] == email
    assert reg_json["user"]["username"] == username
    assert isinstance(reg_json["user"].get("token"), str) and len(reg_json["user"]["token"]) > 0

    # Act - login
    login_resp = _login_user(client, email, password)

    # Assert login
    assert login_resp.status_code == 200
    login_json = login_resp.json()
    assert "user" in login_json
    token = login_json["user"]["token"]
    assert token == reg_json["user"]["token"]

    # Act - get current user via token
    me_resp = client.get("/api/user", format="json", **_auth_header(token))

    # Assert get user
    assert me_resp.status_code == 200
    me_json = me_resp.json()
    assert "user" in me_json
    assert me_json["user"]["email"] == email
    assert me_json["user"]["username"] == username
    # token present and matches
    assert me_json["user"]["token"] == token

@pytest.mark.django_db
def test_article_crud_and_favorite_permission(monkeypatch):
    
    # Arrange
    client = APIClient()

    
    try:
        import conduit.apps.core.utils as utils_mod

        monkeypatch.setattr(utils_mod, "generate_random_string", lambda n=6: "fixedslug")
    except Exception:
        # If module not present/accessible, push on; slug will still be deterministic enough for the test.
        pass

    # Create author (alice)
    a_user = {"username": "author", "email": "author@example.com", "password": "passA"}
    resp_a = _register_user(client, a_user["username"], a_user["email"], a_user["password"])
    assert resp_a.status_code == 201
    token_a = resp_a.json()["user"]["token"]

    # Create another user (bob)
    b_user = {"username": "bob", "email": "bob@example.com", "password": "passB"}
    resp_b = _register_user(client, b_user["username"], b_user["email"], b_user["password"])
    assert resp_b.status_code == 201
    token_b = resp_b.json()["user"]["token"]

    # Act - author creates an article with a tag
    title = "Deterministic Title"
    art_resp = _create_article(client, token_a, title, "desc", "body text", tags=["news"])

    # Assert creation
    assert art_resp.status_code == 201
    art_json = art_resp.json()
    assert "article" in art_json
    article = art_json["article"]
    assert article["title"] == title
    assert article["favoritesCount"] == 0
    assert article["author"]["username"] == a_user["username"]
    slug = article["slug"]
    assert isinstance(slug, str) and len(slug) > 0

    # Act - bob (authenticated, not author) attempts to delete -> should be forbidden
    del_resp_by_bob = _delete_article(client, slug, token_b)

    # Assert forbidden (author-only delete)
    assert del_resp_by_bob.status_code in (403, 401)

    # Act - bob favorites the article
    fav_resp = _favorite_article(client, slug, token_b)

    # Assert favoriting succeeded and updated counts
    assert fav_resp.status_code in (200, 201)
    fav_json = fav_resp.json()
    assert "article" in fav_json
    fav_article = fav_json["article"]
    assert fav_article["favorited"] is True
    assert fav_article["favoritesCount"] == 1

    # Act - get article unauthenticated
    get_resp = _get_article(client, slug, token=None)
    assert get_resp.status_code == 200
    get_json = get_resp.json()
    get_article = get_json["article"]
    # favorites count persists
    assert get_article["favoritesCount"] == 1

    # Act - author deletes the article
    del_resp_by_author = _delete_article(client, slug, token_a)

    # Assert deletion succeeded
    assert del_resp_by_author.status_code in (200, 204)

    # Act - subsequent GET should return not found
    get_after_del = client.get(f"/api/articles/{slug}", format="json")
    assert get_after_del.status_code == 404

@pytest.mark.django_db
def test_tags_list_includes_article_tags(monkeypatch):
    
    # Arrange
    client = APIClient()

    # Make any randomness deterministic for slug/tag generation
    try:
        import conduit.apps.core.utils as utils_mod

        monkeypatch.setattr(utils_mod, "generate_random_string", lambda n=6: "tagfix")
    except Exception:
        pass

    # Register a user and create an article with tags
    u = {"username": "charlie", "email": "charlie@example.com", "password": "pwC"}
    reg = _register_user(client, u["username"], u["email"], u["password"])
    assert reg.status_code == 201
    token = reg.json()["user"]["token"]

    tags = ["alpha", "beta", "gamma"]
    art_resp = _create_article(client, token, "T", "D", "B", tags=tags)
    assert art_resp.status_code == 201

    # Act - retrieve tags list endpoint
    tags_resp = client.get("/api/tags", format="json")

    # Assert
    assert tags_resp.status_code == 200
    tags_json = tags_resp.json()
    assert "tags" in tags_json and isinstance(tags_json["tags"], list)
    for tag in tags:
        assert tag in tags_json["tags"]
