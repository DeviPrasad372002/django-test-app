import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/relations.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


class FakeManager:
    def __init__(self, all_result=None, existing=None):
        # all_result: value to return from all()
        # existing: dict mapping tag->Tag instance representing existing records
        self._all_result = all_result if all_result is not None else []
        self.existing = existing if existing is not None else {}
        self.last_get_or_create_call = None

    def all(self):
        return self._all_result

    def get_or_create(self, tag, slug):
        # record call
        self.last_get_or_create_call = {'tag': tag, 'slug': slug}
        if tag in self.existing:
            return self.existing[tag], False
        # create new FakeTag
        new = FakeTag(tag=tag, slug=slug)
        # populate existing for subsequent calls
        self.existing[tag] = new
        return new, True


class FakeTag:
    def __init__(self, tag, slug):
        self.tag = tag
        self.slug = slug


def setup_fake_tag_on_module(monkeypatch, *, all_result=None, existing=None):
    manager = FakeManager(all_result=all_result, existing=existing)
    fake_tag_cls = type("Tag", (), {})  # simple class to attach objects
    fake_tag_cls.objects = manager
    monkeypatch.setattr(target_module, "Tag", fake_tag_cls)
    return manager, fake_tag_cls


def test_get_queryset_returns_manager_all(monkeypatch):
    sentinel = ['a', 'b', 'c']
    manager, fake_tag_cls = setup_fake_tag_on_module(monkeypatch, all_result=sentinel)
    field = target_module.TagRelatedField()
    result = field.get_queryset()
    assert result is sentinel
    # ensure underlying manager all() was used
    assert manager._all_result == sentinel


def test_to_internal_value_creates_tag_and_uses_lowercase_slug(monkeypatch):
    manager, fake_tag_cls = setup_fake_tag_on_module(monkeypatch, all_result=[])
    field = target_module.TagRelatedField()
    tag_input = "PyTest"
    returned = field.to_internal_value(tag_input)
    # returned should be a FakeTag instance
    assert isinstance(returned, FakeTag)
    assert returned.tag == tag_input
    # slug should be lowercased
    assert returned.slug == tag_input.lower()
    # manager recorded the call with correct slug lowercased
    assert manager.last_get_or_create_call == {'tag': tag_input, 'slug': tag_input.lower()}


def test_to_internal_value_returns_existing_tag_when_present(monkeypatch):
    # prepare an existing tag
    existing_tag = FakeTag(tag="existing", slug="existing")
    manager, fake_tag_cls = setup_fake_tag_on_module(monkeypatch, existing={"existing": existing_tag})
    field = target_module.TagRelatedField()
    returned = field.to_internal_value("existing")
    # should return the same existing instance and created flag False behavior is internal
    assert returned is existing_tag
    assert manager.last_get_or_create_call == {'tag': 'existing', 'slug': 'existing'}


def test_to_internal_value_raises_on_non_string(monkeypatch):
    manager, fake_tag_cls = setup_fake_tag_on_module(monkeypatch)
    field = target_module.TagRelatedField()
    # passing a non-string (int) will cause .lower() to not exist -> AttributeError
    with pytest.raises(AttributeError):
        field.to_internal_value(123)


def test_to_representation_returns_tag_attribute():
    field = target_module.TagRelatedField()
    value = FakeTag(tag="python", slug="python")
    result = field.to_representation(value)
    assert result == "python"


def test_to_representation_missing_tag_attribute_raises():
    field = target_module.TagRelatedField()

    class NoTag:
        pass

    with pytest.raises(AttributeError):
        field.to_representation(NoTag())