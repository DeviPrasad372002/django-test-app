import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_render_decodes_bytes_token(monkeypatch):
    renderer = target_module.UserJSONRenderer()
    captured = []

    def fake_render(self, data):
        # capture the exact object passed to super.render
        captured.append(data)
        return "SENTINEL"

    monkeypatch.setattr(target_module.ConduitJSONRenderer, 'render', fake_render)

    data = {'user': {'email': 'a@b.com'}, 'token': b'secret-token'}
    result = renderer.render(data)

    assert result == "SENTINEL"
    assert len(captured) == 1
    # token should have been decoded to str before being passed to super.render
    assert captured[0]['token'] == 'secret-token'
    assert isinstance(captured[0]['token'], str)


def test_render_keeps_str_token(monkeypatch):
    renderer = target_module.UserJSONRenderer()
    captured = []

    def fake_render(self, data):
        captured.append(data)
        return {"ok": True}

    monkeypatch.setattr(target_module.ConduitJSONRenderer, 'render', fake_render)

    data = {'user': {'email': 'x@y.z'}, 'token': 'already-string'}
    result = renderer.render(data, media_type='application/json', renderer_context={'foo': 'bar'})

    assert result == {"ok": True}
    assert captured[0]['token'] == 'already-string'
    assert isinstance(captured[0]['token'], str)


def test_render_keeps_non_bytes_token_types(monkeypatch):
    renderer = target_module.UserJSONRenderer()
    captured = []

    def fake_render(self, data):
        captured.append(data)
        return 42

    monkeypatch.setattr(target_module.ConduitJSONRenderer, 'render', fake_render)

    data = {'user': {}, 'token': 12345}
    result = renderer.render(data)
    assert result == 42
    assert captured[0]['token'] == 12345
    assert isinstance(captured[0]['token'], int)


def test_render_with_no_token_key(monkeypatch):
    renderer = target_module.UserJSONRenderer()
    captured = []

    def fake_render(self, data):
        captured.append(data)
        return b'bytes-result'

    monkeypatch.setattr(target_module.ConduitJSONRenderer, 'render', fake_render)

    data = {'user': {'username': 'no-token'}}
    result = renderer.render(data)
    assert result == b'bytes-result'
    assert 'token' not in captured[0]


def test_render_raises_when_data_is_none():
    renderer = target_module.UserJSONRenderer()
    with pytest.raises(AttributeError):
        renderer.render(None)