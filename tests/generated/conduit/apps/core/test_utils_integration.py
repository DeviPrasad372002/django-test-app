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

def test_default_chars_and_length_monkeypatched(monkeypatch):
    # Ensure the DEFAULT_CHAR_STRING is used and size default is 6
    seen_chars = []
    def fake_choice(chars):
        # record the chars argument for each call and return first char to be deterministic
        seen_chars.append(chars)
        return chars[0]
    monkeypatch.setattr(target_module.random, "choice", fake_choice)

    result = target_module.generate_random_string()
    # default size is 6
    assert isinstance(result, str)
    assert len(result) == 6
    # since fake_choice returned first char every time, all chars are same
    assert result == target_module.DEFAULT_CHAR_STRING[0] * 6
    # every call should have been passed the DEFAULT_CHAR_STRING
    assert all(c is target_module.DEFAULT_CHAR_STRING or c == target_module.DEFAULT_CHAR_STRING for c in seen_chars)
    assert len(seen_chars) == 6

def test_custom_chars_and_size(monkeypatch):
    # Use a small custom charset and size to ensure choices come from it
    seen = []
    def fake_choice(chars):
        seen.append(chars)
        return 'b' if 'b' in chars else chars[0]
    monkeypatch.setattr(target_module.random, "choice", fake_choice)

    res = target_module.generate_random_string(chars='ab', size=4)
    assert res == 'b' * 4
    assert len(seen) == 4
    assert all(s == 'ab' for s in seen)

def test_empty_chars_raises_index_error():
    # random.choice on empty sequence should raise IndexError
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars='', size=1)

def test_size_zero_no_choice_called(monkeypatch):
    # If size is zero, random.choice should not be called
    def fake_choice(_):
        raise AssertionError("random.choice should not be called for size=0")
    monkeypatch.setattr(target_module.random, "choice", fake_choice)

    res = target_module.generate_random_string(chars='abc', size=0)
    assert res == ''

def test_negative_size_returns_empty_and_no_choice(monkeypatch):
    # Negative sizes produce an empty range; random.choice should not be called
    def fake_choice(_):
        raise AssertionError("random.choice should not be called for negative size")
    monkeypatch.setattr(target_module.random, "choice", fake_choice)

    res = target_module.generate_random_string(chars='abc', size=-5)
    assert res == ''

def test_non_int_size_raises_type_error():
    # Passing a non-int to size should raise a TypeError from range()
    with pytest.raises(TypeError):
        target_module.generate_random_string(chars='abc', size=3.5)

def test_large_size_performance_and_content(monkeypatch):
    # For a large size, ensure correct length and content when random.choice is deterministic
    def fake_choice(_):
        return 'x'
    monkeypatch.setattr(target_module.random, "choice", fake_choice)

    n = 1000
    res = target_module.generate_random_string(chars='xyz', size=n)
    assert len(res) == n
    assert res == 'x' * n

def test_default_char_string_value():
    import string as _string
    expected = _string.ascii_lowercase + _string.digits
    assert target_module.DEFAULT_CHAR_STRING == expected