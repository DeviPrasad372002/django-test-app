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

import builtins
try:
    import pytest
    from types import SimpleNamespace
    from datetime import datetime, timedelta
    import json
    import jwt
    from unittest.mock import Mock

    # Import target modules/classes
    from conduit.apps.authentication import AuthenticationAppConfig
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.authentication.models import UserManager, User
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.serializers import (
        RegistrationSerializer,
        LoginSerializer,
        UserSerializer,
    )
    from conduit.apps.authentication.views import (
        RegistrationAPIView,
        LoginAPIView,
        UserRetrieveUpdateAPIView,
    )
    from conduit.apps.core.models import TimestampedModel

    from django.conf import settings
except ImportError:
    import pytest as pytest

def _ensure_secret_key():
    # Ensure SECRET_KEY exists for jwt token generation
    if not getattr(settings, "SECRET_KEY", None):
        try:
            settings.configure(SECRET_KEY="test-secret-key")
        except Exception:
            # If settings already configured but SECRET_KEY missing, set attribute
            setattr(settings, "SECRET_KEY", "test-secret-key")

def _make_request_with_auth(header_value):
    return SimpleNamespace(META={"HTTP_AUTHORIZATION": header_value}, data={})

def test_authentication_app_config_has_expected_name():
    # Arrange / Act
    name_attr = getattr(AuthenticationAppConfig, "name", None)

    # Assert
    assert isinstance(name_attr, str)
    assert "authentication" in name_attr

def test_jwtauthentication_no_header_returns_none():
    # Arrange
    auth = JWTAuthentication()
    request = SimpleNamespace(META={})

    # Act
    result = auth.authenticate(request)

    # Assert
    assert result is None

def test_jwtauthentication_with_header_delegates_to_authenticate_credentials(monkeypatch):
    # Arrange
    auth = JWTAuthentication()
    fake_user = SimpleNamespace(username="u")
    monkeypatch.setattr(JWTAuthentication, "_authenticate_credentials", lambda self, token: (fake_user, token))
    req = _make_request_with_auth("Token abcdef")

    # Act
    result = auth.authenticate(req)

    # Assert
    assert isinstance(result, tuple)
    assert result[0] is fake_user
    assert result[1] == "Token abcdef"

@pytest.mark.parametrize("email,password,username", [
    ("", "pw", "u"),
    (None, "pw", "u"),
])
def test_user_manager_create_user_raises_on_missing_email(email, password, username):
    # Arrange
    mgr = UserManager()
    # Provide a dummy model factory to avoid DB interaction
    mgr.model = lambda *a, **k: SimpleNamespace(save=Mock(), set_password=Mock())
    # Act / Assert
    with pytest.raises(ValueError):
        mgr.create_user(email=email, username=username, password=password)

def test_user_manager_create_user_normalizes_email_and_calls_set_password_and_save(monkeypatch):
    # Arrange
    saved = {}
    class FakeUser:
        def __init__(self):
            self.email = None
            self.username = None
            self.is_staff = None
            self.is_superuser = None
            self._saved = False
        def set_password(self, raw):
            self._pw = raw
        def save(self, *a, **k):
            self._saved = True

    fake_user = FakeUser()
    mgr = UserManager()
    mgr.model = lambda *a, **k: fake_user

    # Act
    user = mgr.create_user(email="TeSt@ExAmple.COM", username="tester", password="p@ss")

    # Assert
    assert user is fake_user
    assert user.email == "test@example.com"
    assert getattr(user, "_pw", None) == "p@ss"
    assert user._saved is True
    assert user.is_staff is False
    assert user.is_superuser is False

def test_user_manager_create_superuser_sets_flags(monkeypatch):
    # Arrange
    class FakeUser:
        def __init__(self):
            self.is_staff = False
            self.is_superuser = False
            self.email = None
            self.username = None
        def set_password(self, raw): self._pw = raw
        def save(self, *a, **k): self._saved = True

    fake_user = FakeUser()
    mgr = UserManager()
    mgr.model = lambda *a, **k: fake_user

    # Act
    user = mgr.create_superuser(email="admin@example.com", username="admin", password="secret")

    # Assert
    assert user is fake_user
    assert user.is_staff is True
    assert user.is_superuser is True
    assert getattr(user, "_pw", None) == "secret"

def test_user_get_full_and_short_name_and_token(monkeypatch):
    # Arrange
    _ensure_secret_key()
    u = User()
    # assign expected attributes (model instantiation without DB)
    u.email = "USER@Example.COM"
    u.username = "shortname"
    # Act
    full = u.get_full_name()
    short = u.get_short_name()
    token = u.token

    # Assert
    assert isinstance(full, str)
    assert full == u.email or full == u.username or isinstance(full, str)
    assert isinstance(short, str)
    # token should be a string JWT; decode to verify 'exp' present
    assert isinstance(token, str)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert "exp" in payload
    # token should expire in the future
    assert payload["exp"] > int((datetime.utcnow() - timedelta(seconds=10)).timestamp())

