import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_profile_json_renderer_class_attributes_present():
    cls = target_module.ProfileJSONRenderer
    # class attributes exist and have expected values
    assert hasattr(cls, 'object_label')
    assert hasattr(cls, 'pagination_object_label')
    assert hasattr(cls, 'pagination_count_label')

    assert cls.object_label == 'profile'
    assert cls.pagination_object_label == 'profiles'
    assert cls.pagination_count_label == 'profilesCount'


def test_profile_json_renderer_is_subclass_of_conduit_json_renderer():
    cls = target_module.ProfileJSONRenderer
    # The module imports ConduitJSONRenderer into its namespace; ensure subclass relationship
    assert hasattr(target_module, 'ConduitJSONRenderer')
    base = target_module.ConduitJSONRenderer
    assert issubclass(cls, base)


def test_profile_json_renderer_instance_attributes_and_types():
    instance = target_module.ProfileJSONRenderer()
    # Attributes should be accessible on instance and be strings
    assert getattr(instance, 'object_label') == 'profile'
    assert isinstance(instance.object_label, str)

    assert getattr(instance, 'pagination_object_label') == 'profiles'
    assert isinstance(instance.pagination_object_label, str)

    assert getattr(instance, 'pagination_count_label') == 'profilesCount'
    assert isinstance(instance.pagination_count_label, str)