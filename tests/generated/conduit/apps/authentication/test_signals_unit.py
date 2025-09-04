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

# Ensure required symbols exist in the imported module
_missing = []
if not hasattr(target_module, 'create_related_profile'):
    _missing.append('create_related_profile')
if not hasattr(target_module, 'Profile'):
    _missing.append('Profile')
if _missing:
    pytest.skip(f'Missing symbols in target module: {", ".join(_missing)}', allow_module_level=True)

from types import SimpleNamespace

def test_create_related_profile_creates_and_assigns(monkeypatch):
    # Arrange
    class DummyUser:
        pass
    instance = DummyUser()
    created_profile = object()
    called = {}

    def fake_create(user):
        # verify the user passed is the instance
        assert user is instance
        called['was_called'] = True
        return created_profile

    fake_objects = SimpleNamespace(create=fake_create)
    fake_Profile = SimpleNamespace(objects=fake_objects)

    monkeypatch.setattr(target_module, 'Profile', fake_Profile)

    # Act
    result = target_module.create_related_profile(sender=None, instance=instance, created=True)

    # Assert
    assert result is None  # function returns None
    assert called.get('was_called', False) is True
    assert hasattr(instance, 'profile')
    assert instance.profile is created_profile

def test_create_related_profile_does_not_create_when_created_false(monkeypatch):
    # Arrange
    class DummyUser:
        pass
    instance = DummyUser()

    def fake_create(user):
        raise AssertionError("Profile.objects.create should not be called when created=False")

    fake_objects = SimpleNamespace(create=fake_create)
    fake_Profile = SimpleNamespace(objects=fake_objects)
    monkeypatch.setattr(target_module, 'Profile', fake_Profile)

    # Act
    result = target_module.create_related_profile(sender=None, instance=instance, created=False)

    # Assert
    assert result is None
    # profile should not be set
    assert not hasattr(instance, 'profile')

def test_create_related_profile_handles_none_instance_without_call(monkeypatch):
    # Arrange
    called = {'count': 0}

    def fake_create(user):
        called['count'] += 1
        return object()

    fake_objects = SimpleNamespace(create=fake_create)
    fake_Profile = SimpleNamespace(objects=fake_objects)
    monkeypatch.setattr(target_module, 'Profile', fake_Profile)

    # Act
    result = target_module.create_related_profile(sender=None, instance=None, created=True)

    # Assert
    assert result is None
    assert called['count'] == 0

def test_create_related_profile_propagates_exceptions_from_create(monkeypatch):
    # Arrange
    class DummyUser:
        pass
    instance = DummyUser()

    def fake_create(user):
        raise ValueError("creation failed")

    fake_objects = SimpleNamespace(create=fake_create)
    fake_Profile = SimpleNamespace(objects=fake_objects)
    monkeypatch.setattr(target_module, 'Profile', fake_Profile)

    # Act & Assert
    with pytest.raises(ValueError, match="creation failed"):
        target_module.create_related_profile(sender=None, instance=instance, created=True)

def test_create_related_profile_accepts_extra_args_and_kwargs(monkeypatch):
    # Arrange
    class DummyUser:
        pass
    instance = DummyUser()
    created_profile = object()
    recorded = {}

    def fake_create(user):
        recorded['user'] = user
        return created_profile

    fake_objects = SimpleNamespace(create=fake_create)
    fake_Profile = SimpleNamespace(objects=fake_objects)
    monkeypatch.setattr(target_module, 'Profile', fake_Profile)

    # Provide extra positional and keyword arguments to simulate signal behavior
    result = target_module.create_related_profile(None, instance, True, 'extra_arg', another_kw='value')

    # Assert
    assert result is None
    assert recorded.get('user') is instance
    assert instance.profile is created_profile