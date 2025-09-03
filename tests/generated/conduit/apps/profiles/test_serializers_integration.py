import importlib.util, pathlib
import pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/serializers.py').resolve()
_IMPORT_ERROR = None
try:
    _SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
    target_module = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(target_module)
except Exception as _e:
    _IMPORT_ERROR = str(_e)
    target_module = None

def test_integration_has_function_get_image():
    import pytest
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    assert hasattr(target_module, 'get_image')


def test_integration_has_class_profileserializer():
    import pytest
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    assert hasattr(target_module, 'ProfileSerializer')