import importlib.util, pathlib, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/exceptions.py').resolve()
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

def test_class_attributes_present_and_types():
    cls = target_module.ProfileDoesNotExist
    # class attributes
    assert hasattr(cls, 'status_code'), "status_code attribute missing"
    assert hasattr(cls, 'default_detail'), "default_detail attribute missing"
    assert isinstance(cls.status_code, int)
    assert isinstance(cls.default_detail, str)
    assert cls.status_code == 400
    assert cls.default_detail == 'The requested profile does not exist.'

def test_is_subclass_of_api_exception():
    cls = target_module.ProfileDoesNotExist
    # Ensure the module imported the APIException symbol
    assert hasattr(target_module, 'APIException'), "APIException symbol not present in module"
    APIException = target_module.APIException
    assert issubclass(cls, APIException)
    inst = cls()
    assert isinstance(inst, APIException)
    assert isinstance(inst, cls)

def test_default_instance_detail_and_status_code():
    cls = target_module.ProfileDoesNotExist
    inst = cls()
    # Instances should reflect the class defaults
    assert getattr(inst, 'status_code') == cls.status_code
    # APIException stores the message in .detail (DRF behavior)
    assert getattr(inst, 'detail') == cls.default_detail

def test_raise_and_catch_exception_has_default_detail():
    cls = target_module.ProfileDoesNotExist
    with pytest.raises(target_module.APIException) as excinfo:
        raise cls()
    exc = excinfo.value
    assert isinstance(exc, cls)
    # detail on caught exception should equal default_detail
    assert getattr(exc, 'detail') == cls.default_detail
    # status_code should be present on the instance as well
    assert getattr(exc, 'status_code') == cls.status_code

@pytest.mark.parametrize("custom_detail", [
    "A custom message",
    {"msg": "structured"},
    ["list", "of", "messages"],
    12345,  # non-string detail
])
def test_custom_detail_preserved_on_instance(custom_detail):
    cls = target_module.ProfileDoesNotExist
    inst = cls(custom_detail)
    # The detail of the instance should be exactly what was passed
    assert getattr(inst, 'detail') == custom_detail

def test_default_detail_not_mutated_by_instance_change():
    cls = target_module.ProfileDoesNotExist
    inst = cls()
    # mutate instance detail
    inst.detail = "modified"
    # class default should remain unchanged
    assert cls.default_detail == 'The requested profile does not exist.'
    # a fresh instance should still have original default
    new_inst = cls()
    assert new_inst.detail == cls.default_detail