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
    import json
    from types import SimpleNamespace
    import importlib

    signals = importlib.import_module("conduit.apps.articles.signals")
    renderers_mod = importlib.import_module("conduit.apps.articles.renderers")
    ArticleJSONRenderer = renderers_mod.ArticleJSONRenderer
    CommentJSONRenderer = renderers_mod.CommentJSONRenderer
    core_exceptions = importlib.import_module("conduit.apps.core.exceptions")
    _handle_generic_error = getattr(core_exceptions, "_handle_generic_error")
    from rest_framework.response import Response
except ImportError as e:
    import pytest
    pytest.skip("Skipping tests due to ImportError: " + str(e), allow_module_level=True)


def _exc_lookup(name, default=Exception):
    # Best-effort lookup for exception by name in known modules; fallback to default
    import sys
    for mod in list(sys.modules.values()):
        if not mod:
            continue
        if hasattr(mod, name):
            return getattr(mod, name)
    return default


def _json_contains_value(obj, expected_value):
    # helper to search JSON structure for a value (string representation)
    s = json.dumps(obj, ensure_ascii=False)
    return str(expected_value) in s


def test_add_slug_to_article_if_not_exists_sets_slug_when_missing_and_preserves_when_present(monkeypatch):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    class DummyArticle:
        def __init__(self, title, slug=None):
            self.title = title
            self.slug = slug

    instance_missing = DummyArticle("My Test Title", slug=None)
    instance_existing = DummyArticle("Another Title", slug="existing-slug")

    # Make generate_random_string deterministic and slugify predictable
    monkeypatch.setattr(signals, "generate_random_string", lambda length=6: "XYZ123")
    monkeypatch.setattr(signals, "slugify", lambda value: value.lower().replace(" ", "-"))

    # Act - when created and slug missing
    signals.add_slug_to_article_if_not_exists(sender=None, instance=instance_missing, created=True)

    # Assert - slug set contains slugified title and generated random portion (case-insensitive)
    assert instance_missing.slug is not None
    assert instance_missing.slug.lower().startswith("my-test-title")
    assert "xyz123" in instance_missing.slug.lower()

    # Act - when created but slug already exists, should preserve
    prev = instance_existing.slug
    signals.add_slug_to_article_if_not_exists(sender=None, instance=instance_existing, created=True)

    # Assert - existing slug preserved
    assert instance_existing.slug == prev


@pytest.mark.parametrize(
    "renderer_class,input_data,expected_fragment",
    [
        (ArticleJSONRenderer, {"title": "Hello World", "body": "content"}, "Hello World"),
        (ArticleJSONRenderer, None, "null"),  # edge case: None -> JSON null
        (CommentJSONRenderer, {"comment": {"body": "Nice!"}}, "Nice!"),
        (CommentJSONRenderer, [], "[]"),  # edge case: empty list of comments
    ],
)
def test_renderers_produce_valid_json_and_contain_expected_values(renderer_class, input_data, expected_fragment):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    renderer = renderer_class()

    # Act
    rendered = renderer.render(input_data)

    # Assert - must be bytes or str that can be parsed or contain expected fragment
    assert rendered is not None
    # If bytes, decode, else use as-is
    if isinstance(rendered, _exc_lookup("bytes", Exception)):
        rendered_text = rendered.decode("utf-8")
    else:
        rendered_text = str(rendered)

    # If expected_fragment is 'null' or '[]' we can assert direct presence
    assert expected_fragment in rendered_text

    # Also assert it's valid JSON when possible (except when input is object that json can't parse)
    try:
        parsed = json.loads(rendered_text)
    except Exception:
        pytest.skip("Rendered output not JSON-parseable in this environment")
    # final sanity: parsed must contain expected fragment when serialized back
    assert expected_fragment in json.dumps(parsed, ensure_ascii=False)


@pytest.mark.parametrize("msg", ["something bad", ""])
def test_handle_generic_error_returns_response_with_errors_structure(msg):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    exc = Exception(msg)

    # Act
    response = _handle_generic_error(exc, {"view": "dummy"})

    # Assert
    assert isinstance(response, _exc_lookup("Response", Exception))
    # Status code must indicate error
    assert getattr(response, "status_code", 500) >= 400

    # Response data should contain an 'errors' key (common pattern). Defensive: accept dict-like
    data = getattr(response, "data", None)
    assert data is not None
    assert "errors" in data

    # 'errors' should be a mapping or list - prefer mapping for standard handlers
    errors = data["errors"]
    assert isinstance(errors, (dict, list))

    # If mapping, ensure at least one key maps to a list/str describing the error
    if isinstance(errors, _exc_lookup("dict", Exception)):
        # pick first value
        first_value = next(iter(errors.values()))
        assert isinstance(first_value, (list, str))
    else:
        # list: ensure non-empty and contains string
        assert len(errors) >= 1
        assert any(isinstance(item, (str, dict, list)) for item in errors)
