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


def test_profile_does_not_exist_class_attributes():
    cls = target_module.ProfileDoesNotExist
    # Is a class
    assert isinstance(cls, type)
    # Has expected class attributes
    assert hasattr(cls, 'status_code')
    assert hasattr(cls, 'default_detail')
    assert cls.status_code == 400
    assert cls.default_detail == 'The requested profile does not exist.'
    # Subclass of Exception (and likely APIException)
    assert issubclass(cls, Exception)


def _get_detail_from_instance(exc_instance):
    # Helper to retrieve detail in a robust way across APIException implementations
    if hasattr(exc_instance, 'detail'):
        return exc_instance.detail
    # Fallback: string conversion
    return str(exc_instance)


def test_default_detail_on_instantiation():
    exc = target_module.ProfileDoesNotExist()
    detail = _get_detail_from_instance(exc)
    # Detail should include default_detail text
    assert 'The requested profile does not exist.' in detail
    # status_code available on instance
    assert getattr(exc, 'status_code', None) == 400


def test_custom_detail_string_and_other_types():
    # Custom string detail
    custom = 'no profile for user'
    exc_str = target_module.ProfileDoesNotExist(custom)
    detail_str = _get_detail_from_instance(exc_str)
    assert custom in detail_str

    # Custom dict detail
    custom_dict = {'username': ['not found']}
    exc_dict = target_module.ProfileDoesNotExist(custom_dict)
    # If detail attribute exists, it should equal the dict; otherwise str(...) contains its representation
    if hasattr(exc_dict, 'detail'):
        assert exc_dict.detail == custom_dict
    else:
        assert str(custom_dict) in str(exc_dict)

    # Custom list detail
    custom_list = ['a', 'b']
    exc_list = target_module.ProfileDoesNotExist(custom_list)
    if hasattr(exc_list, 'detail'):
        assert exc_list.detail == custom_list
    else:
        assert str(custom_list) in str(exc_list)


def test_raise_and_catch_exception_preserves_status_code():
    with pytest.raises(target_module.ProfileDoesNotExist) as ctx:
        raise target_module.ProfileDoesNotExist()
    exc = ctx.value
    # Ensure status code is preserved on caught exception
    assert getattr(exc, 'status_code', None) == 400
    # And detail includes default message
    assert 'The requested profile does not exist.' in _get_detail_from_instance(exc)


def test_instance_modification_does_not_change_class_attribute():
    exc = target_module.ProfileDoesNotExist()
    # Modify instance attribute
    exc.status_code = 401
    assert exc.status_code == 401
    # Class attribute remains unchanged
    assert target_module.ProfileDoesNotExist.status_code == 400
    # default_detail also unchanged
    assert target_module.ProfileDoesNotExist.default_detail == 'The requested profile does not exist.'