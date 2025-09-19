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

import json
import os
import random
from unittest.mock import Mock
try:
    import pytest
except ModuleNotFoundError:
    try:
        import pytest
    except ModuleNotFoundError:
        import importlib.util, sys, os
        _tr=os.environ.get('TARGET_ROOT') or 'target'
        _p1=os.path.join(_tr, 'pytest.py'); _p2=os.path.join(_tr, 'pytest.py')
        _pp=[_p for _p in (_p1,_p2) if os.path.isfile(_p)]
        if _pp:
            _spec=importlib.util.spec_from_file_location('pytest', _pp[0])
            _m=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
            sys.modules.setdefault('pytest', _m)
        else:
            raise

try:
    from target.conduit.apps.core.utils import generate_random_string
    from target.conduit.apps.authentication.renderers import UserJSONRenderer
    from target.conduit.apps.articles.renderers import ArticleJSONRenderer, CommentJSONRenderer
    from target.conduit.apps.profiles.serializers import get_image
    from target.conduit.apps.authentication import AuthenticationAppConfig
    from target.conduit.apps.articles import ArticlesAppConfig
    from target.conduit.apps.core.exceptions import core_exception_handler
    from rest_framework.response import Response
    from rest_framework.exceptions import ValidationError
except ImportError as e:
    pytest.skip("Required project or third-party modules not available: %s" % e, allow_module_level=True)

@pytest.mark.parametrize("length,expected_char", [(1, "A"), (5, "A"), (10, "A")])
def test_generate_random_string_fixed_choice(length, expected_char, monkeypatch):
    
    # Arrange
    monkeypatch.setattr(random, "choice", lambda seq: expected_char)
    # Act
    result = generate_random_string(length)
    # Assert
    assert isinstance(result, str)
    assert len(result) == length
    assert set(result) == {expected_char}

@pytest.mark.parametrize(
    "renderer_class,input_data,expected_key",
    [
        (UserJSONRenderer, {"user": {"email": "x@y.test"}}, "user"),
        (ArticleJSONRenderer, {"article": {"title": "T"}}, "article"),
        (CommentJSONRenderer, {"comment": {"body": "C"}}, "comment"),
    ],
)
def test_json_renderers_produce_bytes_and_valid_json(renderer_class, input_data, expected_key):
    
    # Arrange
    renderer = renderer_class()
    # Act
    rendered = renderer.render(input_data, accepted_media_type=None, renderer_context=None)
    # Assert
    assert isinstance(rendered, (bytes, bytearray))
    parsed = json.loads(rendered.decode("utf-8"))
    assert expected_key in parsed
    assert isinstance(parsed[expected_key], dict)

def test_get_image_handles_missing_files(monkeypatch):
    
    # Arrange
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    # Provide a minimal object that mimics a profile with an image having a url attribute.
    class Img:
        url = "/static/fallback.png"

    class Profile:
        image = Img()

    # Act
    result = get_image(Profile())
    # Assert
    assert isinstance(result, str)
    assert result != ""

@pytest.mark.parametrize("appconfig_class", [AuthenticationAppConfig, ArticlesAppConfig])
def test_appconfig_ready_does_not_raise(appconfig_class):
    
    # Arrange
    # AppConfig signature: AppConfig(name, app_module)
    name = getattr(appconfig_class, "name", appconfig_class.__name__)
    app_module = getattr(appconfig_class, "module", None) or appconfig_class.__module__
    app = appconfig_class(name, app_module)
    
    assert app.ready() is None

def test_core_exception_handler_validation_error_returns_400():
    
    # Arrange
    exc = ValidationError(detail="invalid")
    context = {}
    # Act
    response = core_exception_handler(exc, context)
    # Assert
    assert isinstance(response, Response)
    assert response.status_code == 400
