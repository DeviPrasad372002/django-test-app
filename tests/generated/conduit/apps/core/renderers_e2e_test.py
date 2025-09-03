import importlib.util, pathlib, json, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_render_with_results_raises_attribute_error():
    renderer = target_module.ConduitJSONRenderer()
    data = {'results': [{'id': 1}], 'count': 1}
    with pytest.raises(AttributeError):
        renderer.render(data, media_type=None, renderer_context=None)


def test_render_with_results_empty_list_raises_attribute_error():
    renderer = target_module.ConduitJSONRenderer()
    data = {'results': [], 'count': 0}
    with pytest.raises(AttributeError):
        renderer.render(data, media_type=None, renderer_context=None)


def test_render_with_errors_delegates_to_jsonrenderer():
    renderer = target_module.ConduitJSONRenderer()
    data = {'errors': {'detail': 'not allowed'}}
    result = renderer.render(data, media_type=None, renderer_context=None)
    expected = target_module.JSONRenderer().render(data)
    assert result == expected


def test_render_with_single_object_wraps_object():
    renderer = target_module.ConduitJSONRenderer()
    payload = {'a': 1, 'b': 'two'}
    data = payload
    result = renderer.render(data, media_type=None, renderer_context=None)
    assert result == json.dumps({'object': payload})


def test_render_with_empty_dict_returns_wrapped_object():
    renderer = target_module.ConduitJSONRenderer()
    data = {}
    result = renderer.render(data, media_type=None, renderer_context=None)
    assert result == json.dumps({'object': {}})


def test_render_with_custom_object_label():
    renderer = target_module.ConduitJSONRenderer()
    renderer.object_label = 'article'
    payload = {'title': 'Hello'}
    result = renderer.render(payload, media_type=None, renderer_context=None)
    assert result == json.dumps({'article': payload})


def test_render_with_none_raises_attribute_error():
    renderer = target_module.ConduitJSONRenderer()
    with pytest.raises(AttributeError):
        renderer.render(None, media_type=None, renderer_context=None)