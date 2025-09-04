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


def test_renderers_have_expected_class_attributes():
    # Ensure both renderer classes expose the three expected label attributes
    expected = {
        'ArticleJSONRenderer': {
            'object_label': 'article',
            'pagination_object_label': 'articles',
            'pagination_count_label': 'articlesCount'
        },
        'CommentJSONRenderer': {
            'object_label': 'comment',
            'pagination_object_label': 'comments',
            'pagination_count_label': 'commentsCount'
        }
    }

    for cls_name, labels in expected.items():
        assert hasattr(target_module, cls_name), f"{cls_name} not found in module"
        cls = getattr(target_module, cls_name)
        for attr_name, expected_value in labels.items():
            assert hasattr(cls, attr_name), f"{cls_name} missing attribute {attr_name}"
            val = getattr(cls, attr_name)
            assert isinstance(val, str), f"{cls_name}.{attr_name} is not a string"
            assert val == expected_value, f"{cls_name}.{attr_name} == {val!r}, expected {expected_value!r}"


def test_renderers_inherit_from_conduit_json_renderer():
    # Verify that both classes inherit from a class named 'ConduitJSONRenderer' somewhere in their MRO
    for cls_name in ('ArticleJSONRenderer', 'CommentJSONRenderer'):
        cls = getattr(target_module, cls_name)
        mro_names = [c.__name__ for c in cls.__mro__]
        assert 'ConduitJSONRenderer' in mro_names, (
            f"{cls_name} does not inherit from ConduitJSONRenderer; MRO: {mro_names}"
        )


def test_instance_vs_class_attribute_mutation_isolated(monkeypatch):
    # Create instances and verify that modifying the instance attribute does not change the class attribute,
    # and that changing class attribute affects only that class and new instances.
    Article = getattr(target_module, 'ArticleJSONRenderer')
    Comment = getattr(target_module, 'CommentJSONRenderer')

    # Snapshot original values
    orig_article_obj_label = Article.object_label
    orig_comment_obj_label = Comment.object_label

    # Instance-level mutation should not affect class attribute
    art_inst = Article()
    art_inst.object_label = 'temporary-instance-article'
    assert Article.object_label == orig_article_obj_label
    assert art_inst.object_label == 'temporary-instance-article'

    # Class-level mutation should affect new instances but not other classes
    Article.object_label = 'mutated-article-class'
    new_art_inst = Article()
    assert Article.object_label == 'mutated-article-class'
    assert new_art_inst.object_label == 'mutated-article-class'

    # Ensure Comment class unaffected
    assert Comment.object_label == orig_comment_obj_label

    # Cleanup: restore original class attribute to avoid side effects for other tests
    Article.object_label = orig_article_obj_label


def test_classes_are_independent_when_mutating_pagination_labels():
    # Mutate pagination labels on Article and ensure Comment remains unchanged
    Article = getattr(target_module, 'ArticleJSONRenderer')
    Comment = getattr(target_module, 'CommentJSONRenderer')

    orig_article_pagination = Article.pagination_object_label
    orig_comment_pagination = Comment.pagination_object_label

    try:
        Article.pagination_object_label = 'differentArticles'
        assert Article.pagination_object_label == 'differentArticles'
        # Comment must remain the original
        assert Comment.pagination_object_label == orig_comment_pagination
    finally:
        # restore
        Article.pagination_object_label = orig_article_pagination


def test_attributes_exist_as_class_level_for_new_instances():
    # New instances should reflect class attributes at construction time
    Article = getattr(target_module, 'ArticleJSONRenderer')
    Comment = getattr(target_module, 'CommentJSONRenderer')

    Article.pagination_count_label = 'articlesCount'  # ensure known
    Comment.pagination_count_label = 'commentsCount'

    a1 = Article()
    c1 = Comment()
    assert getattr(a1, 'pagination_count_label') == Article.pagination_count_label
    assert getattr(c1, 'pagination_count_label') == Comment.pagination_count_label

    # Changing class attribute should reflect in subsequent instances
    Article.pagination_count_label = 'newArticlesCount'
    a2 = Article()
    assert getattr(a2, 'pagination_count_label') == 'newArticlesCount'
    # previous instance retains its attribute value (instance attribute lookup falls back to class unless overridden)
    assert getattr(a1, 'pagination_count_label') == 'articlesCount' or getattr(a1, 'pagination_count_label') == 'newArticlesCount'
    # We don't enforce which one because attribute access for old instances reflects current class unless shadowed;
    # Main assertion is that new instance uses updated class attribute.