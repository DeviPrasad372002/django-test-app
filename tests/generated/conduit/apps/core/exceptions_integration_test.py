import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/exceptions.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


class SimpleResponse:
    def __init__(self, data):
        self.data = data


def make_exception_class(name):
    return type(name, (Exception,), {})


def test_handle_validation_error_wraps_errors(monkeypatch):
    # Arrange
    exc = make_exception_class('ValidationError')()
    response = SimpleResponse({'field': ['invalid']})
    monkeypatch.setattr(target_module, 'exception_handler', lambda e, c: response)

    # Act
    result = target_module.core_exception_handler(exc, {})

    # Assert
    assert result is response
    assert result.data == {'errors': {'field': ['invalid']}}


def test_handle_not_found_with_queryset_verbose_name(monkeypatch):
    # Arrange
    exc = make_exception_class('NotFound')()
    response = SimpleResponse({'detail': 'Not found.'})
    monkeypatch.setattr(target_module, 'exception_handler', lambda e, c: response)

    class Meta:
        verbose_name = 'article'

    class Model:
        _meta = Meta()

    class QuerySet:
        model = Model()

    class View:
        queryset = QuerySet()

    context = {'view': View()}

    # Act
    result = target_module.core_exception_handler(exc, context)

    # Assert
    assert result is response
    assert result.data == {'errors': {'article': 'Not found.'}}


def test_handle_not_found_without_queryset_uses_generic(monkeypatch):
    # Arrange
    exc = make_exception_class('NotFound')()
    response = SimpleResponse({'detail': 'Not found.'})
    monkeypatch.setattr(target_module, 'exception_handler', lambda e, c: response)

    class View:
        queryset = None

    context = {'view': View()}

    # Act
    result = target_module.core_exception_handler(exc, context)

    # Assert: falls back to generic handler which wraps the original data under 'errors'
    assert result is response
    assert result.data == {'errors': {'detail': 'Not found.'}}


def test_unknown_exception_returns_original_response(monkeypatch):
    # Arrange
    exc = make_exception_class('SomeOtherError')()
    response = SimpleResponse({'info': 'original'})
    monkeypatch.setattr(target_module, 'exception_handler', lambda e, c: response)

    # Act
    result = target_module.core_exception_handler(exc, {})

    # Assert
    assert result is response
    assert result.data == {'info': 'original'}


def test_handled_exception_with_no_response_raises(monkeypatch):
    # Arrange: DRF exception_handler returns None (possible in some cases)
    exc = make_exception_class('ValidationError')()
    monkeypatch.setattr(target_module, 'exception_handler', lambda e, c: None)

    # Act & Assert: accessing response.data should raise AttributeError
    with pytest.raises(AttributeError):
        target_module.core_exception_handler(exc, {})