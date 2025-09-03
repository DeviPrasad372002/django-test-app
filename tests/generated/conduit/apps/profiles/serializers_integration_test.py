import importlib.util, pathlib
import types
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/serializers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_get_image_returns_default_when_none():
    class Obj:
        image = None

    # Call the unbound method directly; self is not used by get_image
    result = target_module.ProfileSerializer.get_image(None, Obj())
    assert result == 'https://static.productionready.io/images/smiley-cyrus.jpg'


def test_get_image_returns_value_when_present():
    class Obj:
        image = 'http://example.com/pic.jpg'

    result = target_module.ProfileSerializer.get_image(None, Obj())
    assert result == 'http://example.com/pic.jpg'


def test_get_following_returns_false_when_no_request_in_context():
    dummy_self = types.SimpleNamespace(context={})
    followee = object()
    result = target_module.ProfileSerializer.get_following(dummy_self, followee)
    assert result is False


def test_get_following_returns_false_when_user_not_authenticated():
    class User:
        def is_authenticated(self):
            return False

        profile = None  # shouldn't be accessed

    class Request:
        user = User()

    dummy_self = types.SimpleNamespace(context={'request': Request()})
    followee = object()
    result = target_module.ProfileSerializer.get_following(dummy_self, followee)
    assert result is False


def test_get_following_returns_true_when_follower_reports_following():
    # follower.is_following should be called with the followee instance
    class Follower:
        def __init__(self):
            self.called_with = None

        def is_following(self, followee):
            self.called_with = followee
            return True

    follower = Follower()

    class User:
        def is_authenticated(self):
            return True

        profile = follower

    class Request:
        user = User()

    dummy_self = types.SimpleNamespace(context={'request': Request()})
    followee = object()
    result = target_module.ProfileSerializer.get_following(dummy_self, followee)
    assert result is True
    assert follower.called_with is followee


def test_get_following_returns_false_when_follower_reports_not_following():
    class Follower:
        def is_following(self, followee):
            return False

    follower = Follower()

    class User:
        def is_authenticated(self):
            return True

        profile = follower

    class Request:
        user = User()

    dummy_self = types.SimpleNamespace(context={'request': Request()})
    followee = object()
    result = target_module.ProfileSerializer.get_following(dummy_self, followee)
    assert result is False


def test_get_following_raises_attribute_error_when_user_has_no_profile():
    class User:
        def is_authenticated(self):
            return True

    class Request:
        user = User()

    dummy_self = types.SimpleNamespace(context={'request': Request()})
    followee = object()
    with pytest.raises(AttributeError):
        target_module.ProfileSerializer.get_following(dummy_self, followee)


def test_get_following_raises_type_error_when_is_authenticated_not_callable():
    # If is_authenticated is a boolean (as in some Django versions it's a property),
    # the code attempts to call it; that should raise a TypeError.
    class User:
        is_authenticated = True
        profile = types.SimpleNamespace(is_following=lambda x: True)

    class Request:
        user = User()

    dummy_self = types.SimpleNamespace(context={'request': Request()})
    followee = object()
    with pytest.raises(TypeError):
        target_module.ProfileSerializer.get_following(dummy_self, followee)