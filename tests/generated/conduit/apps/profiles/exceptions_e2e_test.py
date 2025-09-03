import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/exceptions.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_profile_does_not_exist_class_definition():
    # class exists
    assert hasattr(target_module, 'ProfileDoesNotExist')
    cls = target_module.ProfileDoesNotExist

    # is subclass of APIException imported into the module
    assert hasattr(target_module, 'APIException')
    assert issubclass(cls, target_module.APIException)

    # class attributes as defined
    assert getattr(cls, 'status_code') == 400
    assert getattr(cls, 'default_detail') == 'The requested profile does not exist.'


def test_default_instantiation_behavior():
    inst = target_module.ProfileDoesNotExist()

    # instance has detail attribute and it matches the class default_detail
    assert hasattr(inst, 'detail')
    assert inst.detail == target_module.ProfileDoesNotExist.default_detail

    # instance inherits status_code
    assert getattr(inst, 'status_code') == 400

    # string representation contains the default detail
    assert target_module.ProfileDoesNotExist.default_detail in str(inst)


def test_custom_detail_overrides_default():
    custom = 'This is a custom error message.'
    inst = target_module.ProfileDoesNotExist(detail=custom)

    # detail should reflect the custom value passed
    assert inst.detail == custom
    assert custom in str(inst)

    # raising and catching should preserve status_code and message
    with pytest.raises(target_module.APIException) as excinfo:
        raise inst
    caught = excinfo.value
    assert getattr(caught, 'status_code') == 400
    assert custom in str(caught)


def test_non_string_detail_is_preserved():
    complex_detail = {'id': 123, 'reason': 'not found'}
    inst = target_module.ProfileDoesNotExist(detail=complex_detail)

    # The detail attribute should preserve non-string values (dicts, lists, etc.)
    assert inst.detail == complex_detail
    # str() should at least include a stringified form of the detail
    assert str(complex_detail) in str(inst)


def test_can_be_caught_by_specific_and_base_exception_types():
    # Raised exception should be catchable by both the specific class and APIException
    with pytest.raises(target_module.ProfileDoesNotExist):
        raise target_module.ProfileDoesNotExist()

    with pytest.raises(target_module.APIException):
        raise target_module.ProfileDoesNotExist()