import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_render_decodes_token_bytes_and_calls_super(monkeypatch):
    # Prepare data with token as bytes
    data = {'user': {'email': 'a@b.com'}, 'token': b'secret-token'}
    captured = []

    # Stub the parent ConduitJSONRenderer.render to capture the data passed to it
    def stub_render(self, passed_data):
        # Record a shallow copy to ensure we can assert modifications
        captured.append(dict(passed_data))
        return 'PARENT_RENDERED'

    monkeypatch.setattr(target_module.ConduitJSONRenderer, 'render', stub_render, raising=True)

    renderer = target_module.UserJSONRenderer()
    result = renderer.render(data)

    # Ensure parent was called and its return value propagated
    assert result == 'PARENT_RENDERED'
    assert len(captured) == 1

    # Ensure the token was decoded to a str before calling the parent
    assert captured[0]['token'] == 'secret-token'
    # Ensure original dict was mutated as well
    assert isinstance(data['token'], str)
    assert data['token'] == 'secret-token'


def test_render_leaves_str_token_unchanged_and_calls_super(monkeypatch):
    data = {'user': {'email': 'x@y.com'}, 'token': 'already-string'}
    captured = []

    def stub_render(self, passed_data):
        captured.append(dict(passed_data))
        return {'rendered': True}

    monkeypatch.setattr(target_module.ConduitJSONRenderer, 'render', stub_render, raising=True)

    renderer = target_module.UserJSONRenderer()
    result = renderer.render(data, media_type='application/json', renderer_context={'a': 1})

    assert result == {'rendered': True}
    assert len(captured) == 1
    # Token should remain unchanged and still be a str
    assert captured[0]['token'] == 'already-string'
    assert data['token'] == 'already-string'


def test_render_without_token_calls_super_with_same_data(monkeypatch):
    data = {'user': {'email': 'nobody@example.com'}}
    captured = []

    def stub_render(self, passed_data):
        captured.append(passed_data)
        return b'{}'

    monkeypatch.setattr(target_module.ConduitJSONRenderer, 'render', stub_render, raising=True)

    renderer = target_module.UserJSONRenderer()
    result = renderer.render(data)

    assert result == b'{}'
    assert len(captured) == 1
    # Ensure data passed is the same dict object (not a copy)
    assert captured[0] is data
    assert 'token' not in captured[0]


def test_render_with_none_data_raises_attribute_error():
    renderer = target_module.UserJSONRenderer()
    with pytest.raises(AttributeError):
        # data is None -> data.get will raise AttributeError
        renderer.render(None)


def test_render_with_invalid_utf8_token_raises_unicode_error():
    renderer = target_module.UserJSONRenderer()
    # b'\xff' is invalid in utf-8 and will raise UnicodeDecodeError when decoded
    data = {'user': {}, 'token': b'\xff'}
    with pytest.raises(UnicodeDecodeError):
        renderer.render(data)