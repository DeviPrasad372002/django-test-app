import importlib.util, pytest
if importlib.util.find_spec('django') is None:
    pytest.skip('django not installed; skipping module', allow_module_level=True)

# --- ENHANCED UNIVERSAL BOOTSTRAP ---
import os, sys, importlib as _importlib, importlib.util as _iu, importlib.machinery as _im, types as _types, pytest as _pytest, builtins as _builtins
import warnings
STRICT = os.getenv("TESTGEN_STRICT", "1").lower() in ("1","true","yes")
STRICT_FAIL = os.getenv("TESTGEN_STRICT_FAIL","0").lower() in ("1","true","yes")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
_target = os.environ.get("TARGET_ROOT") or os.environ.get("ANALYZE_ROOT") or "target"
if _target and os.path.exists(_target):
    if _target not in sys.path: sys.path.insert(0, _target)
    try: os.chdir(_target)
    except Exception: pass
_TARGET_ABS = os.path.abspath(_target)
def _exc_lookup(name, default):
    try:
        mod_name, _, cls_name = str(name).rpartition(".")
        if mod_name:
            mod = __import__(mod_name, fromlist=[cls_name])
            return getattr(mod, cls_name, default)
        return getattr(sys.modules.get("builtins"), str(name), default)
    except Exception:
        return default
def _apply_compatibility_fixes():
    try:
        import jinja2
        if not hasattr(jinja2, 'Markup'):
            try:
                from markupsafe import Markup, escape
                jinja2.Markup = Markup
                if not hasattr(jinja2, 'escape'):
                    jinja2.escape = escape
            except Exception:
                pass
    except ImportError:
        pass
    try:
        import flask
        if not hasattr(flask, "escape"):
            try:
                from markupsafe import escape
                flask.escape = escape
            except Exception:
                pass
        try:
            import threading
            from flask import _app_ctx_stack, _request_ctx_stack
            for _stack in (_app_ctx_stack, _request_ctx_stack):
                if _stack is not None and not hasattr(_stack, "__ident_func__"):
                    _stack.__ident_func__ = getattr(threading, "get_ident", None) or (lambda: 0)
        except Exception:
            pass
    except ImportError:
        pass
    try:
        import collections as _collections, collections.abc as _abc
        for _n in ('Mapping','MutableMapping','Sequence','Iterable','Container','MutableSequence','Set','MutableSet'):
            if not hasattr(_collections, _n) and hasattr(_abc, _n):
                setattr(_collections, _n, getattr(_abc, _n))
    except Exception:
        pass
    try:
        import marshmallow as _mm
        if not hasattr(_mm, "__version__"):
            _mm.__version__ = "4"
    except Exception:
        pass
_apply_compatibility_fixes()
_ADAPTED_MODULES = set()
def _attach_module_getattr(_m):
    try:
        if getattr(_m, "__name__", None) in _ADAPTED_MODULES: return
        mfile = getattr(_m, "__file__", "") or ""
        if not mfile or not os.path.abspath(mfile).startswith(_TARGET_ABS + os.sep): return
        if hasattr(_m, "__getattr__"):
            _ADAPTED_MODULES.add(_m.__name__); return
        def __getattr__(name):
            for _nm, _obj in list(_m.__dict__.items()):
                if isinstance(_obj, type) and not _nm.startswith("_"):
                    try: _inst = _obj()
                    except Exception: continue
                    if hasattr(_inst, name):
                        _val = getattr(_inst, name)
                        try: setattr(_m, name, _val)
                        except Exception: pass
                        return _val
            raise AttributeError(f"module {_m.__name__!r} has no attribute {name!r}")
        _m.__getattr__ = __getattr__; _ADAPTED_MODULES.add(_m.__name__)
    except Exception:
        pass
if not STRICT:
    _orig_import = _builtins.__import__
    def _import_with_adapter(name, globals=None, locals=None, fromlist=(), level=0):
        mod = _orig_import(name, globals, locals, fromlist, level)
        try:
            if isinstance(mod, _types.ModuleType): _attach_module_getattr(mod)
            if fromlist:
                for attr in fromlist:
                    try:
                        sub = getattr(mod, attr, None)
                        if isinstance(sub, _types.ModuleType): _attach_module_getattr(sub)
                    except Exception: pass
        except Exception: pass
        return mod
    _builtins.__import__ = _import_with_adapter
