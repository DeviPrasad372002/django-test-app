import importlib.util, pathlib, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/signals.py').resolve()
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

class _CallRecorder:
    def __init__(self, result=None, exc=None):
        self.calls = []
        self._result = result
        self._exc = exc

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc:
            raise self._exc
        return self._result

def _make_instance():
    class Dummy:
        pass
    return Dummy()

def test_create_related_profile_creates_profile_when_created_true(monkeypatch):
    # Arrange
    inst = _make_instance()
    inst.profile = None

    created_profile = object()
    recorder = _CallRecorder(result=created_profile)
    FakeProfile = type('FakeProfile', (), {'objects': recorder})

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    # Act
    # sender can be anything; pass None for simplicity
    target_module.create_related_profile(sender=None, instance=inst, created=True)

    # Assert
    assert inst.profile is created_profile, "Instance.profile should be set to the created profile"
    assert recorder.calls == [{'user': inst}], "Profile.objects.create should be called once with user=instance"

def test_create_related_profile_does_not_create_when_created_false(monkeypatch):
    # Arrange
    inst = _make_instance()
    inst.profile = 'existing'

    recorder = _CallRecorder(result=object())
    FakeProfile = type('FakeProfile', (), {'objects': recorder})

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    # Act
    target_module.create_related_profile(sender=None, instance=inst, created=False)

    # Assert
    # Should not change existing profile
    assert inst.profile == 'existing'
    assert recorder.calls == [], "Profile.objects.create should not be called when created is False"

def test_create_related_profile_handles_none_instance(monkeypatch):
    # Arrange
    # If instance is falsy, ensure no create is attempted and no exception is raised
    recorder = _CallRecorder(result=object())
    FakeProfile = type('FakeProfile', (), {'objects': recorder})
    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    # Act & Assert: should not raise
    target_module.create_related_profile(sender=None, instance=None, created=True)
    assert recorder.calls == [], "Profile.objects.create should not be called when instance is falsy"

def test_create_related_profile_overwrites_existing_profile_when_created_true(monkeypatch):
    # Arrange
    inst = _make_instance()
    inst.profile = 'old_profile'

    new_profile = object()
    recorder = _CallRecorder(result=new_profile)
    FakeProfile = type('FakeProfile', (), {'objects': recorder})
    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    # Act
    target_module.create_related_profile(sender=None, instance=inst, created=True)

    # Assert
    assert inst.profile is new_profile, "Existing profile should be overwritten when created is True"
    assert recorder.calls == [{'user': inst}]

def test_create_related_profile_propagates_exception_from_create(monkeypatch):
    # Arrange
    inst = _make_instance()
    inst.profile = None

    exc = RuntimeError("create failed")
    recorder = _CallRecorder(result=None, exc=exc)
    FakeProfile = type('FakeProfile', (), {'objects': recorder})
    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    # Act & Assert
    with pytest.raises(RuntimeError, match="create failed"):
        target_module.create_related_profile(sender=None, instance=inst, created=True)
    assert recorder.calls == [{'user': inst}]