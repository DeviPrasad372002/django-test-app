import importlib.util, pathlib
import types
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/relations.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


class _FakeObjects:
    def __init__(self, items=None):
        self._items = [] if items is None else list(items)
        self.last_get_or_create_kwargs = None
        self._next_created = True

    def all(self):
        return self._items

    def get_or_create(self, tag, slug):
        # record call and return a simple object
        self.last_get_or_create_kwargs = {'tag': tag, 'slug': slug}
        obj = types.SimpleNamespace(tag=tag, slug=slug)
        return obj, self._next_created


class _FakeTag:
    def __init__(self, items=None):
        self.objects = _FakeObjects(items)


def test_get_queryset_returns_objects_all(monkeypatch):
    fake = _FakeTag(items=['a', 'b', 'c'])
    monkeypatch.setattr(target_module, 'Tag', fake)
    field = target_module.TagRelatedField()
    result = field.get_queryset()
    assert result == ['a', 'b', 'c']

def test_to_internal_value_calls_get_or_create_and_returns_tag(monkeypatch):
    fake = _FakeTag()
    monkeypatch.setattr(target_module, 'Tag', fake)
    field = target_module.TagRelatedField()

    # provide a string; slug should be lowercased
    data = "PythonTag"
    tag_obj = field.to_internal_value(data)
    assert hasattr(tag_obj, 'tag')
    assert hasattr(tag_obj, 'slug')
    assert tag_obj.tag == data
    assert tag_obj.slug == data.lower()
    # confirm objects.get_or_create recorded the expected kwargs
    assert fake.objects.last_get_or_create_kwargs == {'tag': data, 'slug': data.lower()}

def test_to_internal_value_non_string_raises_attribute_error(monkeypatch):
    fake = _FakeTag()
    monkeypatch.setattr(target_module, 'Tag', fake)
    field = target_module.TagRelatedField()
    with pytest.raises(AttributeError):
        # integers do not have .lower(), so should raise AttributeError
        field.to_internal_value(123)

def test_to_representation_returns_tag_attribute():
    field = target_module.TagRelatedField()
    value = types.SimpleNamespace(tag='django')
    result = field.to_representation(value)
    assert result == 'django'

def test_to_representation_missing_tag_attribute_raises(monkeypatch):
    field = target_module.TagRelatedField()
    value = object()
    with pytest.raises(AttributeError):
        field.to_representation(value)