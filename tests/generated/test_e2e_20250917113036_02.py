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
except ImportError:
    import pytest as _pytest
    _pytest.skip("pytest and djangorestframework required for these tests", allow_module_level=True)

random.seed(0)

def _unique(name_prefix: str) -> str:
    # deterministic suffix via random seeded above
    return f"{name_prefix}_{random.randint(1000, 9999)}"

def _register_user(client: APIClient, username: str, email: str, password: str):
    payload = {"user": {"username": username, "email": email, "password": password}}
    resp = client.post("/api/users/", payload, format="json")
    return resp

def _login_user(client: APIClient, email: str, password: str):
    payload = {"user": {"email": email, "password": password}}
    resp = client.post("/api/users/login/", payload, format="json")
    return resp

def _auth_client_for_user(client: APIClient, token: str):
    auth_client = client
    auth_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return auth_client

def _create_article(client: APIClient, title: str, description: str, body: str, tags=None):
    if tags is None:
        tags = []
    payload = {"article": {"title": title, "description": description, "body": body, "tagList": tags}}
    resp = client.post("/api/articles/", payload, format="json")
    return resp

def _get_article(client: APIClient, slug: str):
    return client.get(f"/api/articles/{slug}", format="json")

@pytest.mark.django_db
def test_user_registration_login_and_get_current_user():
    
    # Arrange
    client = APIClient()
    username = _unique("alice")
    email = f"{username}@example.com"
    password = "s3cret-pass"

    # Act - register
    resp_reg = _register_user(client, username, email, password)

    # Assert - registration
    assert resp_reg.status_code == 201
    body = resp_reg.json()
    assert "user" in body and isinstance(body["user"], dict)
    assert body["user"].get("email") == email
    assert body["user"].get("username") == username
    token = body["user"].get("token")
    assert isinstance(token, str) and len(token) > 0

    # Act - login (using endpoint)
    resp_login = _login_user(client, email, password)

    # Assert - login
    assert resp_login.status_code == 200
    login_body = resp_login.json()
    assert "user" in login_body and login_body["user"]["email"] == email
    token_login = login_body["user"].get("token")
    assert isinstance(token_login, str) and len(token_login) > 0

    # Act - get current user with token
    auth_client = _auth_client_for_user(client, token_login)
    resp_me = auth_client.get("/api/user", format="json")

    # Assert - profile retrieved
    assert resp_me.status_code == 200
    me = resp_me.json()
    assert "user" in me and me["user"]["username"] == username and me["user"]["email"] == email

@pytest.mark.django_db
def test_article_crud_filter_and_forbidden_update_and_delete():
    
    # Arrange - register author1 and author2
    client = APIClient()
    author1 = _unique("author1")
    author1_email = f"{author1}@example.com"
    author1_pass = "password1!"
    r1 = _register_user(client, author1, author1_email, author1_pass)
    assert r1.status_code == 201
    token1 = r1.json()["user"]["token"]
    auth1 = _auth_client_for_user(client, token1)

    author2 = _unique("author2")
    author2_email = f"{author2}@example.com"
    author2_pass = "password2!"
    r2 = _register_user(client, author2, author2_email, author2_pass)
    assert r2.status_code == 201
    token2 = r2.json()["user"]["token"]
    auth2 = APIClient()
    auth2 = _auth_client_for_user(auth2, token2)

    # Act - author1 creates an article
    title = "Deterministic Title"
    description = "desc"
    body_text = "This is the article body."
    resp_create = _create_article(auth1, title, description, body_text, tags=["testtag"])

    # Assert - creation
    assert resp_create.status_code == 201
    created = resp_create.json()
    assert "article" in created and isinstance(created["article"], dict)
    article = created["article"]
    slug = article.get("slug")
    assert isinstance(slug, str) and len(slug) > 0
    assert article.get("title") == title
    assert article.get("author") and article["author"].get("username") == author1

    # Act - list articles filtered by author
    resp_list = client.get(f"/api/articles/?author={author1}", format="json")

    # Assert - filter returns the created article
    assert resp_list.status_code == 200
    list_body = resp_list.json()
    assert "articles" in list_body and isinstance(list_body["articles"], list)
    slugs = [a.get("slug") for a in list_body["articles"]]
    assert slug in slugs

    # Act - attempt to update article as author2 (should be forbidden)
    update_payload = {"article": {"body": "Malicious edit"}}
    resp_forbidden = auth2.put(f"/api/articles/{slug}", update_payload, format="json")

    # Assert - forbidden for non-author
    assert resp_forbidden.status_code in (403, 401)
    
    if resp_forbidden.status_code == 403:
        
        try:
            body = resp_forbidden.json()
            assert isinstance(body, dict)
        except ValueError:
            # empty body is acceptable for some implementations
            assert True

    # Act - delete the article as the author
    resp_delete = auth1.delete(f"/api/articles/{slug}", format="json")

    # Assert - deletion succeeded (204 or 200 depending on implementation)
    assert resp_delete.status_code in (204, 200)

    # Act - try to fetch deleted article
    resp_get_after = _get_article(client, slug)

    # Assert - article not found
    assert resp_get_after.status_code == 404
