import sys
import types
import importlib.util
import pathlib
import pytest

# Prepare a fake conduit.apps.core.renderers module with a ConduitJSONRenderer base class
renderers_mod = types.ModuleType("conduit.apps.core.renderers")
class ConduitJSONRenderer:
    """
    Minimal stub implementation for testing the ArticleJSONRenderer and CommentJSONRenderer.
    - If data is a list, returns a dict using pagination_object_label and pagination_count_label.
    - If data is a dict (single object), returns a dict using object_label.
    - Otherwise raises TypeError.
    """
    object_label = 'object'
    pagination_object_label = 'objects'
    pagination_count_label = 'objectsCount'

    def render(self, data):
        if isinstance(data, list):
            return {self.pagination_object_label: data, self.pagination_count_label: len(data)}
        if isinstance(data, dict) or data is None:
            return {self.object_label: data}
        raise TypeError("Unsupported data type for render")

renderers_mod.ConduitJSONRenderer = ConduitJSONRenderer

# Build package hierarchy modules so the import inside target file succeeds
conduit_mod = types.ModuleType("conduit")
conduit_apps_mod = types.ModuleType("conduit.apps")
conduit_apps_core_mod = types.ModuleType("conduit.apps.core")

# Insert into sys.modules before importing the target module
sys.modules["conduit"] = conduit_mod
sys.modules["conduit.apps"] = conduit_apps_mod
sys.modules["conduit.apps.core"] = conduit_apps_core_mod
sys.modules["conduit.apps.core.renderers"] = renderers_mod

# Now import the target module using the provided pattern
import importlib.util, pathlib
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/articles/renderers.py').resolve()
_SPEC = importlib.util.spec_from_file_location('target_module', _MODULE_PATH)
target_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target_module)


def test_renderer_classes_inherit_stub_base():
    # Ensure the classes exist and inherit from the stub ConduitJSONRenderer
    assert hasattr(target_module, "ArticleJSONRenderer")
    assert hasattr(target_module, "CommentJSONRenderer")

    assert issubclass(target_module.ArticleJSONRenderer, ConduitJSONRenderer)
    assert issubclass(target_module.CommentJSONRenderer, ConduitJSONRenderer)


def test_article_renderer_labels_are_set_correctly():
    # Check explicit class attributes for ArticleJSONRenderer
    cls = target_module.ArticleJSONRenderer
    assert getattr(cls, "object_label") == "article"
    assert getattr(cls, "pagination_object_label") == "articles"
    assert getattr(cls, "pagination_count_label") == "articlesCount"


def test_comment_renderer_labels_are_set_correctly():
    # Check explicit class attributes for CommentJSONRenderer
    cls = target_module.CommentJSONRenderer
    assert getattr(cls, "object_label") == "comment"
    assert getattr(cls, "pagination_object_label") == "comments"
    assert getattr(cls, "pagination_count_label") == "commentsCount"


def test_article_render_single_object():
    renderer = target_module.ArticleJSONRenderer()
    data = {"title": "Test Article", "body": "Content"}
    rendered = renderer.render(data)
    # Should wrap using 'article' label
    assert isinstance(rendered, dict)
    assert "article" in rendered
    assert rendered["article"] == data


def test_article_render_list_pagination():
    renderer = target_module.ArticleJSONRenderer()
    data = [{"id": 1}, {"id": 2}]
    rendered = renderer.render(data)
    # Should produce pagination keys 'articles' and 'articlesCount'
    assert "articles" in rendered
    assert "articlesCount" in rendered
    assert rendered["articles"] == data
    assert rendered["articlesCount"] == 2


def test_comment_render_empty_list_and_count_zero():
    renderer = target_module.CommentJSONRenderer()
    data = []
    rendered = renderer.render(data)
    assert "comments" in rendered
    assert "commentsCount" in rendered
    assert rendered["comments"] == []
    assert rendered["commentsCount"] == 0


def test_render_unsupported_type_raises_type_error():
    renderer = target_module.ArticleJSONRenderer()
    with pytest.raises(TypeError):
        renderer.render(12345)