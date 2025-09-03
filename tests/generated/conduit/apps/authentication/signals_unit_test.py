import importlib.util, pathlib
import types
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/signals.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_create_related_profile_creates_profile(monkeypatch):
    class DummyObjects:
        def __init__(self):
            self.called = False
            self.kwargs = None

        def create(self, **kwargs):
            self.called = True
            self.kwargs = kwargs
            return {"id": 1, "user": kwargs.get("user")}

    dummy_objects = DummyObjects()
    dummy_profile_container = types.SimpleNamespace(objects=dummy_objects)
    monkeypatch.setattr(target_module, "Profile", dummy_profile_container)

    class DummyUser:
        pass

    user = DummyUser()
    # Ensure no profile attr initially
    assert not hasattr(user, "profile")

    result = target_module.create_related_profile(sender=target_module, instance=user, created=True)
    # function returns None
    assert result is None

    # Profile.objects.create should have been called with user=user
    assert dummy_objects.called is True
    assert dummy_objects.kwargs == {"user": user}

    # instance.profile should be set to the created profile object
    assert hasattr(user, "profile")
    assert user.profile == {"id": 1, "user": user}


def test_create_related_profile_does_not_create_when_not_created(monkeypatch):
    class DummyObjects:
        def __init__(self):
            self.called = False

        def create(self, **kwargs):
            self.called = True
            return {"id": 2}

    dummy_objects = DummyObjects()
    dummy_profile_container = types.SimpleNamespace(objects=dummy_objects)
    monkeypatch.setattr(target_module, "Profile", dummy_profile_container)

    class DummyUser:
        def __init__(self):
            self.profile = "existing_profile"

    user = DummyUser()

    result = target_module.create_related_profile(sender=target_module, instance=user, created=False)
    assert result is None

    # Should not have called create
    assert dummy_objects.called is False
    # Existing profile should remain unchanged
    assert user.profile == "existing_profile"


def test_create_related_profile_no_action_when_instance_none(monkeypatch):
    class DummyObjects:
        def __init__(self):
            self.called = False

        def create(self, **kwargs):
            self.called = True
            return {"id": 3}

    dummy_objects = DummyObjects()
    dummy_profile_container = types.SimpleNamespace(objects=dummy_objects)
    monkeypatch.setattr(target_module, "Profile", dummy_profile_container)

    # instance is None, created True -> no action
    result = target_module.create_related_profile(sender=target_module, instance=None, created=True)
    assert result is None
    assert dummy_objects.called is False


def test_create_related_profile_propagates_exceptions(monkeypatch):
    class DummyObjects:
        def create(self, **kwargs):
            raise ValueError("creation failed")

    dummy_profile_container = types.SimpleNamespace(objects=DummyObjects())
    monkeypatch.setattr(target_module, "Profile", dummy_profile_container)

    class DummyUser:
        pass

    user = DummyUser()

    with pytest.raises(ValueError, match="creation failed"):
        target_module.create_related_profile(sender=target_module, instance=user, created=True)