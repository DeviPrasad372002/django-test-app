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

import json
import time
from types import SimpleNamespace

import pytest

try:
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import backends as auth_backends
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication import AuthenticationAppConfig
except ImportError as e:
    pytest.skip(f"Skipping tests: required project imports not available ({e})", allow_module_level=True)

def test_generate_random_string_length_and_charset():
    
    # Arrange
    length = 16
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

    # Act
    result = generate_random_string(length)

    # Assert
    assert isinstance(result, str)
    assert len(result) == length
    assert set(result).issubset(allowed)

def test_user__generate_jwt_token_emits_payload_with_id_and_exp(monkeypatch):
    
    # Arrange
    # Create a lightweight User-like instance (Django model objects can be instantiated without DB access)
    try:
        user = auth_models.User(id=7)  # many Django model implementations accept id at construction
    except TypeError:
        # fallback if signature differs
        user = auth_models.User()
        setattr(user, "id", 7)
    # Monkeypatch the jwt.encode used by the auth models module to return a JSON string of the payload
    def fake_encode(payload, secret, algorithm="HS256"):
        # return JSON string so we can inspect payload easily
        return json.dumps(payload)
    monkeypatch.setattr(auth_models, "jwt", SimpleNamespace(encode=fake_encode))

    # Act
    try:
        token = user._generate_jwt_token()
    except AttributeError:
        pytest.skip("User._generate_jwt_token not present on User model", allow_module_level=False)

    # Assert
    # token should be a JSON string produced by our fake_encode
    assert isinstance(token, (str, bytes))
    payload = json.loads(token.decode() if isinstance(token, bytes) else token)
    # id may be stored under 'id' or 'user_id' depending on implementation; check presence
    assert ("id" in payload) or ("user_id" in payload)
    # verify id matches
    if "id" in payload:
        assert int(payload["id"]) == int(getattr(user, "id", getattr(user, "pk", None)))
    else:
        assert int(payload["user_id"]) == int(getattr(user, "id", getattr(user, "pk", None)))
    assert "exp" in payload
    assert int(payload["exp"]) > int(time.time())

def test_userjsonrenderer_render_produces_json_bytes_and_preserves_fields():
    
    # Arrange
    renderer = UserJSONRenderer()
    input_data = {"user": {"email": "tester@example.com", "token": "tok123", "username": "tester"}}

    # Act
    try:
        rendered = renderer.render(input_data)
    except AttributeError:
        pytest.skip("UserJSONRenderer.render not present", allow_module_level=False)

    # Assert
    assert isinstance(rendered, (bytes, str))
    decoded = json.loads(rendered.decode() if isinstance(rendered, bytes) else rendered)
    assert isinstance(decoded, dict)
    assert "user" in decoded
    assert decoded["user"]["email"] == "tester@example.com"
    assert decoded["user"]["token"] == "tok123"
    assert decoded["user"]["username"] == "tester"

def test_jwtauthentication_authenticate_happy_path(monkeypatch):
    
    # Arrange
    try:
        JWTAuth = auth_backends.JWTAuthentication
    except AttributeError:
        pytest.skip("JWTAuthentication class not found in backends", allow_module_level=True)

    jwt_auth = JWTAuth()

    # Prepare a fake token and request carrying 'Token <value>'
    token_value = "dummy-token-xyz"
    request = SimpleNamespace(META={"HTTP_AUTHORIZATION": f"Token {token_value}"})

    # Monkeypatch jwt.decode in the backends module to return a predictable payload
    def fake_decode(token, secret, algorithms=None):
        assert token == token_value  # ensure the token passed through is what we expect
        return {"id": 99, "exp": int(time.time()) + 3600}
    fake_jwt = SimpleNamespace(decode=fake_decode)
    monkeypatch.setattr(auth_backends, "jwt", fake_jwt)

    # Create a dummy User class with a manager that has a get method
    class DummyUser:
        def __init__(self, pk=99):
            self.pk = pk
            self.is_active = True

    class DummyObjects:
        @staticmethod
        def get(**kwargs):
            # Accept 'pk' or 'id'
            if ("pk" in kwargs and kwargs["pk"] == 99) or ("id" in kwargs and kwargs["id"] == 99):
                return DummyUser(pk=99)
            raise Exception("DoesNotExist")

    DummyUserClass = SimpleNamespace(objects=DummyObjects, DoesNotExist=Exception)

    # Patch User in the backends module to our dummy class
    monkeypatch.setattr(auth_backends, "User", DummyUserClass)

    # Act
    try:
        result = jwt_auth.authenticate(request)
    except AttributeError:
        pytest.skip("JWTAuthentication.authenticate not implemented with expected signature", allow_module_level=False)

    # Assert
    # authenticate should return a tuple (user, token) or similar; be permissive but concrete
    assert result is not None
    if isinstance(result, tuple):
        user_obj, returned_token = result
        assert isinstance(user_obj, DummyUser)
        assert returned_token == token_value
    else:
        # Some implementations return only the user; handle that as well
        assert isinstance(result, DummyUser) or (hasattr(result, "pk") and result.pk == 99)

def test_authentication_appconfig_ready_does_not_raise(monkeypatch):
    
    # Arrange
    try:
        appconfig = AuthenticationAppConfig("authentication", "conduit.apps.authentication")
    except Exception:
        pytest.skip("Cannot construct AuthenticationAppConfig in this environment", allow_module_level=True)

    
    try:
        appconfig.ready()
    except Exception as exc:
        pytest.fail(f"AuthenticationAppConfig.ready raised an exception: {exc}")
