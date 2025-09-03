import importlib.util, pathlib, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/models.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_article_str_returns_title_when_set():
    a = target_module.Article()
    a.title = "Test Article Title"
    # direct call should return the title string
    assert a.__str__() == "Test Article Title"
    # str(...) should also work when a proper string is returned
    assert str(a) == "Test Article Title"


def test_article_str_without_title_returns_none_and_str_raises():
    a = target_module.Article()
    # when title is not set, __str__ returns None
    assert a.__str__() is None
    # calling str(a) should raise because __str__ returned non-string
    with pytest.raises(TypeError):
        str(a)


def test_article_str_prefers_title_over_other_fields():
    a = target_module.Article()
    a.title = "Title Only"
    a.slug = "title-only"
    # ensure __str__ uses title, not slug or other attributes
    assert a.__str__() == "Title Only"
    assert str(a) == "Title Only"


def test_tag_str_returns_tag_when_set():
    t = target_module.Tag()
    t.tag = "python"
    assert t.__str__() == "python"
    assert str(t) == "python"


def test_tag_str_with_non_string_returns_value_and_str_raises():
    t = target_module.Tag()
    t.tag = 12345
    # __str__ returns the raw value
    assert t.__str__() == 12345
    # str(...) should raise because __str__ did not return a string
    with pytest.raises(TypeError):
        str(t)


def test_model_field_attributes_exist_on_classes():
    # Check Article fields
    assert hasattr(target_module.Article, 'slug')
    assert hasattr(target_module.Article, 'title')
    assert hasattr(target_module.Article, 'description')
    assert hasattr(target_module.Article, 'body')
    assert hasattr(target_module.Article, 'author')
    assert hasattr(target_module.Article, 'tags')

    # Check Comment fields
    assert hasattr(target_module.Comment, 'body')
    assert hasattr(target_module.Comment, 'article')
    assert hasattr(target_module.Comment, 'author')

    # Check Tag fields
    assert hasattr(target_module.Tag, 'tag')
    assert hasattr(target_module.Tag, 'slug')