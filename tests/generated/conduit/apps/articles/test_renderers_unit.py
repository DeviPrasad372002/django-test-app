import importlib.util, pathlib, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/renderers.py').resolve()
_IMPORT_ERROR = None
try:
    _SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
    target_module = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(target_module)
except Exception as _e:
    _IMPORT_ERROR = str(_e)
    target_module = None
if _IMPORT_ERROR:
    pytest.skip(f'Cannot import target module: {_IMPORT_ERROR}', allow_module_level=True)


def test_article_renderer_class_attributes_exist_and_are_strings():
    cls = target_module.ArticleJSONRenderer
    assert hasattr(cls, 'object_label'), "ArticleJSONRenderer should define object_label"
    assert hasattr(cls, 'pagination_object_label'), "ArticleJSONRenderer should define pagination_object_label"
    assert hasattr(cls, 'pagination_count_label'), "ArticleJSONRenderer should define pagination_count_label"

    assert isinstance(cls.object_label, str)
    assert isinstance(cls.pagination_object_label, str)
    assert isinstance(cls.pagination_count_label, str)

    assert cls.object_label == 'article'
    assert cls.pagination_object_label == 'articles'
    assert cls.pagination_count_label == 'articlesCount'


def test_comment_renderer_class_attributes_exist_and_are_strings():
    cls = target_module.CommentJSONRenderer
    assert hasattr(cls, 'object_label'), "CommentJSONRenderer should define object_label"
    assert hasattr(cls, 'pagination_object_label'), "CommentJSONRenderer should define pagination_object_label"
    assert hasattr(cls, 'pagination_count_label'), "CommentJSONRenderer should define pagination_count_label"

    assert isinstance(cls.object_label, str)
    assert isinstance(cls.pagination_object_label, str)
    assert isinstance(cls.pagination_count_label, str)

    assert cls.object_label == 'comment'
    assert cls.pagination_object_label == 'comments'
    assert cls.pagination_count_label == 'commentsCount'


def test_inheritance_from_conduit_json_renderer():
    # Ensure the two classes inherit from the expected base
    base = getattr(target_module, 'ConduitJSONRenderer', None)
    assert base is not None, "ConduitJSONRenderer should be imported into the module"
    assert issubclass(target_module.ArticleJSONRenderer, base)
    assert issubclass(target_module.CommentJSONRenderer, base)


def test_instance_attribute_override_does_not_change_class():
    cls = target_module.ArticleJSONRenderer
    inst = cls()
    original_class_value = cls.object_label
    # override on the instance
    inst.object_label = 'temp-override'
    assert inst.object_label == 'temp-override'
    # class attribute should remain unchanged
    assert cls.object_label == original_class_value


def test_setting_class_attribute_with_monkeypatch_affects_only_target_class(monkeypatch):
    # Temporarily change ArticleJSONRenderer.pagination_count_label
    article_cls = target_module.ArticleJSONRenderer
    comment_cls = target_module.CommentJSONRenderer

    original_article = article_cls.pagination_count_label
    original_comment = comment_cls.pagination_count_label

    monkeypatch.setattr(article_cls, 'pagination_count_label', 'temporaryArticlesCount', raising=False)
    try:
        assert article_cls.pagination_count_label == 'temporaryArticlesCount'
        # Ensure comment class remains unchanged
        assert comment_cls.pagination_count_label == original_comment
    finally:
        # monkeypatch will restore automatically at test end; ensure values are consistent now
        pass


@pytest.mark.parametrize("cls_name, expected_object_label, expected_pagination_label, expected_count_label", [
    ("ArticleJSONRenderer", "article", "articles", "articlesCount"),
    ("CommentJSONRenderer", "comment", "comments", "commentsCount"),
])
def test_attributes_via_getattr(cls_name, expected_object_label, expected_pagination_label, expected_count_label):
    cls = getattr(target_module, cls_name)
    assert getattr(cls, 'object_label') == expected_object_label
    assert getattr(cls, 'pagination_object_label') == expected_pagination_label
    assert getattr(cls, 'pagination_count_label') == expected_count_label


def test_class_attributes_are_distinct_between_classes():
    a = target_module.ArticleJSONRenderer
    c = target_module.CommentJSONRenderer
    assert a.object_label != c.object_label
    assert a.pagination_object_label != c.pagination_object_label
    assert a.pagination_count_label != c.pagination_count_label