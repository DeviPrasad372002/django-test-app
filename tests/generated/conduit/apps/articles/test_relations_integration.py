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

class _FakeTag:
    def __init__(self, tag, slug=None):
        self.tag = tag
        self.slug = slug if slug is not None else (tag.lower() if isinstance(tag, str) else None)

class _FakeManager:
    def __init__(self):
        self.all_value = ['SENTINEL_ALL']
        self.get_or_create_result = (_FakeTag('default'), True)
        self.last_get_or_create_kwargs = None

    def all(self):
        return self.all_value

    def get_or_create(self, **kwargs):
        # store kwargs and return preset result
        self.last_get_or_create_kwargs = kwargs
        return self.get_or_create_result

class _FakeTagModel:
    def __init__(self, manager):
        # expose objects attribute like Django model
        self.objects = manager

@pytest.fixture
def fake_manager():
    return _FakeManager()

@pytest.fixture
def patch_tag_model(monkeypatch, fake_manager):
    """
    Monkeypatch target_module.Tag to a fake model exposing .objects manager.
    Provides ability to adjust get_or_create_result on the manager.
    """
    fake_model = _FakeTagModel(fake_manager)
    monkeypatch.setattr(target_module, 'Tag', fake_model, raising=False)
    return fake_manager

def test_get_queryset_returns_manager_all(patch_tag_model):
    field = target_module.TagRelatedField()
    # ensure get_queryset returns exactly the manager.all() value
    result = field.get_queryset()
    assert result == patch_tag_model.all_value

def test_to_internal_value_creates_new_tag_when_created(monkeypatch, patch_tag_model):
    # Prepare manager to return a created tag tuple
    created_tag = _FakeTag('Python', 'python')
    patch_tag_model.get_or_create_result = (created_tag, True)

    field = target_module.TagRelatedField()
    returned = field.to_internal_value('Python')

    # It should return the tag instance and call get_or_create with proper kwargs
    assert returned is created_tag
    assert patch_tag_model.last_get_or_create_kwargs == {'tag': 'Python', 'slug': 'python'}

def test_to_internal_value_returns_existing_tag_when_not_created(monkeypatch, patch_tag_model):
    existing_tag = _FakeTag('Existing', 'existing')
    patch_tag_model.get_or_create_result = (existing_tag, False)

    field = target_module.TagRelatedField()
    returned = field.to_internal_value('Existing')

    assert returned is existing_tag
    assert patch_tag_model.last_get_or_create_kwargs == {'tag': 'Existing', 'slug': 'existing'}

def test_to_internal_value_non_string_raises_attribute_error(patch_tag_model):
    field = target_module.TagRelatedField()
    # Passing non-string (int) should error when calling lower()
    with pytest.raises(AttributeError):
        field.to_internal_value(123)

def test_to_representation_returns_tag_property():
    field = target_module.TagRelatedField()
    value = _FakeTag('Django', 'django')
    assert field.to_representation(value) == 'Django'

def test_to_representation_missing_tag_attribute_raises():
    field = target_module.TagRelatedField()
    class NoTag: pass
    with pytest.raises(AttributeError):
        field.to_representation(NoTag())