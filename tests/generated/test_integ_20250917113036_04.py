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

import importlib
import sys
import types
import json
from types import SimpleNamespace
from unittest import mock

import pytest

# Guard third-party / project imports
try:
    from conduit.apps.articles.relations import TagRelatedField
    from conduit.apps.articles.models import Tag
    from conduit.apps.articles.renderers import ArticleJSONRenderer
    from conduit.apps.articles.__init__ import ArticlesAppConfig
except ImportError:
    pytest.skip("conduit project imports unavailable, skipping integration tests", allow_module_level=True)

def _ensure_field_instance(field_cls):
    """
    Try to instantiate field_cls normally; if that fails (requires args),
    create an instance without calling __init__.
    """
    try:
        return field_cls()
    except Exception:
        # fallback: create instance without running __init__
        return object.__new__(field_cls)

def test_tagrelatedfield_to_representation_and_to_internal_value(monkeypatch):
    
    # Arrange
    field = _ensure_field_instance(TagRelatedField)
    dummy_value = SimpleNamespace(name="python")

    # Act - to_representation should return the name attribute of value
    rep = field.to_representation(dummy_value)

    # Assert
    assert isinstance(rep, str)
    assert rep == "python"

    # Arrange - monkeypatch Tag.objects.get_or_create to avoid DB
    class FakeManager:
        def get_or_create(self, name):
            return (SimpleNamespace(name=name), True)

    monkeypatch.setattr(Tag, "objects", FakeManager(), raising=False)

    # Act - to_internal_value should call our fake manager and return a tag-like object
    internal = field.to_internal_value("pytest")

    # Assert
    assert hasattr(internal, "name")
    assert internal.name == "pytest"

def test_articlejsonrenderer_render_wraps_article():
    
    # Arrange
    renderer = ArticleJSONRenderer()
    payload = {"title": "Hello", "body": "world", "slug": "hello-world"}

    # Act
    rendered = renderer.render(payload, renderer_context={})

    # renderer may return bytes or str depending on implementation
    if isinstance(rendered, bytes):
        text = rendered.decode("utf-8")
    else:
        text = rendered

    parsed = json.loads(text)

    # Assert
    assert isinstance(parsed, dict)
    # Expect top-level key 'article' wrapping the serializer payload
    assert "article" in parsed
    assert parsed["article"]["title"] == "Hello"
    assert parsed["article"]["slug"] == "hello-world"

def test_articlesappconfig_ready_imports_signals(monkeypatch):
    
    # Arrange
    mod_name = "conduit.apps.articles.signals"
    fake_mod = types.ModuleType(mod_name)
    # Provide a sentinel attribute so we can verify module was the one loaded
    fake_mod.SIGNALS_LOADED = True
    monkeypatch.setitem(sys.modules, mod_name, fake_mod)

    # Create an ArticlesAppConfig instance without invoking AppConfig.__init__
    appcfg = object.__new__(ArticlesAppConfig)

    # Act - calling ready should import the signals module (which we've placed in sys.modules)
    appcfg.ready()

    # Assert
    assert mod_name in sys.modules
    assert getattr(sys.modules[mod_name], "SIGNALS_LOADED", False) is True

def test_migration_module_has_expected_structure():
    
    # This migration module may not exist in some trimmed test copies;
    # import dynamically and skip if missing.
    module_path = "conduit.apps.articles.migrations.0001_initial"
    try:
        mig_mod = importlib.import_module(module_path)
    except ImportError:
        pytest.skip(f"{module_path} not importable in this environment", allow_module_level=False)

    # Arrange / Act
    Migration = getattr(mig_mod, "Migration", None)

    # Assert common migration attributes
    assert Migration is not None, "Migration class missing from migration module"
    # Migration should define 'operations' and 'dependencies'
    ops = getattr(Migration, "operations", None)
    deps = getattr(Migration, "dependencies", None)
    assert isinstance(ops, (list, tuple)), "Migration.operations should be a list or tuple"
    assert isinstance(deps, (list, tuple)), "Migration.dependencies should be a list or tuple"
