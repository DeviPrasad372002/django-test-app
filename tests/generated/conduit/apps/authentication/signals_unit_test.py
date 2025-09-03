import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/signals.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_create_related_profile_creates_profile_when_created_true_and_instance_provided(monkeypatch):
    class DummyInstance:
        pass

    created_calls = []

    class FakeManager:
        @staticmethod
        def create(user):
            created_calls.append({'user': user})
            return {'profile_for': user}

    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile)

    inst = DummyInstance()
    result = target_module.create_related_profile(sender=None, instance=inst, created=True)
    assert result is None
    assert hasattr(inst, 'profile')
    assert inst.profile == {'profile_for': inst}
    assert created_calls == [{'user': inst}]


def test_create_related_profile_no_action_when_created_false(monkeypatch):
    class DummyInstance:
        pass

    called = {'flag': False}

    class FakeManager:
        @staticmethod
        def create(user):
            called['flag'] = True
            return None

    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile)

    inst = DummyInstance()
    result = target_module.create_related_profile(sender=None, instance=inst, created=False)
    assert result is None
    # No profile attribute should be set and manager.create should not have been called
    assert not hasattr(inst, 'profile')
    assert called['flag'] is False


def test_create_related_profile_no_action_when_instance_none(monkeypatch):
    called = {'flag': False}

    class FakeManager:
        @staticmethod
        def create(user):
            called['flag'] = True
            return None

    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile)

    result = target_module.create_related_profile(sender=None, instance=None, created=True)
    assert result is None
    assert called['flag'] is False


def test_create_related_profile_overwrites_existing_profile(monkeypatch):
    class DummyInstance:
        def __init__(self):
            self.profile = 'old_profile'

    class FakeManager:
        @staticmethod
        def create(user):
            return 'new_profile'

    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile)

    inst = DummyInstance()
    target_module.create_related_profile(sender=None, instance=inst, created=True)
    assert inst.profile == 'new_profile'


def test_create_related_profile_propagates_exception_from_create(monkeypatch):
    class DummyInstance:
        pass

    class FakeManager:
        @staticmethod
        def create(user):
            raise ValueError("creation failed")

    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile)

    inst = DummyInstance()
    with pytest.raises(ValueError, match="creation failed"):
        target_module.create_related_profile(sender=None, instance=inst, created=True)