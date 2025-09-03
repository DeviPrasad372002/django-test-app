import importlib.util, pathlib
import types
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/signals.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


class DummyInstance:
    def __init__(self):
        self.profile = None


def test_create_related_profile_creates_profile_when_created_true(monkeypatch):
    instance = DummyInstance()
    calls = []

    def fake_create(user):
        calls.append({'user': user})
        return {'id': 1, 'user': user}

    # Replace Profile.objects with a simple namespace having create
    fake_manager = types.SimpleNamespace(create=fake_create)
    monkeypatch.setattr(target_module.Profile, "objects", fake_manager, raising=False)

    result = target_module.create_related_profile(sender=object, instance=instance, created=True)

    # function should return None
    assert result is None
    # create should have been called once with the instance
    assert len(calls) == 1
    assert calls[0]['user'] is instance
    # instance.profile should be set to created profile
    assert instance.profile == {'id': 1, 'user': instance}


def test_create_related_profile_does_nothing_when_created_false(monkeypatch):
    instance = DummyInstance()

    def should_not_be_called(user):
        raise AssertionError("Profile.objects.create should not be called when created=False")

    fake_manager = types.SimpleNamespace(create=should_not_be_called)
    monkeypatch.setattr(target_module.Profile, "objects", fake_manager, raising=False)

    result = target_module.create_related_profile(sender=object, instance=instance, created=False)

    # function should return None and not modify instance.profile
    assert result is None
    assert instance.profile is None


def test_create_related_profile_does_nothing_when_instance_none(monkeypatch):
    def should_not_be_called(user):
        raise AssertionError("Profile.objects.create should not be called when instance is None")

    fake_manager = types.SimpleNamespace(create=should_not_be_called)
    monkeypatch.setattr(target_module.Profile, "objects", fake_manager, raising=False)

    result = target_module.create_related_profile(sender=object, instance=None, created=True)

    assert result is None


def test_create_related_profile_overwrites_existing_profile_when_created_true(monkeypatch):
    instance = DummyInstance()
    instance.profile = "old_profile"
    calls = []

    def fake_create(user):
        calls.append(user)
        return "new_profile_obj"

    fake_manager = types.SimpleNamespace(create=fake_create)
    monkeypatch.setattr(target_module.Profile, "objects", fake_manager, raising=False)

    result = target_module.create_related_profile(sender=object, instance=instance, created=True)

    assert result is None
    assert calls == [instance]
    assert instance.profile == "new_profile_obj"