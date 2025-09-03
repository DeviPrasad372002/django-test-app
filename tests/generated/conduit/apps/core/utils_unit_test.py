import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/utils.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)

def test_default_length_and_characters():
    result = target_module.generate_random_string()
    assert isinstance(result, str)
    assert len(result) == 6
    # all characters should come from DEFAULT_CHAR_STRING
    assert set(result).issubset(set(target_module.DEFAULT_CHAR_STRING))

def test_custom_chars_and_size():
    chars = 'abc'
    size = 10
    result = target_module.generate_random_string(chars=chars, size=size)
    assert isinstance(result, str)
    assert len(result) == size
    assert set(result).issubset(set(chars))

def test_chars_as_list_and_size():
    chars = ['x', 'y']
    size = 5
    result = target_module.generate_random_string(chars=chars, size=size)
    assert isinstance(result, str)
    assert len(result) == size
    assert set(result).issubset(set(chars))

def test_size_zero_returns_empty_string():
    assert target_module.generate_random_string(size=0) == ''

@pytest.mark.parametrize("neg_size", [-1, -5, -100])
def test_negative_size_returns_empty_string(neg_size):
    assert target_module.generate_random_string(size=neg_size) == ''

def test_non_integer_size_raises_type_error():
    with pytest.raises(TypeError):
        target_module.generate_random_string(size=3.5)

def test_empty_chars_raises_index_error():
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars='', size=1)

def test_none_chars_raises_type_error():
    with pytest.raises(TypeError):
        target_module.generate_random_string(chars=None, size=1)

def test_monkeypatched_random_choice_called_expected_number_of_times(monkeypatch):
    calls = []
    def fake_choice(seq):
        calls.append(seq)
        # return first element to make output predictable
        return seq[0]
    monkeypatch.setattr(target_module.random, 'choice', fake_choice)
    chars = 'zyx'
    size = 4
    result = target_module.generate_random_string(chars=chars, size=size)
    assert result == chars[0] * size
    assert len(calls) == size
    # each call should have received the same sequence object (chars)
    for call_seq in calls:
        assert call_seq == chars

def test_single_character_chars_repeats():
    chars = 'Q'
    result = target_module.generate_random_string(chars=chars, size=7)
    assert result == 'Q' * 7
    # also works if chars provided as single-item list
    result2 = target_module.generate_random_string(chars=['Z'], size=3)
    assert result2 == 'Z' * 3