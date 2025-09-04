import importlib.util, pathlib, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/relations.py').resolve()
_IMPORT_ERROR = None
try:
    _SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
    target_module = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(target_module)
except Exception as _e:
    _IMPORT_ERROR = str(_e)
    target_module = None
if _IMPORT_ERROR:
    pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}', allow_module_level=True)

from types import SimpleNamespace

class DummyManager:
    def __init__(self, all_return=None, get_or_create_result=None, raise_on_get_or_create=False):
        self.all_called = False
        self.all_return = all_return if all_return is not None else []
        self.get_or_create_called_with = None
        self.get_or_create_result = get_or_create_result
        self.raise_on_get_or_create = raise_on_get_or_create

    def all(self):
        self.all_called = True
        return self.all_return

    def get_or_create(self, **kwargs):
        self.get_or_create_called_with = kwargs
        if self.raise_on_get_or_create:
            raise RuntimeError("simulated DB error")
        if isinstance(self.get_or_create_result, Exception):
            raise self.get_or_create_result
        return self.get_or_create_result

class DummyTag:
    def __init__(self, manager):
        # class attribute objects expected by code; set on class for easy assignment
        self.objects = manager

def test_get_queryset_calls_manager_all(monkeypatch):
    manager = DummyManager(all_return=['t1', 't2'])
    # create a fake Tag class with objects manager
    class FakeTag:
        objects = manager
    monkeypatch.setattr(target_module, 'Tag', FakeTag)
    field = target_module.TagRelatedField()
    result = field.get_queryset()
    assert result == ['t1', 't2']
    assert manager.all_called is True

def test_to_internal_value_returns_created_tag_and_slug(monkeypatch):
    # Prepare a fake tag instance to be returned by get_or_create
    fake_tag_instance = SimpleNamespace(tag='PythonTag', slug='pythontag')
    manager = DummyManager(get_or_create_result=(fake_tag_instance, True))
    class FakeTag:
        objects = manager
    monkeypatch.setattr(target_module, 'Tag', FakeTag)
    field = target_module.TagRelatedField()
    returned = field.to_internal_value('PythonTag')
    assert returned is fake_tag_instance
    # Ensure get_or_create was called with correct args
    assert manager.get_or_create_called_with == {'tag': 'PythonTag', 'slug': 'pythontag'}

def test_to_internal_value_handles_mixed_case_and_spaces(monkeypatch):
    fake_tag_instance = SimpleNamespace(tag='Hello World', slug='hello world')
    manager = DummyManager(get_or_create_result=(fake_tag_instance, False))
    class FakeTag:
        objects = manager
    monkeypatch.setattr(target_module, 'Tag', FakeTag)
    field = target_module.TagRelatedField()
    # spaces and mixed case should be lowered for slug
    returned = field.to_internal_value('Hello World')
    assert returned is fake_tag_instance
    assert manager.get_or_create_called_with == {'tag': 'Hello World', 'slug': 'hello world'}

def test_to_internal_value_propagates_exception(monkeypatch):
    manager = DummyManager(raise_on_get_or_create=True)
    class FakeTag:
        objects = manager
    monkeypatch.setattr(target_module, 'Tag', FakeTag)
    field = target_module.TagRelatedField()
    with pytest.raises(RuntimeError) as exc:
        field.to_internal_value('X')
    assert "simulated DB error" in str(exc.value)

def test_to_internal_value_non_string_data_raises(monkeypatch):
    # If data has no lower() attribute, AttributeError should be raised when trying to call lower()
    fake_tag_instance = SimpleNamespace(tag='ignored', slug='ignored')
    manager = DummyManager(get_or_create_result=(fake_tag_instance, True))
    class FakeTag:
        objects = manager
    monkeypatch.setattr(target_module, 'Tag', FakeTag)
    field = target_module.TagRelatedField()
    with pytest.raises(AttributeError):
        # int has no lower method
        field.to_internal_value(123)

def test_to_representation_returns_tag_value():
    field = target_module.TagRelatedField()
    obj = SimpleNamespace(tag='pytest-tag')
    assert field.to_representation(obj) == 'pytest-tag'

def test_to_representation_missing_tag_raises():
    field = target_module.TagRelatedField()
    class NoTag: pass
    with pytest.raises(AttributeError):
        field.to_representation(NoTag())