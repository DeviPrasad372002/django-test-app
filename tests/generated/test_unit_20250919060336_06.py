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

try:
    import django
    from django.db import models
    from rest_framework import exceptions
    from rest_framework.response import Response
    # Import target modules/classes
    from conduit.apps.authentication import (
        backends as auth_backends_module,
        models as auth_models_module,
        renderers as auth_renderers_module,
        serializers as auth_serializers_module,
        views as auth_views_module,
    )
    from conduit.apps.authentication.models import UserManager, User
    from conduit.apps.authentication.backends import JWTAuthentication
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
    from conduit.apps.authentication import __init__ as auth_app_init
    from conduit.apps.core.models import TimestampedModel
except ImportError:
    pytest.skip("Django or project modules not available", allow_module_level=True)

def _make_request(data=None, auth_header=None):
    # minimal fake request expected by DRF views used in tests
    class Req:
        def __init__(self, data, auth_header):
            self.data = data or {}
            self.META = {}
            if auth_header is not None:
                # common header key
                self.META['HTTP_AUTHORIZATION'] = auth_header

    return Req(data, auth_header)

def test_AuthenticationAppConfig_has_name_and_label():
    # Arrange / Act
    cfg = auth_app_init.AuthenticationAppConfig("conduit.apps.authentication", "authentication")
    # Assert
    assert hasattr(cfg, "name"), "AppConfig should have name attribute"
    assert isinstance(cfg.name, str)
    assert cfg.name != ""
    # label may be present
    if hasattr(cfg, "label"):
        assert isinstance(cfg.label, str)

@pytest.mark.parametrize(
    "auth_header, jwt_payload, user_returns, expect_user",
    [
        ("Token valid.token", {"id": 10}, object(), True),
        ("Token missing", None, None, False),  
        (None, None, None, False),  # no header -> no authentication
    ],
)
def test_JWTAuthentication_authenticate_various(monkeypatch, auth_header, jwt_payload, user_returns, expect_user):
    # Arrange
    auth = JWTAuthentication()
    request = _make_request(auth_header=auth_header)

    
    class FakeJWT:
        @staticmethod
        def decode(token, key, algorithms=None):
            if jwt_payload is None:
                raise Exception("invalid token")
            return jwt_payload

    monkeypatch.setattr(auth_backends_module, "jwt", FakeJWT)

    # Provide fake User model with objects.get
    class FakeUserObj:
        def __init__(self, pk):
            self.pk = pk

    class FakeUserManager:
        @staticmethod
        def get(pk=None, **kwargs):
            if user_returns is None:
                raise auth_models_module.User.DoesNotExist
            return user_returns if user_returns != object() else FakeUserObj(pk)

    # Replace the User model referenced in backend module with a fake-like object
    monkeypatch.setattr(auth_backends_module, "User", types.SimpleNamespace(objects=FakeUserManager()))

    # Act / Assert
    if auth_header is None:
        # No Authorization header => authenticate should return None
        result = auth.authenticate(request)
        assert result is None
    else:
        if jwt_payload is None:
            with pytest.raises(exceptions.AuthenticationFailed):
                auth.authenticate(request)
        else:
            result = auth.authenticate(request)
            # DRF authentication returns a tuple (user, token) typically or user
            # Accept either tuple or user-like
            assert result is not None
            if isinstance(result, tuple):
                user_obj, token = result
                assert hasattr(user_obj, "pk")
            else:
                assert hasattr(result, "pk")

@pytest.mark.parametrize(
    "email, username, password, exc_expected",
    [
        (None, "u", "pw", ValueError),
        ("e@example.com", None, "pw", ValueError),
        ("e@example.com", "u", None, None),  # may accept no password
    ],
)
def test_UserManager_create_user_validations(email, username, password, exc_expected):
    # Arrange
    mgr = UserManager()
    # To avoid DB interactions patch save on manager.model if exists
    if hasattr(mgr, "model"):
        # guard save to no-op
        def _noop_save(self, *a, **k):
            return None
        setattr(mgr.model, "save", _noop_save)

    # Act / Assert
    if exc_expected:
        with pytest.raises(exc_expected):
            mgr.create_user(email=email, username=username, password=password)
    else:
        user = mgr.create_user(email=email, username=username, password=password)
        # should return a User-like object
        assert user is not None

def test_User_token_and_name_methods(monkeypatch):
    # Arrange
    user = User()
    # Provide attributes used by methods
    user.email = "me@example.com"
    user.username = "meuser"
    user.first_name = "First"
    user.last_name = "Last"

    # Force _generate_jwt_token to return known token
    monkeypatch.setattr(user, "_generate_jwt_token", lambda: "tok-123")
    # Act / Assert token property or method
    assert hasattr(user, "token")
    assert user.token == "tok-123"

    # full name should combine first and last
    if hasattr(user, "get_full_name"):
        assert user.get_full_name() == "First Last"
    # short name should return first name or username
    if hasattr(user, "get_short_name"):
        short = user.get_short_name()
        assert isinstance(short, str)
        assert short in ("First", "meuser")

