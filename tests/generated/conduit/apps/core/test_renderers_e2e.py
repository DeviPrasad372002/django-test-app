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

def test_render_plain_object_returns_wrapped_json():
    renderer = target_module.ConduitJSONRenderer()
    data = {'username': 'alice', 'bio': 'dev'}
    result = renderer.render(data)
    # Expect a JSON string representing {"object": data}
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert 'object' in parsed
    assert parsed['object'] == data

def test_render_with_errors_uses_super_render(monkeypatch):
    # Replace the parent JSONRenderer.render to observe that Conduit uses it
    called = {}
    def fake_super_render(self, data, media_type=None, renderer_context=None):
        called['data'] = data
        # Return bytes as DRF JSONRenderer typically does
        return b'__super_render_called__'
    # Monkeypatch the JSONRenderer.render that ConduitJSONRenderer inherits from
    monkeypatch.setattr(target_module, 'JSONRenderer', type('J', (), {'render': fake_super_render}))
    # Recreate an instance of ConduitJSONRenderer class object will still be the same class,
    # but its MRO will pick up the patched JSONRenderer attribute on the module only for the call
    # to super().render. To ensure super() resolves to our fake, we call the unbound function directly
    renderer = target_module.ConduitJSONRenderer()
    data = {'errors': {'detail': 'Authentication failed'}}
    result = renderer.render(data)
    # Our fake returns bytes, so result should be bytes
    assert result == b'__super_render_called__'
    # Ensure the fake was called with the same data
    assert called['data'] == data

def test_render_pagination_raises_attribute_error_due_to_bad_attribute_name():
    renderer = target_module.ConduitJSONRenderer()
    data = {'results': [{'id': 1}], 'count': 1}
    # The implementation refers to self.pagination_count_label which is not defined,
    # so accessing it should raise AttributeError
    with pytest.raises(AttributeError):
        renderer.render(data)

def test_render_non_dict_input_raises_attribute_error():
    renderer = target_module.ConduitJSONRenderer()
    # If data is None or a non-dict, .get will not exist and should raise AttributeError
    with pytest.raises(AttributeError):
        renderer.render(None)
    with pytest.raises(AttributeError):
        renderer.render([1, 2, 3])

def test_render_pagination_if_attribute_added_behaves_correctly(monkeypatch):
    # To test the intended pagination behavior, temporarily add the missing attribute
    renderer = target_module.ConduitJSONRenderer()
    # Attach the expected attribute name to the instance to emulate correct implementation
    setattr(renderer, 'pagination_count_label', renderer.pagination_object_count)
    data = {'results': [{'id': 1}, {'id': 2}], 'count': 2}
    result = renderer.render(data)
    # Should be a JSON string; parse and verify structure
    assert isinstance(result, str)
    parsed = json.loads(result)
    assert 'objects' in parsed
    assert parsed['objects'] == data['results']
    assert 'count' in parsed
    assert parsed['count'] == data['count']