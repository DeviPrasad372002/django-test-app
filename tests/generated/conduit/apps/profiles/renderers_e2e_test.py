import importlib.util, pathlib
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_profilejsonrenderer_is_subclass_of_conduitjsonrenderer():
    assert hasattr(target_module, 'ProfileJSONRenderer'), "ProfileJSONRenderer should be defined in the module"
    assert hasattr(target_module, 'ConduitJSONRenderer'), "ConduitJSONRenderer should be imported into the module"
    assert issubclass(target_module.ProfileJSONRenderer, target_module.ConduitJSONRenderer)


def test_class_attributes_have_expected_values():
    cls = target_module.ProfileJSONRenderer
    assert getattr(cls, 'object_label') == 'profile'
    assert getattr(cls, 'pagination_object_label') == 'profiles'
    assert getattr(cls, 'pagination_count_label') == 'profilesCount'
    # types
    assert isinstance(cls.object_label, str)
    assert isinstance(cls.pagination_object_label, str)
    assert isinstance(cls.pagination_count_label, str)


def test_instance_accesses_same_class_attributes():
    inst = target_module.ProfileJSONRenderer()
    assert inst.object_label == target_module.ProfileJSONRenderer.object_label
    assert inst.pagination_object_label == target_module.ProfileJSONRenderer.pagination_object_label
    assert inst.pagination_count_label == target_module.ProfileJSONRenderer.pagination_count_label


def test_setting_instance_attribute_does_not_modify_class_attribute():
    cls = target_module.ProfileJSONRenderer
    inst = cls()
    original = cls.object_label
    try:
        inst.object_label = 'modified-instance'
        # instance should reflect change
        assert inst.object_label == 'modified-instance'
        # class should remain unchanged
        assert cls.object_label == original
    finally:
        # cleanup in case other tests rely on original (defensive)
        if hasattr(inst, 'object_label'):
            delattr(inst, 'object_label')


def test_modifying_class_attribute_affects_new_instances_and_restored_afterwards():
    cls = target_module.ProfileJSONRenderer
    orig_object_label = cls.object_label
    orig_pagination_object_label = cls.pagination_object_label
    orig_pagination_count_label = cls.pagination_count_label
    try:
        cls.object_label = 'new-profile'
        cls.pagination_object_label = 'new-profiles'
        cls.pagination_count_label = 'new-profilesCount'
        new_inst = cls()
        assert new_inst.object_label == 'new-profile'
        assert new_inst.pagination_object_label == 'new-profiles'
        assert new_inst.pagination_count_label == 'new-profilesCount'
    finally:
        # restore originals to avoid side effects
        cls.object_label = orig_object_label
        cls.pagination_object_label = orig_pagination_object_label
        cls.pagination_count_label = orig_pagination_count_label


def test_attribute_presence_and_immutability_of_literals():
    cls = target_module.ProfileJSONRenderer
    # Ensure attributes exist and are simple string literals (immutable)
    for name in ('object_label', 'pagination_object_label', 'pagination_count_label'):
        assert hasattr(cls, name)
        val = getattr(cls, name)
        # strings are immutable; operations should return new objects, value unchanged
        upper = val.upper()
        assert getattr(cls, name) == val
        assert isinstance(upper, str)
        # check equality to expected values for each known attribute
    assert cls.object_label == 'profile'
    assert cls.pagination_object_label == 'profiles'
    assert cls.pagination_count_label == 'profilesCount'