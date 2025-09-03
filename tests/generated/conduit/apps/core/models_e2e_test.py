import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/models.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)

from django import db
from django.core.exceptions import FieldDoesNotExist


def test_timestampedmodel_is_subclass_of_django_model():
    assert issubclass(target_module.TimestampedModel, db.models.Model)


def test_fields_exist_and_are_datetimefield_instances():
    tm = target_module.TimestampedModel
    created_field = tm._meta.get_field('created_at')
    updated_field = tm._meta.get_field('updated_at')

    # Ensure correct field types
    from django.db.models import DateTimeField
    assert isinstance(created_field, DateTimeField)
    assert isinstance(updated_field, DateTimeField)


def test_auto_now_flags_on_fields():
    tm = target_module.TimestampedModel
    created_field = tm._meta.get_field('created_at')
    updated_field = tm._meta.get_field('updated_at')

    # created_at should have auto_now_add True and auto_now False (or falsy)
    assert getattr(created_field, 'auto_now_add', False) is True
    assert getattr(created_field, 'auto_now', False) is False

    # updated_at should have auto_now True and auto_now_add False (or falsy)
    assert getattr(updated_field, 'auto_now', False) is True
    assert getattr(updated_field, 'auto_now_add', False) is False


def test_meta_is_abstract_and_ordering_defaults():
    tm = target_module.TimestampedModel
    opts = tm._meta

    assert opts.abstract is True
    # ordering should be exactly the list defined in the Meta class
    assert list(opts.ordering) == ['-created_at', '-updated_at']


def test_get_field_raises_for_missing_field():
    tm = target_module.TimestampedModel
    with pytest.raises(FieldDoesNotExist):
        tm._meta.get_field('this_field_does_not_exist_123')


def test_subclass_inherits_fields_and_ordering_and_is_concrete():
    # Create a concrete subclass of the abstract base model
    class ConcreteTimestampModel(target_module.TimestampedModel):
        class Meta:
            # Do not mark this subclass abstract so it becomes concrete
            abstract = False

    opts = ConcreteTimestampModel._meta

    # The subclass should not be abstract
    assert opts.abstract is False

    # It should inherit the ordering from the abstract base by default
    assert list(opts.ordering) == ['-created_at', '-updated_at']

    # The subclass should have the same datetime fields with same flags
    created_field = opts.get_field('created_at')
    updated_field = opts.get_field('updated_at')

    from django.db.models import DateTimeField
    assert isinstance(created_field, DateTimeField)
    assert isinstance(updated_field, DateTimeField)
    assert getattr(created_field, 'auto_now_add', False) is True
    assert getattr(updated_field, 'auto_now', False) is True