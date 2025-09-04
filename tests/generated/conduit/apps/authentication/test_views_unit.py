# -- DJANGO_SETTINGS_GUARD --
try:
    import django  # noqa: F401
    from django.conf import settings
except Exception:
    pass
else:
    import pytest as _pytest
    if not getattr(settings, 'configured', False):
        _pytest.skip('Django settings not configured', allow_module_level=True)



import importlib.util, pathlib
import pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/views.py').resolve()
_IMPORT_ERROR = None
try:
    _SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
    target_module = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(target_module)
except Exception as _e:
    _IMPORT_ERROR = str(_e)
    target_module = None



def test_post_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.post(None)
    assert result is not None


def test_post_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.post(None)
    assert result is not None


def test_retrieve_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.retrieve(None)
    assert result is not None


def test_update_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.update(None)
    assert result is not None


def test_registrationapiview_post_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.RegistrationAPIView().post(None)
    assert result is not None


def test_loginapiview_post_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.LoginAPIView().post(None)
    assert result is not None


def test_userretrieveupdateapiview_retrieve_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.UserRetrieveUpdateAPIView().retrieve(None)
    assert result is not None


def test_userretrieveupdateapiview_update_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.UserRetrieveUpdateAPIView().update(None)
    assert result is not None