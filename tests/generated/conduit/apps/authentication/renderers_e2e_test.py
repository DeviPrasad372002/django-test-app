import importlib.util, pathlib
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)

import json
import pytest


def _load_rendered(output):
    # Accept bytes or str as returned by renderer
    if isinstance(output, bytes):
        text = output.decode('utf-8')
    else:
        text = output
    return json.loads(text)


def test_class_attributes_are_set():
    renderer_cls = target_module.UserJSONRenderer
    assert hasattr(renderer_cls, 'charset')
    assert renderer_cls.charset == 'utf-8'
    assert renderer_cls.object_label == 'user'
    assert renderer_cls.pagination_object_label == 'users'
    assert renderer_cls.pagination_count_label == 'usersCount'


def test_render_decodes_token_bytes_and_mutates_input():
    r = target_module.UserJSONRenderer()
    data = {'user': {'email': 'a@example.com'}, 'token': b'byte-token-123'}
    output = r.render(data)
    parsed = _load_rendered(output)
    # Ensure token is decoded in output JSON
    assert parsed.get('token') == 'byte-token-123'
    # Ensure the original data dict was mutated to have a str token
    assert isinstance(data['token'], str)
    assert data['token'] == 'byte-token-123'
    # Other keys preserved
    assert parsed.get('user', {}).get('email') == 'a@example.com'


def test_render_leaves_string_token_unchanged():
    r = target_module.UserJSONRenderer()
    data = {'user': {'username': 'bob'}, 'token': 'already-string'}
    output = r.render(data)
    parsed = _load_rendered(output)
    assert parsed['token'] == 'already-string'
    # original object remains a string
    assert isinstance(data['token'], str)


def test_render_absent_token_key_results_in_no_token_in_output():
    r = target_module.UserJSONRenderer()
    data = {'user': {'username': 'no_token_user'}}
    output = r.render(data)
    parsed = _load_rendered(output)
    assert 'token' not in parsed
    # Ensure user data present
    assert parsed.get('user', {}).get('username') == 'no_token_user'


def test_render_token_none_is_preserved_as_null():
    r = target_module.UserJSONRenderer()
    data = {'token': None}
    output = r.render(data)
    parsed = _load_rendered(output)
    # JSON null -> Python None
    assert parsed.get('token') is None
    # input dict still has None
    assert data['token'] is None


def test_render_with_non_dict_raises_attribute_error():
    r = target_module.UserJSONRenderer()
    with pytest.raises(AttributeError):
        # Passing None should cause data.get to fail
        r.render(None)


def test_render_with_invalid_utf8_bytes_raises_unicode_decode_error():
    r = target_module.UserJSONRenderer()
    # Create bytes not valid in UTF-8
    data = {'token': b'\xff'}
    with pytest.raises(UnicodeDecodeError):
        r.render(data)