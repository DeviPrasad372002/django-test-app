import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/models.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)

import django.db.models as dj_models

def test_article_str_returns_title():
    a = target_module.Article(title='My Article Title')
    # __str__ should return the title directly
    assert a.__str__() == 'My Article Title'
    assert str(a) == 'My Article Title'

def test_tag_str_returns_tag():
    t = target_module.Tag(tag='python')
    assert t.__str__() == 'python'
    assert str(t) == 'python'

def test_article_slug_field_properties():
    slug_field = target_module.Article._meta.get_field('slug')
    assert isinstance(slug_field, dj_models.SlugField)
    # properties as defined in source
    assert slug_field.max_length == 255
    assert slug_field.unique is True
    assert slug_field.db_index is True

def test_article_title_field_properties():
    title_field = target_module.Article._meta.get_field('title')
    assert isinstance(title_field, dj_models.CharField)
    assert title_field.max_length == 255
    assert title_field.db_index is True

def test_tag_slug_field_unique_and_indexed():
    slug_field = target_module.Tag._meta.get_field('slug')
    assert isinstance(slug_field, dj_models.SlugField)
    assert slug_field.unique is True
    assert slug_field.db_index is True

def test_comment_fields_and_relations():
    # Ensure Comment has expected fields and relation types
    body_field = target_module.Comment._meta.get_field('body')
    assert isinstance(body_field, dj_models.TextField)

    article_field = target_module.Comment._meta.get_field('article')
    assert isinstance(article_field, dj_models.ForeignKey)
    assert article_field.related_model.__name__ in ('Article', 'Article')  # name check

    author_field = target_module.Comment._meta.get_field('author')
    assert isinstance(author_field, dj_models.ForeignKey)
    assert author_field.related_name == 'comments'

def test_article_tags_many_to_many_field():
    tags_field = target_module.Article._meta.get_field('tags')
    assert isinstance(tags_field, dj_models.ManyToManyField)
    assert tags_field.related_name == 'articles'
    # related model name check
    assert tags_field.related_model.__name__ in ('Tag', 'Tag')

def test_str_methods_with_missing_values():
    # If title/tag are None, __str__ returns None, but str(obj) should raise TypeError
    a = target_module.Article()  # no title provided
    # Direct __str__ call returns whatever attribute is (likely None)
    assert a.__str__() is None
    with pytest.raises(TypeError):
        _ = str(a)

    t = target_module.Tag()  # no tag provided
    assert t.__str__() is None
    with pytest.raises(TypeError):
        _ = str(t)