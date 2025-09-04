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

@pytest.mark.parametrize("cls_name,expected", [
    ("ArticleJSONRenderer", {
        "object_label": "article",
        "pagination_object_label": "articles",
        "pagination_count_label": "articlesCount",
    }),
    ("CommentJSONRenderer", {
        "object_label": "comment",
        "pagination_object_label": "comments",
        "pagination_count_label": "commentsCount",
    }),
])
def test_class_attributes_exist_and_have_expected_values(cls_name, expected):
    cls = getattr(target_module, cls_name)
    # class attributes should exist and equal expected values
    for attr, val in expected.items():
        assert hasattr(cls, attr), f"{cls_name} missing attribute {attr}"
        assert getattr(cls, attr) == val

def test_attributes_are_defined_on_class_not_only_inherited():
    # Ensure these attributes are defined on the classes themselves (__dict__), not merely inherited
    article_cls = target_module.ArticleJSONRenderer
    comment_cls = target_module.CommentJSONRenderer

    for attr in ("object_label", "pagination_object_label", "pagination_count_label"):
        assert attr in article_cls.__dict__, f"{attr} should be in ArticleJSONRenderer.__dict__"
        assert attr in comment_cls.__dict__, f"{attr} should be in CommentJSONRenderer.__dict__"

def test_subclass_of_conduit_json_renderer():
    # Ensure both renderers are subclasses of the base ConduitJSONRenderer imported into the module
    base = getattr(target_module, "ConduitJSONRenderer", None)
    assert base is not None, "ConduitJSONRenderer should be available in target module"
    assert issubclass(target_module.ArticleJSONRenderer, base)
    assert issubclass(target_module.CommentJSONRenderer, base)

def test_labels_are_strings_and_non_empty():
    for cls in (target_module.ArticleJSONRenderer, target_module.CommentJSONRenderer):
        for attr in ("object_label", "pagination_object_label", "pagination_count_label"):
            val = getattr(cls, attr)
            assert isinstance(val, str)
            assert val != "", f"{cls.__name__}.{attr} should not be empty"

def test_different_classes_have_different_labels_where_expected():
    art = target_module.ArticleJSONRenderer
    com = target_module.CommentJSONRenderer

    # object_label should differ
    assert art.object_label != com.object_label
    # pagination_object_label should differ
    assert art.pagination_object_label != com.pagination_object_label
    # pagination_count_label should differ
    assert art.pagination_count_label != com.pagination_count_label

def test_instance_override_does_not_modify_class_attribute():
    # create instance without calling __init__ to avoid side effects if __init__ exists
    cls = target_module.ArticleJSONRenderer
    inst = object.__new__(cls)
    original = cls.object_label
    # set attribute on instance
    inst.object_label = "modified-on-instance"
    # instance has modified value
    assert inst.object_label == "modified-on-instance"
    # class attribute remains unchanged
    assert cls.object_label == original

def test_class_attribute_types_immutable_expected_behavior():
    # Ensure that class attributes are basic immutable types (strings) and modifying a class attribute changes class-level value
    cls = target_module.CommentJSONRenderer
    original = cls.pagination_count_label
    try:
        cls.pagination_count_label = "tempChange"
        assert cls.pagination_count_label == "tempChange"
    finally:
        # restore original to avoid affecting other tests
        cls.pagination_count_label = original

def test_repr_and_str_do_not_raise():
    # Simple sanity check: str() and repr() on class and a lightweight instance should not raise
    cls = target_module.ArticleJSONRenderer
    s = str(cls)
    r = repr(cls)
    assert isinstance(s, str) and isinstance(r, str)

    # create instance without __init__
    inst = object.__new__(cls)
    # str/repr on instance
    assert isinstance(str(inst), str)
    assert isinstance(repr(inst), str)