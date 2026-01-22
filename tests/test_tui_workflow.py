#!/usr/bin/env python3
"""Test TUI workflow - verify all screens are created and callable."""

from src.cli.benchmark_tui import BenchmarkTUI
from src.cli.benchmark_config import ModelSpec

def test_tui_initialization():
    """Test that TUI initializes without errors."""
    tui = BenchmarkTUI()
    assert tui is not None
    print("✓ TUI initialization successful")

def test_task_selection_method_exists():
    """Test that task_selection method exists."""
    tui = BenchmarkTUI()
    assert hasattr(tui, 'task_selection')
    print("✓ task_selection method exists")

def test_task_specific_config_method_exists():
    """Test that task_specific_config method exists."""
    tui = BenchmarkTUI()
    assert hasattr(tui, 'task_specific_config')
    print("✓ task_specific_config method exists")

def test_prompt_configuration_method_exists():
    """Test that prompt_configuration method exists."""
    tui = BenchmarkTUI()
    assert hasattr(tui, 'prompt_configuration')
    print("✓ prompt_configuration method exists")

def test_test_parameters_method_exists():
    """Test that test_parameters method exists."""
    tui = BenchmarkTUI()
    assert hasattr(tui, 'test_parameters')
    print("✓ test_parameters method exists")

def test_create_new_benchmark_method_exists():
    """Test that create_new_benchmark method exists."""
    tui = BenchmarkTUI()
    assert hasattr(tui, 'create_new_benchmark')
    print("✓ create_new_benchmark method exists")

def test_benchmark_config_has_task_fields():
    """Test that BenchmarkConfig has task_type and task_config fields."""
    from src.cli.benchmark_config import BenchmarkConfig
    config = BenchmarkConfig(name="Test")
    assert hasattr(config, 'task_type')
    assert hasattr(config, 'task_config')
    assert config.task_type == "gol"  # Default value
    assert config.task_config == {}
    print("✓ BenchmarkConfig has task_type and task_config fields")

def test_benchmark_config_task_assignment():
    """Test that task fields can be assigned."""
    from src.cli.benchmark_config import BenchmarkConfig
    config = BenchmarkConfig(name="Test")
    config.task_type = "ari"
    config.task_config = {"difficulties": [1, 2, 3]}
    assert config.task_type == "ari"
    assert config.task_config["difficulties"] == [1, 2, 3]
    print("✓ BenchmarkConfig task fields can be assigned")

if __name__ == "__main__":
    print("Testing TUI Workflow...")
    print()
    
    test_tui_initialization()
    test_task_selection_method_exists()
    test_task_specific_config_method_exists()
    test_prompt_configuration_method_exists()
    test_test_parameters_method_exists()
    test_create_new_benchmark_method_exists()
    test_benchmark_config_has_task_fields()
    test_benchmark_config_task_assignment()
    
    print()
    print("✓ All tests passed!")
