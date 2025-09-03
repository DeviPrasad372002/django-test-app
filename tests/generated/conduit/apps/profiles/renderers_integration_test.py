import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_profilejsonrenderer_class_attributes_exist_and_values():
    cls = target_module.ProfileJSONRenderer
    # Class attributes exist
    assert hasattr(cls, 'object_label'), "Missing object_label on class"
    assert hasattr(cls, 'pagination_object_label'), "Missing pagination_object_label on class"
    assert hasattr(cls, 'pagination_count_label'), "Missing pagination_count_label on class"

    # Values are exactly as expected
    assert cls.object_label == 'profile'
    assert cls.pagination_object_label == 'profiles'
    assert cls.pagination_count_label == 'profilesCount'


def test_profilejsonrenderer_is_subclass_and_instance():
    cls = target_module.ProfileJSONRenderer
    base = target_module.ConduitJSONRenderer

    # Subclass relationship
    assert issubclass(cls, base)

    # Can instantiate without arguments and is instance of both class and base
    inst = cls()
    assert isinstance(inst, cls)
    assert isinstance(inst, base)


def test_instance_attribute_override_does_not_modify_class_attribute():
    cls = target_module.ProfileJSONRenderer
    inst = cls()

    # original class value
    original = cls.object_label
    assert original == 'profile'

    # override on instance only
    inst.object_label = 'changed_profile'
    assert inst.object_label == 'changed_profile'
    # class attribute remains unchanged
    assert cls.object_label == original


def test_attribute_types_and_non_empty_strings():
    cls = target_module.ProfileJSONRenderer
    # Ensure attributes are strings and non-empty
    for attr in ('object_label', 'pagination_object_label', 'pagination_count_label'):
        val = getattr(cls, attr)
        assert isinstance(val, str)
        assert val != ''


def test_profilejsonrenderer_exported_in_module_namespace():
    # Ensure the name is available in the module namespace
    assert 'ProfileJSONRenderer' in dir(target_module)
    # Ensure ConduitJSONRenderer was imported into the module namespace
    assert 'ConduitJSONRenderer' in dir(target_module)