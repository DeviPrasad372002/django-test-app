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

class DummyManager:
    def __init__(self, all_return=None, get_or_create_return=None, raise_on_all=False, raise_on_get_or_create=False):
        self._all_return = all_return if all_return is not None else []
        # get_or_create_return may be a tuple (obj, created) or callable
        self._get_or_create_return = get_or_create_return
        self.raise_on_all = raise_on_all
        self.raise_on_get_or_create = raise_on_get_or_create
        self.last_get_or_create_args = None
        self.last_get_or_create_kwargs = None

    def all(self):
        if self.raise_on_all:
            raise RuntimeError("all failed")
        return self._all_return

    def get_or_create(self, *args, **kwargs):
        if self.raise_on_get_or_create:
            raise RuntimeError("get_or_create failed")
        self.last_get_or_create_args = args
        self.last_get_or_create_kwargs = kwargs
        if callable(self._get_or_create_return):
            return self._get_or_create_return(*args, **kwargs)
        return self._get_or_create_return

class FakeTag:
    def __init__(self, tag):
        self.tag = tag
        self.slug = tag.lower()

def make_fake_tag_class(manager):
    class _T:
        objects = manager
    return _T

def test_get_queryset_returns_manager_all(monkeypatch):
    sentinel = ['a', 'b', 'c']
    mgr = DummyManager(all_return=sentinel)
    fake_tag_cls = make_fake_tag_class(mgr)
    monkeypatch.setattr(target_module, 'Tag', fake_tag_cls, raising=False)

    field = target_module.TagRelatedField()
    qs = field.get_queryset()
    assert qs is sentinel

def test_get_queryset_propagates_exception(monkeypatch):
    mgr = DummyManager(raise_on_all=True)
    fake_tag_cls = make_fake_tag_class(mgr)
    monkeypatch.setattr(target_module, 'Tag', fake_tag_cls, raising=False)

    field = target_module.TagRelatedField()
    with pytest.raises(RuntimeError) as exc:
        field.get_queryset()
    assert "all failed" in str(exc.value)

def test_to_internal_value_existing_tag(monkeypatch):
    expected_tag = FakeTag('Python')
    mgr = DummyManager(get_or_create_return=(expected_tag, False))
    fake_tag_cls = make_fake_tag_class(mgr)
    monkeypatch.setattr(target_module, 'Tag', fake_tag_cls, raising=False)

    field = target_module.TagRelatedField()
    result = field.to_internal_value('Python')
    assert result is expected_tag
    # ensure get_or_create called with tag and lowercase slug
    assert mgr.last_get_or_create_kwargs == {'tag': 'Python', 'slug': 'python'}

def test_to_internal_value_created_tag(monkeypatch):
    created_tag = FakeTag('NewTag')
    mgr = DummyManager(get_or_create_return=(created_tag, True))
    fake_tag_cls = make_fake_tag_class(mgr)
    monkeypatch.setattr(target_module, 'Tag', fake_tag_cls, raising=False)

    field = target_module.TagRelatedField()
    result = field.to_internal_value('NewTag')
    assert result is created_tag
    assert mgr.last_get_or_create_kwargs == {'tag': 'NewTag', 'slug': 'newtag'}

def test_to_internal_value_propagates_exception(monkeypatch):
    mgr = DummyManager(raise_on_get_or_create=True)
    fake_tag_cls = make_fake_tag_class(mgr)
    monkeypatch.setattr(target_module, 'Tag', fake_tag_cls, raising=False)

    field = target_module.TagRelatedField()
    with pytest.raises(RuntimeError) as exc:
        field.to_internal_value('X')
    assert "get_or_create failed" in str(exc.value)

def test_to_representation_returns_tag_attribute():
    field = target_module.TagRelatedField()

    class Obj:
        def __init__(self, tag):
            self.tag = tag

    o = Obj('django')
    assert field.to_representation(o) == 'django'

def test_to_representation_missing_attribute_raises():
    field = target_module.TagRelatedField()

    class NoTag:
        pass

    with pytest.raises(AttributeError):
        field.to_representation(NoTag())