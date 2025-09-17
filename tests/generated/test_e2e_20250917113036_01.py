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
import random

try:
    from rest_framework.test import APIClient
    import django
    from django.utils import timezone as dj_timezone
except Exception:
    pytest.skip("Django REST framework or Django not available", allow_module_level=True)

def _register_user(client, username, email, password):
    payload = {"user": {"username": username, "email": email, "password": password}}
    return client.post("/api/users/", payload, format="json")

def _login_user(client, email, password):
    payload = {"user": {"email": email, "password": password}}
    return client.post("/api/users/login/", payload, format="json")

def _create_article(client, token, title, description="desc", body="body", tagList=None):
    if tagList is None:
        tagList = []
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    payload = {"article": {"title": title, "description": description, "body": body, "tagList": tagList}}
    return client.post("/api/articles/", payload, format="json")

def _favorite_article(client, token, slug):
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client.post(f"/api/articles/{slug}/favorite", {}, format="json")

def _unfavorite_article(client, token, slug):
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client.delete(f"/api/articles/{slug}/favorite", format="json")

def _delete_article(client, token, slug):
    if token:
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    else:
        client.credentials()  # remove credentials
    return client.delete(f"/api/articles/{slug}", format="json")

def _get_article(client, token, slug):
    if token:
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    else:
        client.credentials()
    return client.get(f"/api/articles/{slug}", format="json")

def _list_articles(client, token=None, params=None):
    if token:
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    else:
        client.credentials()
    if params:
        return client.get("/api/articles/", params, format="json")
    return client.get("/api/articles/", format="json")

@pytest.mark.django_db
def test_create_and_list_article_freeze_time_and_slug(monkeypatch):
    
    # Arrange
    client = APIClient()

    # Freeze timezone.now for deterministic createdAt/updatedAt
    fixed_dt = datetime.datetime(2020, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(dj_timezone, "now", lambda: fixed_dt)

    # Seed randomness deterministically
    random.seed(0)

    username = "author1"
    email = "author1@example.com"
    password = "pass1234"

    # Act: register and login
    res = _register_user(client, username, email, password)
    assert res.status_code in (200, 201)
    login_res = _login_user(client, email, password)
    assert login_res.status_code == 200
    token = login_res.json()["user"]["token"]
    assert isinstance(token, str) and token != ""

    # Act: create article
    title = "Test Article Unique Title"
    create_res = _create_article(client, token, title, description="d", body="b", tagList=["x", "y"])
    assert create_res.status_code == 201
    article = create_res.json().get("article")
    assert isinstance(article, dict)

    
    slug = article.get("slug")
    assert isinstance(slug, str) and "test-article-unique-title" in slug

    # Assert: author username
    assert article.get("author", {}).get("username") == username

    # Assert: createdAt and updatedAt are deterministic and equal
    created_at = article.get("createdAt")
    updated_at = article.get("updatedAt")
    assert created_at == updated_at
    
    assert created_at.startswith("2020-01-01T12:00:00")

    # Assert: favorites count zero, favorited False
    assert article.get("favoritesCount") == 0
    assert article.get("favorited") is False

    # Act: list articles (unauthenticated)
    list_res = _list_articles(client)
    assert list_res.status_code == 200
    results = list_res.json().get("articles")
    assert isinstance(results, list)
    # Assert our article is in list by slug
    assert any(a.get("slug") == slug for a in results)

@pytest.mark.django_db
def test_favoriting_changes_count_and_favorited_flag(monkeypatch):
    
    # Arrange
    client = APIClient()

    # Freeze time to keep createdAt invariant
    fixed_dt = datetime.datetime(2021, 6, 15, 8, 30, 0, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(dj_timezone, "now", lambda: fixed_dt)
    random.seed(0)

    # Create author and article
    author_user = {"username": "author2", "email": "author2@example.com", "password": "pw2"}
    _register_user(client, author_user["username"], author_user["email"], author_user["password"])
    login = _login_user(client, author_user["email"], author_user["password"])
    author_token = login.json()["user"]["token"]
    create = _create_article(client, author_token, "Fav Article", description="d", body="b")
    assert create.status_code == 201
    slug = create.json()["article"]["slug"]

    # Create a second user who will favorite
    fav_user = {"username": "favuser", "email": "fav@example.com", "password": "pw3"}
    _register_user(client, fav_user["username"], fav_user["email"], fav_user["password"])
    fav_login = _login_user(client, fav_user["email"], fav_user["password"])
    fav_token = fav_login.json()["user"]["token"]

    # Act: favorite the article
    fav_res = _favorite_article(client, fav_token, slug)
    assert fav_res.status_code == 200
    fav_article = fav_res.json().get("article")
    assert fav_article["favorited"] is True
    assert fav_article["favoritesCount"] == 1

    # Assert: retrieving article as favoriting user shows favorited True
    get_res = _get_article(client, fav_token, slug)
    assert get_res.status_code == 200
    got = get_res.json()["article"]
    assert got["favorited"] is True
    assert got["favoritesCount"] == 1

    # Act: unfavorite the article
    unfav_res = _unfavorite_article(client, fav_token, slug)
    assert unfav_res.status_code == 200
    unfav_article = unfav_res.json()["article"]
    assert unfav_article["favorited"] is False
    assert unfav_article["favoritesCount"] == 0

    # Assert: author still sees favoritesCount 0 and favorited False (authors don't auto-favorite)
    author_view = _get_article(client, author_token, slug)
    assert author_view.status_code == 200
    author_article = author_view.json()["article"]
    assert author_article["favorited"] is False
    assert author_article["favoritesCount"] == 0

@pytest.mark.django_db
def test_delete_article_by_non_author_forbidden_and_unauthenticated(monkeypatch):
    
    # Arrange
    client = APIClient()
    fixed_dt = datetime.datetime(2022, 3, 3, 3, 3, 3, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(dj_timezone, "now", lambda: fixed_dt)
    random.seed(0)

    # Create author and article
    auth = {"username": "author3", "email": "author3@example.com", "password": "pw4"}
    _register_user(client, auth["username"], auth["email"], auth["password"])
    login_res = _login_user(client, auth["email"], auth["password"])
    author_token = login_res.json()["user"]["token"]
    create_res = _create_article(client, author_token, "To Be Protected", description="d", body="b")
    assert create_res.status_code == 201
    slug = create_res.json()["article"]["slug"]

    # Create another user
    other = {"username": "other", "email": "other@example.com", "password": "pw5"}
    _register_user(client, other["username"], other["email"], other["password"])
    other_login = _login_user(client, other["email"], other["password"])
    other_token = other_login.json()["user"]["token"]

    # Act: attempt delete as other user (not the author)
    del_res_other = _delete_article(client, other_token, slug)
    # Assert: forbidden (403) or 401 depending on permission implementation; assert it's one of them
    assert del_res_other.status_code in (401, 403)

    # Act: attempt delete unauthenticated
    del_res_anon = _delete_article(client, token=None, slug=slug)
    # Assert: must be unauthorized (401)
    assert del_res_anon.status_code == 401

    # Finally confirm article still exists when fetched by author
    final_get = _get_article(client, author_token, slug)
    assert final_get.status_code == 200
    assert final_get.json()["article"]["slug"] == slug
