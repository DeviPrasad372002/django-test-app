import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/signals.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)

class DummyProfileManager:
    def __init__(self, to_return=None, raise_exc=None):
        self.to_return = to_return
        self.raise_exc = raise_exc
        self.called_with = None

    def create(self, user=None):
        self.called_with = user
        if self.raise_exc:
            raise self.raise_exc
        return self.to_return

def make_dummy_profile_class(manager):
    DummyProfile = type('DummyProfile', (), {})
    DummyProfile.objects = manager
    return DummyProfile

class SimpleUser:
    def __init__(self):
        # Start without a profile attribute explicitly set to None
        self.profile = None

def test_creates_profile_on_user_creation(monkeypatch):
    returned_profile = object()
    manager = DummyProfileManager(to_return=returned_profile)
    DummyProfile = make_dummy_profile_class(manager)
    monkeypatch.setattr(target_module, 'Profile', DummyProfile)

    user = SimpleUser()
    # Call the signal handler as if a User was just created
    target_module.create_related_profile(sender='tests', instance=user, created=True)

    assert manager.called_with is user
    assert user.profile is returned_profile

def test_does_not_create_when_instance_is_none(monkeypatch):
    manager = DummyProfileManager(to_return=object())
    DummyProfile = make_dummy_profile_class(manager)
    monkeypatch.setattr(target_module, 'Profile', DummyProfile)

    # instance is falsy (None) so nothing should be created
    target_module.create_related_profile(sender='tests', instance=None, created=True)

    assert manager.called_with is None

def test_does_not_create_when_created_flag_false(monkeypatch):
    manager = DummyProfileManager(to_return=object())
    DummyProfile = make_dummy_profile_class(manager)
    monkeypatch.setattr(target_module, 'Profile', DummyProfile)

    user = SimpleUser()
    user.profile = "existing"
    # created is False, so existing profile should remain and create not called
    target_module.create_related_profile(sender='tests', instance=user, created=False)

    assert manager.called_with is None
    assert user.profile == "existing"

def test_propagates_exception_from_profile_create(monkeypatch):
    exc = RuntimeError("creation failed")
    manager = DummyProfileManager(raise_exc=exc)
    DummyProfile = make_dummy_profile_class(manager)
    monkeypatch.setattr(target_module, 'Profile', DummyProfile)

    user = SimpleUser()
    with pytest.raises(RuntimeError) as ei:
        target_module.create_related_profile(sender='tests', instance=user, created=True)
    assert ei.value is exc
    assert manager.called_with is user

def test_overwrites_profile_attribute_on_creation(monkeypatch):
    returned_profile = {"id": 1}
    manager = DummyProfileManager(to_return=returned_profile)
    DummyProfile = make_dummy_profile_class(manager)
    monkeypatch.setattr(target_module, 'Profile', DummyProfile)

    user = SimpleUser()
    user.profile = "temporary"
    target_module.create_related_profile(sender='tests', instance=user, created=True)

    # Should overwrite previous profile attribute with created profile
    assert user.profile is returned_profile
    assert manager.called_with is user