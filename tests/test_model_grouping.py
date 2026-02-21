#!/usr/bin/env python3
"""Test model grouping functionality in analyze_results.py"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.stages.analyze_results import (
    group_results_by_model,
    aggregate_model_stats,
    extract_summary_stats
)


def create_mock_result(model_name, task_type, accuracy, total_tests=10, parse_error_rate=0.1):
    """Create a mock result dictionary for testing."""
    successful_tests = int(total_tests * (1 - parse_error_rate))
    correct = int(successful_tests * accuracy)
    
    # Create test results matching expected structure with proper task identifiers
    results = []
    for i in range(successful_tests):
        results.append({
            'test_case_id': f'{task_type}_{i}',
            'test_id': f'multi_0000_{task_type}',  # Format expected by extract_task_breakdown
            'evaluation': {
                'is_correct': i < correct,
                'correct': i < correct,  # Both fields for compatibility
                'match_type': 'exact' if i < correct else 'incorrect'
            }
        })
    
    # Add parse errors
    parse_error_count = total_tests - successful_tests
    for i in range(parse_error_count):
        results.append({
            'test_case_id': f'{task_type}_parse_{i}',
            'test_id': f'multi_0000_{task_type}',
            'evaluation': {
                'is_correct': False,
                'correct': False,
                'match_type': 'parse_error'
            }
        })
    
    return {
        'metadata': {
            'result_id': f'result_{model_name}_{task_type}',
            'created_at': '2026-01-25T12:00:00',
            'hostname': 'test-host'
        },
        'model_info': {
            'model_name': model_name,
            'provider': 'ollama',
            'quantization': None
        },
        'testset_metadata': {
            'task_type': task_type,
            'testset_name': f'test_{task_type}_{model_name}',
        },
        'execution_info': {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': 0,
            'duration_seconds': 50.0,
        },
        'summary_statistics': {
            'overall_accuracy': accuracy,
            'correct_responses': correct,
            'parse_error_rate': parse_error_rate,
        },
        'results': results
    }


def test_model_grouping():
    """Test that results are correctly grouped by model."""
    print("Test 1: Model Grouping")
    print("-" * 60)
    
    # Create mock results for 2 models with 2 tasks each
    results = [
        create_mock_result('qwen3:0.6b', 'arithmetic', 0.7, 20),
        create_mock_result('qwen3:0.6b', 'game_of_life', 0.5, 15),
        create_mock_result('gemma3:1b', 'arithmetic', 0.8, 20),
        create_mock_result('gemma3:1b', 'game_of_life', 0.6, 15),
    ]
    
    grouped = group_results_by_model(results)
    
    print(f"✓ Grouped {len(results)} results into {len(grouped)} models")
    assert len(grouped) == 2, f"Expected 2 models, got {len(grouped)}"
    assert 'qwen3:0.6b' in grouped, "Missing qwen3:0.6b"
    assert 'gemma3:1b' in grouped, "Missing gemma3:1b"
    assert len(grouped['qwen3:0.6b']) == 2, "Expected 2 results for qwen3:0.6b"
    assert len(grouped['gemma3:1b']) == 2, "Expected 2 results for gemma3:1b"
    
    print("✓ All models correctly grouped\n")
    return True


def test_aggregate_stats():
    """Test aggregation of statistics across multiple result files."""
    print("Test 2: Statistics Aggregation")
    print("-" * 60)
    
    # Create results with known values for easy verification
    results = [
        create_mock_result('qwen3:0.6b', 'arithmetic', 0.7, 20, 0.1),      # 18 successful, 12.6 correct
        create_mock_result('qwen3:0.6b', 'game_of_life', 0.5, 10, 0.2),    # 8 successful, 4 correct
    ]
    
    agg_stats = aggregate_model_stats(results)
    
    print(f"Model: {agg_stats['model_name']}")
    print(f"Result Count: {agg_stats['result_count']}")
    print(f"Total Tests: {agg_stats['total_tests']}")
    print(f"Successful Tests: {agg_stats['successful_tests']}")
    print(f"Overall Accuracy: {agg_stats['accuracy']:.1%}")
    print(f"Parse Error Rate: {agg_stats['parse_error_rate']:.1%}")
    
    assert agg_stats['result_count'] == 2, "Expected 2 result files"
    assert agg_stats['total_tests'] == 30, f"Expected 30 total tests, got {agg_stats['total_tests']}"
    assert agg_stats['successful_tests'] == 26, f"Expected 26 successful tests, got {agg_stats['successful_tests']}"
    
    # Check task breakdown
    assert 'arithmetic' in agg_stats['task_breakdown'], "Missing arithmetic task"
    assert 'game_of_life' in agg_stats['task_breakdown'], "Missing game_of_life task"
    
    arith_stats = agg_stats['task_breakdown']['arithmetic']
    gol_stats = agg_stats['task_breakdown']['game_of_life']
    
    print(f"\nTask Breakdown:")
    print(f"  Arithmetic: {arith_stats['accuracy']:.1%} ({arith_stats['correct']}/{arith_stats['total']})")
    print(f"  Game of Life: {gol_stats['accuracy']:.1%} ({gol_stats['correct']}/{gol_stats['total']})")
    
    assert arith_stats['total'] == 20, "Expected 20 arithmetic tests"
    assert gol_stats['total'] == 10, "Expected 10 game_of_life tests"
    
    print("\n✓ Statistics correctly aggregated\n")
    return True


def test_quantization_handling():
    """Test handling of quantization in model names."""
    print("Test 3: Quantization Handling")
    print("-" * 60)
    
    # Create results with quantization info (matching expected structure)
    result_with_quant = {
        'metadata': {
            'result_id': 'result_with_quant',
            'created_at': '2026-01-25T12:00:00',
            'hostname': 'test-host'
        },
        'model_info': {
            'model_name': 'gemma3:4b',
            'provider': 'ollama',
            'quantization': 'Q4_K_M'
        },
        'testset_metadata': {
            'task_type': 'arithmetic',
            'testset_name': 'test_arith',
        },
        'execution_info': {
            'total_tests': 10,
            'successful_tests': 9,
            'failed_tests': 0,
            'duration_seconds': 30.0,
        },
        'summary_statistics': {
            'overall_accuracy': 0.7,
            'correct_responses': 7,
        },
        'results': [
            {
                'test_case_id': f'arith_{i}',
                'test_id': f'multi_0000_arithmetic',
                'evaluation': {
                    'is_correct': i < 7,
                    'correct': i < 7,
                    'match_type': 'exact'
                }
            }
            for i in range(9)
        ]
    }
    
    result_without_quant = {
        'metadata': {
            'result_id': 'result_without_quant',
            'created_at': '2026-01-25T12:00:00',
            'hostname': 'test-host'
        },
        'model_info': {
            'model_name': 'gemma3:4b',
            'provider': 'ollama',
            'quantization': None
        },
        'testset_metadata': {
            'task_type': 'game_of_life',
            'testset_name': 'test_gol',
        },
        'execution_info': {
            'total_tests': 10,
            'successful_tests': 9,
            'failed_tests': 0,
            'duration_seconds': 30.0,
        },
        'summary_statistics': {
            'overall_accuracy': 0.5,
            'correct_responses': 5,
        },
        'results': [
            {
                'test_case_id': f'gol_{i}',
                'test_id': f'multi_0000_game_of_life',
                'evaluation': {
                    'is_correct': i < 5,
                    'correct': i < 5,
                    'match_type': 'exact'
                }
            }
            for i in range(9)
        ]
    }
    
    results = [result_with_quant, result_without_quant]
    grouped = group_results_by_model(results)
    
    print(f"Models found: {list(grouped.keys())}")
    
    # Should create separate groups for quantized vs non-quantized
    assert len(grouped) == 2, f"Expected 2 model groups (with/without quantization), got {len(grouped)}"
    
    has_quant = any('Q4_K_M' in key for key in grouped.keys())
    has_plain = any(key == 'gemma3:4b' for key in grouped.keys())
    
    assert has_quant, "Should have quantized model key"
    assert has_plain, "Should have plain model key"
    
    print("✓ Quantization correctly handled in grouping\n")
    return True


def test_multiple_tasks():
    """Test aggregation across multiple different task types."""
    print("Test 4: Multiple Task Types")
    print("-" * 60)
    
    # Create results with 3 different task types
    results = [
        create_mock_result('qwen3:0.6b', 'arithmetic', 0.7, 10),
        create_mock_result('qwen3:0.6b', 'game_of_life', 0.5, 10),
        create_mock_result('qwen3:0.6b', 'grid_tasks', 0.6, 10),
    ]
    
    agg_stats = aggregate_model_stats(results)
    
    print(f"Task types covered: {sorted(agg_stats['task_types'])}")
    assert len(agg_stats['task_types']) == 3, "Expected 3 unique task types"
    assert 'arithmetic' in agg_stats['task_types']
    assert 'game_of_life' in agg_stats['task_types']
    assert 'grid_tasks' in agg_stats['task_types']
    
    # Check task breakdown has all 3 tasks
    assert len(agg_stats['task_breakdown']) == 3, "Expected 3 tasks in breakdown"
    
    for task_type, task_stats in sorted(agg_stats['task_breakdown'].items()):
        print(f"  {task_type}: {task_stats['accuracy']:.1%} ({task_stats['total']} tests)")
    
    print("\n✓ Multiple task types correctly handled\n")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Model Grouping Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_model_grouping,
        test_aggregate_stats,
        test_quantization_handling,
        test_multiple_tasks,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}\n")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
