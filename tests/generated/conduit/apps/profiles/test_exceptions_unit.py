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


def test_profiledoesnotexist_has_expected_class_attributes():
    # Ensure the class exists
    assert hasattr(target_module, 'ProfileDoesNotExist'), "ProfileDoesNotExist class is missing"
    cls = target_module.ProfileDoesNotExist

    # The class should define the expected status code and default detail
    assert hasattr(cls, 'status_code'), "status_code attribute is missing"
    assert cls.status_code == 400

    assert hasattr(cls, 'default_detail'), "default_detail attribute is missing"
    assert cls.default_detail == 'The requested profile does not exist.'


def test_profiledoesnotexist_is_subclass_of_apiexception():
    # Ensure subclass relationship with DRF APIException
    try:
        from rest_framework.exceptions import APIException
    except Exception as e:
        pytest.skip(f"rest_framework not available to assert subclass: {e}")
    assert issubclass(target_module.ProfileDoesNotExist, APIException)


def test_default_instantiation_sets_detail_to_default_and_str_contains_detail():
    exc = target_module.ProfileDoesNotExist()
    # APIException implementations may wrap detail in types; compare textually
    assert hasattr(exc, 'detail')
    assert str(exc.detail) == target_module.ProfileDoesNotExist.default_detail
    # stringifying the exception should include the default detail text
    assert target_module.ProfileDoesNotExist.default_detail in str(exc)


def test_instantiation_with_custom_string_detail_overrides_default():
    custom = "custom profile not found"
    exc = target_module.ProfileDoesNotExist(detail=custom)
    assert hasattr(exc, 'detail')
    # Ensure the provided custom detail overrides default_detail for this instance
    assert str(exc.detail) == custom
    # Class attribute should remain unchanged
    assert target_module.ProfileDoesNotExist.default_detail == 'The requested profile does not exist.'


def test_instantiation_with_complex_detail_preserves_value():
    complex_detail = {"username": "alice", "reason": "deleted"}
    exc = target_module.ProfileDoesNotExist(detail=complex_detail)
    # For complex types, the exception.detail should retain the object (not coerced to its string)
    assert exc.detail == complex_detail


def test_raising_profiledoesnotexist_carries_status_code_and_detail():
    with pytest.raises(target_module.ProfileDoesNotExist) as ctx:
        raise target_module.ProfileDoesNotExist()
    caught = ctx.value
    # Ensure raised exception instance has the configured status code
    assert getattr(caught, 'status_code', None) == 400
    # And its detail text equals the default detail text
    assert str(caught.detail) == target_module.ProfileDoesNotExist.default_detail


def test_mutating_instance_detail_does_not_change_class_default():
    exc = target_module.ProfileDoesNotExist()
    original_default = target_module.ProfileDoesNotExist.default_detail
    exc.detail = "temporarily changed"
    # Instance was changed
    assert str(exc.detail) == "temporarily changed"
    # Class-level default remains unchanged
    assert target_module.ProfileDoesNotExist.default_detail == original_default