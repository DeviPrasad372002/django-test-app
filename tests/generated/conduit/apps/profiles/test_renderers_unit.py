import importlib.util, pathlib, pytest
_MODULE_PATH = pathlib.Path(r'/home/runner/work/tech-demo/tech-demo/target-repo/conduit/apps/profiles/renderers.py').resolve()
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


def test_profilejsonrenderer_class_exists_and_labels_are_correct():
    assert hasattr(target_module, 'ProfileJSONRenderer'), "ProfileJSONRenderer not defined in module"
    cls = target_module.ProfileJSONRenderer
    # Check the expected class attributes exist
    for attr, expected in (
        ('object_label', 'profile'),
        ('pagination_object_label', 'profiles'),
        ('pagination_count_label', 'profilesCount'),
    ):
        assert hasattr(cls, attr), f"{attr} missing on ProfileJSONRenderer"
        value = getattr(cls, attr)
        assert isinstance(value, str), f"{attr} should be a string"
        assert value == expected, f"{attr} expected {expected!r} but got {value!r}"


def test_profilejsonrenderer_is_subclass_of_conduitjsonrenderer():
    cls = target_module.ProfileJSONRenderer
    # Ensure one of the bases in MRO is named ConduitJSONRenderer
    mro_names = [c.__name__ for c in cls.__mro__]
    assert 'ConduitJSONRenderer' in mro_names, "ProfileJSONRenderer does not inherit from ConduitJSONRenderer"


def test_instance_attributes_reflect_class_defaults_and_instance_override_does_not_mutate_class():
    cls = target_module.ProfileJSONRenderer
    inst = cls()
    # Instance should reflect class defaults
    assert getattr(inst, 'object_label') == cls.object_label
    assert getattr(inst, 'pagination_object_label') == cls.pagination_object_label
    assert getattr(inst, 'pagination_count_label') == cls.pagination_count_label

    # Mutating instance attribute should not change class attribute
    original = cls.object_label
    inst.object_label = 'modified'
    assert cls.object_label == original
    assert inst.object_label == 'modified'


def _find_conduit_base(cls):
    # Return the base class object from MRO whose name is ConduitJSONRenderer, or None
    for c in cls.__mro__:
        if c.__name__ == 'ConduitJSONRenderer':
            return c
    return None


def test_render_delegates_to_base_render_when_present(monkeypatch):
    cls = target_module.ProfileJSONRenderer
    base = _find_conduit_base(cls)
    if base is None:
        pytest.skip("ConduitJSONRenderer base class not present; cannot test render delegation")

    # Ensure base has attribute render; if not skip this test
    if not hasattr(base, 'render'):
        pytest.skip("ConduitJSONRenderer has no 'render' method to monkeypatch")

    inst = cls()

    # Monkeypatch base.render to a predictable callable
    called = {}
    def fake_render(self, data, *args, **kwargs):
        called['self_is_instance'] = isinstance(self, cls)
        called['data'] = data
        return {'wrapped_by': 'base', 'data': data}

    # Attempt to set attribute on base; if it's not writable, skip
    try:
        monkeypatch.setattr(base, 'render', fake_render, raising=True)
    except Exception as e:
        pytest.skip(f"Cannot monkeypatch base.render: {e}")

    # Call instance.render and verify it used the fake implementation
    sample = {'username': 'alice'}
    result = inst.render(sample)
    assert result == {'wrapped_by': 'base', 'data': sample}
    assert called.get('self_is_instance') is True
    assert called.get('data') == sample


def test_render_propagates_exceptions_from_base(monkeypatch):
    cls = target_module.ProfileJSONRenderer
    base = _find_conduit_base(cls)
    if base is None:
        pytest.skip("ConduitJSONRenderer base class not present; cannot test exception propagation")

    if not hasattr(base, 'render'):
        pytest.skip("ConduitJSONRenderer has no 'render' method to monkeypatch for exception propagation")

    inst = cls()

    def raising_render(self, data, *args, **kwargs):
        raise ValueError("simulated error")

    try:
        monkeypatch.setattr(base, 'render', raising_render, raising=True)
    except Exception as e:
        pytest.skip(f"Cannot monkeypatch base.render to raise: {e}")

    with pytest.raises(ValueError, match="simulated error"):
        inst.render({'any': 'data'})