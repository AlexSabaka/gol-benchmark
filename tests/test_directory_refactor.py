#!/usr/bin/env python3
"""
Test the refactored directory management.

This script tests that:
1. All output goes to a single directory
2. No configs/, testsets/, results/ subdirectories are created
3. PathManager works with custom output directory
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.path_manager import get_path_manager

def test_path_manager():
    """Test PathManager with custom output directory."""
    
    # Create temporary test directory
    test_dir = Path(tempfile.mkdtemp(prefix="gol_test_"))
    print(f"Testing in: {test_dir}")
    
    try:
        # Initialize PathManager with custom output directory
        pm = get_path_manager(output_dir=test_dir)
        
        # Test config path generation
        config_path = pm.get_testset_config_path(
            name="test_config",
            task_types=["arithmetic", "gol"]
        )
        print(f"\n✓ Config path: {config_path}")
        assert config_path.parent == test_dir, f"Config not in output_dir! {config_path.parent} != {test_dir}"
        
        # Test testset path generation
        testset_path = pm.get_testset_path(
            config_name="test",
            task_types=["arithmetic"],
            config_hash="abc123"
        )
        print(f"✓ Testset path: {testset_path}")
        assert testset_path.parent == test_dir, f"Testset not in output_dir! {testset_path.parent} != {test_dir}"
        
        # Test results path generation
        results_path = pm.get_results_path(
            models=["qwen3:0.6b"],
            testset_name="test_baseline"
        )
        print(f"✓ Results path: {results_path}")
        assert results_path.parent == test_dir, f"Results not in output_dir! {results_path.parent} != {test_dir}"
        
        # Test report path generation
        report_path = pm.get_report_path(
            report_name="test_report"
        )
        print(f"✓ Report path: {report_path}")
        assert report_path.parent == test_dir, f"Report not in output_dir! {report_path.parent} != {test_dir}"
        
        # Test visualization dir generation
        viz_dir = pm.get_visualization_dir(
            report_name="test_report"
        )
        print(f"✓ Visualization dir: {viz_dir}")
        assert viz_dir.parent == test_dir, f"Viz dir not in output_dir! {viz_dir.parent} != {test_dir}"
        assert viz_dir.exists(), "Viz dir not created!"
        
        # Verify no subdirectories were created
        subdirs = [d for d in test_dir.iterdir() if d.is_dir()]
        print(f"\nSubdirectories created: {[d.name for d in subdirs]}")
        
        # Only charts_* directories should exist (from viz dir creation)
        for subdir in subdirs:
            assert subdir.name.startswith("charts_"), f"Unexpected subdir: {subdir.name}"
        
        print("\n✅ All tests passed! Directory structure is flat.")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"Cleaned up: {test_dir}")

if __name__ == "__main__":
    success = test_path_manager()
    sys.exit(0 if success else 1)
