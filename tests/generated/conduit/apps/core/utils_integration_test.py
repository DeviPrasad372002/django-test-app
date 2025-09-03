import importlib.util, pathlib
import random
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/utils.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_generate_random_string_reproducible_with_seed_default():
    random.seed(12345)
    a = target_module.generate_random_string()
    random.seed(12345)
    b = target_module.generate_random_string()
    assert isinstance(a, str)
    assert a == b
    assert len(a) == 6
    assert all(ch in target_module.DEFAULT_CHAR_STRING for ch in a)


def test_generate_random_string_custom_chars_and_size_reproducible():
    chars = "ABC123"
    size = 10
    random.seed(999)
    s1 = target_module.generate_random_string(chars=chars, size=size)
    random.seed(999)
    s2 = target_module.generate_random_string(chars=chars, size=size)
    assert s1 == s2
    assert len(s1) == size
    assert all(ch in chars for ch in s1)


def test_generate_random_string_size_zero_returns_empty_string():
    random.seed(1)
    result = target_module.generate_random_string(size=0)
    assert result == ""
    assert isinstance(result, str)


def test_generate_random_string_negative_size_returns_empty_string():
    # range with negative size yields no iterations, should return empty string
    result = target_module.generate_random_string(size=-5)
    assert result == ""
    assert isinstance(result, str)


def test_generate_random_string_non_integer_size_raises_type_error():
    with pytest.raises(TypeError):
        target_module.generate_random_string(size=2.5)


def test_generate_random_string_empty_chars_raises_index_error():
    # Attempting to choose from an empty sequence should raise IndexError
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars="", size=1)


def test_generate_random_string_accepts_list_of_chars():
    chars_list = ['x', 'y', 'z']
    random.seed(42)
    s = target_module.generate_random_string(chars=chars_list, size=5)
    assert len(s) == 5
    assert all(ch in chars_list for ch in s)


def test_generate_random_string_default_chars_constant_untouched():
    # Ensure DEFAULT_CHAR_STRING is as expected (lowercase letters + digits)
    expected = __import__('string').ascii_lowercase + __import__('string').digits
    assert target_module.DEFAULT_CHAR_STRING == expected