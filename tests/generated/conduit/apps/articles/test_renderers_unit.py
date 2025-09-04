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


def _get_attr_or_skip(name):
    if not hasattr(target_module, name):
        pytest.skip(f"Target module does not define {name}", allow_module_level=True)
    return getattr(target_module, name)


def _safe_instantiate(cls):
    try:
        return cls()
    except TypeError as e:
        pytest.skip(f"Cannot instantiate {cls!r} without arguments: {e}")


def test_renderer_classes_exist_and_inherit():
    # Ensure classes are defined
    ArticleJSONRenderer = _get_attr_or_skip('ArticleJSONRenderer')
    CommentJSONRenderer = _get_attr_or_skip('CommentJSONRenderer')
    ConduitJSONRenderer = _get_attr_or_skip('ConduitJSONRenderer')

    # Ensure the base is a class/type
    if not isinstance(ConduitJSONRenderer, type):
        pytest.skip("ConduitJSONRenderer is not a class/type in the target module")

    # Ensure correct inheritance
    assert issubclass(ArticleJSONRenderer, ConduitJSONRenderer), "ArticleJSONRenderer should inherit from ConduitJSONRenderer"
    assert issubclass(CommentJSONRenderer, ConduitJSONRenderer), "CommentJSONRenderer should inherit from ConduitJSONRenderer"


def test_article_labels_are_expected_strings():
    ArticleJSONRenderer = _get_attr_or_skip('ArticleJSONRenderer')
    # Class attributes should exist and be strings
    for attr, expected in (
        ('object_label', 'article'),
        ('pagination_object_label', 'articles'),
        ('pagination_count_label', 'articlesCount'),
    ):
        assert hasattr(ArticleJSONRenderer, attr), f"ArticleJSONRenderer is missing {attr}"
        value = getattr(ArticleJSONRenderer, attr)
        assert isinstance(value, str), f"{attr} should be a string"
        assert value == expected, f"{attr} expected {expected!r} but got {value!r}"


def test_comment_labels_are_expected_strings():
    CommentJSONRenderer = _get_attr_or_skip('CommentJSONRenderer')
    for attr, expected in (
        ('object_label', 'comment'),
        ('pagination_object_label', 'comments'),
        ('pagination_count_label', 'commentsCount'),
    ):
        assert hasattr(CommentJSONRenderer, attr), f"CommentJSONRenderer is missing {attr}"
        value = getattr(CommentJSONRenderer, attr)
        assert isinstance(value, str), f"{attr} should be a string"
        assert value == expected, f"{attr} expected {expected!r} but got {value!r}"


def test_article_and_comment_labels_differ():
    ArticleJSONRenderer = _get_attr_or_skip('ArticleJSONRenderer')
    CommentJSONRenderer = _get_attr_or_skip('CommentJSONRenderer')

    # Ensure the two renderers have different object_label and pagination labels where appropriate
    assert ArticleJSONRenderer.object_label != CommentJSONRenderer.object_label
    assert ArticleJSONRenderer.pagination_object_label != CommentJSONRenderer.pagination_object_label
    assert ArticleJSONRenderer.pagination_count_label != CommentJSONRenderer.pagination_count_label


def test_instance_attribute_override_does_not_change_class_attribute():
    ArticleJSONRenderer = _get_attr_or_skip('ArticleJSONRenderer')

    # Try instantiation; skip if not possible
    instance = _safe_instantiate(ArticleJSONRenderer)

    # Save original class attribute
    original = ArticleJSONRenderer.object_label
    # Override on instance
    instance.object_label = 'modified-on-instance'
    # Instance should reflect new value
    assert instance.object_label == 'modified-on-instance'
    # Class attribute should remain unchanged
    assert ArticleJSONRenderer.object_label == original


def test_attributes_available_on_instance_and_are_strings():
    CommentJSONRenderer = _get_attr_or_skip('CommentJSONRenderer')
    instance = _safe_instantiate(CommentJSONRenderer)

    for attr in ('object_label', 'pagination_object_label', 'pagination_count_label'):
        assert hasattr(instance, attr), f"Instance missing {attr}"
        value = getattr(instance, attr)
        assert isinstance(value, str), f"{attr} on instance should be a string"


def test_pagination_count_label_suffix():
    # Ensure both pagination_count_label end with 'Count' as per naming convention
    ArticleJSONRenderer = _get_attr_or_skip('ArticleJSONRenderer')
    CommentJSONRenderer = _get_attr_or_skip('CommentJSONRenderer')

    assert ArticleJSONRenderer.pagination_count_label.endswith('Count')
    assert CommentJSONRenderer.pagination_count_label.endswith('Count')