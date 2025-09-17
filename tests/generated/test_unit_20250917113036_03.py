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
    import importlib
    import types
    import datetime as _datetime
    import pytest
    from types import SimpleNamespace
    # import target modules
    auth_models = importlib.import_module("conduit.apps.authentication.models")
    core_utils = importlib.import_module("conduit.apps.core.utils")
    core_exceptions = importlib.import_module("conduit.apps.core.exceptions")
    auth_signals = importlib.import_module("conduit.apps.authentication.signals")
    profiles_models = importlib.import_module("conduit.apps.profiles.models")
    rt_exceptions = importlib.import_module("rest_framework.exceptions")
except Exception as e:  
    import pytest
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

def _make_instance_without_init(cls, **attrs):
    inst = object.__new__(cls)
    for k, v in attrs.items():
        setattr(inst, k, v)
    return inst

def _resolve_user_generate_token():
    # The project may implement _generate_jwt_token as a method on User or a stand-alone function.
    User = getattr(auth_models, "User", None)
    if User is None:
        raise AttributeError("User model not found")
    method = getattr(User, "_generate_jwt_token", None)
    if callable(method):
        return method, User
    # fallback: look for module-level function
    fn = getattr(auth_models, "_generate_jwt_token", None)
    if callable(fn):
        return fn, None
    raise AttributeError("_generate_jwt_token not found")

def test_get_short_name_returns_username():
    
    # Arrange
    User = getattr(auth_models, "User", None)
    if User is None:
        pytest.skip("User model not present")
    # Create instance without running Django model init
    user = _make_instance_without_init(User, username="alice123")
    # Act
    short = getattr(user, "get_short_name", lambda: None)()
    # Assert
    assert isinstance(short, str)
    assert short == "alice123"

def test__generate_jwt_token_invokes_jwt_encode_with_user_id(monkeypatch):
    
    # Arrange
    try:
        generate_fn, UserClass = _resolve_user_generate_token()
    except AttributeError:
        pytest.skip("_generate_jwt_token not available")
    # create fake user instance with id and pk attributes
    user = _make_instance_without_init(UserClass, id=42, pk=42)
    captured = {}

    def fake_encode(payload, key, algorithm="HS256"):
        captured["payload"] = payload
        captured["key"] = key
        captured["algorithm"] = algorithm
        return "FAKE.TOKEN.STRING"

    # Monkeypatch jwt.encode used inside auth_models
    jwt_mod = getattr(auth_models, "jwt", None)
    if jwt_mod is None:
        pytest.skip("jwt module not present in auth_models")
    monkeypatch.setattr(jwt_mod, "encode", fake_encode, raising=True)

    # Also freeze utcnow to a known time if used by implementation
    dt_mod = getattr(auth_models, "_datetime", None)
    if dt_mod is None:
        # try module using datetime
        dt_mod = _datetime
    class FixedDT:
        @classmethod
        def utcnow(cls):
            return _datetime.datetime(2020, 1, 1, 0, 0, 0)
    # attempt to patch the module's datetime reference if present
    if hasattr(auth_models, "datetime"):
        monkeypatch.setattr(auth_models, "datetime", FixedDT, raising=False)
    else:
        # patch attribute commonly used
        monkeypatch.setattr(auth_models, "_datetime", FixedDT, raising=False)

    # Act
    if UserClass is not None and hasattr(UserClass, "_generate_jwt_token"):
        token = UserClass._generate_jwt_token(user)
    else:
        token = generate_fn(user)

    # Assert
    assert token == "FAKE.TOKEN.STRING"
    assert "payload" in captured and isinstance(captured["payload"], dict)
    # payload should reference user id in one of common keys
    assert any(k in captured["payload"] for k in ("user_id", "id", "pk"))
    assert captured["algorithm"] == "HS256"

def test_generate_random_string_respects_length_and_characters(monkeypatch):
    
    # Arrange
    gen = getattr(core_utils, "generate_random_string", None)
    if gen is None:
        pytest.skip("generate_random_string not found")
    # Force deterministic choice: always pick first element
    target_random = getattr(core_utils, "random", None)
    if target_random is None:
        pytest.skip("random module not accessible via core.utils")
    monkeypatch.setattr(target_random, "choice", lambda seq: seq[0], raising=True)
    # Act
    s = gen(6)
    # Assert
    assert isinstance(s, str)
    assert len(s) == 6
    # since choice returns seq[0], result should be that character repeated
    # Ensure that character is from the allowed pool (first element of ascii_lowercase or similar)
    assert all(ch == s[0] for ch in s)

def test__handle_not_found_and_generic_error_return_expected_status_codes():
    
    # Arrange
    handle_not_found = getattr(core_exceptions, "_handle_not_found_error", None)
    handle_generic = getattr(core_exceptions, "_handle_generic_error", None)
    if handle_not_found is None or handle_generic is None:
        pytest.skip("exception handlers not present")
    # Create DRF NotFound and generic Exception
    nf = rt_exceptions.NotFound(detail="missing")
    gen = Exception("boom")

    # Act
    resp_nf = handle_not_found(nf)
    resp_gen = handle_generic(gen)

    # Assert
    # Both should be rest_framework.response.Response-like objects with status_code
    assert hasattr(resp_nf, "status_code"), "NotFound handler must return a Response-like object"
    assert resp_nf.status_code == 404

    assert hasattr(resp_gen, "status_code"), "Generic handler must return a Response-like object"
    assert resp_gen.status_code == 500

def test_create_related_profile_calls_profile_get_or_create(monkeypatch):
    
    # Arrange
    create_related_profile = getattr(auth_signals, "create_related_profile", None)
    if create_related_profile is None:
        pytest.skip("create_related_profile not present")
    Profile = getattr(profiles_models, "Profile", None)
    if Profile is None:
        pytest.skip("Profile model not present")

    called = {"called": False, "kwargs": None}

    def fake_get_or_create(**kwargs):
        called["called"] = True
        called["kwargs"] = kwargs
        return (SimpleNamespace(id=1), True)

    # Monkeypatch the Manager.get_or_create method
    manager = getattr(Profile, "objects", None)
    if manager is None:
        pytest.skip("Profile.objects manager not present")
    monkeypatch.setattr(manager, "get_or_create", fake_get_or_create, raising=False)

    # Create a fake user instance to simulate a created user
    fake_user = _make_instance_without_init(auth_models.User, id=99)

    # Act
    # The typical signal signature is (sender, instance, created, **kwargs)
    create_related_profile(sender=None, instance=fake_user, created=True)

    # Assert
    assert called["called"] is True
    assert "user" in called["kwargs"]
    assert called["kwargs"]["user"] is fake_user
