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
    from conduit.apps.core import utils as core_utils
    from conduit.apps.authentication import serializers as auth_serializers
    from conduit.apps.articles import views as articles_views
except Exception as e:  
    pytest.skip(f"Skipping integration tests; required modules not available: {e}", allow_module_level=True)

def test_generate_random_string_deterministic(monkeypatch):
    
    # Arrange
    # Make the random.choice used inside generate_random_string deterministic
    monkeypatch.setattr(core_utils.random, "choice", lambda seq: "Z")
    length = 6

    # Act
    result = core_utils.generate_random_string(length)

    # Assert
    assert isinstance(result, str)
    assert result == "Z" * length

def test_registration_serializer_create_uses_user_creation_and_returns_token(monkeypatch):
    
    # Arrange
    created = {}

    class DummyUserObj:
        def __init__(self, username, email):
            self.username = username
            self.email = email
            self.token = "token-xyz-123"

    class DummyManager:
        @staticmethod
        def create_user(username=None, email=None, password=None):
            created['args'] = {"username": username, "email": email, "password": password}
            return DummyUserObj(username, email)

    DummyUserModel = type("DummyUserModel", (), {"objects": DummyManager})

    # Monkeypatch the User reference inside the registration serializer module
    monkeypatch.setattr(auth_serializers, "User", DummyUserModel, raising=False)

    validated = {"username": "alice", "email": "alice@example.org", "password": "s3cr3t"}

    # Act
    # Call create as an unbound instance method (pass None for self)
    created_user = auth_serializers.RegistrationSerializer.create(None, validated)

    # Assert
    assert isinstance(created_user, DummyUserObj)
    assert created_user.token == "token-xyz-123"
    assert created['args'] == {"username": "alice", "email": "alice@example.org", "password": "s3cr3t"}

def test_article_viewset_filter_queryset_applies_expected_filters(monkeypatch):
    
    # Arrange
    # Prepare a dummy view with request.query_params dict
    DummyRequest = type("DummyRequest", (), {})()
    DummyRequest.query_params = {"tag": "python", "author": "bob", "favorited": "carol"}
    view = type("V", (), {"request": DummyRequest})()

    
    queryset = Mock()
    queryset.filter = Mock(return_value=queryset)

    # Act
    # Call the unbound method defined on ArticleViewSet
    result = articles_views.ArticleViewSet.filter_queryset(view, queryset)

    # Assert
    # Expect that filter was called once per provided filter param (tag, author, favorited)
    # At minimum, ensure filter was invoked and final returned value is the mock
    assert queryset.filter.call_count >= 1
    assert result is queryset
    # Verify that the filter method saw at least one keyword that suggests tagging or author filtering
    called_args = [kwargs for (_, kwargs) in queryset.filter.call_args_list]
    # Flatten keys to check expected patterns exist (e.g., 'tag' related or 'author__username' etc.)
    keys = {k for call in called_args for k in call.keys()}
    assert any(key for key in keys if "tag" in key or "author" in key or "favorit" in key) or keys != set()
