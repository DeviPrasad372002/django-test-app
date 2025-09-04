import importlib.util, pathlib, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/core/utils.py').resolve()
_IMPORT_ERROR = None
try:
    _SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
    target_module = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(target_module)
except Exception as _e:
    _IMPORT_ERROR = str(_e)
    target_module = None
if _IMPORT_ERROR:
    pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}', allow_module_level=True)

def test_default_length_and_charset_membership():
    # Default size is 6
    s = target_module.generate_random_string()
    assert isinstance(s, str)
    assert len(s) == 6
    # All characters should come from DEFAULT_CHAR_STRING
    for ch in s:
        assert ch in target_module.DEFAULT_CHAR_STRING

def test_custom_single_char_returns_repeated_char():
    # If chars contains only one character, result should be repeated same char
    res = target_module.generate_random_string(chars='Z', size=4)
    assert res == 'Z' * 4

def test_zero_size_returns_empty_string():
    assert target_module.generate_random_string(size=0) == ''

def test_negative_size_returns_empty_string():
    # range with negative produces empty iteration => empty string
    assert target_module.generate_random_string(size=-5) == ''

def test_non_integer_size_raises_type_error():
    # Passing a non-integer to range should raise a TypeError
    with pytest.raises(TypeError):
        target_module.generate_random_string(size=2.5)

def test_empty_chars_raises_index_error():
    # random.choice on empty sequence raises IndexError
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars='', size=3)

def test_monkeypatched_random_choice_returns_deterministic_and_receives_chars(monkeypatch):
    # Recorder that returns the first element of the sequence and records calls
    calls = []
    def fake_choice(seq):
        calls.append(seq)
        return seq[0]
    monkeypatch.setattr(target_module.random, 'choice', fake_choice)

    out = target_module.generate_random_string(chars='abc', size=5)
    # Should be 'a' repeated 5 times because fake_choice returns seq[0]
    assert out == 'a' * 5
    # Ensure random.choice was called exactly 'size' times and with the provided chars each time
    assert calls == ['abc'] * 5

    # Also test default charset is passed when chars is omitted
    calls.clear()
    out2 = target_module.generate_random_string(size=3)
    assert out2 == target_module.DEFAULT_CHAR_STRING[0] * 3
    assert calls == [target_module.DEFAULT_CHAR_STRING] * 3

def test_monkeypatched_random_choice_is_called_correct_number_of_times(monkeypatch):
    # Ensure the patched function is called exactly 'size' times
    counter = {'n': 0}
    def counting_choice(seq):
        counter['n'] += 1
        # Return last character just to vary
        return seq[-1]
    monkeypatch.setattr(target_module.random, 'choice', counting_choice)

    size = 7
    res = target_module.generate_random_string(chars='xyz', size=size)
    assert len(res) == size
    assert counter['n'] == size
    # Each returned char should be the last of 'xyz' => 'z'
    assert res == 'z' * size