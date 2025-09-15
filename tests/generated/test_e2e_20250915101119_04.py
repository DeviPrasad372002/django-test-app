import importlib.util, pytest
if importlib.util.find_spec('django') is None:
    pytest.skip('django not installed; skipping module', allow_module_level=True)

# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib.util as _iu, types as _types, pytest as _pytest, builtins as _builtins, warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

_target = os.environ.get("TARGET_ROOT") or os.environ.get("ANALYZE_ROOT") or "target"
if _target and os.path.isdir(_target):
    _parent = os.path.abspath(os.path.join(_target, os.pardir))
    for p in (_parent, _target):
        if p not in sys.path:
            sys.path.insert(0, p)
    if "target" not in sys.modules:
        _pkg = _types.ModuleType("target")
        _pkg.__path__ = [_target]
        sys.modules["target"] = _pkg

def _exc_lookup(name, default):
    try:
        mod_name, _, cls_name = str(name).rpartition(".")
        if mod_name:
            mod = __import__(mod_name, fromlist=[cls_name])
            return getattr(mod, cls_name, default)
        return getattr(sys.modules.get("builtins"), str(name), default)
    except Exception:
        return default

if os.getenv("TESTGEN_ENABLE_DJANGO_BOOTSTRAP","0") in ("1","true","yes"):
    try:
        import django
        from django.conf import settings as _dj_settings
        from django import apps as _dj_apps
        if not _dj_settings.configured:
            _cfg = dict(
                DEBUG=True, SECRET_KEY='pytest-secret',
                DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3','NAME': ':memory:'}},
                INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages'],
                MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware'],
                USE_TZ=True, TIME_ZONE='UTC',
            )
            try: _cfg["DEFAULT_AUTO_FIELD"] = "django.db.models.AutoField"
            except Exception: pass
            try: _dj_settings.configure(**_cfg)
            except Exception: pass
        if not _dj_apps.ready:
            try: django.setup()
            except Exception: pass
        try: import django.contrib.auth.base_user as _dj_probe  # noqa
        except Exception as _e:
            _pytest.skip(f"Django core import failed safely: {_e.__class__.__name__}: {_e}", allow_module_level=True)
    except Exception as _e:
        _pytest.skip(f"Django bootstrap not available: {_e.__class__.__name__}: {_e}", allow_module_level=True)

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

try:
    import pytest
    import importlib
    from types import SimpleNamespace
    profiles_models = importlib.import_module('conduit.apps.profiles.models')
    profiles_serializers = importlib.import_module('conduit.apps.profiles.serializers')
except Exception as e:
    try:
        import pytest
        pytest.skip(f"Required project modules not available: {e}", allow_module_level=True)
    except Exception:
        raise

def _locate_callable(module, name):
    # Search module-level callables first, then class members
    for attr in dir(module):
        obj = getattr(module, attr)
        if callable(obj) and getattr(obj, '__name__', None) == name:
            return obj
        if isinstance(obj, type):
            if hasattr(obj, name):
                member = getattr(obj, name)
                if callable(member):
                    return member
    raise AttributeError(f"No callable named {name} found in module {module.__name__}")

class FakeQuery:
    def __init__(self, exists_value):
        self._exists = exists_value
    def exists(self):
        return self._exists

class FakeFollowers:
    def __init__(self, existing_ids):
        self.existing_ids = set(existing_ids)
    def filter(self, **kwargs):
        # Support common lookup keys
        val = kwargs.get('id') or kwargs.get('pk') or kwargs.get('user__id') or kwargs.get('user_id')
        if val is None:
            return FakeQuery(False)
        return FakeQuery(val in self.existing_ids)

class FakeFavorites:
    def __init__(self):
        self.items = set()
    def add(self, obj):
        self.items.add(getattr(obj, 'id', obj))
    def remove(self, obj):
        self.items.discard(getattr(obj, 'id', obj))
    def discard(self, obj):
        self.remove(obj)
    def filter(self, **kwargs):
        val = kwargs.get('id') or kwargs.get('pk')
        if val is None:
            return FakeQuery(False)
        return FakeQuery(val in self.items)

