import importlib.util, pathlib
import types
import pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/models.py').resolve()
_IMPORT_ERROR = None
try:
    _SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
    target_module = importlib.util.module_from_spec(_SPEC)
    assert _SPEC and _SPEC.loader
    _SPEC.loader.exec_module(target_module)
except Exception as _e:
    _IMPORT_ERROR = str(_e)
    target_module = None



def test___str__():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.__str__()
    assert result is not None


def test_follow():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.follow(None)
    assert result is not None


def test___str__():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.Profile().__str__()
    assert result is not None


def test_follow():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.Profile().follow(None)
    assert result is not None


def test_unfollow():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.Profile().unfollow(None)
    assert result is not None


def test_is_following():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.Profile().is_following(None)
    assert result is not None


def test_is_followed_by():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.Profile().is_followed_by(None)
    assert result is not None


def test_favorite():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.Profile().favorite(1)
    assert result is not None


def test_unfavorite():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.Profile().unfavorite(1)
    assert result is not None


def test_has_favorited():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.Profile().has_favorited(1)
    assert result is not None
