#!/usr/bin/env python3
"""
Integration test for object_tracking plugin - verify full pipeline works.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_plugin_registration():
    """Verify plugin is properly registered."""
    from src.plugins import PluginRegistry
    
    task_types = PluginRegistry.list_task_types()
    assert 'object_tracking' in task_types, f"object_tracking not in {task_types}"
    print("✓ Plugin registered in PluginRegistry")
    
    plugins = PluginRegistry.list_plugins()
    ot_plugin = [p for p in plugins if p['task_type'] == 'object_tracking']
    assert len(ot_plugin) == 1, "object_tracking plugin not found"
    assert ot_plugin[0]['display_name'] == 'Object Tracking (Grape Test)'
    print(f"✓ Plugin metadata: {ot_plugin[0]['display_name']}")

def test_generator():
    """Test generator creates valid test cases."""
    from src.plugins.object_tracking.generator import ObjectTrackingTestCaseGenerator
    
    generator = ObjectTrackingTestCaseGenerator()
    
    config = {
        'object': ['grape'],
        'container': ['cup'],
        'distractor_count': [0, 1],
        'post_inversion_moves': [0, 1]
    }
    
    prompt_config = {
        'user_style': 'casual',
        'system_style': 'none',
        'language': 'en',
        'name': 'test_casual_none'
    }
    
    test_cases = generator.generate_batch(
        config=config,
        prompt_config=prompt_config,
        count=3,
        seed=42
    )
    
    assert len(test_cases) == 3, f"Expected 3 test cases, got {len(test_cases)}"
    
    for tc in test_cases:
        assert hasattr(tc, 'test_id'), "Test case missing 'test_id'"
        assert hasattr(tc, 'prompts'), "Test case missing 'prompts'"
        assert hasattr(tc, 'task_params'), "Test case missing 'task_params'"
        assert 'expected_answer' in tc.task_params, "task_params missing 'expected_answer'"
        assert 'difficulty' in tc.task_params, "task_params missing 'difficulty'"
        assert 'distractor_count' in tc.task_params, "task_params missing 'distractor_count'"
    
    print(f"✓ Generator created {len(test_cases)} valid test cases")
    print(f"  Example question (first 100 chars): {test_cases[0].prompts['user'][:100]}...")
    print(f"  Example answer: {test_cases[0].task_params['expected_answer']}")
    print(f"  Difficulty: {test_cases[0].task_params['difficulty']}")

def test_parser():
    """Test parser extracts locations correctly."""
    from src.plugins.object_tracking.parser import ObjectTrackingResponseParser
    
    parser = ObjectTrackingResponseParser()
    
    # Mock task_params with known locations
    task_params = {
        'object': 'grape',
        'initial_location': 'counter',
        'container': 'cup'
    }
    
    test_cases = [
        ("counter", "counter"),
        ("Answer: table", "table"),
        ("The grape is on the floor.", "floor"),
        ("It's on the desk now.", "desk"),
        ("cabinet", "cabinet"),
    ]
    
    for response, expected in test_cases:
        parsed = parser.parse(response, task_params)
        assert parsed.value == expected, f"Failed to parse '{response}': got '{parsed.value}', expected '{expected}'"
    
    print(f"✓ Parser correctly extracted {len(test_cases)} locations")

def test_evaluator():
    """Test evaluator compares locations correctly."""
    from src.plugins.object_tracking.evaluator import ObjectTrackingResultEvaluator
    from src.plugins.base import ParsedAnswer
    
    evaluator = ObjectTrackingResultEvaluator()
    
    task_params = {
        'object': 'grape',
        'expected_answer': 'counter',
        'difficulty': 'easy'
    }
    
    # Exact match
    parsed = ParsedAnswer(value="counter", raw_response="counter", parse_strategy='single_word')
    result = evaluator.evaluate(parsed, "counter", task_params)
    assert result.correct == True
    assert result.match_type == 'exact'
    
    # Synonym match
    parsed = ParsedAnswer(value="countertop", raw_response="countertop", parse_strategy='single_word')
    result = evaluator.evaluate(parsed, "counter", task_params)
    assert result.correct == True
    assert result.match_type == 'synonym_match'
    
    # Mismatch
    parsed = ParsedAnswer(value="table", raw_response="table", parse_strategy='single_word')
    result = evaluator.evaluate(parsed, "counter", task_params)
    assert result.correct == False
    assert result.match_type == 'mismatch'
    
    # Parse error
    parsed = ParsedAnswer(value=None, raw_response="", parse_strategy='failed', error='Empty response')
    result = evaluator.evaluate(parsed, "counter", task_params)
    assert result.correct == False
    assert result.match_type == 'parse_error'
    
    print("✓ Evaluator correctly compares locations")

def test_tui_integration():
    """Verify TUI has object_tracking in available tasks."""
    from src.cli.benchmark_tui import BenchmarkTUI
    import inspect
    
    tui = BenchmarkTUI()
    source = inspect.getsource(tui.multi_task_configuration)
    
    # Check if tracking task is in available_tasks
    assert "'id': 'tracking'" in source, "tracking task not found in TUI available_tasks"
    assert "'name': 'Tracking (Grape Test)'" in source, "Tracking display name not found"
    print("✓ TUI has object_tracking in task selection")
    
    # Check task type mapping
    yaml_source = inspect.getsource(tui._create_multi_task_yaml_config)
    assert "'tracking': 'object_tracking'" in yaml_source, "tracking task type mapping missing"
    print("✓ TUI has task type mapping: tracking → object_tracking")
    
    # Check YAML generation has object_tracking parameters
    assert "mapped_task_type == 'object_tracking'" in yaml_source, "object_tracking YAML generation missing"
    print("✓ TUI has YAML generation parameters for object_tracking")

def test_analyze_results_integration():
    """Verify analyze_results can extract object_tracking task type."""
    from src.stages.analyze_results import extract_task_breakdown
    
    mock_results = [
        {'test_id': 'multi_0000_object_tracking', 'evaluation': {'correct': True}},
        {'test_id': 'multi_0001_tracking', 'evaluation': {'correct': False}},
        {'test_id': 'multi_0002_object_tracking', 'evaluation': {'correct': True}},
    ]
    
    breakdown = extract_task_breakdown(mock_results)
    
    assert 'object_tracking' in breakdown, f"object_tracking not in breakdown: {list(breakdown.keys())}"
    assert breakdown['object_tracking']['total'] == 3, f"Expected 3, got {breakdown['object_tracking']['total']}"
    assert breakdown['object_tracking']['correct'] == 2, f"Expected 2 correct, got {breakdown['object_tracking']['correct']}"
    
    print("✓ analyze_results correctly extracts object_tracking task type")
    print(f"  Breakdown: {breakdown['object_tracking']['total']} total, {breakdown['object_tracking']['correct']} correct")

def test_end_to_end_plugin_system():
    """Test that plugin can be retrieved and used through plugin system."""
    from src.plugins import PluginRegistry
    
    # Get plugin through registry
    plugins_dict = {p['task_type']: p for p in PluginRegistry.list_plugins()}
    assert 'object_tracking' in plugins_dict
    
    # Retrieve actual plugin object
    from src.plugins.object_tracking import plugin
    assert plugin.task_type == 'object_tracking'
    assert plugin.display_name == 'Object Tracking (Grape Test)'
    
    # Test generator through plugin
    generator = plugin.get_generator()
    config = {'object': ['grape'], 'container': ['cup'], 'distractor_count': [0], 'post_inversion_moves': [0]}
    prompt_config = {'user_style': 'casual', 'system_style': 'none', 'language': 'en', 'name': 'test'}
    test_cases = generator.generate_batch(config=config, prompt_config=prompt_config, count=2, seed=42)
    assert len(test_cases) == 2
    print(f"✓ Plugin system works end-to-end: generated {len(test_cases)} test cases")
    
    # Test parser through plugin
    parser = plugin.get_parser()
    task_params = {'object': 'grape', 'initial_location': 'counter'}
    parsed = parser.parse("counter", task_params)
    assert parsed.value == "counter"
    print("✓ Plugin parser works through plugin system")
    
    # Test evaluator through plugin
    evaluator = plugin.get_evaluator()
    from src.plugins.base import ParsedAnswer
    parsed_ans = ParsedAnswer(value="counter", raw_response="counter", parse_strategy='single_word')
    result = evaluator.evaluate(parsed_ans, "counter", task_params)
    assert result.correct == True
    print("✓ Plugin evaluator works through plugin system")

if __name__ == '__main__':
    print("=" * 60)
    print("Object Tracking Plugin Integration Test")
    print("=" * 60)
    print()
    
    try:
        test_plugin_registration()
        print()
        
        test_generator()
        print()
        
        test_parser()
        print()
        
        test_evaluator()
        print()
        
        test_tui_integration()
        print()
        
        test_analyze_results_integration()
        print()
        
        test_end_to_end_plugin_system()
        print()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nObject Tracking plugin is fully integrated and working.")
        print("\nNext steps:")
        print("  1. Run TUI: python -m src.cli.benchmark_tui")
        print("  2. Select 'Tracking (Grape Test)' as a task type")
        print("  3. Generate test set and run benchmarks")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
