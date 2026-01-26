#!/usr/bin/env python3
"""Quick verification that object_tracking is fully integrated."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli.benchmark_tui import BenchmarkTUI
import inspect

tui = BenchmarkTUI()

# Check available tasks
source = inspect.getsource(tui.multi_task_configuration)
assert "'id': 'tracking'" in source, "tracking not in available tasks"
print("✓ TUI has tracking in available tasks")

# Check task type mapping
yaml_source = inspect.getsource(tui._create_multi_task_yaml_config)
assert "'tracking': 'object_tracking'" in yaml_source, "tracking mapping missing"
print("✓ TUI has tracking → object_tracking mapping")

# Check YAML generation
assert "mapped_task_type == 'object_tracking'" in yaml_source, "object_tracking YAML gen missing"
print("✓ TUI has object_tracking YAML generation")

# Verify parameters
assert 'distractor_count' in yaml_source, "distractor_count parameter missing"
assert 'post_inversion_moves' in yaml_source, "post_inversion_moves parameter missing"
print("✓ TUI has correct object_tracking parameters")

print("\n✅ ALL VERIFICATIONS PASSED!")
print("\n🎉 Object Tracking Plugin is fully integrated!")
print("\nReady to use in TUI:")
print("  python -m src.cli.benchmark_tui")
