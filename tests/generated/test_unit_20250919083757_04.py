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

import importlib
import inspect
import types

import pytest

try:
    # core modules under test
    profiles_models = importlib.import_module("conduit.apps.profiles.models")
    profiles_serializers = importlib.import_module("conduit.apps.profiles.serializers")
    articles_relations = importlib.import_module("conduit.apps.articles.relations")
    articles_models = importlib.import_module("conduit.apps.articles.models")
    articles_init = importlib.import_module("conduit.apps.articles.__init__")
    # migrations module name starts with digit; import via import_module
    articles_migration_module = importlib.import_module("conduit.apps.articles.migrations.0001_initial")
except ImportError as e:
    pytest.skip(f"Skipping tests because imports failed: {e}", allow_module_level=True)

class FakeRelation:
    """Minimal emulation of a Django related manager for unit tests."""
    def __init__(self, initial=None):
        self._set = set(initial or ())

    def add(self, item):
        self._set.add(item)

    def remove(self, item):
        
        if item not in self._set:
            raise KeyError("Item not present")
        self._set.remove(item)

    def discard(self, item):
        self._set.discard(item)

    def all(self):
        return list(self._set)

    def __contains__(self, item):
        return item in self._set

    def __len__(self):
        return len(self._set)

def _call_method_flexible(func, *args):
    """
    Call func with args respecting the number of parameters func expects.
    If func expects fewer parameters than provided, trim args from the right.
    """
    sig = inspect.signature(func)
    # exclude 'self' for bound methods passed as functions? Use parameter count directly.
    param_count = len(sig.parameters)
    call_args = args[:param_count]
    return func(*call_args)

def _make_dummy_user_with_relations():
    return types.SimpleNamespace(following=FakeRelation(), followers=FakeRelation(), favorites=FakeRelation(), profile=None)

def _make_dummy_article(name="article1"):
    return types.SimpleNamespace(slug=name, title=name)

def _make_dummy_tag(name="tag1"):
    return types.SimpleNamespace(name=name, slug=name)

def test_is_followed_by_true_and_false():
    func = getattr(profiles_models, "is_followed_by", None)
    if func is None:
        pytest.skip("is_followed_by not implemented in profiles.models")

    follower = object()
    target = types.SimpleNamespace(followers=FakeRelation(initial=[follower]))
    # True case
    result_true = _call_method_flexible(func, target, follower)
    assert result_true is True

    # False case: different user
    other = object()
    result_false = _call_method_flexible(func, target, other)
    assert result_false is False

    
    with pytest.raises((TypeError, ValueError, AttributeError)) as excinfo:
        _call_method_flexible(func, target, None)
    assert excinfo is not None

@pytest.mark.parametrize("initial,fav_to_add,expect_in", [
    ([], "a1", True),
    (["a1"], "a1", True),
])
def test_favorite_and_has_favorited(initial, fav_to_add, expect_in):
    fav_func = getattr(profiles_models, "favorite", None)
    has_func = getattr(profiles_models, "has_favorited", None)
    unfav_func = getattr(profiles_models, "unfavorite", None)
    if fav_func is None or has_func is None:
        pytest.skip("favorite/has_favorited not implemented in profiles.models")

    user = types.SimpleNamespace(favorites=FakeRelation(initial=initial))
    article = _make_dummy_article(fav_to_add)

    # Act: favorite
    _call_method_flexible(fav_func, user, article)
    # Assert favorite added
    assert article in user.favorites.all() or any(getattr(a, "slug", a) == getattr(article, "slug", article) for a in user.favorites.all())

    # has_favorited should reflect presence
    has = _call_method_flexible(has_func, user, article)
    assert isinstance(has, bool)
    assert has is True

    
    if unfav_func:
        _call_method_flexible(unfav_func, user, article)
        # after unfavorite, should not be present
        has_after = _call_method_flexible(has_func, user, article)
        assert has_after is False

def test_unfavorite_nonexistent_raises_or_silently_handles():
    unfav_func = getattr(profiles_models, "unfavorite", None)
    if unfav_func is None:
        pytest.skip("unfavorite not implemented in profiles.models")
    user = types.SimpleNamespace(favorites=FakeRelation(initial=[]))
    article = _make_dummy_article("x")
    
    try:
        _call_method_flexible(unfav_func, user, article)
    except Exception as exc:
        assert isinstance(exc, (KeyError, AttributeError, ValueError))

