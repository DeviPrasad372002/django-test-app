import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)

from conduit.apps.core.renderers import ConduitJSONRenderer


def test_article_renderer_is_subclass_of_conduit_json_renderer():
    assert issubclass(target_module.ArticleJSONRenderer, ConduitJSONRenderer)


def test_comment_renderer_is_subclass_of_conduit_json_renderer():
    assert issubclass(target_module.CommentJSONRenderer, ConduitJSONRenderer)


def test_article_renderer_class_attributes_exist_and_have_expected_values():
    cls = target_module.ArticleJSONRenderer
    # attributes defined on the class
    assert 'object_label' in cls.__dict__
    assert 'pagination_object_label' in cls.__dict__
    assert 'pagination_count_label' in cls.__dict__
    # expected values
    assert cls.object_label == 'article'
    assert cls.pagination_object_label == 'articles'
    assert cls.pagination_count_label == 'articlesCount'
    # types
    assert isinstance(cls.object_label, str)
    assert isinstance(cls.pagination_object_label, str)
    assert isinstance(cls.pagination_count_label, str)


def test_comment_renderer_class_attributes_exist_and_have_expected_values():
    cls = target_module.CommentJSONRenderer
    # attributes defined on the class
    assert 'object_label' in cls.__dict__
    assert 'pagination_object_label' in cls.__dict__
    assert 'pagination_count_label' in cls.__dict__
    # expected values
    assert cls.object_label == 'comment'
    assert cls.pagination_object_label == 'comments'
    assert cls.pagination_count_label == 'commentsCount'
    # types
    assert isinstance(cls.object_label, str)
    assert isinstance(cls.pagination_object_label, str)
    assert isinstance(cls.pagination_count_label, str)


def test_article_and_comment_renderers_have_distinct_labels():
    a = target_module.ArticleJSONRenderer
    c = target_module.CommentJSONRenderer
    assert a.object_label != c.object_label
    assert a.pagination_object_label != c.pagination_object_label
    assert a.pagination_count_label != c.pagination_count_label


def test_renderer_class_attributes_are_class_level_only():
    # Ensure attributes are on the class dict (not only inherited) and unchanged
    a_cls = target_module.ArticleJSONRenderer
    c_cls = target_module.CommentJSONRenderer

    # verify present in class dict
    assert 'object_label' in a_cls.__dict__
    assert 'object_label' in c_cls.__dict__

    # Changing an attribute on the class should reflect on the class but tests should restore original
    original = a_cls.object_label
    try:
        a_cls.object_label = 'temp'
        assert a_cls.object_label == 'temp'
    finally:
        a_cls.object_label = original  # restore to avoid side effects for other tests


def test_no_unexpected_extra_attributes_on_renderers():
    # Only verify that the known labels are present; there shouldn't be duplicate label keys
    a_keys = {k for k in target_module.ArticleJSONRenderer.__dict__.keys() if k.endswith('label') or k.endswith('Count')}
    c_keys = {k for k in target_module.CommentJSONRenderer.__dict__.keys() if k.endswith('label') or k.endswith('Count')}
    # Expect at least the three known labels; no duplicates beyond them
    assert {'object_label', 'pagination_object_label', 'pagination_count_label'}.issubset(a_keys)
    assert {'object_label', 'pagination_object_label', 'pagination_count_label'}.issubset(c_keys)