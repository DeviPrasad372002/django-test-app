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
import json

try:
    import pytest
    import datetime
    import jwt
    from types import SimpleNamespace

    # project modules
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import serializers as auth_serializers
    from conduit.apps.authentication.renderers import UserJSONRenderer
    from conduit.apps.authentication.serializers import UserSerializer, RegistrationSerializer
except Exception:
    import pytest
    pytest.skip("required project modules are not available", allow_module_level=True)

def _has_attr(obj, *names):
    return any(hasattr(obj, n) for n in names)

def _get_token_from_user(user):
    # support either property 'token' or method '_generate_jwt_token' / 'generate_jwt_token'
    if hasattr(user, "token"):
        return getattr(user, "token")
    for n in ("_generate_jwt_token", "generate_jwt_token"):
        if hasattr(user, n):
            fn = getattr(user, n)
            return fn() if callable(fn) else fn
    raise AttributeError("no token generator found on user")

def test_user__generate_jwt_token_contains_id_and_exp(monkeypatch):
    
    # Arrange
    # Provide deterministic SECRET_KEY and deterministic datetime.utcnow
    fake_secret = "test-secret-123"
    # Monkeypatch auth_models.settings if present or create a simple namespace
    if hasattr(auth_models, "settings"):
        monkeypatch.setattr(auth_models, "settings", SimpleNamespace(SECRET_KEY=fake_secret), raising=False)
    else:
        setattr(auth_models, "settings", SimpleNamespace(SECRET_KEY=fake_secret))

    # Freeze datetime used inside the auth_models module for deterministic exp
    fixed_now = datetime.datetime(2020, 1, 1, 0, 0, 0)

    class _FakeDateTime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return fixed_now

    # Some implementations import datetime at module level; patch the name in module
    monkeypatch.setattr(auth_models, "datetime", datetime, raising=False)
    # If module uses datetime.datetime.utcnow directly, replace attribute
    try:
        monkeypatch.setattr(auth_models, "datetime", types.SimpleNamespace(datetime=_FakeDateTime, timedelta=datetime.timedelta), raising=False)
    except Exception:
        # best-effort; continue even if replacement not possible
        pass

    # Create a lightweight user instance and assign an id/pk attribute
    try:
        user = auth_models.User()
    except Exception:
        # Fallback to a simple object shaped like expected User
        user = SimpleNamespace()

    # Assign an id that the token should carry; try common attribute names
    for id_attr in ("id", "pk", "user_id"):
        try:
            setattr(user, id_attr, 42)
            break
        except Exception:
            continue

    
    # If models defined token as property reading _generate_jwt_token, prefer that
    # Act
    token = _get_token_from_user(user)

    # Assert
    assert isinstance(token, (str, bytes)), "token should be a string/bytes JWT"

    # Decode token verifying signature with our fake secret; if algorithm not known, allow common HS256
    decoded = jwt.decode(token, fake_secret, algorithms=["HS256"])
    # Expect the payload to include an identifier for the user and expiration
    # Common key names: 'user_id', 'id', 'pk'
    assert any(k in decoded for k in ("user_id", "id", "pk")), "decoded JWT missing user id key"
    assert "exp" in decoded and isinstance(decoded["exp"], int)

def test_registration_serializer_creates_user_and_userserializer_serializes(monkeypatch):
    
    # Arrange
    input_payload = {"username": "alice", "email": "alice@example.com", "password": "s3cret"}
    # Prepare a fake user returned by the create_user flow
    class FakeUser:
        def __init__(self, username, email):
            self.username = username
            self.email = email
            self._token = "fake-token-xyz"

        @property
        def token(self):
            return self._token

    fake_user = FakeUser(input_payload["username"], input_payload["email"])

    # Patch the manager create_user to return our fake user. The serializer may call:
    # auth_models.User.objects.create_user or auth_models.UserManager.create_user
    if hasattr(auth_models, "UserManager"):
        # Patch the manager method so that any call returns our fake_user
        def _create_user(self, *args, **kwargs):
            return fake_user

        monkeypatch.setattr(auth_models.UserManager, "create_user", _create_user, raising=False)

    # Also attempt to patch User.objects.create_user if present as instance
    if hasattr(auth_models, "User") and hasattr(auth_models.User, "objects"):
        try:
            monkeypatch.setattr(auth_models.User.objects.__class__, "create_user", lambda self, **kwargs: fake_user, raising=False)
        except Exception:
            # best-effort
            pass

    # Act
    serializer = RegistrationSerializer(data=input_payload)
    assert serializer.is_valid(), "registration serializer should validate sample payload"
    created = serializer.save()

    # Assert: serializer.save returns our fake instance (or at least an object with expected attributes)
    assert created is fake_user or getattr(created, "email", None) == input_payload["email"]

    # Now ensure UserSerializer serializes the returned object and includes key fields
    user_serializer = UserSerializer(created)
    data = user_serializer.data if hasattr(user_serializer, "data") else user_serializer

    
    serialized = data if isinstance(data, dict) else dict(data)
    assert "username" in serialized and serialized["username"] == input_payload["username"]
    assert "email" in serialized and serialized["email"] == input_payload["email"]
    assert any(k in serialized for k in ("token",)), "serialized user missing token"

def test_user_json_renderer_renders_user_payload(monkeypatch):
    
    # Arrange
    renderer = UserJSONRenderer()
    payload = {"user": {"username": "bob", "email": "bob@example.com", "token": "tk-1"}}

    # Act
    rendered = renderer.render(payload)

    # Assert
    # renderer may return bytes or str
    if isinstance(rendered, bytes):
        text = rendered.decode("utf-8")
    else:
        text = rendered
    obj = json.loads(text)
    assert "user" in obj and isinstance(obj["user"], dict)
    assert obj["user"].get("username") == "bob"
    assert obj["user"].get("email") == "bob@example.com"
    assert obj["user"].get("token") == "tk-1"
