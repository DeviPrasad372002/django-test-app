import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/models.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_timestampedmodel_has_datetime_fields_with_correct_flags():
    # Ensure the model defines the expected fields
    created_field = target_module.TimestampedModel._meta.get_field('created_at')
    updated_field = target_module.TimestampedModel._meta.get_field('updated_at')

    # Field types
    assert isinstance(created_field, target_module.models.DateTimeField)
    assert isinstance(updated_field, target_module.models.DateTimeField)

    # auto flags
    assert getattr(created_field, 'auto_now_add', False) is True
    assert getattr(created_field, 'auto_now', False) is False

    assert getattr(updated_field, 'auto_now', False) is True
    # updated_at should not have auto_now_add set
    assert getattr(updated_field, 'auto_now_add', False) is False


def test_metadata_is_abstract_and_has_default_ordering():
    meta = target_module.TimestampedModel._meta

    # The model should be abstract
    assert meta.abstract is True

    # Default ordering should be reverse-chronological by created_at then updated_at
    assert list(meta.ordering) == ['-created_at', '-updated_at']


def test_fields_presence_in_model_field_list():
    field_names = {f.name for f in target_module.TimestampedModel._meta.get_fields()}
    # Ensure both fields are present in the model fields
    assert 'created_at' in field_names
    assert 'updated_at' in field_names

    # No unexpected boolean flags on the model class itself
    assert not hasattr(target_module.TimestampedModel, 'auto_now')
    assert not hasattr(target_module.TimestampedModel, 'auto_now_add')