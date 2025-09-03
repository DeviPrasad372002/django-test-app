import importlib.util, pathlib
import pytest

_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_article_class_has_expected_labels():
    cls = target_module.ArticleJSONRenderer
    # attributes defined on class
    assert 'object_label' in cls.__dict__
    assert 'pagination_object_label' in cls.__dict__
    assert 'pagination_count_label' in cls.__dict__
    # values are exact expected strings
    assert cls.object_label == 'article'
    assert cls.pagination_object_label == 'articles'
    assert cls.pagination_count_label == 'articlesCount'


def test_comment_class_has_expected_labels():
    cls = target_module.CommentJSONRenderer
    # attributes defined on class
    assert 'object_label' in cls.__dict__
    assert 'pagination_object_label' in cls.__dict__
    assert 'pagination_count_label' in cls.__dict__
    # values are exact expected strings
    assert cls.object_label == 'comment'
    assert cls.pagination_object_label == 'comments'
    assert cls.pagination_count_label == 'commentsCount'


def test_classes_inherit_conduit_json_renderer():
    art_base = target_module.ArticleJSONRenderer.__mro__[1]
    com_base = target_module.CommentJSONRenderer.__mro__[1]
    # Base class name is ConduitJSONRenderer
    assert art_base.__name__ == 'ConduitJSONRenderer'
    assert com_base.__name__ == 'ConduitJSONRenderer'
    # Base class likely defined in conduit.apps.core.renderers
    assert 'conduit.apps.core.renderers' in art_base.__module__
    assert 'conduit.apps.core.renderers' in com_base.__module__


def test_label_types_and_uniqueness_between_classes():
    a_obj = target_module.ArticleJSONRenderer.object_label
    a_pag_obj = target_module.ArticleJSONRenderer.pagination_object_label
    a_pag_cnt = target_module.ArticleJSONRenderer.pagination_count_label

    c_obj = target_module.CommentJSONRenderer.object_label
    c_pag_obj = target_module.CommentJSONRenderer.pagination_object_label
    c_pag_cnt = target_module.CommentJSONRenderer.pagination_count_label

    # all are strings
    for v in (a_obj, a_pag_obj, a_pag_cnt, c_obj, c_pag_obj, c_pag_cnt):
        assert isinstance(v, str)

    # object labels differ
    assert a_obj != c_obj
    # pagination object labels differ
    assert a_pag_obj != c_pag_obj
    # pagination count labels differ
    assert a_pag_cnt != c_pag_cnt

    # simple convention checks
    assert a_pag_obj.endswith('s')
    assert c_pag_obj.endswith('s')
    assert a_pag_cnt.endswith('Count')
    assert c_pag_cnt.endswith('Count')