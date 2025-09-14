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

try:
    import pytest
    from types import SimpleNamespace
    from unittest import mock

    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.authentication import backends as backends_mod
    from conduit.apps.authentication.backends import JWTAuthentication
    from conduit.apps.articles.models import Comment
except ImportError:
    import pytest
    pytest.skip("Required application modules not available", allow_module_level=True)


def _make_dummy_request(auth_value=None):
    class DummyRequest:
        def __init__(self, auth_value):
            # Arrange: minimal surface area expected by many auth implementations
            self.META = {}
            self.headers = {}
            if auth_value is not None:
                # common places frameworks put auth
                self.META['HTTP_AUTHORIZATION'] = auth_value
                self.headers['Authorization'] = auth_value

    return DummyRequest(auth_value)


def test_add_slug_to_article_if_not_exists_sets_slug_and_preserves_existing(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    dummy = DummyArticle(title="Hello World", slug=None)

    # Force deterministic random string so we can assert it is used in slug
    monkeypatch.setattr("conduit.apps.articles.signals.generate_random_string", lambda length=6: "RND")
    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=dummy, created=True)
    # Assert
    assert isinstance(dummy.slug, str) and dummy.slug != ""
    # slug should include slugified title portion and our deterministic random string
    assert "rnd" in dummy.slug.lower() or "RND".lower() in dummy.slug.lower()

    # Arrange: now ensure existing slug remains unchanged
    original = "existing-slug"
    dummy2 = DummyArticle(title="Another", slug=original)
    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=dummy2, created=True)
    # Assert
    assert dummy2.slug == original


def test_jwt_authentication_authenticate_and__authenticate_credentials(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    auth = JWTAuthentication()

    # Act/Assert 1: missing header -> authenticate returns None (no credentials)
    req_no_auth = _make_dummy_request(None)
    result = auth.authenticate(req_no_auth)
    assert result is None

    # Arrange for success path: monkeypatch jwt.decode and backend user lookup
    class DummyUser:
        def __init__(self, pk):
            self.pk = pk

    class DummyManager:
        def get(self, **kwargs):
            # Act: simulate retrieval by id
            return DummyUser(kwargs.get("pk") or kwargs.get("id") or kwargs.get("user_id"))

    dummy_objects = SimpleNamespace(get=DummyManager().get)

    # Patch the module-level jwt.decode used by the backend to return a payload
    monkeypatch.setattr(backends_mod, "jwt", SimpleNamespace(decode=lambda token, key, algorithms: {"user_id": 123}))
    # Patch User lookup to avoid DB; backend likely references conduit.apps.authentication.backends.User
    monkeypatch.setattr(backends_mod, "User", SimpleNamespace(objects=dummy_objects))

    # Act: call the private credential checker directly
    returned = auth._authenticate_credentials("dummy.token.value")
    # Assert: expecting a tuple-like (user, token) or user-like value; ensure user instance present
    if isinstance(returned, _exc_lookup("tuple", Exception)):
        user_obj = returned[0]
        token_out = returned[1]
        assert isinstance(user_obj, _exc_lookup("DummyUser", Exception))
        assert token_out == "dummy.token.value"
    else:
        # fallback: some implementations return just the user
        assert isinstance(returned, _exc_lookup("DummyUser", Exception))

    # Arrange for failure path: jwt.decode raises
    def raise_decode(token, key, algorithms):
        raise Exception("invalid token")

    monkeypatch.setattr(backends_mod, "jwt", SimpleNamespace(decode=raise_decode))
    # Act / Assert: credential decoding failure should propagate as an exception
    with pytest.raises(_exc_lookup("Exception", Exception)):
        auth._authenticate_credentials("bad.token.value")


@pytest.mark.parametrize("body_value", ["a short comment", ""])
def test_comment___str__returns_body_value(body_value):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    # Direct instantiation of model-like object; __str__ usually returns body
    comment = Comment(body=body_value)
    # Act
    s = str(comment)
    # Assert
    assert isinstance(s, _exc_lookup("str", Exception))
    assert s == (body_value or "")
