import importlib.util, pathlib
import types
import pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/serializers.py').resolve()
_IMPORT_ERROR = None
try:
    _SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
    target_module = importlib.util.module_from_spec(_SPEC)
    assert _SPEC and _SPEC.loader
    _SPEC.loader.exec_module(target_module)
except Exception as _e:
    _IMPORT_ERROR = str(_e)
    target_module = None



def test_create():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.create(1)
    assert result is not None


def test_get_created_at():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.get_created_at(1)
    assert result is not None


def test_create():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.ArticleSerializer().create(1)
    assert result is not None


def test_get_created_at():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.ArticleSerializer().get_created_at(1)
    assert result is not None


def test_get_favorited():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.ArticleSerializer().get_favorited(1)
    assert result is not None


def test_get_favorites_count():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.ArticleSerializer().get_favorites_count(1)
    assert result is not None


def test_get_updated_at():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.ArticleSerializer().get_updated_at(1)
    assert result is not None
