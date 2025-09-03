import importlib.util, pathlib
import pytest
from rest_framework.exceptions import APIException

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/exceptions.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_class_attributes():
    # Ensure the class exposes the configured HTTP status and default detail
    cls = target_module.ProfileDoesNotExist
    assert hasattr(cls, "status_code")
    assert cls.status_code == 400
    assert hasattr(cls, "default_detail")
    assert cls.default_detail == "The requested profile does not exist."


def test_instance_default_behavior():
    # Instantiating without args uses the default detail and exposes status_code
    ex = target_module.ProfileDoesNotExist()
    # status_code should be available on instance
    assert hasattr(ex, "status_code")
    assert ex.status_code == 400
    # detail should reflect the default_detail; comparing string form for robustness
    assert str(ex.detail) == target_module.ProfileDoesNotExist.default_detail
    assert ex.detail == target_module.ProfileDoesNotExist.default_detail


def test_instance_custom_detail_override():
    # Providing a custom detail should override the default_detail
    custom = "custom profile missing"
    ex = target_module.ProfileDoesNotExist(detail=custom)
    assert str(ex.detail) == custom
    assert ex.detail == custom
    # status_code remains the class-defined value
    assert ex.status_code == 400


def test_raise_and_catch_exception_contents():
    # When raised, caught exception should present same detail and status_code
    try:
        raise target_module.ProfileDoesNotExist()
    except target_module.ProfileDoesNotExist as e:
        assert isinstance(e, target_module.ProfileDoesNotExist)
        assert str(e.detail) == target_module.ProfileDoesNotExist.default_detail
        assert e.status_code == 400
    else:
        pytest.fail("ProfileDoesNotExist was not raised")


def test_non_string_detail_preserved():
    # Passing a non-string detail (e.g., dict) should preserve the value
    payload = {"user": "alice", "reason": "not found"}
    ex = target_module.ProfileDoesNotExist(detail=payload)
    assert ex.detail == payload
    # And status_code is unchanged
    assert ex.status_code == 400


def test_empty_string_detail_is_allowed():
    # Empty string is treated as a provided detail (not replaced by default)
    ex = target_module.ProfileDoesNotExist(detail="")
    assert ex.detail == ""
    assert str(ex.detail) == ""
    assert ex.status_code == 400


def test_inherits_api_exception():
    # Confirm the class and instance subclass DRF's APIException
    cls = target_module.ProfileDoesNotExist
    assert issubclass(cls, APIException)
    inst = cls()
    assert isinstance(inst, APIException)