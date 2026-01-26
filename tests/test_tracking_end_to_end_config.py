#!/usr/bin/env python3
"""
End-to-end test: TUI config → YAML generation → test set generation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_yaml_generation():
    """Test that TUI config properly generates YAML with tracking parameters."""
    from src.cli.benchmark_tui import BenchmarkTUI, MultiTaskConfig, TaskConfiguration, PromptSpec
    import yaml
    import tempfile
    
    tui = BenchmarkTUI()
    
    # Create a test configuration
    task_config = TaskConfiguration(
        task_type='tracking',
        task_name='Tracking (Grape Test)',
        batch_size=10,
        prompts=PromptSpec(user_styles=['casual'], system_styles=['none']),
        parameters={
            'objects': ['grape', 'marble'],
            'containers': ['cup', 'bowl'],
            'distractor_count': [0, 1],
            'post_inversion_moves': [0, 1, 2],
            'location_initial': ['counter', 'table'],
            'distractor_types': ['irrelevant', 'spatial']
        }
    )
    
    multi_config = MultiTaskConfig(
        name='test_tracking_config',
        description='Test object tracking configuration',
        tasks=[task_config],
        output_dir='/tmp/test_tracking',
        temperature=0.1,
        language='en',
        thinking_enabled=False
    )
    
    # Generate YAML
    yaml_path = tui._create_multi_task_yaml_config(multi_config)
    
    # Load and verify YAML
    with open(yaml_path, 'r') as f:
        yaml_data = yaml.safe_load(f)
    
    print(f"✓ YAML generated: {yaml_path}")
    
    # Verify structure
    assert 'tasks' in yaml_data, "Missing 'tasks' in YAML"
    assert len(yaml_data['tasks']) == 1, "Expected 1 task"
    
    task = yaml_data['tasks'][0]
    assert task['type'] == 'object_tracking', f"Expected 'object_tracking', got '{task['type']}'"
    
    gen = task['generation']
    assert gen['count'] == 10, f"Expected count=10, got {gen['count']}"
    assert gen['object'] == ['grape', 'marble'], f"Unexpected objects: {gen['object']}"
    assert gen['container'] == ['cup', 'bowl'], f"Unexpected containers: {gen['container']}"
    assert gen['distractor_count'] == [0, 1], f"Unexpected distractor_count: {gen['distractor_count']}"
    assert gen['post_inversion_moves'] == [0, 1, 2], f"Unexpected post_inversion_moves: {gen['post_inversion_moves']}"
    
    # Check advanced parameters
    assert 'location_initial' in gen, "Missing 'location_initial'"
    assert gen['location_initial'] == ['counter', 'table'], f"Unexpected location_initial: {gen['location_initial']}"
    assert 'distractor_types' in gen, "Missing 'distractor_types'"
    assert gen['distractor_types'] == ['irrelevant', 'spatial'], f"Unexpected distractor_types: {gen['distractor_types']}"
    
    print("✓ YAML structure validated")
    print(f"  Task type: {task['type']}")
    print(f"  Test count: {gen['count']}")
    print(f"  Objects: {gen['object']}")
    print(f"  Containers: {gen['container']}")
    print(f"  Distractor counts: {gen['distractor_count']}")
    print(f"  Post-inversion moves: {gen['post_inversion_moves']}")
    print(f"  Initial locations: {gen['location_initial']}")
    print(f"  Distractor types: {gen['distractor_types']}")
    
    return yaml_path

def test_test_generation(yaml_path):
    """Test that YAML config successfully generates test set."""
    import subprocess
    import glob
    import gzip
    import json
    import tempfile
    
    output_dir = tempfile.mkdtemp(prefix='tracking_test_')
    
    # Run Stage 1
    result = subprocess.run(
        ['./bin/python', 'src/stages/generate_testset.py', yaml_path, '--output-dir', output_dir],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode != 0:
        print(f"❌ Stage 1 failed:")
        print(result.stdout)
        print(result.stderr)
        return False
    
    print(f"✓ Stage 1 completed successfully")
    
    # Find generated test set
    testset_files = glob.glob(f'{output_dir}/testset_*.json.gz')
    assert len(testset_files) > 0, "No test set file generated"
    
    testset_path = testset_files[0]
    print(f"✓ Test set generated: {testset_path}")
    
    # Load and verify test set
    with gzip.open(testset_path, 'rt') as f:
        testset = json.load(f)
    
    assert 'test_cases' in testset, "Missing 'test_cases' in test set"
    test_cases = testset['test_cases']
    assert len(test_cases) == 10, f"Expected 10 test cases, got {len(test_cases)}"
    
    # Verify first test case
    test_case = test_cases[0]
    assert test_case['task_type'] == 'object_tracking', f"Expected 'object_tracking', got '{test_case['task_type']}'"
    assert 'prompts' in test_case, "Missing 'prompts'"
    assert 'task_params' in test_case, "Missing 'task_params'"
    
    params = test_case['task_params']
    assert 'object' in params, "Missing 'object' in task_params"
    assert 'container' in params, "Missing 'container' in task_params"
    assert 'expected_answer' in params, "Missing 'expected_answer' in task_params"
    assert 'difficulty' in params, "Missing 'difficulty' in task_params"
    
    print(f"✓ Test set validated")
    print(f"  Total test cases: {len(test_cases)}")
    print(f"  Sample object: {params['object']}")
    print(f"  Sample container: {params['container']}")
    print(f"  Sample answer: {params['expected_answer']}")
    print(f"  Sample difficulty: {params['difficulty']}")
    print(f"  Question preview: {test_case['prompts']['user'][:80]}...")
    
    return True

if __name__ == '__main__':
    print("=" * 70)
    print("Object Tracking End-to-End Configuration Test")
    print("=" * 70)
    print()
    
    try:
        print("Stage 1: YAML Generation from TUI Config")
        print("-" * 70)
        yaml_path = test_yaml_generation()
        print()
        
        print("Stage 2: Test Set Generation from YAML")
        print("-" * 70)
        success = test_test_generation(yaml_path)
        print()
        
        if success:
            print("=" * 70)
            print("✅ ALL END-TO-END TESTS PASSED!")
            print("=" * 70)
            print("\nComplete workflow validated:")
            print("  1. TUI configuration → MultiTaskConfig")
            print("  2. MultiTaskConfig → YAML file")
            print("  3. YAML file → Test set generation")
            print("  4. Test set contains proper object_tracking cases")
            print("\nReady for production use! 🎉")
        else:
            print("❌ Test generation failed")
            sys.exit(1)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
