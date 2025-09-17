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

import types
import pytest
from types import SimpleNamespace

try:
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.relations import TagRelatedField
    from conduit.apps.articles.models import Tag
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.authentication import backends as auth_backends_module
    from conduit.apps.authentication.models import User
    from rest_framework.exceptions import AuthenticationFailed
except ImportError as exc:
    pytest.skip(f"Required project modules not available: {exc}", allow_module_level=True)

def test_add_slug_to_article_if_not_exists_adds_slug_when_missing(monkeypatch):
    
    # Arrange
    class FakeArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug
            self._saved = False

        def save(self, *args, **kwargs):
            self._saved = True

    article = FakeArticle("My Title", slug=None)

    # Monkeypatch the random generator used in the signal to be deterministic
    monkeypatch.setattr(
        "conduit.apps.articles.signals.generate_random_string",
        lambda length=6: "abc123",
        raising=False,
    )

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=article, created=True)

    # Assert
    assert isinstance(article.slug, str)
    # slugify('My Title') -> 'my-title', plus suffix '-abc123'
    assert article.slug == "my-title-abc123"
    assert article._saved is True

def test_TagRelatedField_to_internal_value_and_to_representation_roundtrip(monkeypatch):
    
    # Arrange
    fake_tag = SimpleNamespace(name="python")

    # Replace Tag.objects.get_or_create to avoid DB interaction
    fake_objects = SimpleNamespace(get_or_create=lambda **kwargs: (fake_tag, True))
    monkeypatch.setattr(Tag, "objects", fake_objects, raising=False)

    field = object.__new__(TagRelatedField)

    # Act
    internal = field.to_internal_value("python")
    represented = field.to_representation(fake_tag)

    # Assert
    assert internal is fake_tag
    assert represented == "python"
    assert getattr(internal, "name") == "python"

def test_JWTAuthentication_authenticate_success(monkeypatch):
    
    # Arrange
    fake_user = SimpleNamespace(id=42, username="jdoe")
    request = SimpleNamespace(META={"HTTP_AUTHORIZATION": "Token faketoken"})

    # Make jwt.decode deterministic and return payload with id
    monkeypatch.setattr(
        auth_backends_module, "jwt", types.SimpleNamespace(decode=lambda token, key, algorithms: {"id": 42})
    )

    # Monkeypatch User.objects.get to return our fake_user for any lookup
    fake_objects = SimpleNamespace(get=lambda *args, **kwargs: fake_user)
    monkeypatch.setattr(User, "objects", fake_objects, raising=False)

    auth = JWTAuthentication()

    # Act
    result = auth.authenticate(request)

    # Assert
    assert result is not None
    # JWTAuthentication returns a tuple (user, token) or (user, None)
    assert result[0] is fake_user

def test_JWTAuthentication_authenticate_invalid_token_raises(monkeypatch):
    
    # Arrange
    request = SimpleNamespace(META={"HTTP_AUTHORIZATION": "Token invalidtoken"})

    
    def bad_decode(token, key, algorithms):
        raise Exception("invalid token")

    monkeypatch.setattr(auth_backends_module, "jwt", types.SimpleNamespace(decode=bad_decode))

    auth = JWTAuthentication()

    # Act / Assert
    with pytest.raises(AuthenticationFailed):
        auth.authenticate(request)
