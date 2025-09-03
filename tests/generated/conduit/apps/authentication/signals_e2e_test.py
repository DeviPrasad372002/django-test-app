import importlib.util, pathlib
import pytest
from unittest.mock import Mock

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/signals.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_no_instance_does_not_create_profile(monkeypatch):
    # Arrange
    mock_create = Mock()
    mock_profile_model = Mock()
    mock_profile_model.objects.create = mock_create
    monkeypatch.setattr(target_module, 'Profile', mock_profile_model)

    # Act
    result = target_module.create_related_profile(sender=object(), instance=None, created=True)

    # Assert
    mock_create.assert_not_called()
    assert result is None


def test_not_created_does_not_create_profile(monkeypatch):
    # Arrange
    mock_create = Mock()
    mock_profile_model = Mock()
    mock_profile_model.objects.create = mock_create
    monkeypatch.setattr(target_module, 'Profile', mock_profile_model)
    instance = object()

    # Act
    result = target_module.create_related_profile(sender=object(), instance=instance, created=False)

    # Assert
    mock_create.assert_not_called()
    assert result is None


def test_created_creates_and_attaches_profile(monkeypatch):
    # Arrange
    instance = Mock()
    profile_obj = Mock()
    mock_create = Mock(return_value=profile_obj)
    mock_profile_model = Mock()
    mock_profile_model.objects.create = mock_create
    monkeypatch.setattr(target_module, 'Profile', mock_profile_model)

    # Act
    result = target_module.create_related_profile(sender=object(), instance=instance, created=True)

    # Assert
    mock_create.assert_called_once_with(user=instance)
    assert getattr(instance, 'profile') is profile_obj
    assert result is None


def test_exception_propagates_and_does_not_set_profile(monkeypatch):
    # Arrange
    instance = Mock()
    def raise_error(**kwargs):
        raise RuntimeError("db failure")
    mock_profile_model = Mock()
    mock_profile_model.objects.create = Mock(side_effect=raise_error)
    monkeypatch.setattr(target_module, 'Profile', mock_profile_model)

    # Act / Assert
    with pytest.raises(RuntimeError) as excinfo:
        target_module.create_related_profile(sender=object(), instance=instance, created=True)
    assert "db failure" in str(excinfo.value)
    assert not hasattr(instance, 'profile')


def test_existing_profile_is_replaced_on_create(monkeypatch):
    # Arrange
    instance = Mock()
    instance.profile = "old_profile"
    new_profile = "new_profile"
    mock_create = Mock(return_value=new_profile)
    mock_profile_model = Mock()
    mock_profile_model.objects.create = mock_create
    monkeypatch.setattr(target_module, 'Profile', mock_profile_model)

    # Act
    target_module.create_related_profile(sender=object(), instance=instance, created=True)

    # Assert
    mock_create.assert_called_once_with(user=instance)
    assert instance.profile == new_profile