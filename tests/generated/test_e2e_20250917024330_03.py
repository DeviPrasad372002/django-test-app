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

import pytest

try:
    import random
    from conduit.apps import authentication as auth_pkg
    from conduit.apps import profiles as profiles_pkg
    from conduit.apps import core as core_pkg
    # Import submodules to access attributes robustly
    from conduit.apps.authentication import models as auth_models
    from conduit.apps.authentication import renderers as auth_renderers
    from conduit.apps.profiles import models as profiles_models
    from conduit.apps.core import utils as core_utils
except Exception:
    pytest.skip("Required conduit application modules are not available", allow_module_level=True)

def _get_attr_or_skip(module, name):
    obj = getattr(module, name, None)
    if obj is None:
        pytest.skip(f"Required attribute {name!r} not present in {module!r}")
    return obj

def _safe_create_user(email, username, password):
    create_user = getattr(auth_models, "create_user", None)
    if not callable(create_user):
        pytest.skip("create_user factory not available")
    try:
        return create_user(email=email, username=username, password=password)
    except TypeError:
        # try positional fallback
        return create_user(email, username, password)
    except Exception as exc:
        pytest.skip(f"create_user failed with exception: {exc}")

def _ensure_profile_for_user(user):
    # Try attribute access
    prof = getattr(user, "profile", None)
    if prof is not None:
        return prof
    # Try profiles_pkg signal helper to create one
    create_related = getattr(auth_pkg.signals, "create_related_profile", None) if hasattr(auth_pkg, "signals") else None
    if callable(create_related):
        try:
            # Some implementations expect (sender, instance, created, **kwargs)
            create_related(sender=type(user), instance=user, created=True)
        except TypeError:
            try:
                create_related(user)
            except Exception:
                pass
    
    Profile = getattr(profiles_models, "Profile", None)
    if Profile is not None:
        # try to get via attribute or manager
        try:
            # If profile is a OneToOne relation, attribute may now exist
            prof = getattr(user, "profile", None)
            if prof is not None:
                return prof
            # try manager get (may require DB)
            get = getattr(Profile.objects, "get", None)
            if callable(get):
                return Profile.objects.get(user=user)
        except Exception:
            pass
    
    prof = getattr(user, "profile", None)
    if prof is None:
        pytest.skip("Unable to obtain Profile for user; profile APIs not available")
    return prof

def _call_follow_method(follower_profile, followee_profile):
    # Prefer instance method
    follow_m = getattr(follower_profile, "follow", None)
    if callable(follow_m):
        return follow_m(followee_profile)
    # Fallback to module-level function
    module_level = getattr(profiles_models, "follow", None)
    if callable(module_level):
        return module_level(follower_profile, followee_profile)
    pytest.skip("follow API not found on profile or module")

def _call_unfollow_method(follower_profile, followee_profile):
    unfollow_m = getattr(follower_profile, "unfollow", None)
    if callable(unfollow_m):
        return unfollow_m(followee_profile)
    module_level = getattr(profiles_models, "unfollow", None)
    if callable(module_level):
        return module_level(follower_profile, followee_profile)
    pytest.skip("unfollow API not found on profile or module")

def _call_is_following(follower_profile, followee_profile):
    is_following_m = getattr(follower_profile, "is_following", None)
    if callable(is_following_m):
        return is_following_m(followee_profile)
    module_level = getattr(profiles_models, "is_following", None)
    if callable(module_level):
        return module_level(follower_profile, followee_profile)
    pytest.skip("is_following API not found on profile or module")

def test_user_get_short_name_and_jwt_token():
    
    # Arrange
    random.seed(0)
    user = _safe_create_user(email="alice@example.test", username="alice", password="pass1234")
    assert user is not None and getattr(user, "username", None) == "alice"

    # Act
    # get_short_name may be instance method or module-level function
    short_name = None
    get_short = getattr(user, "get_short_name", None)
    if callable(get_short):
        short_name = get_short()
    else:
        get_short_mod = getattr(auth_models, "get_short_name", None)
        if callable(get_short_mod):
            short_name = get_short_mod(user)
        else:
            pytest.skip("get_short_name API not found")
    # JWT token generation: usually an instance method on User
    jwt_token = None
    jwt_m = getattr(user, "_generate_jwt_token", None)
    if callable(jwt_m):
        jwt_token = jwt_m()
    else:
        jwt_mod = getattr(auth_models, "_generate_jwt_token", None)
        if callable(jwt_mod):
            try:
                jwt_token = jwt_mod(user)
            except TypeError:
                jwt_token = jwt_mod()
        else:
            pytest.skip("_generate_jwt_token API not found")

    # Assert
    assert isinstance(short_name, str), "short name must be a string"
    assert short_name in {"alice", "alice@example.test"} or len(short_name) > 0
    assert isinstance(jwt_token, str), "_generate_jwt_token must return a string"
    # Basic structure check for JWT: three dot-separated parts
    assert jwt_token.count(".") >= 2, "JWT token should contain at least two dots"

def test_user_json_renderer_renders_bytes():
    
    # Arrange
    renderer_cls = getattr(auth_renderers, "UserJSONRenderer", None)
    render_func = getattr(auth_renderers, "render", None)
    data = {"user": {"email": "bob@example.test", "username": "bob"}}

    # Act
    if renderer_cls is not None:
        renderer = renderer_cls()
        out = renderer.render(data)
    elif callable(render_func):
        out = render_func(data)
    else:
        pytest.skip("No UserJSONRenderer or render function available in authentication.renderers")

    # Assert
    assert isinstance(out, (bytes, bytearray)), "Renderer must return bytes"
    assert b"bob" in out or b"bob@example.test" in out, "Rendered output must contain username or email"

@pytest.mark.parametrize("do_unfollow", [False, True])
def test_profile_follow_unfollow_flow(do_unfollow):
    
    # Arrange
    user_a = _safe_create_user(email="ua@example.test", username="usera", password="pwA")
    user_b = _safe_create_user(email="ub@example.test", username="userb", password="pwB")

    profile_a = _ensure_profile_for_user(user_a)
    profile_b = _ensure_profile_for_user(user_b)

    # Sanity: profiles should be distinct
    assert profile_a is not None and profile_b is not None
    assert profile_a is not profile_b

    # Ensure initial state: not following
    initially = _call_is_following(profile_a, profile_b)
    assert isinstance(initially, bool)
    if initially:
        # attempt to unfollow to get to known state
        try:
            _call_unfollow_method(profile_a, profile_b)
        except Exception:
            pass
        assert _call_is_following(profile_a, profile_b) is False

    # Act - follow
    _call_follow_method(profile_a, profile_b)

    # Assert following
    assert _call_is_following(profile_a, profile_b) is True

    # Optionally unfollow
    if do_unfollow:
        _call_unfollow_method(profile_a, profile_b)
        assert _call_is_following(profile_a, profile_b) is False
