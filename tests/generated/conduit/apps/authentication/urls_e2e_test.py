import importlib.util, pathlib
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/authentication/urls.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)

import types
import pytest

def _extract_pattern_string(pat):
    # Try several attribute names used across Django versions
    # RegexURLPattern (old): .regex.pattern
    if hasattr(pat, 'regex'):
        regex = getattr(pat.regex, 'pattern', None)
        if isinstance(regex, str):
            return regex
    # Django 2.0+ might have .pattern which could be object; str() is often informative
    if hasattr(pat, 'pattern'):
        try:
            return str(pat.pattern)
        except Exception:
            pattern_attr = getattr(pat.pattern, '_route', None) or getattr(pat.pattern, 'regex', None)
            if isinstance(pattern_attr, str):
                return pattern_attr
    # Fallbacks
    if hasattr(pat, 'callback'):
        cb = pat.callback
        # Some wrappers may include .__name__ showing pattern; avoid assuming
    return None

def _extract_view_class_name(pat):
    # The callback produced by as_view() should have .view_class attribute
    cb = None
    if hasattr(pat, 'callback'):
        cb = pat.callback
    elif hasattr(pat, 'lookup_str'):  # unlikely, but safe
        cb = getattr(pat, 'lookup_str')
    if cb is None:
        return None
    # cb may be a function with attribute view_class
    return getattr(cb, 'view_class', None).__name__ if getattr(cb, 'view_class', None) is not None else None

def test_urlpatterns_defined_and_is_list():
    assert hasattr(target_module, 'urlpatterns'), "module must define urlpatterns"
    urlpatterns = target_module.urlpatterns
    assert isinstance(urlpatterns, (list, tuple)), "urlpatterns should be a list or tuple"
    assert len(urlpatterns) == 3, "expected exactly 3 URL patterns"

def test_urlpatterns_have_expected_unique_patterns_and_order():
    urlpatterns = list(target_module.urlpatterns)
    patterns = [_extract_pattern_string(p) for p in urlpatterns]
    # Ensure all patterns were extracted
    assert all(p is not None for p in patterns), f"Failed to extract pattern strings: {patterns}"
    # Expected regex strings from source
    expected = ['^user/?$', '^users/?$', '^users/login/?$']
    assert patterns == expected, f"Patterns mismatch. Got {patterns}, expected {expected}"
    # Ensure uniqueness
    assert len(set(patterns)) == len(patterns), "URL patterns should be unique"

def test_urlpatterns_map_to_correct_view_classes():
    urlpatterns = list(target_module.urlpatterns)
    expected_view_names = ['UserRetrieveUpdateAPIView', 'RegistrationAPIView', 'LoginAPIView']
    for pat, expected_name in zip(urlpatterns, expected_view_names):
        view_name = _extract_view_class_name(pat)
        assert view_name == expected_name, f"Expected view class {expected_name} but got {view_name}"

def test_pattern_callbacks_are_callable_and_have_view_class_attr():
    urlpatterns = list(target_module.urlpatterns)
    for pat in urlpatterns:
        # callback must exist and be callable
        assert hasattr(pat, 'callback'), "pattern missing callback attribute"
        cb = pat.callback
        assert callable(cb), "pattern callback must be callable"
        # callback should expose the original class under .view_class
        assert hasattr(cb, 'view_class'), "callback must have view_class attribute from as_view()"

def test_accessing_out_of_range_pattern_index_raises_index_error():
    urlpatterns = list(target_module.urlpatterns)
    with pytest.raises(IndexError):
        _ = urlpatterns[10]

def test_no_unexpected_attributes_on_urlpatterns_items():
    urlpatterns = list(target_module.urlpatterns)
    for pat in urlpatterns:
        # basic sanity: should be an object (not a primitive)
        assert isinstance(pat, object)
        # should have either regex or pattern and a callback
        assert (hasattr(pat, 'regex') or hasattr(pat, 'pattern')), "pattern should have regex or pattern attribute"
        assert hasattr(pat, 'callback'), "pattern should have callback attribute"