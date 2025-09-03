import importlib.util, pathlib, json, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_render_with_results_raises_attribute_error_due_to_typo():
    renderer = target_module.ConduitJSONRenderer()
    data = {'results': [{'id': 1}], 'count': 1}
    with pytest.raises(AttributeError) as excinfo:
        renderer.render(data)
    assert 'pagination_count_label' in str(excinfo.value)


def test_render_with_errors_uses_super_render(monkeypatch):
    called = {}

    def fake_super_render(self, data, media_type=None, renderer_context=None):
        # record that we were called and return a distinct value
        called['data'] = data
        called['media_type'] = media_type
        called['renderer_context'] = renderer_context
        return b'__super_rendered__'

    # Patch the JSONRenderer.render method that the ConduitJSONRenderer will call via super()
    monkeypatch.setattr(target_module.JSONRenderer, 'render', fake_super_render, raising=True)

    renderer = target_module.ConduitJSONRenderer()
    payload = {'errors': {'detail': 'unauthenticated'}}
    result = renderer.render(payload, media_type='application/json', renderer_context={'foo': 'bar'})

    assert result == b'__super_rendered__'
    assert called['data'] is payload
    assert called['media_type'] == 'application/json'
    assert called['renderer_context'] == {'foo': 'bar'}


def test_render_single_object_returns_wrapped_json_string():
    renderer = target_module.ConduitJSONRenderer()
    data = {'username': 'alice', 'email': 'a@example.com'}
    result = renderer.render(data)
    # Should wrap the data under the 'object' label
    expected = json.dumps({renderer.object_label: data})
    assert isinstance(result, str)
    assert result == expected


def test_render_with_results_none_treated_as_object():
    renderer = target_module.ConduitJSONRenderer()
    data = {'results': None}
    result = renderer.render(data)
    # results is None so it should not trigger the pagination branch; it should be wrapped as object
    expected = json.dumps({renderer.object_label: data})
    assert result == expected


def test_render_with_none_data_raises_attribute_error():
    renderer = target_module.ConduitJSONRenderer()
    with pytest.raises(AttributeError):
        # Passing None should cause an AttributeError when attempting to call .get on None
        renderer.render(None)