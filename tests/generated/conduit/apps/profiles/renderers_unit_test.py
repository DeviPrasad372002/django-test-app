import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_class_attributes_exist_and_match_expected():
    cls = target_module.ProfileJSONRenderer
    # Expected labels from the source
    assert hasattr(cls, 'object_label')
    assert hasattr(cls, 'pagination_object_label')
    assert hasattr(cls, 'pagination_count_label')

    assert cls.object_label == 'profile'
    assert cls.pagination_object_label == 'profiles'
    assert cls.pagination_count_label == 'profilesCount'


def test_instance_has_same_attribute_values_as_class():
    cls = target_module.ProfileJSONRenderer
    inst = cls()
    # Instance should expose same attribute values as the class
    assert inst.object_label == cls.object_label == 'profile'
    assert inst.pagination_object_label == cls.pagination_object_label == 'profiles'
    assert inst.pagination_count_label == cls.pagination_count_label == 'profilesCount'


def test_attribute_types_and_non_empty_strings():
    cls = target_module.ProfileJSONRenderer
    for attr in ('object_label', 'pagination_object_label', 'pagination_count_label'):
        val = getattr(cls, attr)
        assert isinstance(val, str)
        assert val != ''


def test_inheritance_in_mro_contains_conduitjsonrenderer():
    cls = target_module.ProfileJSONRenderer
    names_in_mro = [c.__name__ for c in cls.__mro__]
    assert 'ConduitJSONRenderer' in names_in_mro


def test_modifying_instance_attribute_does_not_change_class_attribute():
    cls = target_module.ProfileJSONRenderer
    inst = cls()
    original = cls.object_label
    inst.object_label = 'modified'
    # instance change should not mutate the class attribute
    assert cls.object_label == original
    assert inst.object_label == 'modified'


def test_instance_has_render_callable_if_inherited():
    cls = target_module.ProfileJSONRenderer
    inst = cls()
    render_attr = getattr(inst, 'render', None)
    assert render_attr is not None and callable(render_attr)