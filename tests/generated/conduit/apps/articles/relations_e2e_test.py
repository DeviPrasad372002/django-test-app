import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/relations.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


@pytest.mark.django_db
def test_get_queryset_returns_all_tags():
    Tag = target_module.Tag
    # create two tags
    t1 = Tag.objects.create(tag='One', slug='one')
    t2 = Tag.objects.create(tag='Two', slug='two')

    field = target_module.TagRelatedField()
    qs = field.get_queryset()

    # ensure it's a queryset and contains the created tags
    assert hasattr(qs, 'filter')
    items = list(qs)
    assert t1 in items
    assert t2 in items
    # ensure count matches
    assert qs.count() == 2


@pytest.mark.django_db
def test_to_internal_value_creates_new_tag():
    Tag = target_module.Tag
    field = target_module.TagRelatedField()

    # no tag exists initially
    assert Tag.objects.filter(tag='MyTag').count() == 0

    result = field.to_internal_value('MyTag')

    # returned object is a Tag instance and persisted
    assert isinstance(result, Tag)
    persisted = Tag.objects.get(tag='MyTag')
    assert persisted.pk == result.pk
    assert persisted.slug == 'mytag'


@pytest.mark.django_db
def test_to_internal_value_returns_existing_instance_instead_of_creating_duplicate():
    Tag = target_module.Tag
    # create an existing tag
    existing = Tag.objects.create(tag='existing', slug='existing')
    count_before = Tag.objects.count()

    field = target_module.TagRelatedField()
    result = field.to_internal_value('existing')

    # should return the existing instance (no new row created)
    assert isinstance(result, Tag)
    assert result.pk == existing.pk
    assert Tag.objects.count() == count_before


@pytest.mark.django_db
def test_to_internal_value_raises_for_invalid_input_types():
    field = target_module.TagRelatedField()

    # None should cause an AttributeError when calling .lower()
    with pytest.raises(AttributeError):
        field.to_internal_value(None)

    # integers don't have lower() either
    with pytest.raises(AttributeError):
        field.to_internal_value(123)


@pytest.mark.django_db
def test_to_representation_returns_tag_string_and_errors_on_invalid_value():
    Tag = target_module.Tag
    tag = Tag.objects.create(tag='Alpha', slug='alpha')

    field = target_module.TagRelatedField()
    rep = field.to_representation(tag)
    assert rep == 'Alpha'

    # passing an object without .tag should raise AttributeError
    class Dummy:
        pass

    with pytest.raises(AttributeError):
        field.to_representation(Dummy())