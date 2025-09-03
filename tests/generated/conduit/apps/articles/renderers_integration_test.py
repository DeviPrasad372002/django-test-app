import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_article_renderer_class_attributes_and_inheritance():
    # Class exists
    assert hasattr(target_module, 'ArticleJSONRenderer')
    Article = target_module.ArticleJSONRenderer
    # Inherits from ConduitJSONRenderer
    assert hasattr(target_module, 'ConduitJSONRenderer')
    assert issubclass(Article, target_module.ConduitJSONRenderer)
    # Class attribute values
    assert getattr(Article, 'object_label') == 'article'
    assert getattr(Article, 'pagination_object_label') == 'articles'
    assert getattr(Article, 'pagination_count_label') == 'articlesCount'


def test_comment_renderer_class_attributes_and_inheritance():
    # Class exists
    assert hasattr(target_module, 'CommentJSONRenderer')
    Comment = target_module.CommentJSONRenderer
    # Inherits from ConduitJSONRenderer
    assert hasattr(target_module, 'ConduitJSONRenderer')
    assert issubclass(Comment, target_module.ConduitJSONRenderer)
    # Class attribute values
    assert getattr(Comment, 'object_label') == 'comment'
    assert getattr(Comment, 'pagination_object_label') == 'comments'
    assert getattr(Comment, 'pagination_count_label') == 'commentsCount'


def test_instances_are_creatable_and_attributes_accessible():
    # Instantiate both renderers (should not raise)
    article_instance = target_module.ArticleJSONRenderer()
    comment_instance = target_module.CommentJSONRenderer()
    # Instances expose the attributes and they match class values initially
    assert article_instance.object_label == target_module.ArticleJSONRenderer.object_label
    assert article_instance.pagination_object_label == target_module.ArticleJSONRenderer.pagination_object_label
    assert article_instance.pagination_count_label == target_module.ArticleJSONRenderer.pagination_count_label

    assert comment_instance.object_label == target_module.CommentJSONRenderer.object_label
    assert comment_instance.pagination_object_label == target_module.CommentJSONRenderer.pagination_object_label
    assert comment_instance.pagination_count_label == target_module.CommentJSONRenderer.pagination_count_label


def test_instance_attribute_mutation_does_not_change_class_attributes():
    article_instance = target_module.ArticleJSONRenderer()
    # Mutate instance attribute
    article_instance.object_label = 'mutated'
    # Instance changed
    assert article_instance.object_label == 'mutated'
    # Class remains unchanged
    assert target_module.ArticleJSONRenderer.object_label == 'article'


def test_labels_are_non_empty_strings():
    for cls in (target_module.ArticleJSONRenderer, target_module.CommentJSONRenderer):
        for attr in ('object_label', 'pagination_object_label', 'pagination_count_label'):
            val = getattr(cls, attr)
            assert isinstance(val, str)
            assert val != ''


def test_article_and_comment_have_distinct_labels():
    a = target_module.ArticleJSONRenderer
    c = target_module.CommentJSONRenderer
    # Ensure at least one label differs to confirm they are distinct renderers
    assert a.object_label != c.object_label
    assert a.pagination_object_label != c.pagination_object_label
    assert a.pagination_count_label != c.pagination_count_label


def test_render_method_presence_if_provided_by_base():
    base = target_module.ConduitJSONRenderer
    Article = target_module.ArticleJSONRenderer()
    # If base provides a 'render' attribute, it should be callable on instances
    if hasattr(base, 'render'):
        assert hasattr(Article, 'render')
        assert callable(getattr(Article, 'render'))