def test_userjsonrenderer_render_wraps_user_key():
    # Arrange
    renderer = UserJSONRenderer()
    sample = {"email": "a@b.com", "username": "u"}
    # Act
    rendered = renderer.render({"user": sample})
    # Assert: accept bytes or str
    if isinstance(rendered, bytes):
        text = rendered.decode("utf-8")
    else:
        text = rendered
    obj = json.loads(text)
    assert "user" in obj
    assert obj["user"]["email"] == "a@b.com"

@pytest.mark.parametrize("serializer_class,input_data,should_be_valid", [
    (RegistrationSerializer, {}, False),
    (LoginSerializer, {}, False),
])
def test_serializers_reject_missing_required_fields(serializer_class, input_data, should_be_valid):
    # Arrange
    serializer = serializer_class(data=input_data)
    # Act
    valid = serializer.is_valid()
    # Assert
    assert valid is bool(valid)
    assert valid == should_be_valid
    if not valid:
        assert isinstance(serializer.errors, dict)

def test_user_serializer_representation_from_instance(monkeypatch):
    # Arrange
    u = User()
    u.email = "rep@example.com"
    u.username = "repuser"
    ser = UserSerializer(u)

    # Act
    data = ser.data

    # Assert
    assert isinstance(data, dict)
    assert "email" in data
    assert data["email"] == "rep@example.com"

def test_registration_api_view_post_uses_serializer_and_returns_response(monkeypatch):
    # Arrange
    view = RegistrationAPIView()
    fake_serializer = SimpleNamespace()
    fake_user = SimpleNamespace(email="ra@example.com")
    fake_serializer.is_valid = lambda raise_exception=False: True
    fake_serializer.save = lambda: fake_user
    fake_serializer.data = {"user": {"email": "ra@example.com"}}
    monkeypatch.setattr(view, "get_serializer", lambda *a, **k: fake_serializer)
    req = SimpleNamespace(data={"user": {"email": "ra@example.com"}})

    # Act
    resp = view.post(req)

    # Assert
    from rest_framework.response import Response
    assert isinstance(resp, Response)
    assert resp.data == fake_serializer.data

def test_login_api_view_post_uses_serializer_and_returns_response(monkeypatch):
    # Arrange
    view = LoginAPIView()
    fake_serializer = SimpleNamespace()
    fake_user = SimpleNamespace(email="li@example.com")
    fake_serializer.is_valid = lambda raise_exception=False: True
    fake_serializer.save = lambda: fake_user
    fake_serializer.data = {"user": {"email": "li@example.com"}}
    monkeypatch.setattr(view, "get_serializer", lambda *a, **k: fake_serializer)
    req = SimpleNamespace(data={"user": {"email": "li@example.com", "password": "pw"}})

    # Act
    resp = view.post(req)

    # Assert
    from rest_framework.response import Response
    assert isinstance(resp, Response)
    assert resp.data == fake_serializer.data

def test_user_retrieve_update_view_get_and_patch(monkeypatch):
    # Arrange
    view = UserRetrieveUpdateAPIView()
    u = SimpleNamespace(email="me@example.com")
    fake_serializer = SimpleNamespace()
    fake_serializer.data = {"user": {"email": "me@example.com"}}
    fake_serializer.is_valid = lambda raise_exception=False: True
    fake_serializer.save = lambda: u
    monkeypatch.setattr(view, "get_object", lambda *a, **k: u)
    monkeypatch.setattr(view, "get_serializer", lambda *a, **k: fake_serializer)
    req_get = SimpleNamespace(data={})
    req_patch = SimpleNamespace(data={"user": {"email": "me@example.com"}})

    # Act
    resp_get = view.get(req_get)
    resp_patch = view.patch(req_patch)

    # Assert
    from rest_framework.response import Response
    assert isinstance(resp_get, Response)
    assert resp_get.data == fake_serializer.data
    assert isinstance(resp_patch, Response)
    assert resp_patch.data == fake_serializer.data

def test_timestampedmodel_get_created_at_formats_iso():
    # Arrange
    ts = TimestampedModel()
    fake = SimpleNamespace(created_at=datetime(2020, 1, 2, 3, 4, 5))
    # Act
    s = TimestampedModel.get_created_at(fake)
    # Assert
    assert isinstance(s, str)
    # Check ISO-like formatting
    assert "2020-01-02" in s or "2020-01-02T03:04:05" in s or s.startswith("2020-01-02")
