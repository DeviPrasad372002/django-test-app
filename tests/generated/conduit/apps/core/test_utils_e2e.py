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

def test_default_behavior_length_and_charset():
    # Default size is 6
    s = target_module.generate_random_string()
    assert isinstance(s, str)
    assert len(s) == 6
    # All chars should be from DEFAULT_CHAR_STRING
    allowed = set(target_module.DEFAULT_CHAR_STRING)
    assert all(ch in allowed for ch in s)

def test_custom_chars_and_size_with_list():
    chars = ['A', 'B', 'C']
    size = 10
    s = target_module.generate_random_string(chars=chars, size=size)
    assert isinstance(s, str)
    assert len(s) == size
    assert set(s).issubset(set(chars))

def test_custom_chars_and_size_with_tuple():
    chars = ('x', 'y')
    size = 4
    s = target_module.generate_random_string(chars=chars, size=size)
    assert len(s) == size
    assert set(s).issubset(set(chars))

def test_zero_size_returns_empty_string():
    s = target_module.generate_random_string(size=0)
    assert s == ''

def test_negative_size_returns_empty_string():
    # range with negative size produces no iterations -> empty string
    s = target_module.generate_random_string(size=-5)
    assert s == ''

def test_non_int_size_raises_type_error():
    # Passing a non-int (float) should raise TypeError from range()
    with pytest.raises(TypeError):
        target_module.generate_random_string(size=3.5)

def test_empty_chars_raises_index_error():
    # random.choice on empty sequence raises IndexError
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars='', size=1)

def test_none_chars_raises_type_error():
    # random.choice with None raises TypeError
    with pytest.raises(TypeError):
        target_module.generate_random_string(chars=None, size=1)

def test_monkeypatched_choice_produces_repeated_char(monkeypatch):
    # Force deterministic output by patching random.choice to always return 'z'
    def fake_choice(_seq):
        return 'z'
    monkeypatch.setattr(target_module.random, 'choice', fake_choice)
    s = target_module.generate_random_string(chars='abc', size=8)
    assert s == 'z' * 8

def test_random_choice_called_exact_number_of_times(monkeypatch):
    # Count how many times random.choice is called
    calls = {'n': 0}
    def counting_choice(seq):
        calls['n'] += 1
        # Always return the first item to keep result predictable
        return seq[0]
    monkeypatch.setattr(target_module.random, 'choice', counting_choice)
    size = 7
    s = target_module.generate_random_string(chars='xyz', size=size)
    assert calls['n'] == size
    assert s == 'x' * size

def test_large_size_output_properties():
    # Ensure function can handle a reasonably large size and output constraints
    size = 1000
    s = target_module.generate_random_string(size=size)
    assert len(s) == size
    allowed = set(target_module.DEFAULT_CHAR_STRING)
    assert set(s).issubset(allowed)