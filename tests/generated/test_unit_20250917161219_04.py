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

import inspect
from types import SimpleNamespace

import pytest

try:
    from conduit.apps.articles import relations as articles_relations
    from conduit.apps.articles.relations import TagRelatedField
    from conduit.apps.profiles import serializers as profiles_serializers
    from conduit.apps.profiles.serializers import get_image
except (ImportError, ModuleNotFoundError) as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)

def _call_maybe_bound(func, obj):
    # Helper to call a function that might be defined as a serializer method (self, obj)
    sig = inspect.signature(func)
    if len(sig.parameters) == 1:
        return func(obj)
    return func(None, obj)

def test_TagRelatedField_to_internal_value_creates_tag(monkeypatch):
    
    # Arrange
    created = []

    class FakeTag:
        def __init__(self, name):
            self.name = name

    class FakeManager:
        @staticmethod
        def get_or_create(*args, **kwargs):
            # Support both positional and keyword 'name'
            name = kwargs.get("name")
            if not name and args:
                name = args[0]
            obj = FakeTag(name)
            created.append((name, True))
            return obj, True

    # Ensure the relations module uses our FakeTag with a manager
    FakeTag.objects = FakeManager()
    monkeypatch.setattr(articles_relations, "Tag", FakeTag, raising=True)

    field = TagRelatedField()

    # Act
    result = field.to_internal_value("python")

    # Assert
    assert isinstance(result, FakeTag)
    assert result.name == "python"
    assert created == [("python", True)]

def test_TagRelatedField_to_representation_returns_name():
    
    # Arrange
    field = TagRelatedField()
    tag_obj = SimpleNamespace(name="django-testing")

    # Act
    rep = field.to_representation(tag_obj)

    # Assert
    assert isinstance(rep, str)
    assert rep == "django-testing"

@pytest.mark.parametrize(
    "obj,expected",
    [
        (SimpleNamespace(image="http://example.com/avatar.png"), "http://example.com/avatar.png"),
        (SimpleNamespace(image=None), ""),
        (SimpleNamespace(), ""),
    ],
)
def test_get_image_handles_present_none_and_missing(obj, expected):
    
    # Arrange/Act
    result = _call_maybe_bound(get_image, obj)

    # Assert
    assert isinstance(result, str)
    assert result == expected
