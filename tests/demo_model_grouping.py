#!/usr/bin/env python3
"""
Demo script showing model-grouped analysis feature.
Creates synthetic result files and demonstrates the grouping functionality.
"""

import sys
import json
import gzip
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_synthetic_result(model_name, task_type, accuracy, total_tests=20, quantization=None):
    """Create a synthetic result file for demonstration."""
    successful_tests = int(total_tests * 0.9)  # 90% successful (10% parse errors)
    correct = int(successful_tests * accuracy)
    
    # Create result structure
    results = []
    for i in range(successful_tests):
        results.append({
            'test_case_id': f'{task_type}_{i}',
            'test_id': f'multi_0000_{task_type}',
            'evaluation': {
                'is_correct': i < correct,
                'correct': i < correct,
                'match_type': 'exact' if i < correct else 'incorrect'
            }
        })
    
    # Add parse errors
    for i in range(total_tests - successful_tests):
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
            'result_id': f'demo_result_{model_name}_{task_type}',
            'created_at': datetime.now().isoformat(),
            'hostname': 'demo-machine',
            'schema_version': '2.0.0'
        },
        'model_info': {
            'model_name': model_name,
            'provider': 'ollama',
            'quantization': quantization,
            'temperature': 0.1,
            'max_tokens': 512
        },
        'testset_metadata': {
            'testset_name': f'demo_testset_{task_type}',
            'testset_id': f'demo_{task_type}',
            'task_type': task_type,
            'test_count': total_tests
        },
        'execution_info': {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': 0,
            'duration_seconds': total_tests * 0.5,
            'start_time': datetime.now().isoformat(),
            'end_time': datetime.now().isoformat()
        },
        'summary_statistics': {
            'overall_accuracy': accuracy,
            'correct_responses': correct,
            'parse_error_rate': (total_tests - successful_tests) / total_tests
        },
        'results': results
    }


def main():
    """Create demo result files and run grouped analysis."""
    print("=" * 70)
    print("Model-Grouped Analysis Demo")
    print("=" * 70)
    print()
    
    # Create demo results directory
    demo_dir = Path("demo_results")
    demo_dir.mkdir(exist_ok=True)
    
    print("Step 1: Creating synthetic result files...")
    print("-" * 70)
    
    # Define test scenarios
    scenarios = [
        # Model 1: qwen3:0.6b (3 tasks)
        ('qwen3:0.6b', 'arithmetic', 0.75, 25, None),
        ('qwen3:0.6b', 'game_of_life', 0.60, 20, None),
        ('qwen3:0.6b', 'grid_tasks', 0.68, 15, None),
        
        # Model 2: gemma3:1b (3 tasks)
        ('gemma3:1b', 'arithmetic', 0.82, 25, None),
        ('gemma3:1b', 'game_of_life', 0.70, 20, None),
        ('gemma3:1b', 'grid_tasks', 0.73, 15, None),
        
        # Model 3: gemma3:4b with quantization (2 tasks)
        ('gemma3:4b', 'arithmetic', 0.88, 25, 'Q4_K_M'),
        ('gemma3:4b', 'game_of_life', 0.78, 20, 'Q4_K_M'),
    ]
    
    result_files = []
    
    for model, task, accuracy, tests, quant in scenarios:
        result = create_synthetic_result(model, task, accuracy, tests, quant)
        
        # Generate filename
        quant_suffix = f"_{quant}" if quant else ""
        filename = f"results_{model.replace(':', '_')}{quant_suffix}_{task}.json.gz"
        filepath = demo_dir / filename
        
        # Save result file
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        
        result_files.append(str(filepath))
        
        print(f"✓ Created: {filename}")
        print(f"  Model: {model} {f'({quant})' if quant else ''}")
        print(f"  Task: {task}")
        print(f"  Tests: {tests}, Accuracy: {accuracy:.1%}")
        print()
    
    print()
    print("Step 2: Running analysis WITHOUT grouping (per-file)...")
    print("-" * 70)
    
    # Import after creating files
    from src.stages.analyze_results import analyze_results
    
    print("\n[Without --comparison flag]")
    analyze_results(result_files, comparison=False)
    
    print("\n")
    print("Step 3: Running analysis WITH model grouping...")
    print("-" * 70)
    
    print("\n[With --comparison flag]")
    output_md = demo_dir / "model_comparison.md"
    output_html = demo_dir / "model_comparison.html"
    
    analyze_results(
        result_files,
        output=str(output_md),
        comparison=True
    )
    
    print()
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print("Generated Files:")
    print(f"  📄 Markdown Report: {output_md}")
    print(f"  🌐 HTML Report: {output_html}")
    print()
    print("View the reports:")
    print(f"  cat {output_md}")
    print(f"  open {output_html}")
    print()
    print("Key Differences:")
    print("  - WITHOUT grouping: Shows 8 separate result summaries")
    print("  - WITH grouping: Shows 3 model summaries with task breakdowns")
    print()
    print("Cleanup:")
    print(f"  rm -rf {demo_dir}")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
