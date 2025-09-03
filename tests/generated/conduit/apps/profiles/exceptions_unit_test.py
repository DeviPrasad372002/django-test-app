import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/exceptions.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_is_subclass_and_class_attributes():
    # The exception class should subclass the imported APIException
    assert issubclass(target_module.ProfileDoesNotExist, target_module.APIException)
    # Class-level status_code and default_detail should be set as in source
    assert hasattr(target_module.ProfileDoesNotExist, 'status_code')
    assert target_module.ProfileDoesNotExist.status_code == 400
    assert hasattr(target_module.ProfileDoesNotExist, 'default_detail')
    assert isinstance(target_module.ProfileDoesNotExist.default_detail, str)
    assert target_module.ProfileDoesNotExist.default_detail == 'The requested profile does not exist.'


def test_default_instance_detail_and_str():
    # Instantiating without arguments should use the class default_detail
    exc = target_module.ProfileDoesNotExist()
    assert hasattr(exc, 'detail')
    assert exc.detail == target_module.ProfileDoesNotExist.default_detail
    # The string representation should reflect the detail
    assert str(exc) == target_module.ProfileDoesNotExist.default_detail


def test_custom_detail_overrides_default_and_status_code_unchanged():
    custom = 'Custom not found message'
    exc = target_module.ProfileDoesNotExist(custom)
    assert exc.detail == custom
    # status_code should still be the class-defined value on the instance
    assert getattr(exc, 'status_code', None) == 400
    # Class attribute remains unchanged
    assert target_module.ProfileDoesNotExist.status_code == 400


def test_non_string_detail_is_preserved_and_str_matches():
    detail = {'id': 'missing', 'reason': 'no-such-profile'}
    exc = target_module.ProfileDoesNotExist(detail)
    # Non-string detail (e.g., dict) should be preserved on the instance
    assert exc.detail == detail
    # str() should reflect the detail's string representation
    assert str(exc) == str(detail)


def test_none_detail_uses_default_detail():
    # Passing None should fall back to the class default_detail
    exc = target_module.ProfileDoesNotExist(None)
    assert exc.detail == target_module.ProfileDoesNotExist.default_detail
    assert str(exc) == target_module.ProfileDoesNotExist.default_detail


def test_raising_and_catching_exception_preserves_detail():
    with pytest.raises(target_module.ProfileDoesNotExist) as ctx:
        raise target_module.ProfileDoesNotExist()
    caught = ctx.value
    assert isinstance(caught, target_module.ProfileDoesNotExist)
    assert caught.detail == target_module.ProfileDoesNotExist.default_detail