import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/utils.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_default_length_and_chars():
    result = target_module.generate_random_string()
    assert isinstance(result, str)
    assert len(result) == 6
    for ch in result:
        assert ch in target_module.DEFAULT_CHAR_STRING


def test_custom_chars_and_size_with_monkeypatch(monkeypatch):
    # make random.choice deterministic to pick the second character of the provided chars
    def fake_choice(seq):
        return seq[1]
    monkeypatch.setattr(target_module.random, 'choice', fake_choice)

    result = target_module.generate_random_string(chars='ABC', size=4)
    assert result == 'B' * 4


def test_zero_and_negative_size_returns_empty_string():
    assert target_module.generate_random_string(size=0) == ''
    # negative sizes produce an empty range => empty string
    assert target_module.generate_random_string(size=-1) == ''
    assert target_module.generate_random_string(size=-10) == ''


def test_non_integer_size_raises_type_error():
    with pytest.raises(TypeError):
        target_module.generate_random_string(size='3')
    with pytest.raises(TypeError):
        target_module.generate_random_string(size=3.5)


def test_empty_chars_raises_index_error():
    # random.choice on empty sequence should raise IndexError
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars='', size=1)


def test_non_string_elements_in_chars_raise_type_error():
    # If chars yields non-str elements, ''.join(...) should raise a TypeError
    with pytest.raises(TypeError):
        target_module.generate_random_string(chars=[1, 2, 3], size=2)


def test_large_size_returns_expected_length():
    size = 1000
    result = target_module.generate_random_string(size=size)
    assert isinstance(result, str)
    assert len(result) == size


def test_tuple_chars_work_and_all_chars_from_sequence(monkeypatch):
    # use a tuple of single-character strings and deterministic choice
    seq = ('x', 'y', 'z')
    def fake_choice(seq_in):
        # always return last element to make result predictable
        return seq_in[-1]
    monkeypatch.setattr(target_module.random, 'choice', fake_choice)

    result = target_module.generate_random_string(chars=seq, size=5)
    assert result == 'z' * 5
    for ch in result:
        assert ch in seq