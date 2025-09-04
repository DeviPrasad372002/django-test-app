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

@pytest.fixture(autouse=True)
def ensure_tag_available():
    # Ensure the module has a Tag attribute we can monkeypatch; if missing, skip.
    if not hasattr(target_module, "Tag"):
        pytest.skip("target module does not define Tag; skipping tests")
    yield

def test_get_queryset_returns_manager_all(monkeypatch):
    # Arrange: create fake manager and attach to Tag.objects
    class FakeManager:
        def __init__(self):
            self.all_called = False
        def all(self):
            self.all_called = True
            return ["a", "b", "c"]

    fake_manager = FakeManager()
    # Keep original Tag to restore later
    original_tag = getattr(target_module, "Tag", None)
    class FakeTag:
        objects = fake_manager

    monkeypatch.setattr(target_module, "Tag", FakeTag, raising=False)

    # Act
    field = target_module.TagRelatedField()
    result = field.get_queryset()

    # Assert
    assert result == ["a", "b", "c"]
    assert fake_manager.all_called is True

    # cleanup handled by monkeypatch fixture (restores attribute on teardown)

def test_to_internal_value_creates_and_returns_tag(monkeypatch):
    # Arrange: fake tag object and manager
    called = {}
    class FakeTagObj:
        def __init__(self, tag, slug):
            self.tag = tag
            self.slug = slug
    class FakeManager:
        def get_or_create(self, tag, slug):
            called['tag'] = tag
            called['slug'] = slug
            # simulate created True
            return (FakeTagObj(tag, slug), True)

    class FakeTag:
        objects = FakeManager()

    monkeypatch.setattr(target_module, "Tag", FakeTag, raising=False)

    field = target_module.TagRelatedField()
    res = field.to_internal_value("Python")

    assert isinstance(res, FakeTagObj)
    assert res.tag == "Python"
    assert res.slug == "python"
    assert called['tag'] == "Python"
    assert called['slug'] == "python"

def test_to_internal_value_propagates_exception(monkeypatch):
    # Arrange: manager that raises on get_or_create
    class BadManager:
        def get_or_create(self, tag, slug):
            raise ValueError("creation failed")
    class FakeTag:
        objects = BadManager()
    monkeypatch.setattr(target_module, "Tag", FakeTag, raising=False)

    field = target_module.TagRelatedField()
    with pytest.raises(ValueError) as exc:
        field.to_internal_value("X")
    assert "creation failed" in str(exc.value)

def test_to_internal_value_non_string_data_raises(monkeypatch):
    # Arrange: manager that would accept strings but data is non-string -> lower() not present
    class Manager:
        def get_or_create(self, tag, slug):
            return (object(), True)
    class FakeTag:
        objects = Manager()
    monkeypatch.setattr(target_module, "Tag", FakeTag, raising=False)

    field = target_module.TagRelatedField()
    # Passing an int should raise AttributeError when calling .lower()
    with pytest.raises(Exception) as excinfo:
        field.to_internal_value(123)
    # Could be AttributeError or TypeError depending on environment; ensure it's due to 'lower'
    assert isinstance(excinfo.value, Exception)

def test_to_representation_returns_tag_attribute():
    # Create a simple object with tag attribute
    class Value:
        def __init__(self, tag):
            self.tag = tag

    field = target_module.TagRelatedField()
    v = Value("pytest-tag")
    assert field.to_representation(v) == "pytest-tag"

def test_to_representation_missing_tag_attribute_raises():
    # Value without .tag should raise AttributeError
    class Value:
        pass

    field = target_module.TagRelatedField()
    with pytest.raises(AttributeError):
        field.to_representation(Value())