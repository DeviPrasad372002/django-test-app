import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/exceptions.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_default_attributes():
    cls = target_module.ProfileDoesNotExist
    inst = cls()
    assert hasattr(inst, 'status_code')
    assert inst.status_code == 400
    assert hasattr(cls, 'default_detail')
    assert cls.default_detail == 'The requested profile does not exist.'
    # detail should default to the class default_detail
    assert hasattr(inst, 'detail')
    assert inst.detail == cls.default_detail


def test_custom_detail_string():
    cls = target_module.ProfileDoesNotExist
    custom = 'custom profile missing'
    inst = cls(custom)
    assert inst.detail == custom
    assert inst.status_code == 400  # status code remains unchanged


def test_none_detail_uses_default():
    cls = target_module.ProfileDoesNotExist
    inst = cls(None)
    assert inst.detail == cls.default_detail


def test_empty_string_detail_is_allowed():
    cls = target_module.ProfileDoesNotExist
    inst = cls('')
    assert inst.detail == ''


def test_is_instance_of_api_exception():
    from rest_framework.exceptions import APIException
    cls = target_module.ProfileDoesNotExist
    inst = cls()
    assert isinstance(inst, APIException)


def test_raising_and_catching_exception():
    from rest_framework.exceptions import APIException
    cls = target_module.ProfileDoesNotExist
    with pytest.raises(APIException) as excinfo:
        raise cls()
    caught = excinfo.value
    assert getattr(caught, 'detail', None) == cls.default_detail
    assert getattr(caught, 'status_code', None) == 400