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

import inspect
import types

try:
    import pytest
    from conduit.apps import profiles
    from conduit.apps.profiles import models as profiles_models
    from conduit.apps.profiles import serializers as profiles_serializers
    from conduit.apps.articles import models as articles_models
except Exception:
    import pytest
    pytest.skip("conduit modules not available", allow_module_level=True)

class DummyUser:
    def __init__(self, username, container_type=list):
        self.username = username
        # some implementations use lists, others use sets
        self.following = container_type()
        self.followers = container_type()
        # favorites sometimes on user or article; include both
        self.favorites = container_type()
        # image for serializer tests
        self.image = f"https://example.com/{username}.png"

    def __repr__(self):
        return f"<DummyUser {self.username}>"

    def __hash__(self):
        # allow use in sets
        return hash(self.username)

    def __eq__(self, other):
        return getattr(other, "username", None) == self.username

class DummyArticle:
    def __init__(self, slug="test-article", container_type=list):
        self.slug = slug
        
        self.favorited_by = container_type()

    def __repr__(self):
        return f"<DummyArticle {self.slug}>"

def _call_flexible(func, *args):
    """
    Attempt common calling conventions for integration points in this codebase:
    - func(a, b)
    - func(self=a, profile=b) or variations by param name
    - func(obj) or func(instance)
    Raises the last TypeError if none match.
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())

    # Direct call first
    try:
        return func(*args)
    except TypeError as e_first:
        last_exc = e_first

    # Try mapping by common names if two args provided
    if len(args) >= 2:
        a, b = args[0], args[1]
        mapping_options = [
            {"self": a, "profile": b},
            {"self": a, "user": b},
            {"follower": a, "followee": b},
            {"follower": a, "profile": b},
            {"user": a, "article": b},
            {"user": a, "obj": b},
            {"profile": a, "obj": b},
            {"instance": a, "obj": b},
        ]
        for mapping in mapping_options:
            try:
                return func(**{k: v for k, v in mapping.items() if k in params})
            except TypeError as e:
                last_exc = e

    # Try single-argument call
    try:
        return func(args[0])
    except TypeError as e:
        last_exc = e

    # Final attempt: call with no args
    try:
        return func()
    except TypeError as e:
        last_exc = e

    raise last_exc

@pytest.mark.parametrize("container_type", [list, set])
def test_profile_follow_unfollow_is_followed_by(container_type):
    # Arrange
    alice = DummyUser("alice", container_type=container_type)
    bob = DummyUser("bob", container_type=container_type)

    # Ensure starting state: no following/followers
    assert (bob not in getattr(alice, "following", [])) and (alice not in getattr(bob, "followers", []))

    # Act: follow
    # Many implementations define profiles_models.follow(self, profile) or follow(user, profile)
    _call_flexible(profiles_models.follow, alice, bob)

    
    if isinstance(alice.following, set):
        assert bob in alice.following
    else:
        assert any(getattr(u, "username", None) == "bob" for u in alice.following)

    if isinstance(bob.followers, set):
        assert alice in bob.followers
    else:
        assert any(getattr(u, "username", None) == "alice" for u in bob.followers)

    # Act & Assert: is_following / is_followed_by should reflect relationship
    res_is_following = _call_flexible(profiles_models.is_following, alice, bob)
    assert isinstance(res_is_following, bool)
    assert res_is_following is True

    res_is_followed_by = _call_flexible(profiles_models.is_followed_by, bob, alice)
    assert isinstance(res_is_followed_by, bool)
    assert res_is_followed_by is True

    # Act: unfollow
    _call_flexible(profiles_models.unfollow, alice, bob)

    # Assert: relationship removed
    if isinstance(alice.following, set):
        assert bob not in alice.following
    else:
        assert all(getattr(u, "username", None) != "bob" for u in alice.following)

    if isinstance(bob.followers, set):
        assert alice not in bob.followers
    else:
        assert all(getattr(u, "username", None) != "alice" for u in bob.followers)

    # And checks
    assert _call_flexible(profiles_models.is_following, alice, bob) is False
    assert _call_flexible(profiles_models.is_followed_by, bob, alice) is False

@pytest.mark.parametrize("container_type", [list, set])
def test_favorite_unfavorite_has_favorited(container_type):
    # Arrange
    user = DummyUser("charlie", container_type=container_type)
    article = DummyArticle(slug="fav-test", container_type=container_type)

    # Ensure starting state
    assert (user not in getattr(article, "favorited_by", []))
    assert (getattr(user, "favorites", None) is not None)

    # Act: favorite
    _call_flexible(profiles_models.favorite, user, article)

    
    if isinstance(article.favorited_by, set):
        assert user in article.favorited_by
    else:
        assert any(getattr(u, "username", None) == "charlie" for u in article.favorited_by)

    res_has = _call_flexible(profiles_models.has_favorited, user, article)
    assert isinstance(res_has, bool)
    assert res_has is True

    # Act: unfavorite
    _call_flexible(profiles_models.unfavorite, user, article)

    # Assert: removed and has_favorited False
    if isinstance(article.favorited_by, set):
        assert user not in article.favorited_by
    else:
        assert all(getattr(u, "username", None) != "charlie" for u in article.favorited_by)

    assert _call_flexible(profiles_models.has_favorited, user, article) is False

def test_get_image_and_get_following_serializer_variants(monkeypatch):
    # Arrange a user / profile
    user = DummyUser("dana", container_type=list)
    # Some serializer functions might look for attribute 'image' or nested profile.image
    # Provide both keyed and nested structures
    class Wrapper:
        def __init__(self, inner):
            self.profile = inner

    wrapped = Wrapper(user)

    # Determine get_image signature and try different inputs
    get_image_func = getattr(profiles_serializers, "get_image", None)
    assert callable(get_image_func)

    # Act/Assert: ensure it returns the expected URL when user object provided
    try:
        val = _call_flexible(get_image_func, user)
    except TypeError:
        # fallback: maybe expects object with 'profile'
        val = _call_flexible(get_image_func, wrapped)
    assert isinstance(val, (str, type(None)))
    assert val == "https://example.com/dana.png"

    # get_following often requires serializer context (e.g., to know requesting user)
    get_following_func = getattr(profiles_serializers, "get_following", None)
    assert callable(get_following_func)

    # Create another user that will be followed by 'user'
    target = DummyUser("ellen", container_type=list)
    # Ensure user is following target
    if isinstance(user.following, set):
        user.following.add(target)
    else:
        user.following.append(target)

    # Many implementations accept (obj, context) where context includes 'request' with user attr
    class FakeRequest:
        def __init__(self, user):
            self.user = user

    fake_request = FakeRequest(user)
    context = {"request": fake_request}

    # Try calling with different shapes until success
    result = None
    try:
        result = _call_flexible(get_following_func, target, context)
    except TypeError:
        # maybe signature is (obj, request) or (obj, )
        try:
            result = _call_flexible(get_following_func, target, fake_request)
        except TypeError:
            result = _call_flexible(get_following_func, target)

    assert isinstance(result, bool)
    # since our fake_request.user is 'user' and 'user' follows 'target', should be True
    assert result is True
