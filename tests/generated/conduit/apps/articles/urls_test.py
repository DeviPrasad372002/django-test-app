import importlib.util, pathlib
import types
import pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/urls.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(target_module)

