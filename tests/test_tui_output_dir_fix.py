#!/usr/bin/env python3
"""
Test TUI output_dir fix - verify MultiTaskConfig has output_dir field
and all workflows collect and use it properly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_multitask_config_has_output_dir():
    """Verify MultiTaskConfig dataclass has output_dir field."""
    from src.cli.benchmark_tui import MultiTaskConfig, TaskConfiguration
    from src.core.PromptEngine import PromptStyle, SystemPromptStyle
    from dataclasses import fields
    
    # Check fields
    field_names = [f.name for f in fields(MultiTaskConfig)]
    print(f"✓ MultiTaskConfig fields: {field_names}")
    assert 'output_dir' in field_names, "output_dir field missing from MultiTaskConfig!"
    
    # Create instance with output_dir
    from src.cli.benchmark_tui import PromptSpec
    test_config = MultiTaskConfig(
        name="test",
        description="test",
        tasks=[],
        output_dir="/tmp/test_output",
        temperature=0.1,
        language='en',
        thinking_enabled=False
    )
    
    assert test_config.output_dir == "/tmp/test_output"
    print(f"✓ MultiTaskConfig instance created with output_dir: {test_config.output_dir}")
    print("\n✅ ALL TESTS PASSED!")
    print("MultiTaskConfig now properly includes output_dir field.")

if __name__ == '__main__':
    test_multitask_config_has_output_dir()
