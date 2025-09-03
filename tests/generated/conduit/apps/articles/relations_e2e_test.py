import importlib.util, pathlib
import types
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/relations.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_get_queryset_calls_tag_objects_all(monkeypatch):
    sentinel = object()

    class FakeObjects:
        def all(self_inner):
            return sentinel

    class FakeTag:
        objects = FakeObjects()

    monkeypatch.setattr(target_module, "Tag", FakeTag)

    field = target_module.TagRelatedField()
    result = field.get_queryset()
    assert result is sentinel


def test_to_internal_value_creates_new_tag_when_not_exists(monkeypatch):
    recorded = {}

    class FakeTagInstance:
        def __init__(self, tag, slug):
            self.tag = tag
            self.slug = slug

    class FakeObjects:
        def get_or_create(self_inner, **kwargs):
            recorded.update(kwargs)
            return FakeTagInstance(kwargs.get("tag"), kwargs.get("slug")), True

    class FakeTag:
        objects = FakeObjects()

    monkeypatch.setattr(target_module, "Tag", FakeTag)

    field = target_module.TagRelatedField()
    returned = field.to_internal_value("Python")

    assert isinstance(returned, FakeTagInstance)
    assert returned.tag == "Python"
    assert returned.slug == "python"
    assert recorded["tag"] == "Python"
    assert recorded["slug"] == "python"


def test_to_internal_value_returns_existing_tag_when_exists(monkeypatch):
    recorded = {}

    class ExistingTag:
        def __init__(self, tag, slug):
            self.tag = tag
            self.slug = slug

    existing = ExistingTag("Existing", "existing")

    class FakeObjects:
        def get_or_create(self_inner, **kwargs):
            recorded.update(kwargs)
            return existing, False

    class FakeTag:
        objects = FakeObjects()

    monkeypatch.setattr(target_module, "Tag", FakeTag)

    field = target_module.TagRelatedField()
    returned = field.to_internal_value("Existing")

    assert returned is existing
    assert recorded["tag"] == "Existing"
    assert recorded["slug"] == "existing"


def test_to_internal_value_raises_on_non_string_data(monkeypatch):
    class FakeObjects:
        def get_or_create(self_inner, **kwargs):
            # should not be reached if .lower() fails first
            return None, False

    class FakeTag:
        objects = FakeObjects()

    monkeypatch.setattr(target_module, "Tag", FakeTag)

    field = target_module.TagRelatedField()
    with pytest.raises(AttributeError):
        field.to_internal_value(123)  # int has no .lower()


def test_to_representation_returns_tag_string():
    class Value:
        def __init__(self, tag):
            self.tag = tag

    field = target_module.TagRelatedField()
    value = Value("Django")
    assert field.to_representation(value) == "Django"


def test_to_representation_raises_when_missing_tag():
    field = target_module.TagRelatedField()
    class NoTag:
        pass

    with pytest.raises(AttributeError):
        field.to_representation(NoTag())