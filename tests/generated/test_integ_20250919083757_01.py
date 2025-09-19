import importlib.util, pytest
if importlib.util.find_spec('django') is None:
    pytest.skip('django not installed; skipping module', allow_module_level=True)

import os, sys, types as _types, pytest as _pytest, warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
_t = os.environ.get('TARGET_ROOT') or 'target'
if _t and os.path.isdir(_t):
    _p = os.path.abspath(os.path.join(_t, os.pardir))
    [sys.path.insert(0, p) for p in (_p,_t) if p not in sys.path]
    _pkg=_types.ModuleType('target'); _pkg.__path__=[_t]; sys.modules.setdefault('target', _pkg)

import builtins
import types

import pytest

try:
    from conduit.apps.core.utils import generate_random_string
    from conduit.apps.articles.signals import add_slug_to_article_if_not_exists
    from conduit.apps.articles.models import Article
    from conduit.apps.articles.relations import TagRelatedField
except ImportError as exc:
    pytest.skip(f"Required target modules not available: {exc}", allow_module_level=True)

def test_generate_random_string_deterministic(monkeypatch):
    # Arrange
    calls = []
    def fake_choice(seq):
        # deterministic and records called sequence for assertion
        calls.append(tuple(seq))
        return "x"

    monkeypatch.setattr("random.choice", fake_choice)

    # Act
    out = generate_random_string(6)

    # Assert
    assert isinstance(out, str)
    assert out == "xxxxxx"
    # ensure underlying alphabet was provided (ascii letters + digits expected)
    assert any("a" in s or "A" in s or "0" in s for s in calls[0])

@pytest.mark.parametrize("initial_slug, expected_after", [
    (None, "slugged"),
    ("existing-slug", "existing-slug"),
])
def test_add_slug_to_article_if_not_exists_creates_and_preserves(monkeypatch, initial_slug, expected_after):
    # Arrange
    # Replace slugify with a deterministic implementation
    monkeypatch.setattr("conduit.apps.articles.signals.slugify", lambda s: "slugged")

    # Create a lightweight fake instance that mimics an Article
    FakeArticle = types.SimpleNamespace
    article = FakeArticle(title="Some Title", slug=initial_slug)

    # Act
    # The signal handler signature in many projects: (sender, instance, created, **kwargs)
    add_slug_to_article_if_not_exists(sender=Article, instance=article, created=True)

    # Assert
    assert article.slug == expected_after

def test_article_str_uses_title():
    # Arrange
    fake = types.SimpleNamespace(title="Readable Title")

    # Act
    # Call unbound __str__ to avoid Django model instantiation
    s = Article.__str__(fake)  # type: ignore

    # Assert
    assert isinstance(s, str)
    assert s == "Readable Title"

def test_tagrelatedfield_to_internal_value_and_to_representation(monkeypatch):
    # Arrange
    field = TagRelatedField()

    class FakeTag:
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return f"<Tag {self.name}>"

    # Create a fake queryset-like object with get behavior
    class FakeQuerySet:
        def __init__(self, tags):
            self._tags = {t.name: t for t in tags}

        def get(self, **kwargs):
            # assume lookup by name or value
            if "name" in kwargs:
                key = kwargs["name"]
            elif "value" in kwargs:
                key = kwargs["value"]
            else:
                raise KeyError("unsupported lookup")
            if key in self._tags:
                return self._tags[key]
            raise Exception("DoesNotExist")

    existing_tag = FakeTag("python")
    qs = FakeQuerySet([existing_tag])

    # monkeypatch the field's get_queryset method to return our fake queryset
    monkeypatch.setattr(field, "get_queryset", lambda: qs)

    # Act
    tag_obj = field.to_internal_value("python")
    rep = field.to_representation(existing_tag)

    # Assert
    assert isinstance(tag_obj, FakeTag)
    assert tag_obj is existing_tag
    assert rep == "python" or getattr(rep, "name", None) == "python" or rep == existing_tag.name

    
    monkeypatch.setattr(field, "get_queryset", lambda: FakeQuerySet([]))
    with pytest.raises(Exception):
        field.to_internal_value("missing-tag")
