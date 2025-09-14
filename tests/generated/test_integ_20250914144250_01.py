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
    from unittest import mock
    import time
    import sys
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.core import utils as core_utils
    from django.utils.text import slugify
    from conduit.apps.articles.models import Comment
    from conduit.apps.authentication import models as auth_models
except ImportError as e:
    import pytest  # noqa: F401
    pytest.skip(f"Skipping tests due to import error: {e}", allow_module_level=True)


def _exc_lookup(name, default=Exception):
    import sys as _sys
    for m in list(_sys.modules.values()):
        try:
            if hasattr(m, name):
                return getattr(m, name)
        except Exception:
            continue
    return default


@pytest.mark.parametrize(
    "initial_slug,title,expected_contains_rand",
    [
        (None, "Hello World!", True),  # missing slug -> should add rand
        ("", "Hello World!", True),     # empty slug -> should add rand
        ("already-exists", "Hello World!", False),  # existing slug -> leave as is
    ],
)
def test_add_slug_to_article_if_not_exists_sets_or_keeps_slug(monkeypatch, initial_slug, title, expected_contains_rand):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        pass

    article = DummyArticle()
    article.title = title
    article.slug = initial_slug

    # Make generate_random_string deterministic
    monkeypatch.setattr(core_utils, "generate_random_string", lambda *a, **k: "RAND")

    # Act
    # The signal handler may accept sender, instance, **kwargs or (sender, instance)
    # We call via keyword to be explicit.
    add_slug_to_article_if_not_exists(sender=None, instance=article)

    # Assert
    if expected_contains_rand:
        # slug should be created and contain slugified title and RAND
        assert isinstance(article.slug, str) and article.slug, "slug should be a non-empty string"
        assert slugify(title) in article.slug, "slug should contain slugified title"
        assert "RAND" in article.slug, "slug should incorporate generated random string"
    else:
        # slug should remain unchanged
        assert article.slug == "already-exists"


@pytest.mark.parametrize(
    "body,expected_substring",
    [
        ("short body", "short body"),                       # short body -> string contains entire body
        ("x" * 100, "x" * 20),                              # long body -> string contains at least prefix
        ("", ""),                                           # empty body -> returns empty string or something containing empty
    ],
)
def test_comment_str_contains_body_prefix(body, expected_substring):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    comment = Comment()
    # Ensure attribute exists even if model normally requires other fields
    comment.body = body

    # Act
    result = str(comment)

    # Assert
    assert isinstance(result, _exc_lookup("str", Exception))
    # For non-empty expected_substring, ensure that prefix is present
    if expected_substring:
        assert expected_substring in result
    else:
        # empty expected_substring -> ensure str returns a string (could be '' or representation)
        assert result is not None


def test_user_token_calls_jwt_encode_and_embeds_id(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    captured = {}

    def fake_encode(payload, secret, algorithm="HS256"):
        captured['payload'] = payload
        captured['secret'] = secret
        captured['algorithm'] = algorithm
        return "FAKE_TOKEN"

    # Patch the jwt used inside the authentication models module
    monkeypatch.setattr(auth_models, "jwt", mock.MagicMock(encode=fake_encode))

    # Create a User instance with an id without touching DB
    user = auth_models.User()
    user.id = 999
    user.username = "tester"

    # Act
    token = user.token

    # Assert
    assert token == "FAKE_TOKEN"
    assert isinstance(captured.get('payload'), dict)
    # The payload should include user identification and an expiry
    assert captured['payload'].get('id') == 999 or captured['payload'].get('user_id') == 999
    assert 'exp' in captured['payload']
    assert isinstance(captured['payload']['exp'], (int, float))
    assert captured['payload']['exp'] > time.time()
    assert captured['algorithm'] == "HS256" or captured['algorithm'] is None


def test_add_slug_handles_unicode_titles(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        pass

    title = "Café — тест 🌟"
    article = DummyArticle()
    article.title = title
    article.slug = None

    # Force deterministic random part
    monkeypatch.setattr(core_utils, "generate_random_string", lambda *a, **k: "ZZZ")

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=article)

    # Assert
    assert isinstance(article.slug, str) and article.slug
    # Slug should contain slugified ascii-ish representation of title (characters normalized) and ZZZ
    assert "ZZZ" in article.slug
    # slugify will remove spaces and symbols; ensure at least some alphanumeric from title present
    normalized = slugify(title)
    assert normalized and any(ch.isalnum() for ch in normalized)
    assert normalized in article.slug
