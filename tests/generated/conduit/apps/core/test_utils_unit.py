import importlib.util, pathlib
import types
import pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/utils.py').resolve()
_IMPORT_ERROR = None
try:
    _SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
    target_module = importlib.util.module_from_spec(_SPEC)
    assert _SPEC and _SPEC.loader
    _SPEC.loader.exec_module(target_module)
except Exception as _e:
    _IMPORT_ERROR = str(_e)
    target_module = None



def test_generate_random_string():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.generate_random_string(1, 1)
    assert result is not None
