import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/models.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_article_str_returns_title():
    # Create an Article instance without saving to DB; constructor should accept field values.
    article = target_module.Article(
        title='Test Title',
        slug='test-title',
        description='desc',
        body='body text',
        author=object()
    )
    # __str__ should return the title string
    assert article.__str__() == 'Test Title'
    assert str(article) == 'Test Title'


def test_article_str_handles_non_string_title_by_raising_on_str():
    # If title is None, __str__ returns None and Python's str() should raise TypeError.
    article = target_module.Article(
        title=None,
        slug='no-title',
        description='desc',
        body='body text',
        author=object()
    )
    # direct call to __str__ returns the raw attribute (None)
    assert article.__str__() is None
    # built-in str() must raise TypeError because __str__ returned non-string
    with pytest.raises(TypeError):
        _ = str(article)


def test_tag_str_returns_tag():
    tag = target_module.Tag(tag='python', slug='python')
    assert tag.__str__() == 'python'
    assert str(tag) == 'python'


def test_tag_str_handles_none_tag_by_raising_on_str():
    tag = target_module.Tag(tag=None, slug='none-tag')
    assert tag.__str__() is None
    with pytest.raises(TypeError):
        _ = str(tag)


def test_comment_can_be_instantiated_and_fields_are_assigned():
    # Construct a Comment instance without saving to the DB.
    comment = target_module.Comment(body='Nice article', article=None, author=None)
    assert comment.body == 'Nice article'
    # Foreign key attributes are stored as given (here None) until saved/validated
    assert comment.article is None
    assert comment.author is None