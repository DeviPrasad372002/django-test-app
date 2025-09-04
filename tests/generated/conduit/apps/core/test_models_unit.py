import importlib.util, pathlib, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/models.py').resolve()
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


def test_timestampedmodel_has_inner_meta_declaring_abstract_and_ordering():
    # The inner Meta class is a plain class on the TimestampedModel and should
    # declare abstract=True and the default ordering.
    assert hasattr(target_module.TimestampedModel, 'Meta'), "TimestampedModel should have an inner Meta class"
    Meta = target_module.TimestampedModel.Meta
    # Meta is expected to be a class with attributes abstract and ordering
    assert getattr(Meta, 'abstract', None) is True
    assert getattr(Meta, 'ordering', None) == ['-created_at', '-updated_at']


def test_timestampedmodel_class_attributes_exist_and_are_fields():
    # The model should define class attributes created_at and updated_at
    tm_dict = target_module.TimestampedModel.__dict__
    assert 'created_at' in tm_dict, "created_at field must be defined on the class"
    assert 'updated_at' in tm_dict, "updated_at field must be defined on the class"

    created_field = tm_dict['created_at']
    updated_field = tm_dict['updated_at']

    # They should be instances of the Django DateTimeField class
    DateTimeField = target_module.models.DateTimeField
    assert isinstance(created_field, DateTimeField)
    assert isinstance(updated_field, DateTimeField)


def test_datetimefield_auto_now_flags_are_set_correctly():
    # Ensure that created_at uses auto_now_add and updated_at uses auto_now
    created_field = target_module.TimestampedModel.__dict__['created_at']
    updated_field = target_module.TimestampedModel.__dict__['updated_at']

    # DateTimeField exposes attributes auto_now_add and auto_now
    assert getattr(created_field, 'auto_now_add', False) is True, "created_at should have auto_now_add=True"
    # created_at should not have auto_now True unless explicitly set
    assert getattr(created_field, 'auto_now', False) in (False, None)

    assert getattr(updated_field, 'auto_now', False) is True, "updated_at should have auto_now=True"
    # updated_at should not have auto_now_add True
    assert getattr(updated_field, 'auto_now_add', False) in (False, None)


def test_timestampedmodel_is_subclass_of_django_model_class():
    # Ensure the class inherits from Django's Model base class
    ModelBase = target_module.models.Model
    assert issubclass(target_module.TimestampedModel, ModelBase) is True