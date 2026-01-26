#!/usr/bin/env python3
"""
Test object_tracking TUI configuration screens.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_quick_config():
    """Test quick configuration has object_tracking defaults."""
    from src.cli.benchmark_tui import BenchmarkTUI
    
    tui = BenchmarkTUI()
    
    # Test quick config
    config = tui._configure_single_task_quick('tracking', 'Tracking (Grape Test)')
    
    assert config is not None, "Quick config returned None"
    assert config.task_type == 'tracking'
    assert config.task_name == 'Tracking (Grape Test)'
    assert 'objects' in config.parameters, "Missing 'objects' parameter"
    assert 'containers' in config.parameters, "Missing 'containers' parameter"
    assert 'distractor_count' in config.parameters, "Missing 'distractor_count' parameter"
    assert 'post_inversion_moves' in config.parameters, "Missing 'post_inversion_moves' parameter"
    
    print("✓ Quick configuration includes object_tracking parameters")
    print(f"  Objects: {config.parameters['objects']}")
    print(f"  Containers: {config.parameters['containers']}")
    print(f"  Distractor counts: {config.parameters['distractor_count']}")
    print(f"  Post-inversion moves: {config.parameters['post_inversion_moves']}")

def test_custom_config_exists():
    """Test custom configuration method exists and has tracking support."""
    from src.cli.benchmark_tui import BenchmarkTUI
    import inspect
    
    tui = BenchmarkTUI()
    
    # Check method exists
    assert hasattr(tui, '_configure_task_specific_params'), "Method _configure_task_specific_params missing"
    
    # Check tracking is in the method
    source = inspect.getsource(tui._configure_task_specific_params)
    assert "task_type == 'tracking'" in source, "tracking configuration missing from _configure_task_specific_params"
    assert "'objects'" in source, "objects configuration missing"
    assert "'containers'" in source, "containers configuration missing"
    assert "'distractor_count'" in source, "distractor_count configuration missing"
    assert "'post_inversion_moves'" in source, "post_inversion_moves configuration missing"
    
    print("✓ Custom configuration method has object_tracking support")
    print("  ✓ Objects configuration")
    print("  ✓ Containers configuration")
    print("  ✓ Distractor count configuration")
    print("  ✓ Post-inversion moves configuration")
    
    # Check for advanced options
    if "'location_initial'" in source:
        print("  ✓ Advanced: Initial locations")
    if "'distractor_types'" in source:
        print("  ✓ Advanced: Distractor types")

if __name__ == '__main__':
    print("=" * 60)
    print("Object Tracking TUI Configuration Test")
    print("=" * 60)
    print()
    
    try:
        test_quick_config()
        print()
        
        test_custom_config_exists()
        print()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nObject Tracking TUI configuration is complete.")
        print("\nTry it out:")
        print("  python -m src.cli.benchmark_tui")
        print("  → Select 'Tracking (Grape Test)'")
        print("  → Choose 'Customize prompt styles and parameters'")
        print("  → Configure objects, containers, distractors, etc.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
