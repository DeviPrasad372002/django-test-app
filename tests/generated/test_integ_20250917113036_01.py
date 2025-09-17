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

import pytest

try:
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.relations import TagRelatedField
except ImportError:
    pytest.skip("Django or target modules not available", allow_module_level=True)

def test_add_slug_to_article_if_not_exists_sets_slug_when_missing(monkeypatch):
    
    # Arrange
    class FakeInstance:
        title = "My Title"
        slug = None

    instance = FakeInstance()

    # Ensure deterministic slugify and random string
    monkeypatch.setattr("conduit.apps.articles.signals.slugify", lambda s: "my-title")
    monkeypatch.setattr(
        "conduit.apps.core.utils.generate_random_string", lambda length=6: "XYZ123"
    )

    # Act
    add_slug_to_article_if_not_exists(sender=None, instance=instance, created=True)

    # Assert
    assert instance.slug == "my-title-XYZ123"

def test_TagRelatedField_to_internal_value_and_to_representation(monkeypatch):
    
    # Arrange
    # Create a fake Tag model and manager to simulate get_or_create behavior
    created_flags = []

    class FakeTag:
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return f"<FakeTag name={self.name!r}>"

    class FakeManager:
        def get_or_create(self, name):
            created_flags.append(True)
            return (FakeTag(name), True)

    FakeTag.objects = FakeManager()

    # Patch the Tag reference used inside the relations module
    monkeypatch.setattr("conduit.apps.articles.relations.Tag", FakeTag, raising=False)

    field = TagRelatedField()

    # Act
    tag_obj = field.to_internal_value("python")
    rep = field.to_representation(tag_obj)

    # Assert
    assert isinstance(tag_obj, FakeTag)
    assert tag_obj.name == "python"
    assert rep == "python"
    # Ensure our fake manager was used (created flag recorded)
    assert created_flags == [True]
