import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/urls.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def _extract_regex_string(pattern_obj):
    """
    Try several common attribute access patterns to extract the underlying regex string
    from Django URL pattern objects across versions.
    """
    # Common locations in different Django versions
    attrs_to_try = [
        ("regex", "pattern"),
        ("_regex",),
        ("pattern", "regex", "pattern"),
        ("pattern", "_regex"),
        ("pattern",),
    ]
    for attrs in attrs_to_try:
        current = pattern_obj
        try:
            for a in attrs:
                current = getattr(current, a)
            # At this point current should be a string or a compiled regex; handle both
            if hasattr(current, "pattern"):
                return current.pattern
            if isinstance(current, str):
                return current
        except Exception:
            continue
    # Fallback to str representation
    return str(pattern_obj)


def test_urlpatterns_exists_and_is_list():
    assert hasattr(target_module, "urlpatterns"), "urlpatterns not defined in module"
    urlpatterns = target_module.urlpatterns
    assert isinstance(urlpatterns, (list, tuple)), "urlpatterns should be a list or tuple"
    assert len(urlpatterns) == 2, "Expected exactly 2 URL patterns"


def test_first_pattern_targets_profile_retrieve_view_and_regex():
    pattern = target_module.urlpatterns[0]
    # Ensure callable callback exists
    assert hasattr(pattern, "callback"), "Pattern has no callback attribute"
    callback = pattern.callback
    # The view_class name should match ProfileRetrieveAPIView
    view_class = getattr(callback, "view_class", None)
    assert view_class is not None, "Callback has no view_class attribute"
    assert view_class.__name__ == "ProfileRetrieveAPIView"
    # Regex should capture username and not include 'follow'
    regex = _extract_regex_string(pattern)
    assert r"profiles" in regex
    assert r"(?P<username>\w+)" in regex or r"(?P<username>\\w+)" in regex
    assert "follow" not in regex
    # Should be anchored (contain $) in the source regex
    assert "$" in regex or regex.endswith("$") or "\\$" in regex


def test_second_pattern_targets_profile_follow_view_and_regex():
    pattern = target_module.urlpatterns[1]
    assert hasattr(pattern, "callback"), "Pattern has no callback attribute"
    callback = pattern.callback
    view_class = getattr(callback, "view_class", None)
    assert view_class is not None, "Callback has no view_class attribute"
    assert view_class.__name__ == "ProfileFollowAPIView"
    regex = _extract_regex_string(pattern)
    assert r"profiles" in regex
    assert r"(?P<username>\w+)" in regex or r"(?P<username>\\w+)" in regex
    assert "follow" in regex
    assert "$" in regex or regex.endswith("$") or "\\$" in regex


def test_patterns_are_distinct_objects_and_ordered():
    p0 = target_module.urlpatterns[0]
    p1 = target_module.urlpatterns[1]
    assert p0 is not p1
    # Ensure order corresponds to expected endpoints
    r0 = _extract_regex_string(p0)
    r1 = _extract_regex_string(p1)
    assert "follow" not in r0 and "follow" in r1


def test_pattern_callback_is_callable_and_has_expected_attributes():
    for pattern in target_module.urlpatterns:
        assert hasattr(pattern, "callback")
        cb = pattern.callback
        assert callable(cb)
        # should have view_class attribute from as_view()
        assert hasattr(cb, "view_class")
        vc = cb.view_class
        assert hasattr(vc, "__name__")
        # Ensure docstring or repr present to avoid weird empty classes
        assert isinstance(repr(vc), str) and len(repr(vc)) > 0