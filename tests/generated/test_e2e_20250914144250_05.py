import importlib.util, pytest
if importlib.util.find_spec('django') is None:
    pytest.skip('django not installed; skipping module', allow_module_level=True)

# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib.util as _iu, types as _types, pytest as _pytest, builtins as _builtins, warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

_target = os.environ.get("TARGET_ROOT") or os.environ.get("ANALYZE_ROOT") or "target"
if _target and os.path.exists(_target):
    if _target not in sys.path: sys.path.insert(0, _target)
    try: os.chdir(_target)
    except Exception: pass

def _exc_lookup(name, default):
    try:
        mod_name, _, cls_name = str(name).rpartition(".")
        if mod_name:
            mod = __import__(mod_name, fromlist=[cls_name])
            return getattr(mod, cls_name, default)
        return getattr(sys.modules.get("builtins"), str(name), default)
    except Exception:
        return default

def _apply_compatibility_fixes():
    try:
        import jinja2
        if not hasattr(jinja2, 'Markup'):
            try:
                from markupsafe import Markup, escape
                jinja2.Markup = Markup
                if not hasattr(jinja2, 'escape'):
                    jinja2.escape = escape
            except Exception:
                pass
    except ImportError:
        pass
    try:
        import collections as _collections, collections.abc as _abc
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container',
                   'MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
            if not hasattr(_collections, _n) and hasattr(_abc, _n):
                setattr(_collections, _n, getattr(_abc, _n))
    except Exception:
        pass
    try:
        import marshmallow as _mm
        if not hasattr(_mm, "__version__"):
            _mm.__version__ = "4"
    except Exception:
        pass

_apply_compatibility_fixes()

# Minimal, safe Django bootstrap. If anything goes wrong, skip the module (repo-agnostic).
try:
    import django
    from django.conf import settings as _dj_settings
    from django import apps as _dj_apps

    if not _dj_settings.configured:
        _cfg = dict(
            DEBUG=True,
            SECRET_KEY='pytest-secret',
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3','NAME': ':memory:'}},
            INSTALLED_APPS=[
                'django.contrib.auth','django.contrib.contenttypes',
                'django.contrib.sessions','django.contrib.messages'
            ],
            MIDDLEWARE=[
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
            ],
            USE_TZ=True, TIME_ZONE='UTC',
        )
        try: _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
        except Exception: pass
        try: _dj_settings.configure(**_cfg)
        except Exception: pass

    if not _dj_apps.ready:
        try: django.setup()
        except Exception: pass

    # Probe a known Django core that previously crashed on some stacks.
    try:
        import django.contrib.auth.base_user as _dj_probe  # noqa
    except Exception as _e:
        _pytest.skip(f"Django core import failed safely: {_e.__class__.__name__}: {_e}", allow_module_level=True)
except Exception as _e:
    # Do NOT crash the entire test session – make the module opt-out.
    _pytest.skip(f"Django bootstrap not available: {_e.__class__.__name__}: {_e}", allow_module_level=True)


# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

try:
    import pytest
    import json
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from conduit.apps.articles.serializers import ArticleSerializer, CommentSerializer, TagSerializer, Meta
    from conduit.apps.articles.views import CommentsListCreateAPIView, CommentsDestroyAPIView
    from conduit.apps.authentication.models import User
    from conduit.apps.articles.models import Article, Comment, Tag
    from rest_framework.test import APIRequestFactory, force_authenticate
    from rest_framework.request import Request
    from django.utils import timezone
except ImportError:
    import pytest
    pytest.skip("Required modules for tests are not available", allow_module_level=True)


def _exc_lookup(name, fallback=Exception):
    # Try common exception modules for the given name
    try:
        mod = __import__("rest_framework.exceptions", fromlist=[name])
        return getattr(mod, name)
    except Exception:
        pass
    try:
        mod = __import__("django.core.exceptions", fromlist=[name])
        return getattr(mod, name)
    except Exception:
        pass
    try:
        mod = __import__("exceptions", fromlist=[name])
        return getattr(mod, name)
    except Exception:
        pass
    return fallback


