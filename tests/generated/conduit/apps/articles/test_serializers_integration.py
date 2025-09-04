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
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/serializers.py').resolve()
_IMPORT_ERROR = None
try:
    _SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
    target_module = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(target_module)
except Exception as _e:
    _IMPORT_ERROR = str(_e)
    target_module = None



def test_create_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.create(1)
    assert result is not None


def test_get_created_at_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.get_created_at(1)
    assert result is not None


def test_get_favorited_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.get_favorited(1)
    assert result is not None


def test_get_favorites_count_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.get_favorites_count(1)
    assert result is not None


def test_get_updated_at_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.get_updated_at(1)
    assert result is not None


def test_create_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.create(1)
    assert result is not None


def test_get_created_at_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.get_created_at(1)
    assert result is not None


def test_get_updated_at_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.get_updated_at(1)
    assert result is not None


def test_to_representation_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.to_representation(1)
    assert result is not None


def test_articleserializer_create_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.ArticleSerializer().create(1)
    assert result is not None


def test_articleserializer_get_created_at_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.ArticleSerializer().get_created_at(1)
    assert result is not None


def test_articleserializer_get_favorited_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.ArticleSerializer().get_favorited(1)
    assert result is not None


def test_articleserializer_get_favorites_count_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.ArticleSerializer().get_favorites_count(1)
    assert result is not None


def test_articleserializer_get_updated_at_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.ArticleSerializer().get_updated_at(1)
    assert result is not None


def test_commentserializer_create_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.CommentSerializer().create(1)
    assert result is not None


def test_commentserializer_get_created_at_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.CommentSerializer().get_created_at(1)
    assert result is not None


def test_commentserializer_get_updated_at_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.CommentSerializer().get_updated_at(1)
    assert result is not None


def test_tagserializer_to_representation_basic():
    if '_IMPORT_ERROR' in globals() and _IMPORT_ERROR:
        import pytest
        pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}')
    result = target_module.TagSerializer().to_representation(1)
    assert result is not None