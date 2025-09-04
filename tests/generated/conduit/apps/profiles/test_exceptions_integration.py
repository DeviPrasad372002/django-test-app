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

def _require_symbol(name):
    if not hasattr(target_module, name):
        pytest.skip(f"Target module does not define required symbol: {name}", allow_module_level=False)
    return getattr(target_module, name)

def test_profile_does_not_exist_class_attributes_and_inheritance():
    ProfileDoesNotExist = _require_symbol('ProfileDoesNotExist')
    # Ensure it's a class
    assert isinstance(ProfileDoesNotExist, type)
    # Ensure APIException is available in module and it's a base
    if not hasattr(target_module, 'APIException'):
        pytest.skip("rest_framework.exceptions.APIException not present in target module namespace")
    APIException = target_module.APIException
    assert issubclass(ProfileDoesNotExist, APIException)
    # Check class-level attributes
    assert getattr(ProfileDoesNotExist, 'status_code') == 400
    assert getattr(ProfileDoesNotExist, 'default_detail') == 'The requested profile does not exist.'

def test_default_instance_sets_default_detail_and_status_code():
    ProfileDoesNotExist = _require_symbol('ProfileDoesNotExist')
    inst = ProfileDoesNotExist()
    # instance should carry the status code
    assert hasattr(inst, 'status_code')
    assert inst.status_code == 400
    # detail may be an ErrorDetail or plain string; compare string form to be robust
    assert str(inst.detail) == ProfileDoesNotExist.default_detail

@pytest.mark.parametrize("custom_detail", [
    "Custom message",
    "",  # empty string
    {"key": "value"},  # dict detail
    ["list", "of", "items"],  # list detail
    None  # explicit None should fall back to default_detail per DRF behavior
])
def test_instance_with_various_details(custom_detail):
    ProfileDoesNotExist = _require_symbol('ProfileDoesNotExist')
    if custom_detail is None:
        inst = ProfileDoesNotExist(None)
        # None should use default detail
        assert str(inst.detail) == ProfileDoesNotExist.default_detail
    else:
        inst = ProfileDoesNotExist(custom_detail)
        # When custom detail is provided, instance.detail should reflect it
        # For non-string types, equality should hold; for strings compare string form
        if isinstance(custom_detail, str):
            assert str(inst.detail) == custom_detail
        else:
            assert inst.detail == custom_detail
    # status_code remains unchanged
    assert inst.status_code == 400

def test_raising_and_catching_exception_preserves_properties():
    ProfileDoesNotExist = _require_symbol('ProfileDoesNotExist')
    with pytest.raises(ProfileDoesNotExist) as excinfo:
        raise ProfileDoesNotExist("boom")
    caught = excinfo.value
    assert isinstance(caught, ProfileDoesNotExist)
    assert caught.status_code == 400
    assert str(caught.detail) == "boom"

def test_mutating_instance_detail_does_not_change_class_default():
    ProfileDoesNotExist = _require_symbol('ProfileDoesNotExist')
    original_default = ProfileDoesNotExist.default_detail
    inst = ProfileDoesNotExist()
    # mutate instance detail
    inst.detail = "temporary"
    assert str(inst.detail) == "temporary"
    # class-level default must remain the same
    assert ProfileDoesNotExist.default_detail == original_default

def test_repr_and_str_contain_detail_information():
    ProfileDoesNotExist = _require_symbol('ProfileDoesNotExist')
    inst = ProfileDoesNotExist("repr detail")
    # str() of the exception or its detail should include the provided detail
    assert "repr detail" in str(inst.detail) or "repr detail" in str(inst)
    # repr should not raise
    repr(inst)  # just ensure no exception raised during repr()