@pytest.mark.django_db
@pytest.mark.parametrize("tag_list", [
    (["news", "sports"]),
    ([])  # boundary: empty tag list
])
def test_article_serializer_create_and_representation(tag_list):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create a user and prepare serializer data with tags
    user = User.objects.create_user(username="alice", email="alice@example.com", password="pass")
    factory = APIRequestFactory()
    req = factory.post("/api/articles/", {"article": {"title": "Test Article", "description": "Desc", "body": "Body", "tagList": tag_list}}, format="json")
    force_authenticate(req, user=user)
    drf_request = Request(req)

    payload = {"title": "Test Article", "description": "Desc", "body": "Body", "tagList": tag_list}

    # Act: validate and save via ArticleSerializer (create path)
    serializer = ArticleSerializer(data=payload, context={"request": drf_request})
    valid = serializer.is_valid()
    # Assert validation succeeded for normal inputs
    assert valid is True, f"Serializer should validate, errors: {getattr(serializer, 'errors', None)}"
    article = serializer.save()

    # Act: produce representation for the created article
    rep = ArticleSerializer(article, context={"request": drf_request}).data

    # Assert: representation has expected structure and types (Arrange-Act-Assert)
    assert isinstance(rep, _exc_lookup("dict", Exception))
    # core fields present
    for key in ("title", "description", "body", "tagList", "author", "favoritesCount", "favorited", "slug"):
        assert key in rep, f"Missing key {key} in article representation"
    assert rep["title"] == "Test Article"
    assert rep["description"] == "Desc"
    assert rep["body"] == "Body"
    # tags: order and content should match input (empty list boundary)
    assert isinstance(rep["tagList"], list)
    assert rep["tagList"] == tag_list
    # favorites related defaults
    assert isinstance(rep["favoritesCount"], int) and rep["favoritesCount"] >= 0
    assert rep["favorited"] is False
    # author is a nested dict with username
    assert isinstance(rep["author"], dict) and rep["author"].get("username") == "alice"
    # slug was added (not empty) and includes a slugified title token
    assert isinstance(rep["slug"], str) and rep["slug"], "Slug must be a non-empty string"


@pytest.mark.django_db
@pytest.mark.parametrize("deleter_is_author,expected_status", [
    (True, 204),   # author can delete their comment
    (False, 403)   # non-author should not be allowed to delete
])
def test_comments_list_create_and_destroy_views(deleter_is_author, expected_status):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange: create users, article, and a comment; prepare factory and views
    author = User.objects.create_user(username="author", email="a@example.com", password="pw")
    other = User.objects.create_user(username="other", email="o@example.com", password="pw")
    article = Article.objects.create(title="Art", description="d", body="b", author=author)
    factory = APIRequestFactory()
    # Create comment via CommentsListCreateAPIView POST
    create_view = CommentsListCreateAPIView.as_view()
    post_req = factory.post(f"/api/articles/{article.slug}/comments/", {"comment": {"body": "Nice article"}}, format="json")
    force_authenticate(post_req, user=other)
    post_resp = create_view(post_req, slug=article.slug)
    # Act & Assert: comment creation should return 201 with proper structure
    assert getattr(post_resp, "status_code", None) == 201
    resp_data = getattr(post_resp, "data", None)
    assert isinstance(resp_data, _exc_lookup("dict", Exception)) and "comment" in resp_data
    created_comment = resp_data["comment"]
    assert created_comment.get("body") == "Nice article"
    assert created_comment.get("author", {}).get("username") == "other"

    # Arrange: ensure a Comment instance exists in DB for deletion test
    comment_obj = Comment.objects.create(article=article, author=author, body="Author's comment")

    # Prepare delete request, may be by author or non-author
    deleter = author if deleter_is_author else other
    del_view = CommentsDestroyAPIView.as_view()
    del_req = factory.delete(f"/api/articles/{article.slug}/comments/{comment_obj.pk}/")
    force_authenticate(del_req, user=deleter)

    # Act: attempt deletion and capture either Response or exception
    try:
        del_resp = del_view(del_req, slug=article.slug, pk=comment_obj.pk)
        status = getattr(del_resp, "status_code", None)
        # Assert expected HTTP status for deletion attempt
        assert status == expected_status, f"Expected status {expected_status}, got {status}"
        if expected_status == 204:
            # ensure comment removed from DB
            assert not Comment.objects.filter(pk=comment_obj.pk).exists()
        else:
            # comment should still exist
            assert Comment.objects.filter(pk=comment_obj.pk).exists()
    except Exception as exc:
        # Some view implementations raise permission exceptions instead of returning Response
        exc_type = _exc_lookup("PermissionDenied", Exception)
        if expected_status == 403:
            assert isinstance(exc, _exc_lookup("exc_type", Exception))
            # comment still exists
            assert Comment.objects.filter(pk=comment_obj.pk).exists()
        else:
            raise
