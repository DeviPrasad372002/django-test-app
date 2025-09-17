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
from types import SimpleNamespace

import pytest

try:
    from conduit.apps.profiles import models as profiles_models
    from conduit.apps.articles import serializers as articles_serializers
    from conduit.apps.articles import relations as articles_relations
    from conduit.apps.articles import models as articles_models
except ImportError:
    pytest.skip("conduit package not available", allow_module_level=True)

def _call_with_fallback(func, *args):
    """
    Try calling func with given args; if TypeError arises due to signature,
    attempt to swap first two args (common instance vs reversed param order).
    If still failing, raise the original error.
    """
    try:
        return func(*args)
    except TypeError as e1:
        # try swapped first two args if there are at least two
        if len(args) >= 2:
            try:
                return func(args[1], args[0], *args[2:])
            except TypeError:
                raise e1
        raise e1

def _find_callable_attr(module, name):
    """
    Return attribute by name from module or None.
    """
    return getattr(module, name, None)

def _make_user_stub(username):
    # provide attributes commonly accessed by profile functions
    return SimpleNamespace(username=username, following=set(), followers=set(), favorites=set(), image=None)

def _make_article_stub(slug="test-slug"):
    # common attributes used by favorite logic
    return SimpleNamespace(slug=slug, favorited_by=set(), title="T", body="b", author=None)

def _call_maybe_method(obj, method_name, *args):
    """
    If obj has method_name attribute callable, call it with args and return (True, result).
    Otherwise return (False, None).
    """
    meth = getattr(obj, method_name, None)
    if callable(meth):
        return True, meth(*args)
    return False, None

def test_follow_unfollow_and_is_followed_by_integration():
    
    # Arrange
    alice = _make_user_stub("alice")
    bob = _make_user_stub("bob")

    # locate functions
    follow_fn = _find_callable_attr(profiles_models, "follow")
    unfollow_fn = _find_callable_attr(profiles_models, "unfollow")
    is_following_fn = _find_callable_attr(profiles_models, "is_following")
    is_followed_by_fn = _find_callable_attr(profiles_models, "is_followed_by")

    if not all([follow_fn, unfollow_fn, is_following_fn, is_followed_by_fn]):
        pytest.skip("Profile follow-related functions are not present")

    # Act: alice follows bob
    _call_with_fallback(follow_fn, alice, bob)

    # Assert: check both is_following and is_followed_by report correctly
    res1 = _call_with_fallback(is_following_fn, alice, bob)
    res2 = _call_with_fallback(is_followed_by_fn, bob, alice)

    assert isinstance(res1, bool), "is_following should return a boolean"
    assert isinstance(res2, bool), "is_followed_by should return a boolean"
    assert res1 is True, "Alice should be following Bob after follow()"
    assert res2 is True, "Bob should be followed by Alice after follow()"

    # Act: alice unfollows bob
    _call_with_fallback(unfollow_fn, alice, bob)

    # Assert: both checks are now false
    res1_after = _call_with_fallback(is_following_fn, alice, bob)
    res2_after = _call_with_fallback(is_followed_by_fn, bob, alice)

    assert res1_after is False, "Alice should not be following Bob after unfollow()"
    assert res2_after is False, "Bob should not be followed by Alice after unfollow()"

def test_favorite_unfavorite_and_serializer_favorites_count_integration():
    
    # Arrange
    user = _make_user_stub("u1")
    article = _make_article_stub("an-article")

    favorite_fn = _find_callable_attr(profiles_models, "favorite")
    unfavorite_fn = _find_callable_attr(profiles_models, "unfavorite")
    has_favorited_fn = _find_callable_attr(profiles_models, "has_favorited")

    if not all([favorite_fn, unfavorite_fn, has_favorited_fn]):
        pytest.skip("Favorite-related functions are not present")

    # Find a way to compute favorites count from article serializers
    # Try ArticleSerializer.get_favorites_count, then module-level function
    serializer_count_callable = None
    ArticleSerializer = _find_callable_attr(articles_serializers, "ArticleSerializer")
    if ArticleSerializer:
        # instantiate if possible without args
        try:
            inst = ArticleSerializer()
            if hasattr(inst, "get_favorites_count") and callable(inst.get_favorites_count):
                serializer_count_callable = lambda art: inst.get_favorites_count(art)
        except Exception:
            # fallback to class method invocation pattern
            if hasattr(ArticleSerializer, "get_favorites_count") and callable(ArticleSerializer.get_favorites_count):
                serializer_count_callable = lambda art: ArticleSerializer.get_favorites_count(ArticleSerializer(), art)

    # fallback to module-level get_favorites_count
    if serializer_count_callable is None:
        mod_fn = _find_callable_attr(articles_serializers, "get_favorites_count")
        if callable(mod_fn):
            serializer_count_callable = lambda art: mod_fn(art)
    if serializer_count_callable is None:
        # as last resort, use article.favorited_by length if present
        if hasattr(article, "favorited_by"):
            serializer_count_callable = lambda art: len(getattr(art, "favorited_by") or [])
        else:
            pytest.skip("No way to compute favorites count from serializers or article shape")

    # Act: user favorites the article
    _call_with_fallback(favorite_fn, user, article)

    # Assert: has_favorited should be True and serializer reports 1
    fav_bool = _call_with_fallback(has_favorited_fn, user, article)
    assert fav_bool is True, "User should have favorited the article after favorite()"

    count_after = serializer_count_callable(article)
    assert isinstance(count_after, int), "Favorites count should be an int"
    assert count_after >= 1, "Favorites count should reflect the favorite action"

    # Act: user unfavorites the article
    _call_with_fallback(unfavorite_fn, user, article)

    # Assert: has_favorited false and count decreased
    fav_bool2 = _call_with_fallback(has_favorited_fn, user, article)
    assert fav_bool2 is False, "User should not have favorited the article after unfavorite()"

    count_after2 = serializer_count_callable(article)
    assert isinstance(count_after2, int), "Favorites count should still be an int after unfavorite"
    assert count_after2 <= count_after, "Favorites count should not increase after unfavorite()"

def test_tagrelatedfield_representation_and_internal_value_integration():
    
    # Arrange
    TagRelatedField = _find_callable_attr(articles_relations, "TagRelatedField")
    TagModel = _find_callable_attr(articles_models, "Tag")
    if TagRelatedField is None:
        pytest.skip("TagRelatedField not present in articles.relations")

    trf = TagRelatedField()

    # Prepare a simple tag-like object and a raw string
    tag_obj = SimpleNamespace(name="python")
    raw_value = "django"

    # Act / Assert: to_representation should return the tag.name string if possible
    if hasattr(trf, "to_representation"):
        rep = trf.to_representation(tag_obj)
        assert isinstance(rep, str), "to_representation should return a string"
        assert rep == "python", "to_representation should use tag.name"

    # Act / Assert: to_internal_value should accept a string and produce something reasonable
    if hasattr(trf, "to_internal_value"):
        internal = trf.to_internal_value(raw_value)
        # It may return a Tag instance, a string, or similar — accept TagModel instance or string
        if TagModel is not None and isinstance(internal, TagModel):
            assert getattr(internal, "name", None) == raw_value, "Internal value Tag should have name from raw input"
        else:
            # accept string or object with name attribute
            if isinstance(internal, str):
                assert internal == raw_value
            else:
                # object with name attribute
                name_attr = getattr(internal, "name", None)
                assert name_attr == raw_value, "Internal representation should carry the tag name"
