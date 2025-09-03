import importlib.util, pathlib
import types
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/relations.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


class FakeTag:
    _store = {}

    def __init__(self, tag, slug):
        self.tag = tag
        self.slug = slug

    class objects:
        @staticmethod
        def all():
            return list(FakeTag._store.values())

        @staticmethod
        def get_or_create(tag, slug):
            if tag in FakeTag._store:
                return FakeTag._store[tag], False
            inst = FakeTag(tag, slug)
            FakeTag._store[tag] = inst
            return inst, True


def test_get_queryset_returns_all(monkeypatch):
    # Arrange
    FakeTag._store = {}
    t1 = FakeTag("Python", "python")
    t2 = FakeTag("Django", "django")
    FakeTag._store["Python"] = t1
    FakeTag._store["Django"] = t2

    monkeypatch.setattr(target_module, "Tag", FakeTag)

    field = target_module.TagRelatedField()

    # Act
    qs = field.get_queryset()

    # Assert
    assert isinstance(qs, list)
    assert len(qs) == 2
    assert t1 in qs and t2 in qs


def test_to_internal_value_creates_and_returns_tag(monkeypatch):
    # Arrange
    FakeTag._store = {}
    monkeypatch.setattr(target_module, "Tag", FakeTag)
    field = target_module.TagRelatedField()

    # Act
    result = field.to_internal_value("NewTag")

    # Assert
    assert isinstance(result, FakeTag)
    assert result.tag == "NewTag"
    assert result.slug == "newtag"
    # Ensure it's persisted in the fake store
    assert "NewTag" in FakeTag._store
    assert FakeTag._store["NewTag"] is result


def test_to_internal_value_returns_existing_instance_on_repeat(monkeypatch):
    # Arrange
    FakeTag._store = {}
    monkeypatch.setattr(target_module, "Tag", FakeTag)
    field = target_module.TagRelatedField()

    # Act
    first = field.to_internal_value("Repeat")
    second = field.to_internal_value("Repeat")

    # Assert
    assert first is second
    assert first.tag == "Repeat"
    assert first.slug == "repeat"


def test_to_internal_value_non_string_raises_attribute_error(monkeypatch):
    # Arrange
    FakeTag._store = {}
    monkeypatch.setattr(target_module, "Tag", FakeTag)
    field = target_module.TagRelatedField()

    # Act & Assert
    with pytest.raises(AttributeError):
        # int doesn't have lower(), so should raise AttributeError
        field.to_internal_value(123)


def test_to_representation_returns_tag_string(monkeypatch):
    # Arrange
    monkeypatch.setattr(target_module, "Tag", FakeTag)
    field = target_module.TagRelatedField()
    fake = FakeTag("Example", "example")

    # Act
    rep = field.to_representation(fake)

    # Assert
    assert rep == "Example"


def test_to_representation_missing_tag_attribute_raises(monkeypatch):
    # Arrange
    monkeypatch.setattr(target_module, "Tag", FakeTag)
    field = target_module.TagRelatedField()

    class NoTagAttr:
        pass

    # Act & Assert
    with pytest.raises(AttributeError):
        field.to_representation(NoTagAttr())


def test_get_queryset_propagates_exception(monkeypatch):
    # Arrange
    class BadObjects:
        @staticmethod
        def all():
            raise RuntimeError("database error")

    class BadTag:
        objects = BadObjects()

    monkeypatch.setattr(target_module, "Tag", BadTag)
    field = target_module.TagRelatedField()

    # Act & Assert
    with pytest.raises(RuntimeError) as excinfo:
        field.get_queryset()
    assert "database error" in str(excinfo.value)