import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/exceptions.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


class DummyResponse:
    def __init__(self, data):
        self.data = data


class OtherError(Exception):
    pass


class ValidationError(Exception):
    pass


class NotFound(Exception):
    pass


def test_core_exception_handler_returns_none_when_default_handler_returns_none_and_unhandled():
    # Arrange
    resp = None
    target_module.exception_handler = lambda exc, ctx: resp
    exc = OtherError()
    context = {}

    # Act
    result = target_module.core_exception_handler(exc, context)

    # Assert
    assert result is None


def test_core_exception_handler_returns_default_response_when_unhandled_and_response_present():
    # Arrange
    resp = DummyResponse({'foo': 'bar'})
    target_module.exception_handler = lambda exc, ctx: resp
    exc = OtherError()
    context = {}

    # Act
    result = target_module.core_exception_handler(exc, context)

    # Assert
    assert result is resp
    assert result.data == {'foo': 'bar'}


def test_handle_generic_error_wraps_response_data_in_errors_key():
    # Arrange
    original_data = {'field': ['invalid']}
    resp = DummyResponse(original_data.copy())
    target_module.exception_handler = lambda exc, ctx: resp
    exc = ValidationError()
    context = {}

    # Act
    result = target_module.core_exception_handler(exc, context)

    # Assert
    assert result is resp
    assert result.data == {'errors': {'field': ['invalid']}}


def test_handle_not_found_with_queryset_uses_model_verbose_name():
    # Arrange
    # Create dummy model meta
    class Meta:
        verbose_name = 'widget'

    class Model:
        _meta = Meta()

    class QuerySet:
        def __init__(self, model):
            self.model = model

    class View:
        def __init__(self, queryset):
            self.queryset = queryset

    queryset = QuerySet(Model)
    view = View(queryset)
    context = {'view': view}

    resp = DummyResponse({'detail': 'Not found.'})
    target_module.exception_handler = lambda exc, ctx: resp
    exc = NotFound()

    # Act
    result = target_module.core_exception_handler(exc, context)

    # Assert
    assert result is resp
    assert result.data == {'errors': {'widget': 'Not found.'}}


def test_handle_not_found_without_view_uses_generic_wrapper():
    # Arrange
    resp = DummyResponse({'detail': 'Not found.'})
    target_module.exception_handler = lambda exc, ctx: resp
    exc = NotFound()
    context = {}  # no view provided

    # Act
    result = target_module.core_exception_handler(exc, context)

    # Assert
    assert result is resp
    assert result.data == {'errors': {'detail': 'Not found.'}}


def test_handle_not_found_with_view_but_no_queryset_uses_generic_wrapper():
    # Arrange
    class View:
        queryset = None

    view = View()
    context = {'view': view}
    resp = DummyResponse({'detail': 'Not found.'})
    target_module.exception_handler = lambda exc, ctx: resp
    exc = NotFound()

    # Act
    result = target_module.core_exception_handler(exc, context)

    # Assert
    assert result is resp
    assert result.data == {'errors': {'detail': 'Not found.'}}