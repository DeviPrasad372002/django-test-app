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

def test_profilejsonrenderer_class_attributes_present_and_correct():
    # Ensure class exists
    assert hasattr(target_module, 'ProfileJSONRenderer'), "ProfileJSONRenderer not found in module"
    cls = target_module.ProfileJSONRenderer

    # Expected labels from source
    assert getattr(cls, 'object_label') == 'profile'
    assert getattr(cls, 'pagination_object_label') == 'profiles'
    assert getattr(cls, 'pagination_count_label') == 'profilesCount'

    # Types are strings and not empty
    assert isinstance(cls.object_label, str) and cls.object_label
    assert isinstance(cls.pagination_object_label, str) and cls.pagination_object_label
    assert isinstance(cls.pagination_count_label, str) and cls.pagination_count_label

def test_profilejsonrenderer_is_subclass_of_conduitjsonrenderer():
    cls = target_module.ProfileJSONRenderer
    # The module imports ConduitJSONRenderer into its namespace; ensure subclass relation holds
    assert hasattr(target_module, 'ConduitJSONRenderer'), "ConduitJSONRenderer base class not imported in module"
    base = target_module.ConduitJSONRenderer
    assert issubclass(cls, base), "ProfileJSONRenderer should be a subclass of ConduitJSONRenderer"

def test_instance_sees_class_attributes_and_instance_override_does_not_mutate_class():
    cls = target_module.ProfileJSONRenderer
    inst1 = cls()
    inst2 = cls()

    # Instances initially reflect class attributes
    assert inst1.object_label == 'profile'
    assert inst2.object_label == 'profile'

    # Overriding on one instance should not change the class or other instances
    inst1.object_label = 'custom_profile'
    assert inst1.object_label == 'custom_profile'
    # Class attribute must remain unchanged
    assert cls.object_label == 'profile'
    # New instances should still see original class value
    assert inst2.object_label == 'profile'
    inst3 = cls()
    assert inst3.object_label == 'profile'

def test_attribute_access_via_getattr_and_dir():
    cls = target_module.ProfileJSONRenderer
    inst = cls()

    # getattr should return the same values
    assert getattr(inst, 'object_label') == 'profile'
    assert getattr(inst, 'pagination_object_label') == 'profiles'
    assert getattr(inst, 'pagination_count_label') == 'profilesCount'

    # The attributes should appear in dir() of class and instance (class-level)
    d = dir(cls)
    assert 'object_label' in d
    assert 'pagination_object_label' in d
    assert 'pagination_count_label' in d

def test_pagination_count_label_convention():
    # Small behavioral test: pagination_count_label ends with 'Count' as per naming convention
    cls = target_module.ProfileJSONRenderer
    assert cls.pagination_count_label.endswith('Count'), "pagination_count_label should end with 'Count'"

def test_can_change_class_attributes_and_reflected_in_new_instances():
    cls = target_module.ProfileJSONRenderer
    original = cls.object_label
    try:
        cls.object_label = 'modified'
        # New instance should pick up modified class attribute
        new_inst = cls()
        assert new_inst.object_label == 'modified'
    finally:
        # Restore original to avoid side effects for other tests
        cls.object_label = original

def test_repr_and_str_do_not_error_when_called():
    # Ensure calling repr/str on class and instance doesn't raise
    cls = target_module.ProfileJSONRenderer
    inst = cls()
    assert isinstance(repr(cls), str)
    assert isinstance(str(cls), str)
    assert isinstance(repr(inst), str)
    assert isinstance(str(inst), str)