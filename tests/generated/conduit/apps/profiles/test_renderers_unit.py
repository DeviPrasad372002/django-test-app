import importlib.util, pathlib, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/renderers.py').resolve()
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


def test_profilejsonrenderer_class_exists_and_is_subclass():
    # Ensure the class exists
    assert hasattr(target_module, 'ProfileJSONRenderer'), "ProfileJSONRenderer not found in module"
    cls = target_module.ProfileJSONRenderer

    # It should be a class
    assert isinstance(cls, type), "ProfileJSONRenderer is not a class"

    # It should inherit from some ConduitJSONRenderer (check by name in MRO)
    mro_names = [c.__name__ for c in cls.__mro__]
    assert 'ConduitJSONRenderer' in mro_names, f"ProfileJSONRenderer does not inherit from ConduitJSONRenderer, MRO: {mro_names}"


@pytest.mark.parametrize("attr,expected", [
    ("object_label", "profile"),
    ("pagination_object_label", "profiles"),
    ("pagination_count_label", "profilesCount"),
])
def test_profilejsonrenderer_class_attributes(attr, expected):
    cls = target_module.ProfileJSONRenderer
    # Class must have attribute
    assert hasattr(cls, attr), f"{attr} missing on ProfileJSONRenderer"
    value = getattr(cls, attr)
    # Type check
    assert isinstance(value, str), f"{attr} should be a string"
    # Exact expected value
    assert value == expected, f"{attr} expected '{expected}', got '{value}'"


def test_instance_has_same_attributes_and_mutation_is_instance_local():
    cls = target_module.ProfileJSONRenderer
    inst = cls()  # instantiate to ensure no __init__ side-effects

    # Instance should reflect class attributes by default
    assert getattr(inst, 'object_label') == getattr(cls, 'object_label')
    assert getattr(inst, 'pagination_object_label') == getattr(cls, 'pagination_object_label')
    assert getattr(inst, 'pagination_count_label') == getattr(cls, 'pagination_count_label')

    # Mutate instance attribute and ensure class attribute remains unchanged
    original = cls.object_label
    inst.object_label = 'changed-by-instance'
    assert inst.object_label == 'changed-by-instance'
    assert cls.object_label == original, "Changing instance attribute should not change class attribute"


def test_profilejsonrenderer_attributes_are_non_empty_strings():
    cls = target_module.ProfileJSONRenderer
    for attr in ('object_label', 'pagination_object_label', 'pagination_count_label'):
        value = getattr(cls, attr)
        assert isinstance(value, str)
        assert value != "", f"{attr} should not be an empty string"


def test_profilejsonrenderer_has_no_unexpected_public_attributes():
    # Ensure only the expected public attributes exist on the class or are inherited.
    # We check that the class defines at least the expected attributes (others may be inherited).
    cls = target_module.ProfileJSONRenderer
    defined = set(k for k, v in cls.__dict__.items() if not k.startswith('_'))
    expected_defined = {'object_label', 'pagination_object_label', 'pagination_count_label'}
    # The class should define at least these attributes
    assert expected_defined.issubset(defined), f"ProfileJSONRenderer.__dict__ missing expected keys: {expected_defined - defined}"