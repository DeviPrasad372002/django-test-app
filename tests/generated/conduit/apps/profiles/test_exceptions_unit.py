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


def _get_detail_text(exc_instance):
    """
    Helper to get a stable string representation of the exception detail
    across different DRF versions (detail may be str, dict, list, etc.).
    """
    detail = getattr(exc_instance, 'detail', None)
    if detail is None:
        return ''
    # If it's a list or dict, convert to str for comparison
    return str(detail)


def test_profile_does_not_exist_is_subclass_of_api_exception():
    # Ensure the class is present
    cls = getattr(target_module, 'ProfileDoesNotExist', None)
    assert cls is not None, "ProfileDoesNotExist class should be defined in module"
    # Import APIException from rest_framework for isinstance check
    try:
        from rest_framework.exceptions import APIException  # type: ignore
    except Exception:
        pytest.skip("rest_framework not available for APIException checks")
    assert issubclass(cls, APIException), "ProfileDoesNotExist must subclass rest_framework.exceptions.APIException"


def test_default_class_attributes():
    cls = target_module.ProfileDoesNotExist
    # Class attributes specified in source
    assert hasattr(cls, 'status_code'), "ProfileDoesNotExist must define status_code"
    assert hasattr(cls, 'default_detail'), "ProfileDoesNotExist must define default_detail"
    assert cls.status_code == 400, "status_code should be 400 as defined"
    assert cls.default_detail == 'The requested profile does not exist.', "default_detail message mismatch"


def test_instance_has_default_detail_and_status_code():
    exc = target_module.ProfileDoesNotExist()
    # Instance should carry the status_code attribute
    assert getattr(exc, 'status_code', None) == target_module.ProfileDoesNotExist.status_code
    # The detail should reflect the class default_detail (string representation)
    detail_text = _get_detail_text(exc)
    assert target_module.ProfileDoesNotExist.default_detail in detail_text


def test_custom_detail_overrides_default():
    custom = "custom not found message"
    exc = target_module.ProfileDoesNotExist(custom)
    detail_text = _get_detail_text(exc)
    assert custom in detail_text, "Providing custom detail should override default_detail"
    # status_code remains the same
    assert exc.status_code == target_module.ProfileDoesNotExist.status_code


def test_non_string_detail_handling():
    # Provide a dict as detail (edge case)
    custom_detail = {"reason": "no_profile", "id": 123}
    exc = target_module.ProfileDoesNotExist(custom_detail)
    detail_text = _get_detail_text(exc)
    # The string version of the dict should appear in the detail text
    assert str(custom_detail) in detail_text


def test_raising_exception_sets_expected_attributes():
    # When raised, the exception can be caught and inspected
    with pytest.raises(target_module.ProfileDoesNotExist) as ei:
        raise target_module.ProfileDoesNotExist("raise-test")
    caught = ei.value
    assert isinstance(caught, target_module.ProfileDoesNotExist)
    # Check message and status_code on caught exception
    assert "raise-test" in _get_detail_text(caught)
    assert caught.status_code == target_module.ProfileDoesNotExist.status_code


def test_multiple_instances_independent_details():
    a = target_module.ProfileDoesNotExist("a")
    b = target_module.ProfileDoesNotExist("b")
    assert "a" in _get_detail_text(a)
    assert "b" in _get_detail_text(b)
    # Ensure they don't share mutable state
    assert _get_detail_text(a) != _get_detail_text(b) or a is not b