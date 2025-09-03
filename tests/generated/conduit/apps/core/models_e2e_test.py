import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/models.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)

from django.db import models
from django.core.exceptions import FieldDoesNotExist

def test_is_subclass_of_django_model():
    assert issubclass(target_module.TimestampedModel, models.Model)

def test_has_datetime_fields_with_correct_auto_flags():
    created = target_module.TimestampedModel._meta.get_field('created_at')
    updated = target_module.TimestampedModel._meta.get_field('updated_at')

    assert isinstance(created, models.DateTimeField)
    assert isinstance(updated, models.DateTimeField)

    assert getattr(created, 'auto_now_add', False) is True
    assert getattr(created, 'auto_now', False) is False

    assert getattr(updated, 'auto_now', False) is True
    assert getattr(updated, 'auto_now_add', False) is False

def test_meta_is_abstract_and_has_default_ordering():
    opts = target_module.TimestampedModel._meta
    assert opts.abstract is True
    # ordering may be stored as list/tuple; normalize to list for comparison
    assert list(opts.ordering) == ['-created_at', '-updated_at']

def test_nonexistent_field_raises_field_does_not_exist():
    with pytest.raises(FieldDoesNotExist):
        target_module.TimestampedModel._meta.get_field('this_field_does_not_exist')

def test_field_names_include_created_and_updated():
    field_names = {f.name for f in target_module.TimestampedModel._meta.local_fields}
    assert 'created_at' in field_names
    assert 'updated_at' in field_names