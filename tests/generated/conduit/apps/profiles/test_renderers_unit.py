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

import inspect

def test_profile_renderer_is_subclass_and_has_expected_class_attributes():
    # Ensure the attribute exists on the module
    assert hasattr(target_module, 'ProfileJSONRenderer'), "ProfileJSONRenderer is not defined in target module"
    ProfileJSONRenderer = target_module.ProfileJSONRenderer

    # Ensure ConduitJSONRenderer exists and is a class
    assert hasattr(target_module, 'ConduitJSONRenderer'), "ConduitJSONRenderer not available in target module"
    ConduitJSONRenderer = target_module.ConduitJSONRenderer
    if not inspect.isclass(ConduitJSONRenderer):
        pytest.skip("ConduitJSONRenderer is not a class; skipping inheritance tests")

    # Subclass relationship
    assert issubclass(ProfileJSONRenderer, ConduitJSONRenderer), "ProfileJSONRenderer must subclass ConduitJSONRenderer"

    # Class attributes and expected values
    assert getattr(ProfileJSONRenderer, 'object_label', None) == 'profile'
    assert getattr(ProfileJSONRenderer, 'pagination_object_label', None) == 'profiles'
    assert getattr(ProfileJSONRenderer, 'pagination_count_label', None) == 'profilesCount'

@pytest.mark.parametrize("attr_name, expected", [
    ("object_label", "profile"),
    ("pagination_object_label", "profiles"),
    ("pagination_count_label", "profilesCount"),
])
def test_class_attributes_are_strings_and_non_empty(attr_name, expected):
    ProfileJSONRenderer = target_module.ProfileJSONRenderer
    assert hasattr(ProfileJSONRenderer, attr_name), f"{attr_name} missing on ProfileJSONRenderer"
    val = getattr(ProfileJSONRenderer, attr_name)
    assert isinstance(val, str), f"{attr_name} must be a string"
    assert val == expected, f"{attr_name} expected '{expected}', got '{val}'"
    assert val.strip() != "", f"{attr_name} must not be empty or whitespace"

def test_instance_attribute_resolution_and_mutation_behavior():
    ProfileJSONRenderer = target_module.ProfileJSONRenderer
    inst = ProfileJSONRenderer()

    # Instance should expose the same labels via attribute lookup
    assert getattr(inst, 'object_label') == ProfileJSONRenderer.object_label
    assert getattr(inst, 'pagination_object_label') == ProfileJSONRenderer.pagination_object_label
    assert getattr(inst, 'pagination_count_label') == ProfileJSONRenderer.pagination_count_label

    # Changing instance attribute should not change class attribute
    inst.object_label = 'temp'
    assert inst.object_label == 'temp'
    assert ProfileJSONRenderer.object_label == 'profile', "Modifying instance attribute should not alter class attribute"

def test_dynamic_subclass_override_of_labels():
    ProfileJSONRenderer = target_module.ProfileJSONRenderer

    class CustomProfile(ProfileJSONRenderer):
        object_label = 'custom_profile'
        pagination_object_label = 'custom_profiles'
        pagination_count_label = 'customProfilesCount'

    # Ensure overrides are effective on the subclass
    assert CustomProfile.object_label == 'custom_profile'
    assert CustomProfile.pagination_object_label == 'custom_profiles'
    assert CustomProfile.pagination_count_label == 'customProfilesCount'

    # Instances of subclass reflect the overridden values
    c = CustomProfile()
    assert c.object_label == 'custom_profile'
    assert c.pagination_object_label == 'custom_profiles'
    assert c.pagination_count_label == 'customProfilesCount'

def test_mro_contains_expected_parent():
    ProfileJSONRenderer = target_module.ProfileJSONRenderer
    ConduitJSONRenderer = target_module.ConduitJSONRenderer

    # Ensure ConduitJSONRenderer is somewhere in the MRO
    mro = inspect.getmro(ProfileJSONRenderer)
    assert ConduitJSONRenderer in mro, "ConduitJSONRenderer should be in the MRO of ProfileJSONRenderer"

def test_profile_renderer_attributes_are_independent_from_parent_when_parent_mutated():
    ProfileJSONRenderer = target_module.ProfileJSONRenderer
    ConduitJSONRenderer = target_module.ConduitJSONRenderer

    # Save original parent attributes if they exist
    parent_has_object_label = hasattr(ConduitJSONRenderer, 'object_label')
    orig_parent_val = getattr(ConduitJSONRenderer, 'object_label', None)

    try:
        # Mutate parent attribute to a different value and ensure child class attribute remains unchanged
        ConduitJSONRenderer.object_label = 'parent_changed'
        assert getattr(ProfileJSONRenderer, 'object_label') == 'profile', "Child class attribute should not change when parent attribute is mutated"
    finally:
        # Restore parent's original state
        if parent_has_object_label:
            ConduitJSONRenderer.object_label = orig_parent_val
        else:
            delattr(ConduitJSONRenderer, 'object_label')