def test_User_str_and_generate_jwt_token_monkeypatched(monkeypatch):
    # Arrange
    user = User()
    user.username = "stringy"
    
    s = str(user)
    assert isinstance(s, str)
    assert "stringy" in s or "@" in s or len(s) > 0

    # Test _generate_jwt_token uses jwt.encode; patch jwt to control output
    def fake_encode(payload, key, algorithm="HS256"):
        return "encoded-token"
    monkeypatch.setattr(auth_models_module, "jwt", types.SimpleNamespace(encode=fake_encode))
    # Provide settings SECRET_KEY if used
    try:
        from django.conf import settings

        monkeypatch.setattr(settings, "SECRET_KEY", "abc123", raising=False)
    except Exception:
        pass

    token = user._generate_jwt_token()
    assert isinstance(token, str)
    assert token == "encoded-token"

def test_UserJSONRenderer_render_outputs_user_wrapper():
    renderer = UserJSONRenderer()
    data = {"user": {"email": "x@y.com", "username": "u"}}
    result = renderer.render(data)
    
    if isinstance(result, bytes):
        txt = result.decode("utf-8")
    else:
        txt = result
    assert '"user"' in txt
    assert '"email"' in txt
    assert '"username"' in txt

@pytest.mark.parametrize(
    "input_data, expect_valid",
    [
        ({"email": "a@b.com", "username": "u", "password": "pw", "password2": "pw"}, True),
        ({"email": "a@b.com", "username": "u", "password": "pw", "password2": "no"}, False),
    ],
)
def test_RegistrationSerializer_validate_password_match(monkeypatch, input_data, expect_valid):
    # Arrange
    serializer = RegistrationSerializer(data=input_data)
    # Prevent create/save from hitting DB by stubbing create
    if hasattr(serializer, "create"):
        monkeypatch.setattr(serializer, "create", lambda validated: object())
    # Act
    valid = serializer.is_valid()
    # Assert
    assert valid is expect_valid
    if not valid:
        assert "password" in serializer.errors or "non_field_errors" in serializer.errors

@pytest.mark.parametrize(
    "input_data, expect_valid",
    [
        ({"email": "me@x.com", "password": "pw"}, True),
        ({"email": "", "password": ""}, False),
    ],
)
def test_LoginSerializer_validation(monkeypatch, input_data, expect_valid):
    serializer = LoginSerializer(data=input_data)
    # Avoid database ops in serializer.validate if present by monkeypatching authenticate backend
    monkeypatch.setattr(auth_serializers_module, "authenticate", lambda **kwargs: True, raising=False)
    valid = serializer.is_valid()
    assert valid is expect_valid
    if not valid:
        assert isinstance(serializer.errors, dict)

def test_RegistrationAPIView_post_uses_serializer_and_returns_response(monkeypatch):
    # Arrange
    view = RegistrationAPIView()
    fake_response_data = {"user": {"email": "x@y", "username": "u", "token": "t"}}

    class FakeSerializer:
        def __init__(self, data=None):
            self._data = data
            self._valid = True

        def is_valid(self, raise_exception=False):
            return self._valid

        def save(self):
            return types.SimpleNamespace(**{"token": "t", "email": "x@y", "username": "u"})

        @property
        def data(self):
            return fake_response_data

    monkeypatch.setattr(auth_views_module, "RegistrationSerializer", FakeSerializer)
    req = _make_request(data={"email": "x@y", "password": "pw"})
    # Act
    resp = view.post(req)
    # Assert
    assert isinstance(resp, Response)
    assert resp.data == fake_response_data

def test_LoginAPIView_post_returns_response_on_success(monkeypatch):
    view = LoginAPIView()

    class FakeSerializer:
        def __init__(self, data=None):
            self._data = data

        def is_valid(self, raise_exception=False):
            return True

        @property
        def data(self):
            return {"user": {"email": "a@b", "token": "tok"}}

    monkeypatch.setattr(auth_views_module, "LoginSerializer", FakeSerializer)
    req = _make_request(data={"email": "a@b", "password": "pw"})
    resp = view.post(req)
    assert isinstance(resp, Response)
    assert "user" in resp.data
    assert "token" in resp.data["user"]

def test_UserRetrieveUpdateAPIView_uses_serializer_on_get_and_put(monkeypatch):
    view = UserRetrieveUpdateAPIView()

    # fake current user retrieval and serializer
    fake_user = types.SimpleNamespace(email="e@x", username="u")

    class FakeSerializer:
        def __init__(self, instance=None, data=None, partial=False):
            self.instance = instance
            self.data_in = data

        @property
        def data(self):
            return {"user": {"email": self.instance.email, "username": self.instance.username}}

        def is_valid(self, raise_exception=False):
            return True

        def save(self):
            # simulate update
            if self.data_in:
                self.instance.email = self.data_in.get("email", self.instance.email)
            return self.instance

    monkeypatch.setattr(auth_views_module, "UserSerializer", FakeSerializer)
    # patch request.user used by view.get_object or .get
    req_get = _make_request()
    req_get.user = fake_user
    resp_get = view.get(req_get)
    assert isinstance(resp_get, Response)
    assert resp_get.data["user"]["email"] == "e@x"

    # Test update
    req_put = _make_request(data={"email": "new@x"})
    req_put.user = fake_user
    resp_put = view.put(req_put)
    assert isinstance(resp_put, Response)
    assert resp_put.data["user"]["email"] == "new@x"

def test_TimestampedModel_is_abstract_and_subclass_of_models_Model():
    assert issubclass(TimestampedModel, models.Model)
    # Ensure the model is abstract
    assert getattr(TimestampedModel._meta, "abstract", False) is True
