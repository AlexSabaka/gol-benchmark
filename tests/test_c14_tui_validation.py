#!/usr/bin/env python3
"""
Test script to validate C14 TUI integration fixes.
Tests the complete config → YAML → testset generation flow.
"""

import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.stages.generate_testset import main as generate_testset_main
import yaml
import json
import gzip


def create_test_yaml_config() -> str:
    """Create a minimal C14 YAML config matching TUI output"""
    config = {
        'metadata': {
            'name': 'c14_tui_validation_test',
            'version': '1.0',
            'schema_version': '1.0.0',
            'description': 'Testing C14 TUI integration fixes',
            'created_by': 'test_c14_tui_validation',
            'task_type': 'cellular_automata_1d'
        },
        'tasks': [
            {
                'type': 'cellular_automata_1d',
                'generation': {
                    'seed': 42,
                    'rule_numbers': [90],  # Easy rule
                    'width': 16,
                    'steps': 1,
                    'boundary_condition': 'wrap',
                    'initial_pattern': 'centered_single',
                    'density': 0.3,
                    'cases_per_rule': 3
                },
                'prompt_configs': [
                    {
                        'name': 'minimal_analytical',
                        'user_style': 'minimal',
                        'system_style': 'analytical',
                        'language': 'en'
                    }
                ]
            }
        ],
        'sampling': {
            'temperature': 0.1,
            'max_tokens': 512,
            'top_p': 0.9
        },
        'execution': {
            'no_thinking': True,
            'timeout': 60,
            'retries': 1
        }
    }
    return yaml.dump(config, default_flow_style=False, sort_keys=False)


def test_c14_testset_generation():
    """Test that C14 test set generation works"""
    print("🧪 C14 TUI Integration Validation Test\n")
    print("=" * 60)
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_content = create_test_yaml_config()
        f.write(yaml_content)
        config_path = f.name
    
    print(f"✓ Created test config: {config_path}")
    print("\nConfig content:")
    print("-" * 60)
    print(yaml_content)
    print("-" * 60)
    
    try:
        # Run test set generation (output goes to default testsets/ dir)
        print("\n📦 Generating test set...")
        sys.argv = [
            'generate_testset.py',
            config_path
        ]
        
        generate_testset_main()
        
        # Check output in default testsets/ directory
        testsets_dir = project_root / 'testsets'
        testset_files = list(testsets_dir.glob('testset_c14_tui_validation_test_*.json.gz'))
        
        if not testset_files:
            print("❌ FAILED: No test set file generated")
            return False
        
        # Use the most recent file
        testset_path = max(testset_files, key=lambda p: p.stat().st_mtime)
        print(f"✓ Test set generated: {testset_path.name}")
        
        # Validate test set content
        with gzip.open(testset_path, 'rt') as f:
            testset_data = json.load(f)
        
        print("\n📊 Test Set Validation:")
        print(f"  - Metadata: {testset_data['metadata']['name']}")
        print(f"  - Total cases: {len(testset_data['test_cases'])}")
        
        # Validate test case structure
        if not testset_data['test_cases']:
            print("❌ FAILED: No test cases in test set")
            return False
        
        first_case = testset_data['test_cases'][0]
        required_fields = ['test_id', 'task_type', 'prompts', 'task_params']
        
        print(f"\n  First test case validation:")
        for field in required_fields:
            if field not in first_case:
                print(f"    ❌ Missing field: {field}")
                return False
            print(f"    ✓ {field}: present")
        
        # Validate task_params
        params = first_case['task_params']
        required_params = ['rule_number', 'initial_state', 'expected_next_state', 'width', 'boundary']
        
        print(f"\n  Task params validation:")
        for param in required_params:
            if param not in params:
                print(f"    ❌ Missing param: {param}")
                return False
            print(f"    ✓ {param}: {params[param]}")
        
        # Validate prompt generation
        prompts = first_case['prompts']
        if not prompts.get('user') or not prompts.get('system'):
            print("    ❌ Prompts missing or empty")
            return False
        
        print(f"\n  Prompt validation:")
        print(f"    ✓ System prompt: {len(prompts['system'])} chars")
        print(f"    ✓ User prompt: {len(prompts['user'])} chars")
        
        # Check that rule_number is in the prompt
        if str(params['rule_number']) not in prompts['user']:
            print(f"    ⚠️  Warning: Rule number {params['rule_number']} not found in prompt")
        else:
            print(f"    ✓ Rule number present in prompt")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n📋 Summary:")
        print("  - C14 YAML config structure: ✓")
        print("  - Test set generation: ✓")
        print("  - Test case structure: ✓")
        print("  - Task parameters: ✓")
        print("  - Prompt generation: ✓")
        print("\n🎉 C14 TUI integration is working correctly!")
        
        # Cleanup test file
        print(f"\n🧹 Cleaning up test file: {testset_path.name}")
        testset_path.unlink()
        
        return True
            
    except Exception as e:
        print(f"\n❌ FAILED with exception:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        Path(config_path).unlink(missing_ok=True)


if __name__ == '__main__':
    success = test_c14_testset_generation()
    sys.exit(0 if success else 1)
