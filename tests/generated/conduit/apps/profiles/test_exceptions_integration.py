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

def test_is_subclass_and_mro():
    """
    ProfileDoesNotExist should be a subclass of APIException and appear in its MRO.
    """
    cls = target_module.ProfileDoesNotExist
    base = target_module.APIException
    assert issubclass(cls, base)
    # Ensure the base class is present in the Method Resolution Order
    assert base in cls.__mro__

def test_default_attributes_values():
    """
    Class-level attributes should match expected values.
    """
    cls = target_module.ProfileDoesNotExist
    assert hasattr(cls, 'status_code'), "status_code attribute missing"
    assert hasattr(cls, 'default_detail'), "default_detail attribute missing"
    assert cls.status_code == 400
    assert cls.default_detail == 'The requested profile does not exist.'

def test_instantiation_uses_default_detail_and_status_code():
    """
    Instantiating without arguments should populate .detail with the default_detail
    and expose the status_code on the instance.
    """
    inst = target_module.ProfileDoesNotExist()
    # status_code is a class attribute but should be accessible on the instance
    assert getattr(inst, 'status_code') == 400
    # detail may be an ErrorDetail (subclass of str) or plain str; ensure text matches
    assert str(inst.detail) == target_module.ProfileDoesNotExist.default_detail

def test_instantiation_with_custom_detail_preserved_and_with_non_string_detail():
    """
    If a custom detail is provided it should be preserved exactly.
    Also test that non-string detail (like a dict) is preserved.
    """
    custom_text = 'Custom not found message'
    inst_text = target_module.ProfileDoesNotExist(detail=custom_text)
    assert str(inst_text.detail) == custom_text

    custom_obj = {'username': ['does not exist']}
    inst_obj = target_module.ProfileDoesNotExist(detail=custom_obj)
    # Some DRF versions keep dicts as-is; others may wrap; comparing via string representation is safe
    assert str(inst_obj.detail) == str(custom_obj)

def test_raise_and_catch_as_api_exception():
    """
    Raising the custom exception should be catchable as the base APIException.
    """
    cls = target_module.ProfileDoesNotExist
    base = target_module.APIException
    with pytest.raises(base) as excinfo:
        raise cls()
    # Ensure the captured exception is indeed an instance of our class
    assert isinstance(excinfo.value, cls)
    # And that its message/detail includes the default text
    assert target_module.ProfileDoesNotExist.default_detail in str(excinfo.value.detail)

def test_mutating_default_detail_affects_new_instances_and_restored():
    """
    Temporarily mutate the class default_detail and ensure new instances reflect the change.
    Then restore the original value.
    """
    cls = target_module.ProfileDoesNotExist
    original = cls.default_detail
    try:
        cls.default_detail = 'Temporary override'
        inst = cls()
        assert str(inst.detail) == 'Temporary override'
    finally:
        # restore to avoid side effects for other tests
        cls.default_detail = original