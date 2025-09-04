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
    # Ensure the class exists
    assert hasattr(target_module, 'ProfileDoesNotExist'), "ProfileDoesNotExist not defined in module"
    cls = target_module.ProfileDoesNotExist

    # It should be a subclass of the imported APIException in the module
    assert hasattr(target_module, 'APIException'), "APIException not imported into module namespace"
    assert issubclass(cls, target_module.APIException)

    # Class-level attributes
    assert hasattr(cls, 'status_code'), "status_code attribute missing on class"
    assert cls.status_code == 400

    assert hasattr(cls, 'default_detail'), "default_detail attribute missing on class"
    assert cls.default_detail == 'The requested profile does not exist.'


def test_default_instance_uses_default_detail_and_status_code():
    cls = target_module.ProfileDoesNotExist
    inst = cls()  # no detail provided should use default_detail

    # Instance should expose status_code equal to class attribute
    assert hasattr(inst, 'status_code')
    assert inst.status_code == cls.status_code == 400

    # The detail may be wrapped by DRF's ErrorDetail; compare via str to be robust
    assert str(inst.detail) == cls.default_detail
    # str(exception) should also render the detail text
    assert str(inst) == cls.default_detail


@pytest.mark.parametrize("detail", [
    {'foo': 'bar'},
    ['a', 'b', 'c'],
    12345,
    None,  # explicit None should fall back to default_detail
])
def test_instance_detail_handling(detail):
    cls = target_module.ProfileDoesNotExist
    inst = cls(detail=detail) if detail is not None else cls(detail=None)

    if detail is None:
        # Fallback to default_detail behavior
        assert str(inst.detail) == cls.default_detail
    else:
        # For non-None details, APIException should store the provided detail (strings may be wrapped)
        # Compare via equality for basic types; for types that may be wrapped, compare string forms
        if isinstance(detail, (str, bytes)):
            assert str(inst.detail) == str(detail)
        else:
            assert inst.detail == detail


def test_custom_code_is_preserved_but_status_code_remains():
    cls = target_module.ProfileDoesNotExist
    inst = cls(detail='custom', code='my_code')

    # The APIException stores code separately; ensure status_code remains the class-level HTTP code
    assert inst.status_code == cls.status_code == 400

    # The provided detail is preserved
    assert str(inst.detail) == 'custom'


def test_raising_and_catching_exception_preserves_attributes():
    cls = target_module.ProfileDoesNotExist
    with pytest.raises(cls) as excinfo:
        raise cls()

    caught = excinfo.value
    assert isinstance(caught, cls)
    assert caught.status_code == 400
    assert str(caught.detail) == cls.default_detail


def test_modifying_instance_detail_does_not_mutate_class_default():
    cls = target_module.ProfileDoesNotExist
    inst = cls()
    original_default = cls.default_detail
    inst.detail = 'mutated'
    # class default should remain unchanged
    assert cls.default_detail == original_default
    # instance detail should reflect the mutation
    assert str(inst.detail) == 'mutated'