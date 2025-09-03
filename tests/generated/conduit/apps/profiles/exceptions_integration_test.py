import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/exceptions.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_class_exists_and_inherits_api_exception():
    assert hasattr(target_module, 'ProfileDoesNotExist')
    cls = target_module.ProfileDoesNotExist
    # Ensure it subclasses the imported APIException
    assert issubclass(cls, target_module.APIException)
    # Class attributes
    assert hasattr(cls, 'status_code')
    assert hasattr(cls, 'default_detail')
    assert isinstance(cls.status_code, int)
    assert cls.status_code == 400
    assert cls.default_detail == 'The requested profile does not exist.'


def test_default_instance_has_expected_detail_and_status():
    inst = target_module.ProfileDoesNotExist()
    # status_code should be accessible on instance and equal to class value
    assert hasattr(inst, 'status_code')
    assert inst.status_code == 400
    # detail should default to the class default_detail
    assert hasattr(inst, 'detail')
    assert inst.detail == target_module.ProfileDoesNotExist.default_detail
    # stringifying the exception should reflect the detail
    assert str(inst) == target_module.ProfileDoesNotExist.default_detail


def test_custom_detail_overrides_default():
    custom = 'custom profile missing message'
    inst = target_module.ProfileDoesNotExist(custom)
    assert inst.detail == custom
    assert str(inst) == custom
    # status_code remains the same
    assert inst.status_code == 400


def test_detail_can_be_non_string_like_dict():
    payload = {'field': 'not_found', 'code': 404}
    inst = target_module.ProfileDoesNotExist(payload)
    # detail should preserve the provided object
    assert inst.detail == payload
    # string conversion should match the string form of the provided detail
    assert str(inst) == str(payload)


def test_raising_and_catching_exception_provides_detail():
    with pytest.raises(target_module.ProfileDoesNotExist) as excinfo:
        raise target_module.ProfileDoesNotExist()
    caught = excinfo.value
    assert isinstance(caught, target_module.ProfileDoesNotExist)
    assert caught.detail == target_module.ProfileDoesNotExist.default_detail


def test_instance_mutation_does_not_change_class_default():
    inst = target_module.ProfileDoesNotExist('temporary')
    inst.detail = 'mutated'
    # class default remains unchanged
    assert target_module.ProfileDoesNotExist.default_detail == 'The requested profile does not exist.'
    assert inst.detail != target_module.ProfileDoesNotExist.default_detail