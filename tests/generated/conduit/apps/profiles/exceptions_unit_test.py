import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/exceptions.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_class_attributes_and_types():
    # class exists
    cls = getattr(target_module, 'ProfileDoesNotExist', None)
    assert cls is not None and isinstance(cls, type)

    # class-level attributes
    assert hasattr(cls, 'status_code')
    assert cls.status_code == 400
    assert hasattr(cls, 'default_detail')
    assert isinstance(cls.default_detail, str)
    assert cls.default_detail == 'The requested profile does not exist.'


def test_inheritance_from_api_exception():
    # Should be a subclass of the imported APIException
    assert issubclass(target_module.ProfileDoesNotExist, target_module.APIException)


def test_instance_uses_default_detail_and_str():
    inst = target_module.ProfileDoesNotExist()
    # detail attribute should default to class default_detail
    assert hasattr(inst, 'detail')
    assert inst.detail == target_module.ProfileDoesNotExist.default_detail
    # str() should reflect the detail
    assert str(inst) == target_module.ProfileDoesNotExist.default_detail
    # status_code should be accessible on instance too
    assert getattr(inst, 'status_code') == 400


def test_custom_detail_and_code_override_on_instance():
    custom_detail = 'custom not found'
    custom_code = 'custom_code'
    inst = target_module.ProfileDoesNotExist(detail=custom_detail, code=custom_code)
    # instance stores provided detail and code (code becomes default_code on the instance)
    assert inst.detail == custom_detail
    assert getattr(inst, 'default_code', None) == custom_code
    # class default_detail should remain unchanged
    assert target_module.ProfileDoesNotExist.default_detail == 'The requested profile does not exist.'


def test_exception_can_be_raised_and_caught_with_expected_properties():
    with pytest.raises(target_module.ProfileDoesNotExist) as excinfo:
        raise target_module.ProfileDoesNotExist()
    exc = excinfo.value
    assert isinstance(exc, target_module.ProfileDoesNotExist)
    assert exc.status_code == 400
    assert exc.detail == target_module.ProfileDoesNotExist.default_detail
    assert str(exc) == target_module.ProfileDoesNotExist.default_detail


def test_accepts_non_string_detail_values():
    detail_value = {'reason': 'missing', 'id': 123}
    inst = target_module.ProfileDoesNotExist(detail=detail_value)
    # The detail attribute should store the provided non-string value unchanged
    assert inst.detail == detail_value
    # str(inst) should be stringified version of the detail
    assert isinstance(str(inst), str)
    assert detail_value.__repr__() in str(inst) or str(detail_value) in str(inst)