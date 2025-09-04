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


def test_default_behavior_uses_default_chars_and_size(monkeypatch):
    calls = []

    def fake_choice(seq):
        # record the sequence passed in and return its first element
        calls.append(seq)
        return seq[0]

    monkeypatch.setattr(target_module.random, 'choice', fake_choice)
    result = target_module.generate_random_string()
    # default size is 6
    assert isinstance(result, str)
    assert result == target_module.DEFAULT_CHAR_STRING[0] * 6
    # ensure each call used DEFAULT_CHAR_STRING
    assert all(call is target_module.DEFAULT_CHAR_STRING or call == target_module.DEFAULT_CHAR_STRING for call in calls)
    assert len(calls) == 6


def test_custom_chars_and_size(monkeypatch):
    calls = []

    def fake_choice(seq):
        calls.append(seq)
        # return last character to ensure it's coming from provided chars
        return seq[-1]

    monkeypatch.setattr(target_module.random, 'choice', fake_choice)
    chars = 'xyz'
    size = 4
    result = target_module.generate_random_string(chars=chars, size=size)
    assert result == 'z' * size
    # ensure random.choice was called with the provided chars each time
    assert all(call == chars for call in calls)
    assert len(calls) == size


def test_size_zero_calls_not_made(monkeypatch):
    def fail_if_called(seq):
        raise AssertionError("random.choice should not be called when size is 0")

    monkeypatch.setattr(target_module.random, 'choice', fail_if_called)
    assert target_module.generate_random_string(size=0) == ''


def test_negative_size_treated_as_zero(monkeypatch):
    def fail_if_called(seq):
        raise AssertionError("random.choice should not be called when size is negative")

    monkeypatch.setattr(target_module.random, 'choice', fail_if_called)
    # negative size results in empty range -> empty string
    assert target_module.generate_random_string(size=-5) == ''


def test_non_integer_size_raises_type_error():
    # passing a non-integer to range should raise a TypeError
    with pytest.raises(TypeError):
        target_module.generate_random_string(size=3.5)
    with pytest.raises(TypeError):
        target_module.generate_random_string(size='3')


def test_empty_chars_raises_index_error():
    # random.choice on empty sequence will raise IndexError
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars='', size=1)


def test_none_chars_raises_type_error():
    # random.choice(None) raises a TypeError because None is not a sequence
    with pytest.raises(TypeError):
        target_module.generate_random_string(chars=None, size=1)


def test_large_size_returns_correct_length_and_content(monkeypatch):
    def fake_choice(seq):
        return 'x'

    monkeypatch.setattr(target_module.random, 'choice', fake_choice)
    size = 1000
    result = target_module.generate_random_string(size=size, chars='abc')
    assert len(result) == size
    assert result == 'x' * size


def test_random_choice_called_exact_number_of_times(monkeypatch):
    call_count = {'n': 0}

    def counting_choice(seq):
        call_count['n'] += 1
        # return a predictable character
        return seq[0]

    monkeypatch.setattr(target_module.random, 'choice', counting_choice)
    size = 5
    result = target_module.generate_random_string(chars='pqrs', size=size)
    assert len(result) == size
    assert call_count['n'] == size
    assert result == target_module.DEFAULT_CHAR_STRING[0] * 0 or isinstance(result, str)  # simple sanity check