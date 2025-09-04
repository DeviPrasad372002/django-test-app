import importlib.util, pathlib, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/renderers.py').resolve()
_IMPORT_ERROR = None
try:
    _SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
    target_module = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(target_module)
except Exception as _e:
    _IMPORT_ERROR = str(_e)
    target_module = None
if _IMPORT_ERROR:
    pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}', allow_module_level=True)

import json

@pytest.fixture
def renderer():
    return target_module.ConduitJSONRenderer()

def test_class_default_attributes(renderer):
    # verify declared defaults
    assert getattr(renderer, 'charset') == 'utf-8'
    assert getattr(renderer, 'object_label') == 'object'
    assert getattr(renderer, 'pagination_object_label') == 'objects'
    assert getattr(renderer, 'pagination_object_count') == 'count'
    # There is a known typo: pagination_count_label is not defined
    assert getattr(renderer, 'pagination_count_label', None) is None

def test_render_wraps_object_when_no_results_or_errors(renderer):
    payload = {'title': 'Hello', 'value': 123}
    rendered = renderer.render(payload)
    # Should be a JSON string equal to {"object": payload}
    assert isinstance(rendered, str)
    assert json.loads(rendered) == {'object': payload}

def test_render_with_results_raises_attribute_error_due_to_missing_name(renderer):
    # Provide a paginated-like response; method references a non-existent attribute
    payload = {'results': [{'id': 1}, {'id': 2}], 'count': 2}
    with pytest.raises(AttributeError) as excinfo:
        renderer.render(payload)
    # Ensure the AttributeError is about the missing pagination_count_label attribute
    assert 'pagination_count_label' in str(excinfo.value)

def test_render_with_errors_delegates_to_parent_render(monkeypatch):
    # Replace the parent class render with a fake implementation to observe delegation
    called = {}
    def fake_parent_render(self, *args, **kwargs):
        # mark that parent render was called and return a unique sentinel
        called['was_called'] = True
        return b'parent-rendered-sentinel'

    # Ensure JSONRenderer exists on the target module
    assert hasattr(target_module, 'JSONRenderer')
    monkeypatch.setattr(target_module.JSONRenderer, 'render', fake_parent_render, raising=True)

    renderer = target_module.ConduitJSONRenderer()
    payload = {'errors': {'detail': 'Authentication credentials were not provided.'}}
    result = renderer.render(payload)
    assert called.get('was_called') is True
    assert result == b'parent-rendered-sentinel'

def test_render_with_non_dict_raises_attribute_error(renderer):
    # If data is None, code attempts to call data.get and should raise AttributeError
    with pytest.raises(AttributeError):
        renderer.render(None)

    # If data is a list (has no get), also raises
    with pytest.raises(AttributeError):
        renderer.render([1, 2, 3])