#!/usr/bin/env python3
"""
Test TUI directory consolidation - verify no duplicate directory questions.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_directory_consolidation():
    """Verify execution_configuration and output_configuration no longer ask for output_dir."""
    from src.cli.benchmark_tui import BenchmarkTUI
    import inspect
    
    tui = BenchmarkTUI()
    
    # Check execution_configuration method
    exec_config_source = inspect.getsource(tui.execution_configuration)
    assert "output_dir = questionary.text" not in exec_config_source, \
        "execution_configuration() still asks for output_dir!"
    print("✓ execution_configuration() no longer asks for output_dir")
    
    # Check output_configuration method  
    output_config_source = inspect.getsource(tui.output_configuration)
    assert "output_dir = questionary.text" not in output_config_source, \
        "output_configuration() still asks for output_dir!"
    print("✓ output_configuration() no longer asks for output_dir")
    
    # Check multi_task_configuration asks for it once
    multi_task_source = inspect.getsource(tui.multi_task_configuration)
    assert "output_dir = questionary.text" in multi_task_source, \
        "multi_task_configuration() should ask for output_dir!"
    print("✓ multi_task_configuration() asks for output_dir")
    
    # Check quick_start_benchmark asks for it
    quick_start_source = inspect.getsource(tui.quick_start_benchmark)
    assert "output_dir = questionary.text" in quick_start_source, \
        "quick_start_benchmark() should ask for output_dir!"
    print("✓ quick_start_benchmark() asks for output_dir")
    
    print("\n✅ ALL TESTS PASSED!")
    print("Directory consolidation complete - single output_dir question per workflow.")

if __name__ == '__main__':
    test_directory_consolidation()
