#!/usr/bin/env python3
"""
Test the enhanced run_testset.py with a simple arithmetic test to verify it's working.
"""

import json
import gzip
import tempfile
import sys
import subprocess
from pathlib import Path

def create_simple_test():
    """Create a minimal test set to verify parsing works."""
    testset = {
        "format_version": "1.0.0",
        "metadata": {
            "name": "simple_arithmetic_test",
            "version": "1.0",
            "description": "Test enhanced parsing",
            "total_tests": 2,
            "created_at": "2026-01-23T00:00:00.000000"
        },
        "tests": [
            {
                "test_id": "test_001",
                "task_type": "arithmetic",
                "user_prompt": "2 + 3 = ?\\n\\nAnswer: ",
                "system_prompt": "You are a helpful assistant. Be concise.",
                "task_params": {
                    "expected_answer": 5,
                    "difficulty": 1,
                    "expression": "2 + 3"
                }
            },
            {
                "test_id": "test_002", 
                "task_type": "arithmetic",
                "user_prompt": "10 / 2 = ?\\n\\nAnswer: ",
                "system_prompt": "You are a helpful assistant. Be concise.",
                "task_params": {
                    "expected_answer": 5,
                    "difficulty": 1,
                    "expression": "10 / 2"
                }
            }
        ]
    }
    
    # Write to temporary gzipped file
    temp_dir = Path("/tmp")
    test_file = temp_dir / "simple_test.json.gz"
    
    with gzip.open(test_file, 'wt') as f:
        json.dump(testset, f, indent=2)
    
    print(f"Created test file: {test_file}")
    return test_file

def run_test(test_file):
    """Run the test using our enhanced run_testset.py"""
    cmd = [
        sys.executable, 
        "/Volumes/2TB/repos/gol_eval/src/stages/run_testset.py",
        str(test_file),
        "--model", "qwen3:0.6b",
        "--provider", "ollama",
        "--output-dir", "/tmp"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    print(f"Return code: {result.returncode}")
    print(f"STDOUT:\\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\\n{result.stderr}")
    
    return result.returncode == 0

if __name__ == "__main__":
    print("🧪 Testing Enhanced run_testset.py")
    print("=" * 50)
    
    # Create test
    test_file = create_simple_test()
    
    # Run test
    success = run_test(test_file)
    
    if success:
        print("\\n✅ Test completed successfully!")
    else:
        print("\\n❌ Test failed!")
    
    # Clean up
    test_file.unlink(missing_ok=True)