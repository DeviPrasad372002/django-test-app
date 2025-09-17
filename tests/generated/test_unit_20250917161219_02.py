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
from unittest.mock import Mock

try:
    from conduit.apps.articles.views import CommentsListCreateAPIView, ArticleViewSet
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.authentication.models import User
except Exception as e:  # pragma: no cover - skip if project modules not importable
    pytest.skip(f"Required project modules not available: {e}", allow_module_level=True)

def test_comments_list_create_post_success(monkeypatch):
    
    # Arrange
    view = CommentsListCreateAPIView()
    serializer = Mock()
    serializer.is_valid.return_value = True
    serializer.save.return_value = Mock(id=1, body="ok")
    serializer.data = {"comment": {"id": 1, "body": "ok"}}

    # Patch the view to return our serializer and article object
    monkeypatch.setattr(view, "get_serializer", lambda *a, **k: serializer)
    article = Mock()
    monkeypatch.setattr(view, "get_object", lambda *a, **k: article)

    request = Mock()
    request.data = {"body": "ok"}
    request.user = Mock()

    # Act
    resp = view.post(request, slug="some-slug")

    # Assert
    from rest_framework.response import Response
    assert isinstance(resp, Response)
    assert resp.status_code == 201
    assert resp.data == serializer.data

def test_articleviewset_destroy_calls_delete_and_returns_204(monkeypatch):
    
    # Arrange
    view = ArticleViewSet()
    instance = Mock()
    instance.delete = Mock()

    # Ensure the view returns our instance
    monkeypatch.setattr(view, "get_object", lambda *a, **k: instance)

    request = Mock()

    # Act
    resp = view.destroy(request, pk="1")

    # Assert
    from rest_framework.response import Response
    assert isinstance(resp, Response)
    assert resp.status_code == 204
    assert instance.delete.called is True

def test_jwtauthentication__authenticate_credentials_invalid_raises_auth_failed():
    
    # Arrange
    auth = JWTAuthentication()

    # Act / Assert
    from rest_framework.exceptions import AuthenticationFailed
    with pytest.raises(AuthenticationFailed):
        
        auth._authenticate_credentials(b"this.is.not.valid")

def test_user_get_full_name_and_token_is_string():
    
    # Arrange
    # Instantiate without DB save; accessors should be pure-Python properties/methods
    user = User()
    user.first_name = "Jane"
    user.last_name = "Roe"
    
    setattr(user, "pk", 42)

    # Act
    full = user.get_full_name()
    token_value = user.token

    # Assert
    assert isinstance(full, str)
    assert full == "Jane Roe"
    assert isinstance(token_value, str)
    assert len(token_value) > 0
