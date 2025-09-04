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

def test_default_behavior_length_and_allowed_chars():
    # Default size is 6
    s = target_module.generate_random_string()
    assert isinstance(s, str)
    assert len(s) == 6
    # All characters should come from the DEFAULT_CHAR_STRING
    allowed = set(target_module.DEFAULT_CHAR_STRING)
    assert all(ch in allowed for ch in s)

def test_custom_chars_and_size_with_deterministic_choice(monkeypatch):
    # Make random.choice deterministic by always returning the first element
    def always_first(seq):
        return seq[0]
    monkeypatch.setattr(target_module.random, "choice", always_first)
    res = target_module.generate_random_string(chars="ab", size=10)
    assert res == "a" * 10

def test_size_zero_returns_empty_string():
    res = target_module.generate_random_string(size=0)
    assert res == ""
    assert isinstance(res, str)

def test_negative_size_returns_empty_string():
    # range with negative size yields empty iteration -> empty string
    res = target_module.generate_random_string(size=-5)
    assert res == ""
    assert isinstance(res, str)

def test_empty_chars_raises_index_error():
    # random.choice on empty sequence should raise IndexError
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars="", size=1)

def test_none_chars_raises_type_error():
    # random.choice expects a sequence; None should raise TypeError
    with pytest.raises(TypeError):
        target_module.generate_random_string(chars=None, size=1)

def test_non_integer_size_raises_type_error():
    # range expects integer; float should raise a TypeError before random.choice is called
    with pytest.raises(TypeError):
        target_module.generate_random_string(size=2.5)

def test_large_size_with_monkeypatched_choice_is_fast(monkeypatch):
    # Ensure function can handle larger sizes when choice is cheap
    monkeypatch.setattr(target_module.random, "choice", lambda seq: seq[-1])
    large_n = 5000
    res = target_module.generate_random_string(chars="xyz", size=large_n)
    assert len(res) == large_n
    assert set(res) == {"z"}  # since lambda returns last element

def test_default_char_string_contains_expected_characters():
    # Sanity check for DEFAULT_CHAR_STRING contents (lowercase letters and digits)
    ds = target_module.DEFAULT_CHAR_STRING
    assert all(ch.islower() or ch.isdigit() for ch in ds)
    # ensure at least one digit and one letter present
    assert any(ch.isdigit() for ch in ds)
    assert any(ch.isalpha() for ch in ds)