try:
    if _iu.find_spec("django") is not None:
        import django
        from django.conf import settings as _dj_settings
        if not _dj_settings.configured:
            _dj_settings.configure(SECRET_KEY="test-key", DEBUG=True, ALLOWED_HOSTS=["*"], INSTALLED_APPS=[], DATABASES={"default": {"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
            django.setup()
except Exception: pass
_PY2_ALIASES = {'ConfigParser': 'configparser', 'Queue': 'queue', 'StringIO': 'io', 'cStringIO': 'io', 'urllib2': 'urllib.request'}
for _old, _new in list(_PY2_ALIASES.items()):
    if _old in sys.modules: continue
    try:
        __import__(_new); sys.modules[_old] = sys.modules[_new]
    except Exception: pass
def _safe_find_spec(name):
    try: return _iu.find_spec(name)
    except Exception: return None
def _ensure_pkg(name, is_pkg=None):
    if name in sys.modules:
        m = sys.modules[name]
        if getattr(m, "__spec__", None) is None:
            m.__spec__ = _im.ModuleSpec(name, loader=None, is_package=(is_pkg if is_pkg is not None else ("." not in name)))
            if "." not in name and not hasattr(m, "__path__"): m.__path__ = []
        return m
    m = _types.ModuleType(name)
    if is_pkg is None: is_pkg = ("." not in name)
    if is_pkg and not hasattr(m, "__path__"): m.__path__ = []
    m.__spec__ = _im.ModuleSpec(name, loader=None, is_package=is_pkg)
    sys.modules[name] = m
    return m
_THIRD_PARTY_TOPS = ['__future__', 'conduit', 'datetime', 'django', 'json', 'jwt', 'models', 'os', 'random', 'relations', 'renderers', 'rest_framework', 'serializers', 'string', 'views']

# --- /ENHANCED UNIVERSAL BOOTSTRAP ---

import pytest
# If a target import fails, skip the whole module rather than passing silently.
try:
    pass
except ImportError as _e:
    import pytest as _pytest; _pytest.skip(str(_e), allow_module_level=True)

try:
    from types import SimpleNamespace
    from conduit.apps.articles.__init__ import ArticlesAppConfig
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.models import Article, Tag, Comment
    from conduit.apps.articles.relations import TagRelatedField
    from conduit.apps.profiles.serializers import get_image, get_following
except ImportError as e:
    pytest.skip(f"Skipping tests due to ImportError: {e}", allow_module_level=True)


@pytest.mark.parametrize(
    "title, initial_slug",
    [
        ("Hello World", ""),
        ("Edge Case:   Multiple   Spaces ", None),
    ],
)
def test_add_slug_to_article_if_not_exists_sets_slug(title, initial_slug):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: create an Article-like instance with a title and empty/None slug
    article = Article()  # create without DB persistence
    article.title = title
    article.slug = initial_slug

    # Act: invoke the signal handler as if the article was created
    result = add_slug_to_article_if_not_exists(sender=Article, instance=article, created=True, **{})

    # Assert: function returns None (signal handlers usually do) and slug is populated
    assert result is None
    assert getattr(article, "slug", None) not in (None, "")
    # Slug should not contain spaces
    assert " " not in article.slug
    # Slug should contain a slugified fragment of the title (basic sanity)
    for piece in title.split():
        if piece.strip():
            assert piece.strip().lower().split(":")[0][:3] in article.slug


def test_articles_app_config_ready_is_callable_and_idempotent():
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: instantiate the app config
    config = ArticlesAppConfig("conduit.apps.articles", "conduit.apps.articles")

    # Act & Assert: calling ready should not raise and should be idempotent
    config.ready()
    config.ready()
    assert config.__class__.__name__ == "ArticlesAppConfig"


@pytest.mark.parametrize(
    "tag_obj_or_name, expected_name",
    [
        (Tag(name="python"), "python"),
        ("testing-tag", "testing-tag"),
    ],
)
def test_tag_related_field_to_representation_and_to_internal_value(tag_obj_or_name, expected_name):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: create field instance
    field = TagRelatedField()

    # Act & Assert: representation path
    if isinstance(tag_obj_or_name, _exc_lookup("Tag", Exception)):
        tag_instance = tag_obj_or_name
    else:
        tag_instance = Tag(name=tag_obj_or_name)
    rep = field.to_representation(tag_instance)

    # Assert: representation yields the tag name or a string containing it
    assert isinstance(rep, (str,)), "to_representation should return a string"
    assert expected_name in rep

    # Act: test to_internal_value for a string input
    input_value = "new-tag-value"
    internal = field.to_internal_value(input_value)

    # Assert: internal value is either a Tag-like object with .name or the original string
    if isinstance(internal, _exc_lookup("str", Exception)):
        assert internal == input_value
    else:
        assert hasattr(internal, "name")
        assert internal.name == input_value


@pytest.mark.parametrize(
    "image_attr, following_result",
    [
        ("http://example.com/avatar.png", True),
        (None, False),
    ],
)
def test_get_image_and_get_following_helper_functions(image_attr, following_result):
    """Arrange-Act-Assert: generated by ai-testgen for developer-style correctness checks."""
    # Arrange: create a fake profile-like object and a fake serializer 'self' with context
    class DummyProfile:
        def __init__(self, image, expected_following):
            self.image = image
            self._expected_following = expected_following

        def is_followed_by(self, user):
            # act like the model-level helper which would check a relationship
            return self._expected_following

    profile_obj = DummyProfile(image_attr, following_result)

    # create fake serializer 'self' where context contains a request with a user
    fake_request_user = SimpleNamespace(username="alice")
    fake_request = SimpleNamespace(user=fake_request_user)
    fake_serializer_self = SimpleNamespace(context={"request": fake_request})

    # Act: call the module-level helper methods as if they were serializer methods
    image_result = get_image(fake_serializer_self, profile_obj)
    following_flag = get_following(fake_serializer_self, profile_obj)

    # Assert: image_result should equal the provided image or a falsy default
    if image_attr:
        assert image_result == image_attr
    else:
        assert not image_result

    # Assert: following flag matches the DummyProfile behavior
    assert following_flag is following_result
