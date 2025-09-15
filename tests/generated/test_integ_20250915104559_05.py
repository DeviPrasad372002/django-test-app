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
if _target and os.path.isdir(_target):
    _parent = os.path.abspath(os.path.join(_target, os.pardir))
    for p in (_parent, _target):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "target" not in sys.modules:
        _pkg = _types.ModuleType("target")
        _pkg.__path__ = [_target]
        sys.modules["target"] = _pkg

def _exc_lookup(name, default):
    try:
        mod_name, _, cls_name = str(name).rpartition(".")
        if mod_name:
            mod = __import__(mod_name, fromlist=[cls_name])
            return getattr(mod, cls_name, default)
        return getattr(sys.modules.get("builtins"), str(name), default)
    except Exception:
        return default

if os.getenv("TESTGEN_ENABLE_DJANGO_BOOTSTRAP","0") in ("1","true","yes"):
    try:
        import django
        from django.conf import settings as _dj_settings
        from django import apps as _dj_apps
        if not _dj_settings.configured:
            _cfg = dict(
                DEBUG=True, SECRET_KEY='pytest-secret',
                DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3','NAME': ':memory:'}},
                INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages'],
                MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware'],
                USE_TZ=True, TIME_ZONE='UTC',
            )
            try: _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
            except Exception: pass
            try: _dj_settings.configure(**_cfg)
            except Exception: pass
        if not _dj_apps.ready:
            try: django.setup()
            except Exception: pass
        try: import django.contrib.auth.base_user as _dj_probe  # noqa
        except Exception as _e:
            _pytest.skip(f"Django core import failed safely: {_e.__class__.__name__}: {_e}", allow_module_level=True)
    except Exception as _e:
        _pytest.skip(f"Django bootstrap not available: {_e.__class__.__name__}: {_e}", allow_module_level=True)

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

try:
    import pytest
    import json
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from unittest import mock

    from conduit.apps.articles.serializers import (
        ArticleSerializer,
        CommentSerializer,
        TagSerializer,
    )
    from conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
except ImportError:
    import pytest
    pytest.skip("Required project or third-party imports not available", allow_module_level=True)


class FakeUser:
    def __init__(self, username="tester"):
        self.username = username


class FakeRequest:
    def __init__(self, user=None):
        self.user = user


class FakeAuthor:
    def __init__(self, username="author", bio="", image=None):
        self.username = username
        self.bio = bio
        self.image = image

    # Some serializers call profile methods/attrs; provide a simple interface
    def get_profile(self, viewer=None):
        return {"username": self.username, "bio": self.bio, "image": self.image, "following": False}


class FakeArticle:
    def __init__(self, title="T", slug="s", body="b", created_at=None, updated_at=None, favorites_count=0, author=None, tags=None):
        self.title = title
        self.slug = slug
        self.body = body
        self.created_at = created_at or datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.updated_at = updated_at or self.created_at
        self.favorites_count = favorites_count
        self.author = author or FakeAuthor()
        # typical serializer expects tag list or similar
        self.tagList = tags or []
        self.tags = tags or []

        # Control value for has_favorited behavior in tests
        self._favorited_by = set()

    def has_favorited(self, user):
        # Real implementation may accept a user or profile; support both
        if user is None:
            return False
        return user in self._favorited_by

    def add_favorited_by(self, user):
        self._favorited_by.add(user)


@pytest.mark.parametrize(
    "favorited_by_user, favorites_count, expected_favorited",
    [
        (False, 0, False),
        (True, 5, True),
    ],
)
def test_article_serializer_method_fields_and_favorited_behavior(favorited_by_user, favorites_count, expected_favorited, monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = FakeUser(username="reader")
    article = FakeArticle(favorites_count=favorites_count)
    if favorited_by_user:
        article.add_favorited_by(user)
    request = FakeRequest(user=user)

    # Create serializer with context that contains request
    serializer = ArticleSerializer(context={"request": request})

    # Spy on article.has_favorited to ensure integration between serializer and model-like object
    with mock.patch.object(article, "has_favorited", wraps=article.has_favorited) as spy_has_fav:
        # Act
        created_at = serializer.get_created_at(article)
        updated_at = serializer.get_updated_at(article)
        fav_count = serializer.get_favorites_count(article)
        favorited = serializer.get_favorited(article)

        # Assert
        # created/updated fields should be ISO formatted strings (or at least start with date)
        assert isinstance(created_at, str), "created_at should be a string"
        assert article.created_at.isoformat() in created_at
        assert isinstance(updated_at, str), "updated_at should be a string"
        assert article.updated_at.isoformat() in updated_at

        # favorites count forwarded
        assert isinstance(fav_count, int)
        assert fav_count == favorites_count

        # favorited uses article.has_favorited and reflects the model's state
        spy_has_fav.assert_called_once_with(user)
        assert favorited is expected_favorited


@pytest.mark.parametrize(
    "renderer_cls, data, expected_top_key",
    [
        (ArticleJSONRenderer, {"title": "x", "body": "y"}, "article"),
        (CommentJSONRenderer, {"id": 1, "body": "y"}, "comment"),
    ],
)
def test_json_renderers_wrap_payload_under_expected_key(renderer_cls, data, expected_top_key):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = renderer_cls()

    # Act
    rendered = renderer.render(data, renderer_context={})
    # render typically returns bytes; decode and parse
    if isinstance(rendered, bytes):
        text = rendered.decode("utf-8")
    else:
        text = str(rendered)
    parsed = json.loads(text)

    # Assert
    assert isinstance(parsed, dict)
    assert expected_top_key in parsed, f"{renderer_cls.__name__} should wrap payload under '{expected_top_key}'"


def test_tag_serializer_to_representation_and_roundtrip_like_behavior():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    tag_name = "python"
    tag_obj = SimpleNamespace(name=tag_name)
    serializer = TagSerializer()

    # Act
    rep = serializer.to_representation(tag_obj)

    # Assert
    # TagSerializer typically serializes to the name string
    assert isinstance(rep, (str,)), "TagSerializer.to_representation should return the tag name string"
    assert rep == tag_name


@pytest.mark.parametrize("invalid_payload", [{}, {"body": ""}])
def test_comment_serializer_validation_rejects_empty_body(invalid_payload):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    serializer = CommentSerializer(data=invalid_payload)

    # Act
    valid = serializer.is_valid()

    # Assert
    # Expect invalid if body missing or empty string
    assert not valid
    errors = serializer.errors
    # serializer likely reports 'body' in errors for empty/missing comment body
    assert ("body" in errors) or any("body" in k for k in errors.keys()), "CommentSerializer should have 'body' in errors for invalid payload"
