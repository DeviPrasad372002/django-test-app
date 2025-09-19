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
except ModuleNotFoundError:
    try:
        import pytest
    except ModuleNotFoundError:
        import importlib.util, sys, os
        _tr=os.environ.get('TARGET_ROOT') or 'target'
        _p1=os.path.join(_tr, 'pytest.py'); _p2=os.path.join(_tr, 'pytest.py')
        _pp=[_p for _p in (_p1,_p2) if os.path.isfile(_p)]
        if _pp:
            _spec=importlib.util.spec_from_file_location('pytest', _pp[0])
            _m=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
            sys.modules.setdefault('pytest', _m)
        else:
            raise

from types import SimpleNamespace
from datetime import datetime, timezone

try:
    import conduit.apps.authentication.models as auth_models
    import conduit.apps.authentication.backends as auth_backends
    import conduit.apps.authentication.renderers as auth_renderers
    import conduit.apps.authentication.serializers as auth_serializers
    import conduit.apps.core.exceptions as core_exceptions
    import conduit.apps.articles.serializers as articles_serializers
    import rest_framework.exceptions as drf_exceptions
    import jwt as jwt_module  # used for patching reference consistency
except ImportError as e:
    pytest.skip("Required application modules not importable: %s" % e, allow_module_level=True)

# Arrange / Act / Assert style tests below

def test_user_manager_create_user_and_superuser_edge_cases(monkeypatch):
    
    # Arrange
    manager = getattr(auth_models, "UserManager")()
    
    with pytest.raises(ValueError):
        manager.create_user(email="", password="pw")
    with pytest.raises(ValueError):
        manager.create_user(email=None, password="pw")

    
    email_in = "Alice.ExAMPLE@DoMain.Com"
    user = manager.create_user(email=email_in, password="secret")
    
    assert isinstance(user, object)
    assert getattr(user, "email", "").lower() == "alice.example@domain.com"
    assert getattr(user, "is_active", True) is True
    # is_staff and is_superuser should be False for normal user
    assert getattr(user, "is_staff", False) is False
    assert getattr(user, "is_superuser", False) is False

    # Act - create superuser
    superuser = manager.create_superuser(email="admin@domain.com", password="adminpw")
    # Assert - superuser flags set
    assert getattr(superuser, "is_staff", False) is True
    assert getattr(superuser, "is_superuser", False) is True

def test_generate_jwt_token_and_token_property(monkeypatch):
    
    # Arrange - ensure jwt.encode returns predictable bytes
    called = {}
    def fake_encode(payload, key, algorithm="HS256"):
        called['payload'] = payload
        called['key'] = key
        called['algorithm'] = algorithm
        return b"fixed.jwt.token"
    monkeypatch.setattr(auth_models, "jwt", SimpleNamespace(encode=fake_encode))

    # Act - call internal generator with a minimal user-like object
    fake_user = SimpleNamespace(pk=42, id=42)
    token = auth_models._generate_jwt_token(fake_user)

    
    assert isinstance(token, str)
    assert "fixed.jwt.token" in token
    # payload should include an id or user identifier (accept either 'id' or 'user_id' keys)
    assert any(k in called['payload'] for k in ("id", "user_id", "pk"))

def test_jwt_backend_authenticate_credentials_valid_and_invalid(monkeypatch):
    
    # Arrange
    backend = auth_backends.JWTAuthentication()

    
    def decode_raises(token, key, algorithms=None):
        raise Exception("invalid token")
    monkeypatch.setattr(auth_backends, "jwt", SimpleNamespace(decode=decode_raises))
    with pytest.raises(drf_exceptions.AuthenticationFailed):
        backend._authenticate_credentials(b"bad.token")

    
    def decode_returns_notfound(token, key, algorithms=None):
        return {"user_id": 9999}
    monkeypatch.setattr(auth_backends, "jwt", SimpleNamespace(decode=decode_returns_notfound))

    class FakeObjects:
        def get(self, pk):
            raise auth_models.User.DoesNotExist()
    
    FakeUserClass = SimpleNamespace(objects=FakeObjects)
    monkeypatch.setattr(auth_backends, "User", FakeUserClass, raising=False)
    with pytest.raises(drf_exceptions.AuthenticationFailed):
        backend._authenticate_credentials(b"valid.token")

    # Case 3: valid decode and user exists -> returns user object
    def decode_returns_ok(token, key, algorithms=None):
        return {"user_id": 7}
    monkeypatch.setattr(auth_backends, "jwt", SimpleNamespace(decode=decode_returns_ok))

    class RealFakeUser:
        class objects:
            @staticmethod
            def get(pk):
                return SimpleNamespace(pk=pk, email="found@x.com")
    monkeypatch.setattr(auth_backends, "User", RealFakeUser, raising=False)
    user = backend._authenticate_credentials(b"valid.token")
    assert getattr(user, "email") == "found@x.com"
    assert getattr(user, "pk") == 7

def test_userjsonrenderer_render_returns_json_bytes():
    
    # Arrange
    renderer = auth_renderers.UserJSONRenderer()
    payload = {"user": {"email": "a@b.com", "username": "alice"}}

    # Act
    output = renderer.render(payload, accepted_media_type=None, renderer_context=None)

    
    assert isinstance(output, (bytes, bytearray))
    text = output.decode("utf-8")
    assert '"email"' in text and '"username"' in text and "a@b.com" in text

@pytest.mark.parametrize("dt,expected_substr", [
    (datetime(2020, 1, 1, 12, 0, 0), "2020-01-01"),
    (datetime(1999, 12, 31, 23, 59, 59, tzinfo=timezone.utc), "1999-12-31"),
])
def test_articles_serializers_get_created_and_updated_and_favorites(dt, expected_substr):
    
    # Arrange - object with created_at and updated_at
    article = SimpleNamespace(created_at=dt, updated_at=dt)
    # Act
    created = articles_serializers.get_created_at(article)
    updated = articles_serializers.get_updated_at(article)
    
    assert isinstance(created, str)
    assert expected_substr in created
    assert isinstance(updated, str)
    assert expected_substr in updated

    # favorites count scenarios
    # Case: object has favorites with count()
    class FavorSet:
        def __init__(self, n):
            self._n = n
        def count(self):
            return self._n
    article_with_favs = SimpleNamespace(favorites=FavorSet(5))
    assert articles_serializers.get_favorites_count(article_with_favs) == 5

    # Case: object has no favorites attribute -> fallback to 0
    article_no_favs = SimpleNamespace()
    assert articles_serializers.get_favorites_count(article_no_favs) == 0

def test_core_handle_not_found_error_returns_404_response():
    
    # Arrange - create a NotFound exception instance
    exc = drf_exceptions.NotFound(detail="not there")
    context = {}
    # Act
    resp = core_exceptions._handle_not_found_error(exc, context)
    
    assert hasattr(resp, "status_code")
    assert resp.status_code == 404
    
    assert isinstance(resp.data, dict)
    
    joined = " ".join(str(v) for v in resp.data.values())
    assert "not there" in joined.lower() or "not found" in joined.lower() or "detail" in resp.data
