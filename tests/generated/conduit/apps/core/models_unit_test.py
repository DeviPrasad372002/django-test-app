import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/models.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_timestampedmodel_is_subclass_of_django_model():
    assert hasattr(target_module, "TimestampedModel")
    assert issubclass(target_module.TimestampedModel, target_module.models.Model)


def test_timestampedmodel_is_abstract():
    # Django model options are available via _meta
    opts = target_module.TimestampedModel._meta
    assert opts.abstract is True


def test_timestampedmodel_ordering_defaults():
    opts = target_module.TimestampedModel._meta
    ordering = opts.ordering
    # Ensure ordering is defined and has the expected fields in order
    assert ordering == ['-created_at', '-updated_at']
    assert isinstance(ordering, (list, tuple))
    assert len(ordering) == 2
    assert ordering[0] == '-created_at'
    assert ordering[1] == '-updated_at'


def test_timestampedmodel_has_datetime_fields_with_correct_flags():
    opts = target_module.TimestampedModel._meta

    created_field = opts.get_field('created_at')
    updated_field = opts.get_field('updated_at')

    # Check field classes
    assert isinstance(created_field, target_module.models.DateTimeField)
    assert isinstance(updated_field, target_module.models.DateTimeField)

    # Check auto flags
    assert getattr(created_field, 'auto_now_add', False) is True
    assert getattr(updated_field, 'auto_now', False) is True

    # auto fields are not editable
    assert getattr(created_field, 'editable', True) is False
    assert getattr(updated_field, 'editable', True) is False


def test_requesting_nonexistent_field_raises_field_error():
    opts = target_module.TimestampedModel._meta
    with pytest.raises(Exception):
        # Use a clearly non-existent field name; Meta.get_field should raise
        opts.get_field('this_field_does_not_exist')