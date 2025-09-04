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


def make_dummy_user():
    class DummyUser:
        pass
    return DummyUser()


def test_create_related_profile_creates_profile_when_created_true(monkeypatch):
    # Prepare a dummy user instance
    user = make_dummy_user()
    assert not hasattr(user, 'profile')

    # Prepare a fake Profile.objects.create that records invocation and returns an object
    calls = {}

    class FakeProfileObj:
        def __init__(self, user_passed):
            self.user_passed = user_passed

    class FakeManager:
        @staticmethod
        def create(*args, **kwargs):
            # record that it was called and what was passed
            calls['called'] = True
            calls['args'] = args
            calls['kwargs'] = kwargs
            return FakeProfileObj(kwargs.get('user'))

    class FakeProfile:
        objects = FakeManager()

    # Monkeypatch the Profile in the target module
    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    # Call the signal handler as Django would
    target_module.create_related_profile(sender=object(), instance=user, created=True)

    # Assertions: Profile.objects.create was called once with user=user
    assert calls.get('called') is True
    assert 'user' in calls.get('kwargs', {})
    assert calls['kwargs']['user'] is user

    # The returned profile object was assigned to instance.profile
    assert hasattr(user, 'profile')
    assert isinstance(user.profile, FakeProfileObj)
    assert user.profile.user_passed is user


def test_no_profile_created_when_created_false(monkeypatch):
    user = make_dummy_user()
    assert not hasattr(user, 'profile')

    # Create a fake manager that would raise if called to ensure it's not invoked
    def raise_if_called(*args, **kwargs):
        raise AssertionError("Profile.objects.create should not be called when created is False")

    class FakeManager:
        create = staticmethod(raise_if_called)

    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    # Should not raise
    target_module.create_related_profile(sender=object(), instance=user, created=False)

    # Ensure no profile attribute was set
    assert not hasattr(user, 'profile')


def test_no_profile_created_when_instance_none(monkeypatch):
    # If instance is falsy (None), even if created True, nothing should be called
    calls = {'called': False}

    def create_should_not_be_called(*args, **kwargs):
        calls['called'] = True
        raise AssertionError("Profile.objects.create should not be called when instance is None")

    class FakeManager:
        create = staticmethod(create_should_not_be_called)

    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    # Call with instance None
    target_module.create_related_profile(sender=object(), instance=None, created=True)

    # Ensure create was not called
    assert calls['called'] is False


def test_profile_creation_exception_propagates(monkeypatch):
    user = make_dummy_user()

    # Manager that raises a ValueError to simulate DB error or similar
    def raise_value_error(*args, **kwargs):
        raise ValueError("simulated creation error")

    class FakeManager:
        create = staticmethod(raise_value_error)

    class FakeProfile:
        objects = FakeManager()

    monkeypatch.setattr(target_module, 'Profile', FakeProfile, raising=True)

    # Expect the ValueError to propagate
    with pytest.raises(ValueError) as excinfo:
        target_module.create_related_profile(sender=object(), instance=user, created=True)
    assert "simulated creation error" in str(excinfo.value)

    # Ensure no profile attribute was set on the user after the exception
    assert not hasattr(user, 'profile')