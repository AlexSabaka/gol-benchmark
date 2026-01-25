"""
Unit tests for the Plugin Registry system.
"""

import pytest
from src.plugins import PluginRegistry
from src.plugins.base import BenchmarkPlugin


class TestPluginRegistry:
    """Test the plugin registry discovery and registration."""

    def test_plugin_discovery(self):
        """Test that plugins are auto-discovered."""
        task_types = PluginRegistry.list_task_types()

        # Should have at least 5 plugins
        assert len(task_types) >= 5

        # Check expected plugins are present
        expected_plugins = [
            'game_of_life',
            'arithmetic',
            'linda_fallacy',
            'cellular_automata_1d',
            'ascii_shapes'
        ]

        for plugin_type in expected_plugins:
            assert plugin_type in task_types, f"Missing plugin: {plugin_type}"

    def test_get_plugin(self):
        """Test retrieving plugins by task type."""
        plugin = PluginRegistry.get('game_of_life')

        assert plugin is not None
        assert isinstance(plugin, BenchmarkPlugin)
        assert plugin.task_type == 'game_of_life'
        assert plugin.display_name == "Conway's Game of Life"

    def test_plugin_components(self):
        """Test that plugins have all required components."""
        for task_type in PluginRegistry.list_task_types():
            plugin = PluginRegistry.get(task_type)

            # Test generator
            generator = plugin.get_generator()
            assert generator is not None
            assert hasattr(generator, 'generate_batch')

            # Test parser
            parser = plugin.get_parser()
            assert parser is not None
            assert hasattr(parser, 'parse')

            # Test evaluator
            evaluator = plugin.get_evaluator()
            assert evaluator is not None
            assert hasattr(evaluator, 'evaluate')

    def test_plugin_metadata(self):
        """Test plugin metadata."""
        plugins = PluginRegistry.list_plugins()

        assert len(plugins) >= 5

        for plugin_info in plugins:
            assert 'task_type' in plugin_info
            assert 'display_name' in plugin_info
            assert 'description' in plugin_info
            assert 'version' in plugin_info

            # Version should be semantic
            assert plugin_info['version'].count('.') == 2

    def test_no_discovery_errors(self):
        """Test that plugin discovery has no errors."""
        errors = PluginRegistry.get_discovery_errors()

        # Should have no errors
        assert len(errors) == 0, f"Discovery errors: {errors}"

    def test_plugin_uniqueness(self):
        """Test that each plugin has a unique task_type."""
        task_types = PluginRegistry.list_task_types()

        # No duplicates
        assert len(task_types) == len(set(task_types))

    def test_invalid_plugin(self):
        """Test getting non-existent plugin returns None."""
        plugin = PluginRegistry.get('nonexistent_task')

        assert plugin is None
