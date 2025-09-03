import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_article_renderer_class_attrs():
    cls = target_module.ArticleJSONRenderer
    assert hasattr(cls, 'object_label')
    assert hasattr(cls, 'pagination_object_label')
    assert hasattr(cls, 'pagination_count_label')

    assert cls.object_label == 'article'
    assert cls.pagination_object_label == 'articles'
    assert cls.pagination_count_label == 'articlesCount'


def test_comment_renderer_class_attrs():
    cls = target_module.CommentJSONRenderer
    assert hasattr(cls, 'object_label')
    assert hasattr(cls, 'pagination_object_label')
    assert hasattr(cls, 'pagination_count_label')

    assert cls.object_label == 'comment'
    assert cls.pagination_object_label == 'comments'
    assert cls.pagination_count_label == 'commentsCount'


def test_renderers_have_distinct_labels():
    a = target_module.ArticleJSONRenderer
    c = target_module.CommentJSONRenderer

    assert a.object_label != c.object_label
    assert a.pagination_object_label != c.pagination_object_label
    assert a.pagination_count_label != c.pagination_count_label


def test_inheritance_base_is_conduit_json_renderer():
    # The immediate base class should be ConduitJSONRenderer
    base = target_module.ArticleJSONRenderer.__mro__[1]
    assert base.__name__ == 'ConduitJSONRenderer'
    # base should come from the core renderers module in the conduit package
    assert 'conduit.apps.core.renderers' in base.__module__


def test_instance_attribute_independence():
    inst = target_module.ArticleJSONRenderer()
    # Changing instance attribute should not change class attribute
    inst.object_label = 'temp-article'
    assert inst.object_label == 'temp-article'
    assert target_module.ArticleJSONRenderer.object_label == 'article'

    # New attribute on instance should not appear on class
    inst.new_flag = True
    assert hasattr(inst, 'new_flag')
    assert not hasattr(target_module.ArticleJSONRenderer, 'new_flag')


def test_attribute_types_and_non_empty():
    for cls in (target_module.ArticleJSONRenderer, target_module.CommentJSONRenderer):
        for attr in ('object_label', 'pagination_object_label', 'pagination_count_label'):
            val = getattr(cls, attr)
            assert isinstance(val, str)
            assert val != ''


def test_accessing_missing_attribute_raises_attribute_error():
    inst = target_module.ArticleJSONRenderer()
    with pytest.raises(AttributeError):
        _ = inst.non_existent_attribute  # should raise AttributeError on dot access of missing attribute on instance-level