import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/signals.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


class DummySender:
    pass


def test_create_related_profile_creates_and_assigns(monkeypatch):
    # Setup a dummy instance
    class UserInstance:
        pass

    instance = UserInstance()

    # Prepare fake profile object to be returned by create
    fake_profile = object()

    # Fake manager to capture calls
    class FakeManager:
        def __init__(self):
            self.called = False
            self.kw = None

        def create(self, **kwargs):
            self.called = True
            self.kw = kwargs
            return fake_profile

    class FakeProfileModel:
        objects = FakeManager()

    # Patch the Profile in the module
    monkeypatch.setattr(target_module, "Profile", FakeProfileModel)

    # Call the signal handler
    target_module.create_related_profile(sender=DummySender, instance=instance, created=True)

    # Assertions: create was called with user=instance and instance.profile set
    assert FakeProfileModel.objects.called is True
    assert FakeProfileModel.objects.kw == {"user": instance}
    assert getattr(instance, "profile") is fake_profile


def test_create_related_profile_does_nothing_when_not_created(monkeypatch):
    class UserInstance:
        pass

    instance = UserInstance()

    # Fake manager that would fail if called
    class FakeManager:
        def create(self, **kwargs):
            raise AssertionError("create should not be called when created=False")

    class FakeProfileModel:
        objects = FakeManager()

    monkeypatch.setattr(target_module, "Profile", FakeProfileModel)

    # Should not raise
    target_module.create_related_profile(sender=DummySender, instance=instance, created=False)

    # instance should not have profile attribute
    assert not hasattr(instance, "profile")


def test_create_related_profile_does_nothing_when_instance_none(monkeypatch):
    # Fake manager that would fail if called
    class FakeManager:
        def create(self, **kwargs):
            raise AssertionError("create should not be called when instance is None")

    class FakeProfileModel:
        objects = FakeManager()

    monkeypatch.setattr(target_module, "Profile", FakeProfileModel)

    # instance is None; should not raise
    target_module.create_related_profile(sender=DummySender, instance=None, created=True)


def test_create_related_profile_propagates_exceptions(monkeypatch):
    class UserInstance:
        pass

    instance = UserInstance()

    class FakeManager:
        def create(self, **kwargs):
            raise ValueError("boom")

    class FakeProfileModel:
        objects = FakeManager()

    monkeypatch.setattr(target_module, "Profile", FakeProfileModel)

    with pytest.raises(ValueError) as excinfo:
        target_module.create_related_profile(sender=DummySender, instance=instance, created=True)

    assert "boom" in str(excinfo.value)


def test_create_related_profile_overwrites_existing_profile(monkeypatch):
    class UserInstance:
        def __init__(self):
            self.profile = "old_profile"

    instance = UserInstance()
    new_profile = object()

    class FakeManager:
        def create(self, **kwargs):
            return new_profile

    class FakeProfileModel:
        objects = FakeManager()

    monkeypatch.setattr(target_module, "Profile", FakeProfileModel)

    # created=True should overwrite existing profile attribute
    target_module.create_related_profile(sender=DummySender, instance=instance, created=True)

    assert instance.profile is new_profile