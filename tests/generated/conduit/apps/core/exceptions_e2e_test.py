import importlib.util, pathlib
import types
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/exceptions.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


class DummyResponse:
    def __init__(self, data):
        self.data = data


def make_exception(class_name, message=None):
    cls = type(class_name, (Exception,), {})
    return cls(message) if message is not None else cls()


def make_view_with_queryset_verbose(verbose_name):
    model = types.SimpleNamespace(_meta=types.SimpleNamespace(verbose_name=verbose_name))
    queryset = types.SimpleNamespace(model=model)
    view = types.SimpleNamespace(queryset=queryset)
    return view


def make_view_with_no_queryset():
    return types.SimpleNamespace(queryset=None)


def test_generic_validation_error_wrapped(monkeypatch):
    # Arrange
    exc = make_exception('ValidationError')
    original_response = DummyResponse({'field': ['invalid']})
    def fake_exception_handler(e, context):
        return original_response
    monkeypatch.setattr(target_module, 'exception_handler', fake_exception_handler)

    # Act
    result = target_module.core_exception_handler(exc, context={})

    # Assert
    assert result is original_response
    assert result.data == {'errors': {'field': ['invalid']}}


def test_not_found_with_queryset_uses_verbose_name(monkeypatch):
    # Arrange
    exc = make_exception('NotFound')
    original_response = DummyResponse({'detail': 'Not found.'})
    def fake_exception_handler(e, context):
        return original_response
    monkeypatch.setattr(target_module, 'exception_handler', fake_exception_handler)

    view = make_view_with_queryset_verbose('person')
    context = {'view': view}

    # Act
    result = target_module.core_exception_handler(exc, context=context)

    # Assert
    assert result is original_response
    assert result.data == {'errors': {'person': 'Not found.'}}


def test_not_found_without_queryset_falls_back_to_generic(monkeypatch):
    # Arrange
    exc = make_exception('NotFound')
    original_response = DummyResponse({'detail': 'Missing.'})
    def fake_exception_handler(e, context):
        return original_response
    monkeypatch.setattr(target_module, 'exception_handler', fake_exception_handler)

    view = make_view_with_no_queryset()
    context = {'view': view}

    # Act
    result = target_module.core_exception_handler(exc, context=context)

    # Assert: Should wrap original data under errors (generic handler)
    assert result is original_response
    assert result.data == {'errors': {'detail': 'Missing.'}}


def test_other_exception_delegated_to_default_handler(monkeypatch):
    # Arrange
    exc = make_exception('SomeOtherError')
    original_response = DummyResponse({'ok': True})
    def fake_exception_handler(e, context):
        return original_response
    monkeypatch.setattr(target_module, 'exception_handler', fake_exception_handler)

    # Act
    result = target_module.core_exception_handler(exc, context={})

    # Assert: Should return whatever the default exception handler returned unchanged
    assert result is original_response
    assert result.data == {'ok': True}


def test_handled_exception_when_default_returns_none_raises_attribute_error(monkeypatch):
    # Arrange: default exception_handler returns None
    exc = make_exception('ValidationError')
    def fake_exception_handler(e, context):
        return None
    monkeypatch.setattr(target_module, 'exception_handler', fake_exception_handler)

    # Act & Assert: handler will attempt to set response.data and raise AttributeError
    with pytest.raises(AttributeError):
        target_module.core_exception_handler(exc, context={})