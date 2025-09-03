import importlib.util, pathlib
import pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/models.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def _get_field_or_meta_field(model_cls, field_name):
    # Prefer direct attribute if it's a Field instance; otherwise try Django _meta.
    attr = getattr(model_cls, field_name, None)
    if isinstance(attr, target_module.models.Field):
        return attr
    # Fallback to _meta if available
    meta = getattr(model_cls, '_meta', None)
    if meta is not None:
        try:
            return meta.get_field(field_name)
        except Exception:
            return None
    return None


def test_timestampedmodel_is_subclass_of_django_model():
    assert issubclass(target_module.TimestampedModel, target_module.models.Model)


def test_created_at_field_is_datetime_and_auto_now_add_true():
    field = _get_field_or_meta_field(target_module.TimestampedModel, 'created_at')
    assert field is not None, "created_at field not found on TimestampedModel"
    assert isinstance(field, target_module.models.DateTimeField)
    # created_at should be auto_now_add=True and not auto_now
    assert bool(getattr(field, 'auto_now_add', False)) is True
    assert bool(getattr(field, 'auto_now', False)) is False


def test_updated_at_field_is_datetime_and_auto_now_true():
    field = _get_field_or_meta_field(target_module.TimestampedModel, 'updated_at')
    assert field is not None, "updated_at field not found on TimestampedModel"
    assert isinstance(field, target_module.models.DateTimeField)
    # updated_at should be auto_now=True and not auto_now_add
    assert bool(getattr(field, 'auto_now', False)) is True
    assert bool(getattr(field, 'auto_now_add', False)) is False


def test_meta_inner_class_exists_and_is_abstract_with_ordering():
    meta = getattr(target_module.TimestampedModel, 'Meta', None)
    assert meta is not None, "Meta inner class missing on TimestampedModel"
    # Meta should declare abstract = True
    assert hasattr(meta, 'abstract'), "Meta missing 'abstract' attribute"
    assert getattr(meta, 'abstract') is True
    # ordering should be the expected list
    assert hasattr(meta, 'ordering'), "Meta missing 'ordering' attribute"
    ordering = getattr(meta, 'ordering')
    assert isinstance(ordering, (list, tuple))
    assert list(ordering) == ['-created_at', '-updated_at']


def test_model_meta_fields_include_timestamp_fields_if_meta_available():
    meta = getattr(target_module.TimestampedModel, '_meta', None)
    if meta is None:
        pytest.skip("_meta not available on TimestampedModel in this environment")
    names = [getattr(f, 'name', None) for f in meta.get_fields()]
    assert 'created_at' in names
    assert 'updated_at' in names


def test_field_attributes_do_not_mutate_ordering_list():
    # Ensure that accessing field attributes does not change Meta.ordering
    meta = getattr(target_module.TimestampedModel, 'Meta', None)
    assert meta is not None
    before = list(getattr(meta, 'ordering'))
    # Access field attrs
    _ = _get_field_or_meta_field(target_module.TimestampedModel, 'created_at')
    _ = _get_field_or_meta_field(target_module.TimestampedModel, 'updated_at')
    after = list(getattr(meta, 'ordering'))
    assert before == after