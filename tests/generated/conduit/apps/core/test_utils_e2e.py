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

def test_default_length_and_allowed_chars():
    # Default size is 6
    result = target_module.generate_random_string()
    assert isinstance(result, str)
    assert len(result) == 6
    # All chars in result should be from DEFAULT_CHAR_STRING
    allowed = set(target_module.DEFAULT_CHAR_STRING)
    assert all(ch in allowed for ch in result)

@pytest.mark.parametrize("chars,size", [
    ("abc", 10),
    (list("XYZ"), 5),
])
def test_custom_chars_and_size(chars, size):
    result = target_module.generate_random_string(chars=chars, size=size)
    assert isinstance(result, str)
    assert len(result) == size
    # For list case, ensure each character in result is one of the allowed single-character elements
    allowed = set(chars)
    assert all(ch in allowed for ch in result)

def test_zero_size_returns_empty():
    assert target_module.generate_random_string(size=0) == ""

def test_negative_size_returns_empty():
    # range of negative yields empty iterator -> join over empty -> empty string
    assert target_module.generate_random_string(size=-5) == ""

def test_empty_chars_raises_index_error():
    # random.choice on empty sequence raises IndexError; ensure it's propagated
    with pytest.raises(IndexError):
        target_module.generate_random_string(chars="", size=1)

def test_bytes_chars_raises_type_error():
    # random.choice on bytes yields ints, joining ints into a string should raise TypeError
    with pytest.raises(TypeError):
        target_module.generate_random_string(chars=b"abc", size=3)

def test_monkeypatched_random_choice_deterministic(monkeypatch):
    # Force random.choice to return a constant value to get deterministic output
    monkeypatch.setattr(target_module.random, "choice", lambda c: "Z")
    res = target_module.generate_random_string(chars="abc", size=8)
    assert res == "Z" * 8

def test_large_size_performance_and_content():
    size = 1000
    res = target_module.generate_random_string(size=size)
    assert isinstance(res, str)
    assert len(res) == size
    allowed = set(target_module.DEFAULT_CHAR_STRING)
    assert all(ch in allowed for ch in res)

def test_chars_with_multi_char_elements():
    # If chars is a list of multi-character strings, join will concatenate chosen elements.
    chars = ["aa", "bb", "cc"]
    # Monkeypatch random.choice to cycle through elements deterministically
    seq = ["aa", "bb", "cc"]
    calls = {"i": 0}
    def chooser(c):
        val = seq[calls["i"] % len(seq)]
        calls["i"] += 1
        return val
    # Patch and call
    import types
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(target_module.random, "choice", chooser)
        res = target_module.generate_random_string(chars=chars, size=3)
        # Expect concatenation of the three selected multi-char strings
        assert res == "aabbcc"
    finally:
        monkeypatch.undo()