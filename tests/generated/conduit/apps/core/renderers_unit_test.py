import importlib.util, pathlib
import json
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_class_default_attributes():
    cls = target_module.ConduitJSONRenderer
    assert getattr(cls, 'charset') == 'utf-8'
    assert getattr(cls, 'object_label') == 'object'
    assert getattr(cls, 'pagination_object_label') == 'objects'
    # The source defines pagination_object_count; ensure that attribute exists and equals 'count'
    assert getattr(cls, 'pagination_object_count') == 'count'


def test_render_standard_object_returns_wrapped_json():
    renderer = target_module.ConduitJSONRenderer()
    data = {'foo': 'bar'}
    rendered = renderer.render(data)
    # Should be a JSON string wrapping the object under the 'object' key
    assert rendered == json.dumps({'object': data})


def test_render_pagination_raises_attribute_error_due_to_typo():
    renderer = target_module.ConduitJSONRenderer()
    data = {'results': [1, 2, 3], 'count': 3}
    # The implementation references pagination_count_label which does not exist,
    # causing an AttributeError when handling pagination responses.
    with pytest.raises(AttributeError):
        renderer.render(data)


def test_render_errors_uses_super_render(monkeypatch):
    renderer = target_module.ConduitJSONRenderer()
    called = {}

    def fake_super_render(self, data, *args, **kwargs):
        # record that it was called and return a sentinel value
        called['data'] = data
        return b'__SUPER_RENDERED__'

    # Patch the JSONRenderer.render used by super() in ConduitJSONRenderer.render
    monkeypatch.setattr(target_module.JSONRenderer, 'render', fake_super_render, raising=True)

    data = {'errors': {'detail': 'failure'}}
    result = renderer.render(data)
    assert result == b'__SUPER_RENDERED__'
    assert called.get('data') == data


def test_render_with_none_raises_attribute_error():
    renderer = target_module.ConduitJSONRenderer()
    with pytest.raises(AttributeError):
        renderer.render(None)


def test_render_with_non_mapping_raises_attribute_error():
    renderer = target_module.ConduitJSONRenderer()
    with pytest.raises(AttributeError):
        renderer.render([1, 2, 3])