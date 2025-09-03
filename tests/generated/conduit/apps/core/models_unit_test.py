import importlib.util, pathlib
import pytest
from django.db import models

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/models.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_timestampedmodel_is_subclass_of_django_model():
    cls = target_module.TimestampedModel
    assert issubclass(cls, models.Model)


def test_timestampedmodel_has_datetime_fields_with_correct_flags():
    cls = target_module.TimestampedModel

    # Ensure attributes exist on the class
    assert hasattr(cls, 'created_at'), "created_at field is missing"
    assert hasattr(cls, 'updated_at'), "updated_at field is missing"

    created_field = getattr(cls, 'created_at')
    updated_field = getattr(cls, 'updated_at')

    # Fields should be instances of DateTimeField
    assert isinstance(created_field, models.DateTimeField)
    assert isinstance(updated_field, models.DateTimeField)

    # created_at should use auto_now_add and not auto_now
    assert getattr(created_field, 'auto_now_add', False) is True
    assert getattr(created_field, 'auto_now', False) is False

    # updated_at should use auto_now and not auto_now_add
    assert getattr(updated_field, 'auto_now', False) is True
    assert getattr(updated_field, 'auto_now_add', False) is False


def test_meta_class_exists_and_has_expected_attributes():
    cls = target_module.TimestampedModel

    # Meta inner class should exist and be a class
    assert hasattr(cls, 'Meta')
    assert isinstance(getattr(cls, 'Meta'), type)

    meta = cls.Meta

    # Meta should mark the model as abstract
    assert hasattr(meta, 'abstract')
    assert meta.abstract is True

    # Ordering should match the specified reverse-chronological default
    assert hasattr(meta, 'ordering')
    assert meta.ordering == ['-created_at', '-updated_at']


def test_meta_ordering_elements_are_strings_and_non_empty():
    cls = target_module.TimestampedModel
    ordering = cls.Meta.ordering

    assert isinstance(ordering, list)
    assert all(isinstance(item, str) for item in ordering)
    assert all(len(item) > 0 for item in ordering)


def test_can_inherit_and_override_meta_ordering():
    # Dynamically create a subclass that overrides Meta.ordering to ensure typical behavior
    class CustomTimestamp(target_module.TimestampedModel):
        class Meta:
            ordering = ['-updated_at']

    # Ensure the subclass has its own Meta ordering attribute and it's the overridden one
    assert hasattr(CustomTimestamp, 'Meta')
    assert CustomTimestamp.Meta.ordering == ['-updated_at']