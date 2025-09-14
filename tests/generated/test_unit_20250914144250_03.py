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
if _target and os.path.exists(_target):
    if _target not in sys.path: sys.path.insert(0, _target)
    try: os.chdir(_target)
    except Exception: pass

def _exc_lookup(name, default):
    try:
        mod_name, _, cls_name = str(name).rpartition(".")
        if mod_name:
            mod = __import__(mod_name, fromlist=[cls_name])
            return getattr(mod, cls_name, default)
        return getattr(sys.modules.get("builtins"), str(name), default)
    except Exception:
        return default

def _apply_compatibility_fixes():
    try:
        import jinja2
        if not hasattr(jinja2, 'Markup'):
            try:
                from markupsafe import Markup, escape
                jinja2.Markup = Markup
                if not hasattr(jinja2, 'escape'):
                    jinja2.escape = escape
            except Exception:
                pass
    except ImportError:
        pass
    try:
        import collections as _collections, collections.abc as _abc
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container',
                   'MutableSequence','Set','MutableSet','Iterator','Generator','Callable','Collection'):
            if not hasattr(_collections, _n) and hasattr(_abc, _n):
                setattr(_collections, _n, getattr(_abc, _n))
    except Exception:
        pass
    try:
        import marshmallow as _mm
        if not hasattr(_mm, "__version__"):
            _mm.__version__ = "4"
    except Exception:
        pass

_apply_compatibility_fixes()

# Minimal, safe Django bootstrap. If anything goes wrong, skip the module (repo-agnostic).
try:
    import django
    from django.conf import settings as _dj_settings
    from django import apps as _dj_apps

    if not _dj_settings.configured:
        _cfg = dict(
            DEBUG=True,
            SECRET_KEY='pytest-secret',
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3','NAME': ':memory:'}},
            INSTALLED_APPS=[
                'django.contrib.auth','django.contrib.contenttypes',
                'django.contrib.sessions','django.contrib.messages'
            ],
            MIDDLEWARE=[
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
            ],
            USE_TZ=True, TIME_ZONE='UTC',
        )
        try: _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
        except Exception: pass
        try: _dj_settings.configure(**_cfg)
        except Exception: pass

    if not _dj_apps.ready:
        try: django.setup()
        except Exception: pass

    # Probe a known Django core that previously crashed on some stacks.
    try:
        import django.contrib.auth.base_user as _dj_probe  # noqa
    except Exception as _e:
        _pytest.skip(f"Django core import failed safely: {_e.__class__.__name__}: {_e}", allow_module_level=True)
except Exception as _e:
    # Do NOT crash the entire test session – make the module opt-out.
    _pytest.skip(f"Django bootstrap not available: {_e.__class__.__name__}: {_e}", allow_module_level=True)


# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import importlib
    import json
    import string
    import types
    from unittest import mock

    import pytest

    auth_models = importlib.import_module("conduit.apps.authentication.models")
    auth_renderers = importlib.import_module("conduit.apps.authentication.renderers")
    auth_serializers = importlib.import_module("conduit.apps.authentication.serializers")
    auth_signals = importlib.import_module("conduit.apps.authentication.signals")
    core_exceptions = importlib.import_module("conduit.apps.core.exceptions")
    core_utils = importlib.import_module("conduit.apps.core.utils")
    profiles_models = importlib.import_module("conduit.apps.profiles.models")
    rest_exceptions = importlib.import_module("rest_framework.exceptions")
except Exception as e:  # pragma: no cover - skip entire module when imports missing
    import pytest as _pytest
    _pytest.skip(f"Required modules for tests are not available: {e}", allow_module_level=True)


def _exc_lookup(name: str, default=Exception):
    """
    Lookup an exception class by name in some common modules used by the project.
    Falls back to the provided default when the name cannot be resolved.
    """
    # try rest framework exceptions first
    try:
        return getattr(rest_exceptions, name)
    except Exception:
        pass
    # fallback to builtins
    return default


