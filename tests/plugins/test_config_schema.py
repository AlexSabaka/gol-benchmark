"""Tests for the plugin configuration schema system."""

import pytest
from src.plugins import PluginRegistry, ConfigField
from src.plugins.base import TestCaseGenerator


VALID_FIELD_TYPES = {'number', 'select', 'multi-select', 'text', 'boolean', 'range', 'weight_map'}


class TestConfigField:
    """Tests for the ConfigField dataclass."""

    def test_to_dict_number(self):
        f = ConfigField(name='density', label='Cell density', field_type='number',
                        default=0.5, min_value=0.1, max_value=0.9, step=0.05)
        d = f.to_dict()
        assert d['name'] == 'density'
        assert d['label'] == 'Cell density'
        assert d['type'] == 'number'
        assert d['default'] == 0.5
        assert d['min'] == 0.1
        assert d['max'] == 0.9
        assert d['step'] == 0.05
        # group=basic should not be in output
        assert 'group' not in d

    def test_to_dict_select(self):
        f = ConfigField(name='mode', label='Mode', field_type='select',
                        default='expression', options=['expression', 'equation'])
        d = f.to_dict()
        assert d['type'] == 'select'
        assert d['options'] == ['expression', 'equation']
        assert d['default'] == 'expression'

    def test_to_dict_multi_select(self):
        f = ConfigField(name='rules', label='Rules', field_type='multi-select',
                        default=[30, 90], options=[30, 54, 60, 90, 110])
        d = f.to_dict()
        assert d['type'] == 'multi-select'
        assert d['default'] == [30, 90]
        assert 110 in d['options']

    def test_to_dict_boolean(self):
        f = ConfigField(name='flag', label='Enable', field_type='boolean', default=True)
        d = f.to_dict()
        assert d['type'] == 'boolean'
        assert d['default'] is True

    def test_to_dict_range(self):
        f = ConfigField(name='width_range', label='Width', field_type='range',
                        default=[3, 10], range_min_default=3, range_max_default=10,
                        min_value=1, max_value=50)
        d = f.to_dict()
        assert d['type'] == 'range'
        assert d['range_min_default'] == 3
        assert d['range_max_default'] == 10
        assert d['min'] == 1

    def test_to_dict_weight_map(self):
        f = ConfigField(name='weights', label='Weights', field_type='weight_map',
                        default={'a': 0.5, 'b': 0.5}, weight_keys=['a', 'b'])
        d = f.to_dict()
        assert d['type'] == 'weight_map'
        assert d['weight_keys'] == ['a', 'b']
        assert d['default'] == {'a': 0.5, 'b': 0.5}

    def test_to_dict_advanced_group_included(self):
        f = ConfigField(name='x', label='X', field_type='number', default=1, group='advanced')
        d = f.to_dict()
        assert d['group'] == 'advanced'

    def test_to_dict_help_included(self):
        f = ConfigField(name='x', label='X', field_type='number', default=1,
                        help='Some help text')
        d = f.to_dict()
        assert d['help'] == 'Some help text'

    def test_to_dict_omits_none_optionals(self):
        f = ConfigField(name='x', label='X', field_type='text', default='hi')
        d = f.to_dict()
        assert 'min' not in d
        assert 'max' not in d
        assert 'step' not in d
        assert 'options' not in d
        assert 'range_min_default' not in d
        assert 'weight_keys' not in d


class TestBaseGeneratorDefaults:
    """Test that the base class get_config_schema returns empty list."""

    def test_base_returns_empty(self):
        # TestCaseGenerator is abstract, but we can check the default method
        assert TestCaseGenerator.get_config_schema(None) == []


class TestAllPluginsHaveConfigSchema:
    """Test that every registered plugin provides a config schema."""

    @pytest.fixture(autouse=True)
    def ensure_plugins_loaded(self):
        PluginRegistry._ensure_loaded()

    def test_all_plugins_have_schema(self):
        """Every plugin generator should implement get_config_schema()."""
        for task_type in PluginRegistry.list_task_types():
            plugin = PluginRegistry.get(task_type)
            generator = plugin.get_generator()
            schema = generator.get_config_schema()
            assert isinstance(schema, list), f"{task_type}: get_config_schema must return a list"
            assert len(schema) > 0, f"{task_type}: get_config_schema should not be empty"

    def test_schema_field_types_valid(self):
        """All fields must use a recognized field type."""
        for task_type in PluginRegistry.list_task_types():
            plugin = PluginRegistry.get(task_type)
            generator = plugin.get_generator()
            for field in generator.get_config_schema():
                assert field.field_type in VALID_FIELD_TYPES, \
                    f"{task_type}.{field.name}: unknown type '{field.field_type}'"

    def test_schema_field_names_are_strings(self):
        """All field names must be non-empty strings."""
        for task_type in PluginRegistry.list_task_types():
            plugin = PluginRegistry.get(task_type)
            generator = plugin.get_generator()
            for field in generator.get_config_schema():
                assert isinstance(field.name, str) and field.name, \
                    f"{task_type}: field name must be a non-empty string"

    def test_select_fields_have_options(self):
        """Select and multi-select fields must have options."""
        for task_type in PluginRegistry.list_task_types():
            plugin = PluginRegistry.get(task_type)
            generator = plugin.get_generator()
            for field in generator.get_config_schema():
                if field.field_type in ('select', 'multi-select'):
                    assert field.options is not None and len(field.options) > 0, \
                        f"{task_type}.{field.name}: {field.field_type} must have options"

    def test_weight_map_fields_have_keys(self):
        """Weight map fields must have weight_keys."""
        for task_type in PluginRegistry.list_task_types():
            plugin = PluginRegistry.get(task_type)
            generator = plugin.get_generator()
            for field in generator.get_config_schema():
                if field.field_type == 'weight_map':
                    assert field.weight_keys is not None and len(field.weight_keys) > 0, \
                        f"{task_type}.{field.name}: weight_map must have weight_keys"

    def test_to_dict_roundtrip(self):
        """to_dict should produce valid JSON-serializable dicts."""
        import json
        for task_type in PluginRegistry.list_task_types():
            plugin = PluginRegistry.get(task_type)
            generator = plugin.get_generator()
            for field in generator.get_config_schema():
                d = field.to_dict()
                # Must be JSON-serializable
                json.dumps(d)
                # Must have required keys
                assert 'name' in d
                assert 'label' in d
                assert 'type' in d
                assert 'default' in d
