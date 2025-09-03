import importlib.util, pathlib
import pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/utils.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_default_behavior_length_and_chars():
    # deterministic check by resetting module random seed
    target_module.random.seed(0)
    s = target_module.generate_random_string()
    assert isinstance(s, str)
    assert len(s) == 6
    # all characters come from DEFAULT_CHAR_STRING
    assert all(ch in target_module.DEFAULT_CHAR_STRING for ch in s)


def test_deterministic_with_seed_and_custom_chars():
    chars = 'ab'
    target_module.random.seed(42)
    s1 = target_module.generate_random_string(chars=chars, size=10)
    target_module.random.seed(42)
    s2 = target_module.generate_random_string(chars=chars, size=10)
    assert s1 == s2
    assert len(s1) == 10
    assert all(ch in chars for ch in s1)


def test_empty_chars_raises_indexerror():
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars='', size=1)


def test_none_chars_raises_typeerror():
    with pytest.raises(TypeError):
        target_module.generate_random_string(chars=None, size=3)


def test_bytes_chars_raises_typeerror_on_join():
    # random.choice will yield ints for bytes; join will then raise TypeError
    with pytest.raises(TypeError):
        target_module.generate_random_string(chars=b'abc', size=3)


def test_negative_size_returns_empty_string():
    s = target_module.generate_random_string(size=-5)
    assert isinstance(s, str)
    assert s == ''


def test_zero_size_returns_empty_string():
    s = target_module.generate_random_string(size=0)
    assert s == ''


def test_size_float_raises_typeerror():
    with pytest.raises(TypeError):
        target_module.generate_random_string(size=2.5)


def test_large_size_and_content():
    size = 1000
    s = target_module.generate_random_string(size=size)
    assert isinstance(s, str)
    assert len(s) == size
    assert all(ch in target_module.DEFAULT_CHAR_STRING for ch in s)


def test_chars_as_list_of_single_characters():
    chars = ['x', 'y', 'z']
    target_module.random.seed(7)
    s = target_module.generate_random_string(chars=chars, size=20)
    assert len(s) == 20
    assert all(ch in ''.join(chars) for ch in s)