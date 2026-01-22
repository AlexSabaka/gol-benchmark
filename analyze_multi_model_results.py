#!/usr/bin/env python3
"""
Multi-Model Results Aggregation and Analysis
Processes benchmark results from multiple models and generates structured dataset
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
import re
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class TestResult:
    """Single test result"""
    model: str
    model_short: str  # Simplified name for display
    user_style: str
    system_style: str
    config: str  # Combined user_system
    accuracy: float
    normalized_accuracy: float
    valid_tests: str  # e.g., "20/20"
    parse_errors: int
    success_rate: float
    perfect_scores: int
    
def extract_model_short_name(model_name: str) -> str:
    """Extract short display name from full model identifier"""
    # Handle HuggingFace models
    if model_name.startswith("hf.co/"):
        parts = model_name.split("/")[-1].split(":")
        return parts[0]
    
    # Handle regular models
    if ":" in model_name:
        return model_name.split(":")[0]
    
    # Handle long uncensored names
    if "uncensored" in model_name.lower():
        match = re.search(r"llama[\d.]+_(\d+)b", model_name, re.I)
        if match:
            return f"llama3.2:{match.group(1)}b-uncensored"
    
    return model_name

def parse_result_file(filepath: Path) -> TestResult:
    """Parse a single result file and extract key metrics"""
    
    # Extract model and config from filename
    # Format: {model}_{user_style}_{system_style}.json
    filename = filepath.stem
    parts = filename.split("_")
    
    # Reconstruct model name and config
    if "AceMath" in filename:
        model_full = "hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q4_K_M"
        user_style = parts[-2]
        system_style = parts[-1]
    elif "llama3" in filename and "uncensored" in filename:
        model_full = "llama3.2_3b_122824_uncensored.Q8_0-1739364637622:latest"
        # Find where config starts
        for i, part in enumerate(parts):
            if part in ["minimal", "casual", "linguistic"]:
                user_style = part
                system_style = parts[i+1]
                break
    else:
        # Standard format: model_version_user_system
        # gemma3_4b_minimal_analytical
        model_name = parts[0]
        model_version = parts[1]
        model_full = f"{model_name}:{model_version}"
        user_style = parts[2]
        system_style = parts[3]
    
    # Read file content
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract metrics using regex
    accuracy_match = re.search(r"Avg Accuracy.*?:\s+([\d.]+)%", content)
    norm_acc_match = re.search(r"Norm(?:alized)? Accuracy.*?:\s+([\d.]+)%", content)
    valid_match = re.search(r"Valid Tests.*?:\s+(\d+/\d+)", content)
    parse_errors_match = re.search(r"Parse Errors.*?:\s+(\d+)", content)
    success_match = re.search(r"Success Rate.*?:\s+([\d.]+)%", content)
    perfect_match = re.search(r"Perfect Scores.*?:\s+(\d+)", content)
    
    return TestResult(
        model=model_full,
        model_short=extract_model_short_name(model_full),
        user_style=user_style,
        system_style=system_style,
        config=f"{user_style}+{system_style}",
        accuracy=float(accuracy_match.group(1)) if accuracy_match else 0.0,
        normalized_accuracy=float(norm_acc_match.group(1)) if norm_acc_match else 0.0,
        valid_tests=valid_match.group(1) if valid_match else "0/0",
        parse_errors=int(parse_errors_match.group(1)) if parse_errors_match else 0,
        success_rate=float(success_match.group(1)) if success_match else 0.0,
        perfect_scores=int(perfect_match.group(1)) if perfect_match else 0,
    )

def aggregate_results(results_dir: Path) -> List[TestResult]:
    """Aggregate all result files from directory"""
    results = []
    
    # Find all JSON result files
    json_files = list(results_dir.glob("*.json"))
    
    print(f"Found {len(json_files)} result files")
    
    for filepath in sorted(json_files):
        try:
            result = parse_result_file(filepath)
            results.append(result)
            print(f"✓ Parsed: {result.model_short} - {result.config}: {result.accuracy}%")
        except Exception as e:
            print(f"✗ Error parsing {filepath.name}: {e}")
    
    return results

def generate_summary_stats(results: List[TestResult]) -> Dict:
    """Generate summary statistics per model"""
    stats_by_model = defaultdict(lambda: {
        'accuracies': [],
        'best_config': None,
        'best_accuracy': 0.0,
        'worst_config': None,
        'worst_accuracy': 100.0,
        'avg_accuracy': 0.0,
        'parse_errors_total': 0,
        'perfect_scores_total': 0,
    })
    
    for result in results:
        model = result.model_short
        stats = stats_by_model[model]
        
        stats['accuracies'].append(result.accuracy)
        stats['parse_errors_total'] += result.parse_errors
        stats['perfect_scores_total'] += result.perfect_scores
        
        if result.accuracy > stats['best_accuracy']:
            stats['best_accuracy'] = result.accuracy
            stats['best_config'] = result.config
        
        if result.accuracy < stats['worst_accuracy']:
            stats['worst_accuracy'] = result.accuracy
            stats['worst_config'] = result.config
    
    # Calculate averages
    for model, stats in stats_by_model.items():
        if stats['accuracies']:
            stats['avg_accuracy'] = sum(stats['accuracies']) / len(stats['accuracies'])
            stats['std_dev'] = (sum((x - stats['avg_accuracy']) ** 2 for x in stats['accuracies']) / len(stats['accuracies'])) ** 0.5
            stats['range'] = stats['best_accuracy'] - stats['worst_accuracy']
    
    return dict(stats_by_model)

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_multi_model_results.py <results_directory>")
        sys.exit(1)
    
    results_dir = Path(sys.argv[1])
    if not results_dir.exists():
        print(f"Error: Directory not found: {results_dir}")
        sys.exit(1)
    
    print("=" * 80)
    print("MULTI-MODEL RESULTS AGGREGATION")
    print("=" * 80)
    print()
    
    # Aggregate results
    results = aggregate_results(results_dir)
    
    if not results:
        print("No results found!")
        sys.exit(1)
    
    print()
    print(f"Total results collected: {len(results)}")
    print()
    
    # Generate summary statistics
    summary_stats = generate_summary_stats(results)
    
    print("=" * 80)
    print("SUMMARY STATISTICS BY MODEL")
    print("=" * 80)
    print()
    
    for model in sorted(summary_stats.keys()):
        stats = summary_stats[model]
        print(f"📊 {model}")
        print(f"   Average Accuracy: {stats['avg_accuracy']:.2f}% (±{stats['std_dev']:.2f}σ)")
        print(f"   Range: {stats['worst_accuracy']:.2f}% - {stats['best_accuracy']:.2f}% (span: {stats['range']:.2f} points)")
        print(f"   Best Config: {stats['best_config']} ({stats['best_accuracy']:.2f}%)")
        print(f"   Worst Config: {stats['worst_config']} ({stats['worst_accuracy']:.2f}%)")
        print(f"   Parse Errors: {stats['parse_errors_total']}")
        print(f"   Perfect Scores: {stats['perfect_scores_total']}")
        print()
    
    # Save aggregated data
    output_file = results_dir / "aggregated_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            'results': [asdict(r) for r in results],
            'summary_stats': summary_stats,
        }, f, indent=2)
    
    print(f"✓ Saved aggregated results to: {output_file}")
    
    # Save CSV for easy viewing
    csv_file = results_dir / "aggregated_results.csv"
    with open(csv_file, 'w') as f:
        f.write("model,user_style,system_style,config,accuracy,valid_tests,parse_errors,success_rate,perfect_scores\n")
        for r in results:
            f.write(f"{r.model_short},{r.user_style},{r.system_style},{r.config},{r.accuracy},{r.valid_tests},{r.parse_errors},{r.success_rate},{r.perfect_scores}\n")
    
    print(f"✓ Saved CSV to: {csv_file}")
    print()
    print("=" * 80)
    print("Analysis complete! Ready for visualization generation.")
    print("=" * 80)

if __name__ == "__main__":
    main()