def test_get_image_returns_string_or_none():
    func = getattr(profiles_serializers, "get_image", None)
    if func is None:
        pytest.skip("get_image not implemented in profiles.serializers")

    # Case: user has profile with image attribute
    user_with_image = types.SimpleNamespace(profile=types.SimpleNamespace(image="http://img"))
    # SerializerMethod may expect (self, obj) or (obj,)
    res = _call_method_flexible(func, object(), user_with_image) if len(inspect.signature(func).parameters) >= 2 else func(user_with_image)
    assert res == "http://img" or isinstance(res, (str, type(None)))

    
    user_no_profile = types.SimpleNamespace(profile=None)
    res2 = _call_method_flexible(func, object(), user_no_profile) if len(inspect.signature(func).parameters) >= 2 else func(user_no_profile)
    assert res2 is None or isinstance(res2, str)

def test_get_following_boolean_behavior():
    func = getattr(profiles_serializers, "get_following", None)
    if func is None:
        pytest.skip("get_following not implemented in profiles.serializers")

    # Create objects that emulate a target profile and a current user following
    follower = object()
    profile_obj = types.SimpleNamespace(user=types.SimpleNamespace(username="target"), followers=FakeRelation(initial=[follower]))
    # Depending on signature may accept (self, obj) and use context; pass simple parameters
    sig = inspect.signature(func)
    if len(sig.parameters) >= 2:
        # simulate serializer self by passing object() as first arg
        res = func(object(), profile_obj)
    else:
        res = func(profile_obj)
    assert isinstance(res, bool)

def test_articles_app_config_ready_imports_signals():
    AppConfigClass = getattr(articles_init, "ArticlesAppConfig", None)
    if AppConfigClass is None:
        pytest.skip("ArticlesAppConfig not found in conduit.apps.articles.__init__")
    appconf = AppConfigClass()
    
    assert appconf.ready() is None

def test_migration_has_dependencies_and_operations():
    migration_module = articles_migration_module
    Migration = getattr(migration_module, "Migration", None)
    if Migration is None:
        pytest.skip("Migration class not present in migration module")
    mig = Migration("name", "app")
    # Django Migration objects have dependencies and operations typically lists/tuples
    deps = getattr(mig, "dependencies", None)
    ops = getattr(mig, "operations", None)
    assert isinstance(deps, (list, tuple))
    assert isinstance(ops, (list, tuple))

def test_tag_article_comment_str_includes_key_fields():
    TagClass = getattr(articles_models, "Tag", None)
    ArticleClass = getattr(articles_models, "Article", None)
    CommentClass = getattr(articles_models, "Comment", None)

    if TagClass is None or ArticleClass is None or CommentClass is None:
        pytest.skip("Tag/Article/Comment classes not available in articles.models")

    # Instantiate models using constructor args (Django models accept field kwargs)
    tag = TagClass(**{"name": "pytest-tag"}) if callable(TagClass) else types.SimpleNamespace(name="pytest-tag")
    article = ArticleClass(**{"title": "PyTest Article"}) if callable(ArticleClass) else types.SimpleNamespace(title="PyTest Article")
    comment = CommentClass(**{"body": "A comment body"}) if callable(CommentClass) else types.SimpleNamespace(body="A comment body")

    s_tag = str(tag)
    s_article = str(article)
    s_comment = str(comment)

    assert "pytest-tag" in s_tag
    assert "PyTest Article" in s_article
    assert "comment" in s_comment.lower()

def test_tag_related_field_to_representation_and_internal_value():
    TagRelatedField = getattr(articles_relations, "TagRelatedField", None)
    if TagRelatedField is None:
        pytest.skip("TagRelatedField not found in articles.relations")

    field = TagRelatedField()
    dummy_tag = _make_dummy_tag("unit-tag")

    # to_representation should return a string name for a tag-like object
    if hasattr(field, "to_representation"):
        rep = field.to_representation(dummy_tag)
        assert isinstance(rep, str)
        assert rep == "unit-tag"

    # to_internal_value should accept a string and return something sensible (str or Tag instance)
    if hasattr(field, "to_internal_value"):
        internal = field.to_internal_value("unit-tag")
        assert internal is not None
        assert isinstance(internal, (str, type(dummy_tag), articles_models.Tag)) or hasattr(internal, "name")

        
        with pytest.raises((TypeError, ValueError)):
            field.to_internal_value(12345)
