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

from types import SimpleNamespace

def test_function_is_exposed_and_callable():
    assert hasattr(target_module, 'create_related_profile')
    assert callable(target_module.create_related_profile)
    # Name should remain the original function name
    assert target_module.create_related_profile.__name__ == 'create_related_profile'

def test_no_instance_does_not_call_create(monkeypatch):
    # Prepare a Profile that would fail if create is called
    called = {'flag': False}
    class FakeManager:
        def create(self, **kwargs):
            called['flag'] = True
            raise RuntimeError("Should not be called")
    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    # Calling with instance=None should do nothing and not raise
    target_module.create_related_profile(sender=None, instance=None, created=True)
    assert called['flag'] is False

def test_created_false_does_not_call_create(monkeypatch):
    called = {'flag': False}
    class FakeManager:
        def create(self, **kwargs):
            called['flag'] = True
            raise RuntimeError("Should not be called")
    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    instance = SimpleNamespace()
    # created is False, so should not create profile
    target_module.create_related_profile(sender=None, instance=instance, created=False)
    assert called['flag'] is False
    # instance should not have profile attribute set
    assert not hasattr(instance, 'profile')

def test_created_true_calls_create_and_sets_profile(monkeypatch):
    calls = []
    returned_obj = object()
    class FakeManager:
        def create(self, **kwargs):
            calls.append(kwargs)
            return returned_obj
    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    instance = SimpleNamespace()
    target_module.create_related_profile(sender=None, instance=instance, created=True)
    # Ensure create called once with user=instance
    assert len(calls) == 1
    assert 'user' in calls[0]
    assert calls[0]['user'] is instance
    # Ensure instance.profile set to returned object
    assert hasattr(instance, 'profile')
    assert instance.profile is returned_obj

def test_created_true_overwrites_existing_profile(monkeypatch):
    calls = []
    returned_obj = object()
    class FakeManager:
        def create(self, **kwargs):
            calls.append(kwargs)
            return returned_obj
    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    instance = SimpleNamespace(profile='old')
    target_module.create_related_profile(sender=None, instance=instance, created=True)
    assert len(calls) == 1
    assert instance.profile is returned_obj
    assert instance.profile != 'old'

def test_accepts_extra_args_and_kwargs(monkeypatch):
    calls = []
    returned_obj = object()
    class FakeManager:
        def create(self, **kwargs):
            calls.append(kwargs)
            return returned_obj
    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    instance = SimpleNamespace()
    # pass extra positional and keyword args; function should ignore them but accept them
    target_module.create_related_profile(None, instance, True, 'extra', some_kw='value')
    assert len(calls) == 1
    assert calls[0]['user'] is instance
    assert instance.profile is returned_obj

def test_exception_from_create_propagates(monkeypatch):
    class FakeManager:
        def create(self, **kwargs):
            raise ValueError("creation failed")
    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    instance = SimpleNamespace()
    with pytest.raises(ValueError) as excinfo:
        target_module.create_related_profile(sender=None, instance=instance, created=True)
    assert "creation failed" in str(excinfo.value)