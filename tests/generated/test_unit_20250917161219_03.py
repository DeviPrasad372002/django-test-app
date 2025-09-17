import importlib.util, pytest
if importlib.util.find_spec('django') is None:
    pytest.skip('django not installed; skipping module', allow_module_level=True)

import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

try:
    import json
    import pytest
    from django.http import Http404
    from rest_framework.response import Response
    import conduit.apps.core.utils as core_utils_mod
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.core.exceptions import (
        core_exception_handler,
        _handle_generic_error,
        _handle_not_found_error,
    )
    from conduit.apps.authentication.renderers import render as auth_render
except ImportError as exc:  # pragma: no cover - missing third-party / project modules
    import pytest
    pytest.skip(f"Skipping tests: required import failed: {exc}", allow_module_level=True)

def test_generate_random_string_deterministic_with_monkeypatched_choice(monkeypatch):
    
    # Arrange
    monkeypatch.setattr("conduit.apps.core.utils.random.choice", lambda seq: "x")
    # Act
    out = generate_random_string(6)
    # Assert
    assert isinstance(out, str)
    assert out == "x" * 6
    # Also ensure the module-level random referred to is the one we patched
    assert core_utils_mod.random.choice("abc") == "x"

def test_handle_not_found_returns_404_response():
    
    # Arrange
    exc = Http404("not here")
    # Act
    resp = _handle_not_found_error(exc, context={})
    # Assert
    assert isinstance(resp, Response)
    assert resp.status_code == 404
    assert isinstance(resp.data, dict)

def test_handle_generic_error_returns_500_response():
    
    # Arrange
    exc = Exception("unexpected")
    # Act
    resp = _handle_generic_error(exc, context={})
    # Assert
    assert isinstance(resp, Response)
    assert resp.status_code >= 500
    assert isinstance(resp.data, dict)

def test_core_exception_handler_delegates_to_specific_handlers():
    
    # Arrange
    notfound = Http404("missing")
    generic = Exception("boom")
    # Act
    resp_notfound = core_exception_handler(notfound, context={})
    expected_notfound = _handle_not_found_error(notfound, context={})
    resp_generic = core_exception_handler(generic, context={})
    expected_generic = _handle_generic_error(generic, context={})
    # Assert - compare concrete attributes
    assert isinstance(resp_notfound, Response)
    assert resp_notfound.status_code == expected_notfound.status_code
    assert resp_notfound.data == expected_notfound.data
    assert isinstance(resp_generic, Response)
    assert resp_generic.status_code == expected_generic.status_code
    assert resp_generic.data == expected_generic.data

def test_auth_renderer_render_produces_json_bytes_and_contains_user_key():
    
    # Arrange
    payload = {"user": {"username": "tester", "email": "t@example.com"}}
    # Act
    out = auth_render(payload, accepted_media_type=None, renderer_context=None)
    # Assert
    assert isinstance(out, (bytes, bytearray))
    parsed = json.loads(out.decode("utf-8"))
    assert isinstance(parsed, dict)
    assert "user" in parsed
    assert parsed["user"]["username"] == "tester"
    assert parsed["user"]["email"] == "t@example.com"