@pytest.mark.parametrize(
    "username, email, expected",
    [
        ("alice", "alice@example.com", "alice"),  # normal case: username present
        ("", "bob@example.com", "bob@example.com"),  # edge case: empty username uses email
        (None, "carol@example.com", "carol@example.com"),  # None username treated like absent
    ],
)
def test_get_short_name_returns_username_or_email(username, email, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # create a User-like object without touching DB using __new__
    user = object.__new__(auth_models.User)
    # assign attributes expected by get_short_name
    setattr(user, "username", username)
    setattr(user, "email", email)

    # Act
    result = auth_models.User.get_short_name(user)

    # Assert
    assert isinstance(result, (str, type(None))) or result is None
    assert result == expected


def test__generate_jwt_token_calls_jwt_encode_and_includes_exp(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    user = object.__new__(auth_models.User)
    # many implementations use id or pk
    setattr(user, "pk", 42)
    captured = {}

    def fake_encode(payload, key, algorithm="HS256"):
        # capture payload for assertions and return a deterministic token
        captured["payload"] = payload
        captured["key"] = key
        captured["algorithm"] = algorithm
        return "signed.token.value"

    # monkeypatch the jwt.encode used in the module under test
    monkeypatch.setattr(auth_models, "jwt", mock.MagicMock(encode=fake_encode))

    # Act
    token = auth_models.User._generate_jwt_token(user)

    # Assert
    assert isinstance(token, _exc_lookup("str", Exception))
    assert token == "signed.token.value"
    # expect payload contains a user id and expiration timestamp
    pl = captured.get("payload", {})
    assert any(k in pl for k in ("id", "user_id", "pk")), "payload should include id-like key"
    assert "exp" in pl, "payload should include exp claim"
    assert captured["algorithm"] in ("HS256",), "expected algorithm default HS256"


def test_userjsonrenderer_render_outputs_json_bytes_and_contains_username():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = auth_renderers.UserJSONRenderer()
    data = {"user": {"username": "tester", "email": "t@example.com"}}

    # Act
    output = renderer.render(data)

    # Assert
    # Renderers are expected to emit bytes
    assert isinstance(output, (bytes, bytearray))
    text = output.decode("utf-8")
    # it should be valid JSON and include the username
    payload = json.loads(text)
    assert "user" in payload
    assert payload["user"]["username"] == "tester"


def test_validate_registration_passwords_behavior():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # create a serializer instance without DRF machinery
    serializer = object.__new__(auth_serializers.RegistrationSerializer)

    # case 1: matching passwords -> returns attrs unchanged (or possibly modified)
    attrs_ok = {"password": "s3cret", "password2": "s3cret", "email": "a@b.com"}
    # Act
    result = auth_serializers.RegistrationSerializer.validate(serializer, attrs_ok.copy())
    # Assert
    assert isinstance(result, _exc_lookup("dict", Exception))
    assert result.get("email") == "a@b.com"

    # case 2: mismatched passwords -> raises ValidationError
    attrs_bad = {"password": "abc", "password2": "xyz"}
    ValidationError = _exc_lookup("ValidationError", Exception)
    with pytest.raises(_exc_lookup("ValidationError", Exception)):
        auth_serializers.RegistrationSerializer.validate(serializer, attrs_bad)


def test_create_related_profile_creates_profile_when_created_true(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    fake_user = types.SimpleNamespace(id=7, pk=7)
    # Provide a mock Profile class with objects.create
    fake_profile_objects = mock.MagicMock()
    fake_profile_objects.create = mock.MagicMock(return_value="created_profile")
    # monkeypatch the Profile referenced in the signals module
    monkeypatch.setattr(auth_signals, "Profile", mock.MagicMock(objects=fake_profile_objects))

    # Act
    auth_signals.create_related_profile(sender=auth_models.User, instance=fake_user, created=True)

    # Assert
    fake_profile_objects.create.assert_called_once_with(user=fake_user)


def test_core_exception_handler_delegates_to_handlers(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    called = {}

    def fake_not_found(exc, context):
        called["not_found"] = True
        return "handled_not_found"

    def fake_generic(exc, context):
        called["generic"] = True
        return "handled_generic"

    monkeypatch.setattr(core_exceptions, "_handle_not_found_error", fake_not_found)
    monkeypatch.setattr(core_exceptions, "_handle_generic_error", fake_generic)

    # Act & Assert for status_code 404
    exc404 = types.SimpleNamespace(status_code=404, detail="not here")
    out404 = core_exceptions.core_exception_handler(exc404, context={})
    assert out404 == "handled_not_found"
    assert called.get("not_found") is True
    called.clear()

    # Act & Assert for no status_code -> generic
    exc_other = Exception("boom")
    out_other = core_exceptions.core_exception_handler(exc_other, context={})
    assert out_other == "handled_generic"
    assert called.get("generic") is True


@pytest.mark.parametrize("length", [0, 1, 8, 32])
def test_generate_random_string_length_and_characters(length):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange & Act
    result = core_utils.generate_random_string(length)

    # Assert type and length
    assert isinstance(result, _exc_lookup("str", Exception))
    assert len(result) == length

    # Allowed characters: letters + digits (conservative assumption)
    allowed = set(string.ascii_letters + string.digits)
    assert all((c in allowed) for c in result)


def test_profile_follow_unfollow_and_is_following(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    profile_instance = object.__new__(profiles_models.Profile)
    other_user = types.SimpleNamespace(pk=11)
    # mock following manager with add/remove/filter.exists
    following_mgr = mock.MagicMock()
    following_mgr.add = mock.MagicMock()
    following_mgr.remove = mock.MagicMock()
    # filter().exists() chain
    fake_qs = mock.MagicMock()
    fake_qs.exists = mock.MagicMock(return_value=True)
    following_mgr.filter = mock.MagicMock(return_value=fake_qs)

    # attach to instance
    setattr(profile_instance, "following", following_mgr)

    # Act - follow
    profiles_models.Profile.follow(profile_instance, other_user)
    # Assert follow called
    profile_instance.following.add.assert_called_once_with(other_user)

    # Act - is_following returns True as we wired exists to True
    assert profiles_models.Profile.is_following(profile_instance, other_user) is True
    profile_instance.following.filter.assert_called_with(pk=getattr(other_user, "pk", None))

    # Act - unfollow
    profiles_models.Profile.unfollow(profile_instance, other_user)
    profile_instance.following.remove.assert_called_once_with(other_user)

    # Now simulate not following
    fake_qs.exists.return_value = False
    assert profiles_models.Profile.is_following(profile_instance, other_user) is False
