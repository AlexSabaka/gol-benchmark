"""
Benchmark Plugin System

This module provides a plugin-based architecture for benchmark tasks.
Each benchmark (Game of Life, Arithmetic, Linda Fallacy, etc.) is a
self-contained plugin that can be discovered and used automatically.

Usage:
    from src.plugins import PluginRegistry

    # Get a specific plugin
    plugin = PluginRegistry.get('game_of_life')
    if plugin:
        generator = plugin.get_generator()
        test_cases = generator.generate_batch(config, prompt_config, count=10)

    # List all available plugins
    task_types = PluginRegistry.list_task_types()

    # Get all plugins
    plugins = PluginRegistry.get_all()

Adding a New Plugin:
    1. Create a new directory: src/plugins/my_benchmark/
    2. Create __init__.py with a class extending BenchmarkPlugin
    3. Create a module-level `plugin` variable with an instance
    4. The plugin will be auto-discovered on first registry access
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional

from src.plugins.base import (
    BenchmarkPlugin,
    TestCaseGenerator,
    ResponseParser,
    ResultEvaluator,
    TestCase,
    ParsedAnswer,
    EvaluationResult,
)

__all__ = [
    'PluginRegistry',
    'BenchmarkPlugin',
    'TestCaseGenerator',
    'ResponseParser',
    'ResultEvaluator',
    'TestCase',
    'ParsedAnswer',
    'EvaluationResult',
]


class PluginRegistry:
    """
    Central registry for benchmark plugins with auto-discovery.

    The registry automatically discovers plugins in the src/plugins/ directory.
    Each plugin package must export a `plugin` variable that is an instance
    of BenchmarkPlugin.

    Example:
        # In src/plugins/my_task/__init__.py:
        class MyTaskPlugin(BenchmarkPlugin):
            ...

        plugin = MyTaskPlugin()  # This gets auto-discovered
    """

    _plugins: Dict[str, BenchmarkPlugin] = {}
    _loaded: bool = False
    _discovery_errors: List[str] = []

    @classmethod
    def register(cls, plugin: BenchmarkPlugin) -> None:
        """
        Register a plugin instance.

        Args:
            plugin: BenchmarkPlugin instance to register

        Raises:
            ValueError: If a plugin with the same task_type is already registered
        """
        task_type = plugin.task_type
        if task_type in cls._plugins:
            raise ValueError(
                f"Plugin already registered for task_type '{task_type}'. "
                f"Existing: {cls._plugins[task_type].__class__.__name__}, "
                f"New: {plugin.__class__.__name__}"
            )
        cls._plugins[task_type] = plugin

    @classmethod
    def unregister(cls, task_type: str) -> Optional[BenchmarkPlugin]:
        """
        Unregister a plugin by task type.

        Args:
            task_type: The task type to unregister

        Returns:
            The unregistered plugin, or None if not found
        """
        return cls._plugins.pop(task_type, None)

    @classmethod
    def get(cls, task_type: str) -> Optional[BenchmarkPlugin]:
        """
        Get a plugin by task type.

        Args:
            task_type: The task type identifier (e.g., 'game_of_life')

        Returns:
            BenchmarkPlugin instance or None if not found
        """
        cls._ensure_loaded()
        return cls._plugins.get(task_type)

    @classmethod
    def get_all(cls) -> Dict[str, BenchmarkPlugin]:
        """
        Get all registered plugins.

        Returns:
            Dictionary mapping task_type to BenchmarkPlugin instances
        """
        cls._ensure_loaded()
        return cls._plugins.copy()

    @classmethod
    def list_task_types(cls) -> List[str]:
        """
        List all registered task types.

        Returns:
            List of task type identifiers
        """
        cls._ensure_loaded()
        return list(cls._plugins.keys())

    @classmethod
    def list_plugins(cls) -> List[Dict[str, str]]:
        """
        List all plugins with their metadata.

        Returns:
            List of dictionaries with plugin info
        """
        cls._ensure_loaded()
        return [
            {
                'task_type': p.task_type,
                'display_name': p.display_name,
                'description': p.description,
                'version': p.version,
            }
            for p in cls._plugins.values()
        ]

    @classmethod
    def is_loaded(cls) -> bool:
        """Check if plugins have been loaded."""
        return cls._loaded

    @classmethod
    def get_discovery_errors(cls) -> List[str]:
        """Get any errors encountered during plugin discovery."""
        cls._ensure_loaded()
        return cls._discovery_errors.copy()

    @classmethod
    def reload(cls) -> None:
        """Force reload of all plugins."""
        cls._plugins.clear()
        cls._discovery_errors.clear()
        cls._loaded = False
        cls._ensure_loaded()

    @classmethod
    def _ensure_loaded(cls) -> None:
        """Auto-discover plugins on first access."""
        if cls._loaded:
            return
        cls._auto_discover()
        cls._loaded = True

    @classmethod
    def _auto_discover(cls) -> None:
        """
        Auto-discover plugins in the plugins directory.

        Scans all subdirectories of src/plugins/ for packages that
        export a `plugin` variable that is a BenchmarkPlugin instance.
        """
        plugins_dir = Path(__file__).parent

        for item in plugins_dir.iterdir():
            if not item.is_dir():
                continue
            if item.name.startswith('_'):
                continue
            if item.name == '__pycache__':
                continue

            module_name = f"src.plugins.{item.name}"

            try:
                module = importlib.import_module(module_name)

                if hasattr(module, 'plugin'):
                    plugin = module.plugin
                    if isinstance(plugin, BenchmarkPlugin):
                        cls.register(plugin)
                    else:
                        cls._discovery_errors.append(
                            f"{module_name}: 'plugin' is not a BenchmarkPlugin instance "
                            f"(got {type(plugin).__name__})"
                        )
            except ImportError as e:
                cls._discovery_errors.append(f"{module_name}: Import error - {e}")
            except Exception as e:
                cls._discovery_errors.append(f"{module_name}: {type(e).__name__} - {e}")


def get_plugin(task_type: str) -> Optional[BenchmarkPlugin]:
    """
    Convenience function to get a plugin by task type.

    Args:
        task_type: The task type identifier

    Returns:
        BenchmarkPlugin instance or None
    """
    return PluginRegistry.get(task_type)


def list_plugins() -> List[str]:
    """
    Convenience function to list all task types.

    Returns:
        List of task type identifiers
    """
    return PluginRegistry.list_task_types()
