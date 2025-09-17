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
    import django
    from rest_framework.test import APIClient
except ImportError:
    import pytest
    pytest.skip("Requires django and djangorestframework", allow_module_level=True)

django.setup()

@pytest.mark.django_db
def test_registration_and_user_retrieve_update_user_profile():
    
    # Arrange
    client = APIClient()
    register_payload = {
        "user": {
            "username": "alice",
            "email": "alice@example.com",
            "password": "password123"
        }
    }

    # Act - register
    res = client.post("/api/users/", register_payload, format="json")

    # Assert - registration
    assert res.status_code == 201
    data = res.json()
    assert "user" in data and isinstance(data["user"], dict)
    user = data["user"]
    assert user["username"] == "alice"
    assert user["email"] == "alice@example.com"
    assert isinstance(user.get("token"), str) and len(user["token"]) > 10

    token = user["token"]

    # Act - retrieve current user
    authed = APIClient()
    authed.credentials(HTTP_AUTHORIZATION="Token " + token)
    get_res = authed.get("/api/user/", format="json")

    # Assert - retrieval
    assert get_res.status_code == 200
    got = get_res.json()
    assert "user" in got and got["user"]["username"] == "alice"
    assert got["user"]["email"] == "alice@example.com"

    # Act - update user (bio and image)
    update_payload = {"user": {"bio": "Hello, I'm Alice.", "image": "http://example.org/alice.png"}}
    upd_res = authed.put("/api/user/", update_payload, format="json")

    # Assert - update applied
    assert upd_res.status_code == 200
    upd = upd_res.json()
    assert "user" in upd
    assert upd["user"]["bio"] == "Hello, I'm Alice."
    assert upd["user"]["image"] == "http://example.org/alice.png"

@pytest.mark.django_db
def test_create_article_follow_feed_favorite_and_unfavorite():
    
    # Arrange - create two users: author (bob) and reader (carol)
    client = APIClient()

    bob_payload = {"user": {"username": "bob", "email": "bob@example.com", "password": "s3cr3t"}}
    carol_payload = {"user": {"username": "carol", "email": "carol@example.com", "password": "s3cr3t2"}}

    bob_res = client.post("/api/users/", bob_payload, format="json")
    assert bob_res.status_code == 201
    bob_token = bob_res.json()["user"]["token"]

    carol_res = client.post("/api/users/", carol_payload, format="json")
    assert carol_res.status_code == 201
    carol_token = carol_res.json()["user"]["token"]

    # Author (bob) creates an article
    author_client = APIClient()
    author_client.credentials(HTTP_AUTHORIZATION="Token " + bob_token)
    article_payload = {
        "article": {
            "title": "Deterministic Testing",
            "description": "Testing article endpoints",
            "body": "This is a test body.",
            "tagList": ["testing", "e2e"]
        }
    }

    create_res = author_client.post("/api/articles/", article_payload, format="json")
    assert create_res.status_code == 201
    created = create_res.json()
    assert "article" in created and isinstance(created["article"], dict)
    article = created["article"]
    slug = article["slug"]
    assert isinstance(slug, str) and len(slug) > 0
    assert article.get("favoritesCount") == 0
    assert article.get("favorited") in (False, None) or article.get("favorited") is False

    # Reader (carol) follows bob
    reader_client = APIClient()
    reader_client.credentials(HTTP_AUTHORIZATION="Token " + carol_token)
    follow_res = reader_client.post(f"/api/profiles/{bob_payload['user']['username']}/follow/", format="json")
    assert follow_res.status_code == 200
    follow_data = follow_res.json()
    assert "profile" in follow_data
    assert follow_data["profile"]["username"] == "bob"
    assert follow_data["profile"]["following"] is True

    # Reader fetches feed - should include the article by bob
    feed_res = reader_client.get("/api/articles/feed/", format="json")
    assert feed_res.status_code == 200
    feed = feed_res.json()
    assert "articles" in feed and isinstance(feed["articles"], list)
    slugs = [a["slug"] for a in feed["articles"] if "slug" in a]
    assert slug in slugs

    # Reader favorites the article
    fav_res = reader_client.post(f"/api/articles/{slug}/favorite/", format="json")
    assert fav_res.status_code == 200
    fav_data = fav_res.json()
    assert "article" in fav_data
    assert fav_data["article"]["slug"] == slug
    assert fav_data["article"]["favorited"] is True
    assert isinstance(fav_data["article"]["favoritesCount"], int) and fav_data["article"]["favoritesCount"] >= 1

    # Reader unfavorites the article
    unfav_res = reader_client.delete(f"/api/articles/{slug}/favorite/", format="json")
    assert unfav_res.status_code == 200
    unfav_data = unfav_res.json()
    assert "article" in unfav_data
    assert unfav_data["article"]["slug"] == slug
    # After unfavoriting it should not be favorited and count should be decreased (back to 0)
    assert unfav_data["article"]["favorited"] is False
    assert isinstance(unfav_data["article"]["favoritesCount"], int)
    assert unfav_data["article"]["favoritesCount"] >= 0
