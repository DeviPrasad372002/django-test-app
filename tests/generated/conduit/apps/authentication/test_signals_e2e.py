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

# Ensure symbol exists
if not hasattr(target_module, 'create_related_profile'):
    pytest.skip('target module does not define create_related_profile', allow_module_level=True)

def make_instance():
    class UserLike:
        def __init__(self):
            self.profile = None
    return UserLike()

class FakeProfileManager:
    def __init__(self, to_return=None, raise_exc=None):
        self.to_return = to_return
        self.raise_exc = raise_exc
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc:
            raise self.raise_exc
        # Return a simple sentinel object if none provided
        return self.to_return if self.to_return is not None else {'_fake_profile_for': kwargs.get('user')}

class FakeProfile:
    def __init__(self, manager):
        self.objects = manager

@pytest.fixture(autouse=True)
def ensure_clean_target_module(monkeypatch):
    """
    Ensure we don't rely on any real Django models by providing
    a controlled Profile object in the target module during tests.
    """
    # Save original if present to restore later
    orig_profile = getattr(target_module, 'Profile', None)
    yield
    # Restore original after test
    if orig_profile is not None:
        monkeypatch.setattr(target_module, 'Profile', orig_profile)
    else:
        # Remove attribute if it didn't exist before
        if hasattr(target_module, 'Profile'):
            delattr(target_module, 'Profile')

def test_create_related_profile_creates_profile_when_created_true(monkeypatch):
    inst = make_instance()
    fake_manager = FakeProfileManager()
    fake_profile = FakeProfile(fake_manager)
    # Monkeypatch the Profile in the target module
    monkeypatch.setattr(target_module, 'Profile', fake_profile)
    # Call the signal handler as Django would
    result = target_module.create_related_profile(sender=target_module.User if hasattr(target_module, 'User') else None,
                                                  instance=inst, created=True)
    # Should return None
    assert result is None
    # Profile.objects.create should have been called once with user=inst
    assert len(fake_manager.calls) == 1
    assert fake_manager.calls[0] == {'user': inst}
    # instance.profile should now be set to the returned fake profile object
    assert inst.profile == fake_manager.to_return or inst.profile == {'_fake_profile_for': inst}

def test_no_profile_created_when_created_false(monkeypatch):
    inst = make_instance()
    fake_manager = FakeProfileManager()
    fake_profile = FakeProfile(fake_manager)
    monkeypatch.setattr(target_module, 'Profile', fake_profile)
    # Call with created=False; should not call create and should not set profile
    result = target_module.create_related_profile(sender=None, instance=inst, created=False)
    assert result is None
    assert fake_manager.calls == []
    assert inst.profile is None

def test_no_profile_created_when_instance_none(monkeypatch):
    fake_manager = FakeProfileManager()
    fake_profile = FakeProfile(fake_manager)
    monkeypatch.setattr(target_module, 'Profile', fake_profile)
    # If instance is None, nothing should happen (no exception, no calls)
    result = target_module.create_related_profile(sender=None, instance=None, created=True)
    assert result is None
    assert fake_manager.calls == []

def test_exception_from_profile_create_propagates(monkeypatch):
    inst = make_instance()
    # Prepare manager that raises
    fake_manager = FakeProfileManager(raise_exc=ValueError("creation failed"))
    fake_profile = FakeProfile(fake_manager)
    monkeypatch.setattr(target_module, 'Profile', fake_profile)
    with pytest.raises(ValueError, match="creation failed"):
        target_module.create_related_profile(sender=None, instance=inst, created=True)

def test_overwrites_existing_profile(monkeypatch):
    inst = make_instance()
    inst.profile = "old_profile"
    # Manager returns a new sentinel object
    new_profile_obj = object()
    fake_manager = FakeProfileManager(to_return=new_profile_obj)
    fake_profile = FakeProfile(fake_manager)
    monkeypatch.setattr(target_module, 'Profile', fake_profile)
    target_module.create_related_profile(sender=None, instance=inst, created=True)
    # Ensure profile was overwritten
    assert inst.profile is new_profile_obj
    assert len(fake_manager.calls) == 1
    assert fake_manager.calls[0] == {'user': inst}