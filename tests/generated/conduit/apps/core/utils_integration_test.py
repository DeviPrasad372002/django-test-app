import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/utils.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_default_behavior_with_monkeypatched_choice(monkeypatch):
    # Make random.choice deterministic: always pick first character
    def always_first(chars):
        return chars[0]
    monkeypatch.setattr(target_module.random, "choice", always_first)
    result = target_module.generate_random_string()
    assert isinstance(result, str)
    assert result == target_module.DEFAULT_CHAR_STRING[0] * 6
    assert len(result) == 6


def test_custom_chars_and_size_sequence_choice(monkeypatch):
    seq = iter(['A', 'B', 'A', 'B'])
    def choice_from_sequence(chars):
        return next(seq)
    monkeypatch.setattr(target_module.random, "choice", choice_from_sequence)
    result = target_module.generate_random_string(chars='AB', size=4)
    assert result == "ABAB"
    assert all(c in 'AB' for c in result)


def test_size_zero_returns_empty_string():
    result = target_module.generate_random_string(size=0)
    assert result == ""
    assert isinstance(result, str)


def test_negative_size_returns_empty_string():
    # range with negative size yields no iterations -> empty string
    result = target_module.generate_random_string(size=-5)
    assert result == ""
    assert isinstance(result, str)


def test_non_int_size_raises_type_error():
    with pytest.raises(TypeError):
        target_module.generate_random_string(size=3.5)
    with pytest.raises(TypeError):
        target_module.generate_random_string(size="4")


def test_empty_chars_raises_index_error():
    # Choosing from an empty sequence should raise IndexError when size > 0
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars='', size=1)


def test_none_chars_raises_type_error():
    # random.choice(None) should raise a TypeError
    with pytest.raises(TypeError):
        target_module.generate_random_string(chars=None, size=1)


def test_result_characters_are_within_provided_charset():
    # Use a seeded RNG to make selection deterministic enough for the assertion
    target_module.random.seed(1)
    chars = 'abcd'
    result = target_module.generate_random_string(chars=chars, size=10)
    assert len(result) == 10
    assert all(c in chars for c in result)


def test_default_chars_used_when_not_provided():
    # Ensure default charset is used by checking output characters belong to DEFAULT_CHAR_STRING
    target_module.random.seed(2)
    result = target_module.generate_random_string(size=8)
    assert len(result) == 8
    assert all(c in target_module.DEFAULT_CHAR_STRING for c in result)