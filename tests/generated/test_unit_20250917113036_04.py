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

import pytest as _pytest
_pytest.skip('generator: banned private imports detected; skipping module', allow_module_level=True)

try:
    import importlib
    import pytest
    from types import ModuleType
    from importlib import import_module
    # Import target modules using import_module since some module names (like migrations) may start with digits
    articles_pkg = import_module('target.conduit.apps.articles')
    migration_module = import_module('target.conduit.apps.articles.migrations.0001_initial')
    relations = import_module('target.conduit.apps.articles.relations')
    models = import_module('target.conduit.apps.articles.models')
    django_models = import_module('django.db.models')
except (ImportError, ModuleNotFoundError) as e:
    import pytest as _pytest
    _pytest.skip("required project modules not available: %s" % e, allow_module_level=True)

def test_articles_appconfig_name_contains_articles():
    
    # Arrange
    ArticlesAppConfig = getattr(articles_pkg, 'ArticlesAppConfig', None)
    assert ArticlesAppConfig is not None and callable(ArticlesAppConfig)
    # Act
    app_config = ArticlesAppConfig('conduit.apps.articles', articles_pkg)
    # Assert
    assert isinstance(app_config.name, str)
    assert 'articles' in app_config.name

def test_migration_has_operations_list_and_dependencies():
    
    # Arrange / Act
    Migration = getattr(migration_module, 'Migration', None)
    # Assert basic structure
    assert Migration is not None and isinstance(Migration, type)
    assert hasattr(Migration, 'operations'), "Migration should have 'operations' attribute"
    assert isinstance(getattr(Migration, 'operations'), list)
    # dependencies is often present; assert it's a list if present
    if hasattr(Migration, 'dependencies'):
        assert isinstance(getattr(Migration, 'dependencies'), list)

import pytest

@pytest.mark.parametrize("cls_name", ["Article", "Comment", "Tag"])
def test_models_are_subclasses_of_django_model(cls_name):
    
    # Arrange
    cls = getattr(models, cls_name, None)
    assert cls is not None, f"{cls_name} should be defined in articles.models"
    # Act / Assert
    assert issubclass(cls, django_models.Model), f"{cls_name} must subclass django.db.models.Model"

def test_tagrelatedfield_to_internal_value_and_to_representation(monkeypatch):
    
    # Arrange
    TagRelatedField = getattr(relations, 'TagRelatedField', None)
    assert TagRelatedField is not None and callable(TagRelatedField)
    field = TagRelatedField()

    # Create a fake Tag class and manager to simulate get_or_create behavior
    class FakeTag:
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return f"<FakeTag {self.name!r}>"

    class FakeManager:
        def get_or_create(self, name):
            return (FakeTag(name), True)

    # Act: monkeypatch the Tag attribute used inside relations to our fake implementation
    monkeypatch.setattr(relations, 'Tag', FakeTag, raising=False)
    # Attach objects manager
    setattr(FakeTag, 'objects', FakeManager())

    # Act: convert from string to internal value
    internal = field.to_internal_value('unittest-tag')
    # Assert internal is a FakeTag with correct name
    assert isinstance(internal, FakeTag)
    assert getattr(internal, 'name') == 'unittest-tag'

    # Act: representation should return the tag name
    rep = field.to_representation(internal)
    # Assert
    assert isinstance(rep, str)
    assert rep == 'unittest-tag'