@pytest.mark.parametrize("existing_ids, user_id, expected", [
    ({1,2}, 1, True),
    (set(), 5, False),
])
def test_is_followed_by_returns_boolean_for_present_and_absent_followers(existing_ids, user_id, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    func = _locate_callable(profiles_models, 'is_followed_by')
    dummy_self = SimpleNamespace(followers=FakeFollowers(existing_ids))
    user = SimpleNamespace(id=user_id)
    # Act
    result = func(dummy_self, user)
    # Assert
    assert isinstance(result, bool)
    assert result is expected

def test_is_followed_by_raises_attribute_error_when_user_has_no_id():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    func = _locate_callable(profiles_models, 'is_followed_by')
    dummy_self = SimpleNamespace(followers=FakeFollowers({1}))
    user_without_id = object()
    # Act / Assert
    with pytest.raises(AttributeError):
        _ = func(dummy_self, user_without_id)

@pytest.mark.parametrize("initial_ids, article_id", [
    ([], 10),
    ([7], 7),
])
def test_favorite_unfavorite_and_has_favorited_modify_state_and_report_correctly(initial_ids, article_id):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    favorite_fn = _locate_callable(profiles_models, 'favorite')
    unfavorite_fn = _locate_callable(profiles_models, 'unfavorite')
    has_fav_fn = _locate_callable(profiles_models, 'has_favorited')
    manager = FakeFavorites()
    for i in initial_ids:
        manager.items.add(i)
    dummy_self = SimpleNamespace(favorites=manager)
    article = SimpleNamespace(id=article_id)
    # Act - favorite
    favorite_fn(dummy_self, article)
    # Assert after favorite: item present
    assert article_id in dummy_self.favorites.items
    assert has_fav_fn(dummy_self, article) is True
    # Act - unfavorite
    unfavorite_fn(dummy_self, article)
    # Assert after unfavorite: item absent
    assert article_id not in dummy_self.favorites.items
    assert has_fav_fn(dummy_self, article) is False

def test_unfavorite_on_nonexistent_item_does_not_raise_and_leaves_state_consistent():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    unfavorite_fn = _locate_callable(profiles_models, 'unfavorite')
    manager = FakeFavorites()
    dummy_self = SimpleNamespace(favorites=manager)
    article = SimpleNamespace(id=999)
    # Act / Assert
    # Should not raise
    unfavorite_fn(dummy_self, article)
    assert 999 not in manager.items

@pytest.mark.parametrize("image_obj, expected", [
    (None, None),
    (SimpleNamespace(url='/media/avatar.png'), '/media/avatar.png'),
])
def test_get_image_returns_expected_url_or_none(image_obj, expected):
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    func = _locate_callable(profiles_serializers, 'get_image')
    serializer_self = SimpleNamespace(context={})
    profile = SimpleNamespace(image=image_obj)
    # Act
    result = func(serializer_self, profile)
    # Assert
    assert result == expected
    if result is not None:
        assert isinstance(result, str)

def test_get_image_raises_attribute_error_if_image_has_no_url_attribute():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    func = _locate_callable(profiles_serializers, 'get_image')
    serializer_self = SimpleNamespace(context={})
    profile = SimpleNamespace(image=object())
    # Act / Assert
    with pytest.raises(AttributeError):
        func(serializer_self, profile)

def test_get_following_reflects_request_user_relationship_and_handles_missing_request():
    # Arrange-Act-Assert: generated by ai-testgen
    # Arrange
    func = _locate_callable(profiles_serializers, 'get_following')
    # Case 1: request present and profile.is_followed_by returns True
    user = SimpleNamespace(id=42)
    request = SimpleNamespace(user=user)
    serializer_self = SimpleNamespace(context={'request': request})
    profile_true = SimpleNamespace(is_followed_by=lambda u: u is user or getattr(u, 'id', None) == 42)
    # Act
    result_true = func(serializer_self, profile_true)
    # Assert
    assert isinstance(result_true, bool)
    assert result_true is True
    # Case 2: no request in context -> should be False
    serializer_no_request = SimpleNamespace(context={})
    profile_false = SimpleNamespace(is_followed_by=lambda u: True)  # would be True if asked, but no request means False expected
    result_false = func(serializer_no_request, profile_false)
    assert result_false is False
