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

def test_module_loaded():
    # Sanity check: module should be imported by the header
    assert target_module is not None

def test_profilejsonrenderer_class_exists_and_subclass():
    # The class should exist in the module
    assert hasattr(target_module, 'ProfileJSONRenderer'), "ProfileJSONRenderer missing"
    ProfileJSONRenderer = target_module.ProfileJSONRenderer
    # It should be a class
    assert isinstance(ProfileJSONRenderer, type)
    # It should subclass ConduitJSONRenderer imported into the module
    assert hasattr(target_module, 'ConduitJSONRenderer'), "ConduitJSONRenderer missing in module namespace"
    assert issubclass(ProfileJSONRenderer, target_module.ConduitJSONRenderer)

@pytest.mark.parametrize("attr,expected", [
    ("object_label", "profile"),
    ("pagination_object_label", "profiles"),
    ("pagination_count_label", "profilesCount"),
])
def test_class_labels_are_correct(attr, expected):
    ProfileJSONRenderer = target_module.ProfileJSONRenderer
    # class attribute exists
    assert hasattr(ProfileJSONRenderer, attr), f"{attr} missing on class"
    value = getattr(ProfileJSONRenderer, attr)
    # correct value and type
    assert isinstance(value, str)
    assert value == expected

def test_instance_attributes_and_override_does_not_mutate_class():
    ProfileJSONRenderer = target_module.ProfileJSONRenderer
    inst = ProfileJSONRenderer()
    # Instance should expose the same attributes as class by default
    for attr in ("object_label", "pagination_object_label", "pagination_count_label"):
        assert hasattr(inst, attr)
        assert getattr(inst, attr) == getattr(ProfileJSONRenderer, attr)

    # Mutating instance attribute should not change the class attribute
    old_class_value = ProfileJSONRenderer.object_label
    inst.object_label = "temporary"
    assert inst.object_label == "temporary"
    assert ProfileJSONRenderer.object_label == old_class_value

def test_dynamic_subclass_can_override_labels():
    ProfileJSONRenderer = target_module.ProfileJSONRenderer
    # Create a dynamic subclass that overrides labels
    class CustomProfileRenderer(ProfileJSONRenderer):
        object_label = "custom_profile"
        pagination_object_label = "custom_profiles"
        pagination_count_label = "custom_profiles_count"

    # Ensure subclass has expected overridden values
    c = CustomProfileRenderer()
    assert CustomProfileRenderer.object_label == "custom_profile"
    assert CustomProfileRenderer.pagination_object_label == "custom_profiles"
    assert CustomProfileRenderer.pagination_count_label == "custom_profiles_count"

    # Instance should reflect subclass values
    assert c.object_label == "custom_profile"
    assert c.pagination_object_label == "custom_profiles"
    assert c.pagination_count_label == "custom_profiles_count"

def test_attributes_are_non_empty_strings():
    ProfileJSONRenderer = target_module.ProfileJSONRenderer
    for attr in ("object_label", "pagination_object_label", "pagination_count_label"):
        val = getattr(ProfileJSONRenderer, attr)
        assert isinstance(val, str)
        assert val != "" and val.strip() == val  # non-empty and no surrounding whitespace