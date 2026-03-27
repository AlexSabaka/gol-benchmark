#!/usr/bin/env python3
"""
Analyze test results and generate reports.

This script implements Stage 3 of the 3-stage benchmark architecture:
Results JSON.gz → Analysis → Reports & Visualizations

Usage:
    # Single model analysis
    python scripts/analyze_results.py results/results_qwen3_*.json.gz

    # Multi-model comparison
    python scripts/analyze_results.py results/results_*.json.gz \\
        --comparison \\
        --output reports/comparison_2026-01-22.md

    # Generate visualizations
    python scripts/analyze_results.py results/*.json.gz \\
        --visualize \\
        --output-dir reports/charts/
"""

import json
import gzip
import sys
import os
import html as html_mod
import random as _random
import re as _re
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
import glob

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available. Some analysis features may be limited.")

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    VISUALIZATION_AVAILABLE = True
    
    # Set style
    plt.style.use('default')
    sns.set_palette("husl")
    
except ImportError:
    VISUALIZATION_AVAILABLE = False
    print("Warning: matplotlib/seaborn not available. Visualization features disabled.")

# ================================================================================
# VISUALIZATION COLOR PALETTES (acemath_quantization style)
# ================================================================================

# Quantization level colors (6 variants: full precision down to Q2_K)
QUANTIZATION_COLORS = {
    'FP16': '#2ecc71',      # Green - best quality
    'Q8_0': '#3498db',      # Blue
    'Q6_K': '#9b59b6',      # Purple
    'Q5_K_M': '#f39c12',    # Orange
    'Q4_K_M': '#e67e22',    # Dark orange
    'Q2_K': '#e74c3c',      # Red - lowest quality
}

# Task type colors (8 task types)
TASK_COLORS = {
    'arithmetic': '#3498db',           # Blue
    'game_of_life': '#2ecc71',         # Green
    'linda_fallacy': '#9b59b6',        # Purple
    'ascii_shapes': '#f39c12',         # Orange
    'cellular_automata_1d': '#1abc9c', # Teal
    'object_tracking': '#e74c3c',      # Red
    'sally_anne': '#34495e',           # Dark gray
    'carwash': '#e67e22',              # Amber
    'inverted_cup': '#16a085',         # Dark teal
    'grid_tasks': '#8e44ad',           # Dark purple
    'strawberry': '#e74c3c',           # Red (like a strawberry)
    'measure_comparison': '#2980b9',   # Blue (measurement)
    'misquote': '#c0392b',             # Dark red (misattribution)
    'family_relations': '#d35400',     # Burnt orange (family tree)
    'encoding_cipher': '#27ae60',      # Green (encoding)
    'multi-task': '#95a5a6',           # Light gray
}

# Prompt style colors (5 styles)
PROMPT_COLORS = {
    'minimal': '#3498db',      # Blue
    'casual': '#2ecc71',       # Green
    'linguistic': '#9b59b6',   # Purple
    'analytical': '#f39c12',   # Orange
    'adversarial': '#e74c3c',  # Red
}

# Semantic colors for performance thresholds
SUCCESS_GREEN = '#2ecc71'   # Accuracy >= 70%
WARNING_ORANGE = '#f39c12'  # Accuracy 50-70%
ERROR_RED = '#e74c3c'       # Accuracy < 50%
INFO_BLUE = '#3498db'       # Neutral/informational


def load_result_file(filepath: str) -> Dict:
    """Load result JSON.gz file."""
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        return json.load(f)


def extract_summary_stats(result: Dict) -> Dict:
    """Extract key statistics from a result file with enhanced multi-task support."""
    
    metadata = result.get('metadata', {})
    model_info = result.get('model_info', {})
    execution_info = result.get('execution_info', {})
    summary_stats = result.get('summary_statistics', {})
    testset_metadata = result.get('testset_metadata', {})
    
    # Count result types
    results = result.get('results', [])
    total_tests = len(results)
    successful = execution_info.get('successful_tests', 0)
    failed = execution_info.get('failed_tests', 0)
    
    # Token statistics
    total_input_tokens = summary_stats.get('total_input_tokens', 0)
    total_output_tokens = summary_stats.get('total_output_tokens', 0)
    avg_input_tokens = summary_stats.get('avg_input_tokens_per_test', 0)
    avg_output_tokens = summary_stats.get('avg_output_tokens_per_test', 0)
    
    # If not in summary_stats, calculate from individual results
    if total_input_tokens == 0 and results:
        total_input_tokens = sum(r.get('tokens', {}).get('input_tokens', 0) for r in results)
        total_output_tokens = sum(r.get('tokens', {}).get('output_tokens', 0) for r in results)
        if successful > 0:
            avg_input_tokens = total_input_tokens / successful
            avg_output_tokens = total_output_tokens / successful
    
    # Enhanced multi-task analysis
    task_breakdown = extract_task_breakdown(results)
    prompt_breakdown = extract_prompt_breakdown(results)
    
    # Error analysis
    parse_errors = sum(1 for r in results 
                      if r.get('evaluation', {}).get('match_type') == 'parse_error')
    type_errors = sum(1 for r in results 
                     if r.get('evaluation', {}).get('match_type') == 'type_error')
    
    return {
        'result_id': metadata.get('result_id'),
        'model_name': model_info.get('model_name'),
        'provider': model_info.get('provider'),
        'quantization': model_info.get('quantization'),
        'testset_name': testset_metadata.get('testset_name'),
        'task_type': testset_metadata.get('task_type'),
        'created_at': metadata.get('created_at'),
        'hostname': metadata.get('hostname'),
        
        'total_tests': total_tests,
        'successful_tests': successful,
        'failed_tests': failed,
        'success_rate': successful / total_tests if total_tests > 0 else 0,
        
        'accuracy': summary_stats.get('accuracy', 0),
        'correct_responses': summary_stats.get('correct_responses', 0),
        'parse_errors': parse_errors,
        'parse_error_rate': parse_errors / successful if successful > 0 else 0,
        'type_errors': type_errors,
        
        'duration_seconds': execution_info.get('duration_seconds', 0),
        'avg_time_per_test': execution_info.get('average_time_per_test', 0),
        
        # Token statistics
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'total_tokens': total_input_tokens + total_output_tokens,
        'avg_input_tokens_per_test': avg_input_tokens,
        'avg_output_tokens_per_test': avg_output_tokens,
        'avg_tokens_per_test': avg_input_tokens + avg_output_tokens,
        
        # Prompt configuration metadata (for visualization)
        'user_prompt_style': result.get('test_config', {}).get('user_prompt_style') or \
                            result.get('test_config', {}).get('prompt_style'),
        'system_prompt_style': result.get('test_config', {}).get('system_prompt_style'),
        
        # Task-specific stats
        'avg_cell_accuracy': summary_stats.get('average_cell_accuracy'),  # For GoL
        
        # Multi-task enhanced metadata
        'task_breakdown': task_breakdown,
        'prompt_breakdown': prompt_breakdown,
        'is_multi_task': testset_metadata.get('task_type') == 'multi-task',
    }


def extract_task_breakdown(results: List[Dict]) -> Dict:
    """Extract task-specific performance breakdown from results."""
    task_stats = defaultdict(lambda: {
        'total': 0, 
        'correct': 0, 
        'parse_errors': 0,
        # Linda-specific metrics
        'fallacies_detected': 0,
        'confidence_scores': [],
        'ranking_qualities': [],
        'cultural_breakdown': defaultdict(int)
    })
    
    for r in results:
        # Extract task type from test_id (e.g., 'multi_0000_arithmetic' -> 'arithmetic')
        test_id = r.get('test_id', '')
        task_type = 'unknown'
        if '_arithmetic' in test_id:
            task_type = 'arithmetic'
        elif '_game_of_life' in test_id or '_gol' in test_id:
            task_type = 'game_of_life'
        elif '_linda' in test_id:
            task_type = 'linda_fallacy'
        elif '_ascii_shapes' in test_id:
            task_type = 'ascii_shapes'
        elif '_cellular_automata_1d' in test_id or '_c14' in test_id:
            task_type = 'cellular_automata_1d'
        elif '_object_tracking' in test_id or '_tracking' in test_id:
            task_type = 'object_tracking'
        elif '_sally_anne' in test_id or '_false_belief' in test_id:
            task_type = 'sally_anne'
        elif '_carwash' in test_id or test_id.startswith('carwash_'):
            task_type = 'carwash'
        elif '_inverted_cup' in test_id or test_id.startswith('inverted_cup_'):
            task_type = 'inverted_cup'
        elif '_strawberry' in test_id or test_id.startswith('strawberry_'):
            task_type = 'strawberry'
        elif '_measure_comparison' in test_id or test_id.startswith('measure_comparison_'):
            task_type = 'measure_comparison'
        elif '_grid_tasks' in test_id or test_id.startswith('grid_tasks_'):
            task_type = 'grid_tasks'
        elif '_time_arithmetic' in test_id or test_id.startswith('time_arithmetic_'):
            task_type = 'time_arithmetic'
        elif '_misquote' in test_id or test_id.startswith('misquote_'):
            task_type = 'misquote'
        elif '_false_premise' in test_id or test_id.startswith('false_premise_'):
            task_type = 'false_premise'
        elif '_family_relations' in test_id or test_id.startswith('family_relations_'):
            task_type = 'family_relations'
        elif '_encoding_cipher' in test_id or test_id.startswith('encoding_cipher_'):
            task_type = 'encoding_cipher'
        elif '_symbol_arithmetic' in test_id or test_id.startswith('symbol_arithmetic_'):
            task_type = 'symbol_arithmetic'
        
        task_stats[task_type]['total'] += 1
        
        evaluation = r.get('evaluation', {})
        
        if evaluation.get('correct'):
            task_stats[task_type]['correct'] += 1
        
        if evaluation.get('match_type') == 'parse_error':
            task_stats[task_type]['parse_errors'] += 1
            
        # Linda-specific metrics
        if task_type == 'linda_fallacy':
            if evaluation.get('fallacy_detected'):
                task_stats[task_type]['fallacies_detected'] += 1
            
            # Collect confidence scores
            confidence = evaluation.get('confidence_score', 0)
            if confidence > 0:
                task_stats[task_type]['confidence_scores'].append(confidence)
            
            # Collect ranking quality scores
            ranking_quality = evaluation.get('ranking_quality', 0)
            if ranking_quality > 0:
                task_stats[task_type]['ranking_qualities'].append(ranking_quality)
            
            # Track cultural breakdown
            culture = r.get('input', {}).get('task_params', {}).get('persona', {}).get('culture', 'unknown')
            task_stats[task_type]['cultural_breakdown'][culture] += 1
    
    # Calculate percentages and averages
    for task, stats in task_stats.items():
        total = stats['total']
        if total > 0:
            stats['accuracy'] = stats['correct'] / total
            stats['parse_error_rate'] = stats['parse_errors'] / total
            
            # Linda-specific calculations
            if task == 'linda_fallacy':
                stats['fallacy_detection_rate'] = stats['fallacies_detected'] / total
                stats['avg_confidence'] = sum(stats['confidence_scores']) / len(stats['confidence_scores']) if stats['confidence_scores'] else 0
                stats['avg_ranking_quality'] = sum(stats['ranking_qualities']) / len(stats['ranking_qualities']) if stats['ranking_qualities'] else 0
        else:
            stats['accuracy'] = 0
            stats['parse_error_rate'] = 0
            if task == 'linda_fallacy':
                stats['fallacy_detection_rate'] = 0
                stats['avg_confidence'] = 0
                stats['avg_ranking_quality'] = 0
    
    return dict(task_stats)


def extract_prompt_breakdown(results: List[Dict]) -> Dict:
    """Extract prompt-style specific performance breakdown from results."""
    # This would require prompt style metadata to be stored in results
    # For now, return empty dict until test generation includes this metadata
    return {}


def group_results_by_model(results: List[Dict]) -> Dict[str, List[Dict]]:
    """Group result files by model name for aggregated analysis."""
    grouped = defaultdict(list)
    
    for result in results:
        model_info = result.get('model_info', {})
        model_name = model_info.get('model_name', 'unknown')
        
        # Create a unique key with quantization if present
        quantization = model_info.get('quantization')
        if quantization:
            model_key = f"{model_name} ({quantization})"
        else:
            model_key = model_name
        
        grouped[model_key].append(result)
    
    return dict(grouped)


def aggregate_model_stats(model_results: List[Dict]) -> Dict:
    """Aggregate statistics across multiple result files for the same model."""
    if not model_results:
        return {}
    
    # Extract individual stats
    all_stats = [extract_summary_stats(r) for r in model_results]
    
    # Use first result for model metadata
    first_stat = all_stats[0]
    
    # Aggregate metrics
    total_tests = sum(s['total_tests'] for s in all_stats)
    successful_tests = sum(s['successful_tests'] for s in all_stats)
    correct_responses = sum(s['correct_responses'] for s in all_stats)
    parse_errors = sum(s['parse_errors'] for s in all_stats)
    total_duration = sum(s['duration_seconds'] for s in all_stats)
    
    # Token statistics
    total_input_tokens = sum(s.get('total_input_tokens', 0) for s in all_stats)
    total_output_tokens = sum(s.get('total_output_tokens', 0) for s in all_stats)
    
    # Calculate aggregated rates
    accuracy = correct_responses / successful_tests if successful_tests > 0 else 0
    parse_error_rate = parse_errors / successful_tests if successful_tests > 0 else 0
    success_rate = successful_tests / total_tests if total_tests > 0 else 0
    
    # Aggregate task breakdowns
    combined_task_breakdown = defaultdict(lambda: {
        'total': 0, 'correct': 0, 'parse_errors': 0
    })
    
    for stat in all_stats:
        for task_type, task_stats in stat.get('task_breakdown', {}).items():
            combined_task_breakdown[task_type]['total'] += task_stats['total']
            combined_task_breakdown[task_type]['correct'] += task_stats['correct']
            combined_task_breakdown[task_type]['parse_errors'] += task_stats['parse_errors']
    
    # Calculate task-level percentages
    for task_type, stats in combined_task_breakdown.items():
        if stats['total'] > 0:
            stats['accuracy'] = stats['correct'] / stats['total']
            stats['parse_error_rate'] = stats['parse_errors'] / stats['total']
        else:
            stats['accuracy'] = 0
            stats['parse_error_rate'] = 0
    
    # Collect all unique task types encountered
    task_types = set()
    for stat in all_stats:
        task_types.add(stat.get('task_type', 'unknown'))
    
    return {
        'model_name': first_stat['model_name'],
        'provider': first_stat['provider'],
        'quantization': first_stat['quantization'],
        'result_count': len(model_results),
        'task_types': list(task_types),
        
        'total_tests': total_tests,
        'successful_tests': successful_tests,
        'correct_responses': correct_responses,
        'accuracy': accuracy,
        'parse_errors': parse_errors,
        'parse_error_rate': parse_error_rate,
        'success_rate': success_rate,
        
        'total_duration_seconds': total_duration,
        'avg_time_per_test': total_duration / successful_tests if successful_tests > 0 else 0,
        
        # Token statistics
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'total_tokens': total_input_tokens + total_output_tokens,
        'avg_input_tokens_per_test': total_input_tokens / successful_tests if successful_tests > 0 else 0,
        'avg_output_tokens_per_test': total_output_tokens / successful_tests if successful_tests > 0 else 0,
        
        'task_breakdown': dict(combined_task_breakdown),
        'individual_results': all_stats,
    }


def generate_markdown_report(results: List[Dict], output_path: str, grouped_by_model: bool = False):
    """Generate comprehensive markdown report with enhanced multi-task analysis."""
    
    # Generate timestamp for consistent use
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    report = []
    report.append("# Benchmark Analysis Report\n")
    report.append(f"Generated: {timestamp}\n\n")
    
    # Check if we should group by model
    if grouped_by_model and len(results) > 1:
        # Group results by model
        grouped_results = group_results_by_model(results)
        
        report.append(f"## Overview\n\n")
        report.append(f"Analyzed **{len(results)}** result files across **{len(grouped_results)}** model(s)\n\n")
        
        # Model comparison summary table
        report.append("## Model Comparison Summary\n\n")
        report.append("| Model | Result Files | Total Tests | Accuracy | Parse Error Rate | Avg Time/Test | Avg Tokens/Test | Tasks Covered |\n")
        report.append("|-------|--------------|-------------|----------|------------------|---------------|-----------------|---------------|\n")
        
        model_aggregates = {}
        for model_name, model_results in sorted(grouped_results.items()):
            agg_stats = aggregate_model_stats(model_results)
            model_aggregates[model_name] = agg_stats
            
            tasks_str = ", ".join(sorted(agg_stats['task_types']))[:50]
            if len(", ".join(sorted(agg_stats['task_types']))) > 50:
                tasks_str += "..."
            
            # Format token count with "K" for thousands
            avg_tokens = agg_stats.get('avg_input_tokens_per_test', 0) + agg_stats.get('avg_output_tokens_per_test', 0)
            if avg_tokens >= 1000:
                tokens_str = f"{avg_tokens/1000:.1f}K"
            else:
                tokens_str = f"{avg_tokens:.0f}"
            
            report.append(
                f"| **{model_name}** | {agg_stats['result_count']} | "
                f"{agg_stats['total_tests']} | "
                f"{agg_stats['accuracy']:.1%} | "
                f"{agg_stats['parse_error_rate']:.1%} | "
                f"{agg_stats['avg_time_per_test']:.2f}s | "
                f"{tokens_str} | "
                f"{tasks_str} |\n"
            )
        
        report.append("\n")
        
        # Detailed per-model analysis
        for model_name, model_results in sorted(grouped_results.items()):
            agg_stats = model_aggregates[model_name]
            report.append(f"## {model_name}\n\n")
            
            report.append(f"**Aggregated from {agg_stats['result_count']} result file(s)**\n\n")
            
            # Overall metrics
            report.append("### Overall Performance\n\n")
            report.append(f"- **Total Tests**: {agg_stats['total_tests']}\n")
            report.append(f"- **Successful Tests**: {agg_stats['successful_tests']}\n")
            report.append(f"- **Overall Accuracy**: {agg_stats['accuracy']:.2%} ({agg_stats['correct_responses']}/{agg_stats['successful_tests']})\n")
            report.append(f"- **Parse Error Rate**: {agg_stats['parse_error_rate']:.2%}\n")
            report.append(f"- **Success Rate**: {agg_stats['success_rate']:.2%}\n")
            report.append(f"- **Average Time per Test**: {agg_stats['avg_time_per_test']:.2f} seconds\n")
            report.append(f"- **Total Execution Time**: {agg_stats['total_duration_seconds']:.1f} seconds\n")
            report.append("\n")
            
            # Task breakdown
            if agg_stats['task_breakdown']:
                report.append("### Performance by Task Type\n\n")
                report.append("| Task Type | Tests | Correct | Accuracy | Parse Errors |\n")
                report.append("|-----------|-------|---------|----------|--------------|\n")
                
                for task_type in sorted(agg_stats['task_breakdown'].keys()):
                    task_stats = agg_stats['task_breakdown'][task_type]
                    report.append(
                        f"| {task_type.replace('_', ' ').title()} | "
                        f"{task_stats['total']} | "
                        f"{task_stats['correct']} | "
                        f"{task_stats['accuracy']:.1%} | "
                        f"{task_stats['parse_error_rate']:.1%} |\n"
                    )
                
                report.append("\n")
            
            # Individual result file details
            report.append("### Individual Result Files\n\n")
            for result_stat in agg_stats['individual_results']:
                report.append(f"#### {result_stat['testset_name']}\n\n")
                report.append(f"- **Task Type**: {result_stat['task_type']}\n")
                report.append(f"- **Tests**: {result_stat['total_tests']}\n")
                report.append(f"- **Accuracy**: {result_stat['accuracy']:.2%}\n")
                report.append(f"- **Execution**: {result_stat['created_at'][:19]}\n")
                report.append("\n")
        
        # Write grouped report
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.writelines(report)
        
        print(f"✓ Model-grouped markdown report saved: {output_path}")
        return
    
    # Fall back to original ungrouped report
    # Extract stats from all results
    stats = [extract_summary_stats(r) for r in results]
    
    # Enhanced summary with multi-task breakdown
    report.append("## Summary\n\n")
    
    # Check if we have multi-task results
    multi_task_results = [s for s in stats if s.get('is_multi_task', False)]
    if multi_task_results:
        report.append("### Multi-Task Performance Overview\n\n")
        for stat in stats:
            if stat['task_breakdown']:
                report.append(f"**{stat['model_name']}** Task Breakdown:\n\n")
                for task_type, task_stats in stat['task_breakdown'].items():
                    base_info = (f"- **{task_type.replace('_', ' ').title()}**: "
                                f"{task_stats['accuracy']:.1%} accuracy "
                                f"({task_stats['correct']}/{task_stats['total']} correct), "
                                f"{task_stats['parse_error_rate']:.1%} parse errors")
                    
                    # Add Linda-specific metrics
                    if task_type == 'linda_fallacy':
                        linda_info = (f", {task_stats.get('fallacy_detection_rate', 0):.1%} fallacy detection, "
                                     f"avg confidence: {task_stats.get('avg_confidence', 0):.2f}, "
                                     f"avg ranking quality: {task_stats.get('avg_ranking_quality', 0):.2f}")
                        base_info += linda_info
                    
                    report.append(base_info + "\n")
                report.append("\n")
    
    # Standard summary table
    report.append("| Model | Provider | Task | Tests | Accuracy | Parse Errors | Avg Time | Avg Tokens | Duration |\n")
    report.append("|-------|----------|------|-------|----------|--------------|----------|------------|----------|\n")
    
    for stat in stats:
        model_display = f"{stat['model_name']}"
        if stat['quantization']:
            model_display += f" ({stat['quantization']})"
        
        # Format token count
        avg_tokens = stat.get('avg_input_tokens_per_test', 0) + stat.get('avg_output_tokens_per_test', 0)
        if avg_tokens >= 1000:
            tokens_str = f"{avg_tokens/1000:.1f}K"
        else:
            tokens_str = f"{avg_tokens:.0f}"
            
        report.append(
            f"| {model_display} | {stat['provider']} | {stat['task_type']} | "
            f"{stat['successful_tests']}/{stat['total_tests']} | "
            f"{stat['accuracy']:.1%} | {stat['parse_error_rate']:.1%} | "
            f"{stat['avg_time_per_test']:.1f}s | {tokens_str} | {stat['duration_seconds']:.0f}s |\n"
        )
    
    report.append("\n")
    
    # Detailed analysis per model/task
    for i, (result, stat) in enumerate(zip(results, stats)):
        report.append(f"## {stat['model_name']} - {stat['task_type']}\n\n")
        
        report.append(f"- **Testset**: {stat['testset_name']}\n")
        report.append(f"- **Provider**: {stat['provider']}\n")
        if stat['quantization']:
            report.append(f"- **Quantization**: {stat['quantization']}\n")
        report.append(f"- **Execution**: {stat['created_at'][:19]} on {stat['hostname']}\n")
        report.append("\n")
        
        # Performance metrics
        report.append("### Performance\n\n")
        report.append(f"- **Accuracy**: {stat['accuracy']:.2%} ({stat['correct_responses']}/{stat['successful_tests']})\n")
        report.append(f"- **Parse Error Rate**: {stat['parse_error_rate']:.2%} ({stat['parse_errors']}/{stat['successful_tests']})\n")
        report.append(f"- **Success Rate**: {stat['success_rate']:.2%} ({stat['successful_tests']}/{stat['total_tests']})\n")
        
        if stat['avg_cell_accuracy'] is not None:
            report.append(f"- **Cell-level Accuracy**: {stat['avg_cell_accuracy']:.2%}\n")
        
        report.append(f"- **Average Time per Test**: {stat['avg_time_per_test']:.2f} seconds\n")
        report.append(f"- **Total Duration**: {stat['duration_seconds']:.1f} seconds\n")
        
        # Token statistics
        if stat.get('total_input_tokens', 0) > 0:
            report.append(f"\n**Token Usage:**\n")
            report.append(f"- **Total Input Tokens**: {stat['total_input_tokens']:,}\n")
            report.append(f"- **Total Output Tokens**: {stat['total_output_tokens']:,}\n")
            report.append(f"- **Total Tokens**: {stat['total_tokens']:,}\n")
            report.append(f"- **Avg Input per Test**: {stat['avg_input_tokens_per_test']:.0f}\n")
            report.append(f"- **Avg Output per Test**: {stat['avg_output_tokens_per_test']:.0f}\n")
        
        report.append("\n")
        
        # Task breakdown for multi-task results
        if stat.get('is_multi_task', False) and stat['task_breakdown']:
            report.append("### Task-Specific Performance\n\n")
            report.append("| Task Type | Tests | Accuracy | Parse Errors |\n")
            report.append("|-----------|-------|----------|--------------|\n")
            for task_type, task_stats in stat['task_breakdown'].items():
                report.append(f"| {task_type.replace('_', ' ').title()} | "
                             f"{task_stats['total']} | "
                             f"{task_stats['accuracy']:.1%} | "
                             f"{task_stats['parse_error_rate']:.1%} |\n")
            report.append("\n")
        
        # Error analysis
        if stat['parse_errors'] > 0 or stat['type_errors'] > 0:
            report.append("### Error Analysis\n\n")
            
            error_types = defaultdict(int)
            for r in result['results']:
                error_type = r.get('evaluation', {}).get('match_type')
                if error_type and error_type not in ['exact', 'perfect']:
                    error_types[error_type] += 1
            
            for error_type, count in error_types.items():
                rate = count / max(stat['successful_tests'], 1) * 100
                report.append(f"- **{error_type.replace('_', ' ').title()}**: {count} ({rate:.1f}%)\n")
            
            # Add specific handling for 100% parse errors
            if stat['parse_error_rate'] >= 1.0:
                report.append("\n**Critical Issue**: All responses failed to parse. This typically indicates:\n")
                report.append("- Model output format doesn't match expected pattern\n")
                report.append("- Prompt engineering may need adjustment\n")
                report.append("- Model may require different parsing approach\n")
            
            report.append("\n")
        
        # Sample responses (first few)
        sample_results = result['results'][:3]
        if sample_results:
            report.append("### Sample Results\n\n")
            for j, sample in enumerate(sample_results):
                report.append(f"**Test {j+1}** (`{sample['test_id']}`):\n")
                report.append(f"- Input: `{sample['input']['user_prompt'][:100]}...`\n")
                if sample['status'] == 'success':
                    report.append(f"- Expected: `{sample['input']['task_params'].get('expected_answer', 'N/A')}`\n")
                    report.append(f"- Parsed: `{sample['output']['parsed_answer']}`\n")
                    report.append(f"- Correct: {sample['evaluation']['correct']}\n")
                else:
                    report.append(f"- Error: `{sample.get('error', 'Unknown')}`\n")
                report.append("\n")
        
        if i < len(results) - 1:
            report.append("---\n\n")
    
    # Write report
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.writelines(report)
    
    print(f"✓ Report saved: {output_path}")


def _html_escape(text) -> str:
    """Escape text for safe HTML embedding."""
    if text is None:
        return ''
    return html_mod.escape(str(text))


def _make_slug(name: str) -> str:
    """Turn a display name into a safe HTML id slug."""
    return _re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def _get_shared_css() -> str:
    """Return the shared CSS used by both grouped and ungrouped reports."""
    return """
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 0 40px 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .report-header { background: white; padding: 30px 40px 0; max-width: 1400px; margin: 0 auto; border-radius: 8px 8px 0 0; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-top: 0; }
        h2 { color: #34495e; margin-top: 30px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px; }
        h3 { color: #7f8c8d; margin-top: 25px; }
        h4 { color: #7f8c8d; margin-top: 20px; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; }
        .metric-card.success { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .metric-card.warning { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .metric-card.info { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        .metric-value { font-size: 36px; font-weight: bold; margin: 10px 0; }
        .metric-label { font-size: 14px; opacity: 0.9; text-transform: uppercase; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }
        th { background: #3498db; color: white; padding: 12px; text-align: left; font-weight: 600; }
        td { padding: 12px; border-bottom: 1px solid #ecf0f1; }
        tr:hover { background: #f8f9fa; }
        .model-section { background: #f8f9fa; padding: 30px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #3498db; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-right: 8px; }
        .badge-primary { background: #3498db; color: white; }
        .badge-success { background: #2ecc71; color: white; }
        .badge-warning { background: #f39c12; color: white; }
        .badge-danger { background: #e74c3c; color: white; }
        .task-card { background: white; padding: 20px; margin: 15px 0; border-radius: 6px; border-left: 3px solid #3498db; }
        .progress-bar { height: 8px; background: #ecf0f1; border-radius: 4px; overflow: hidden; margin: 10px 0; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%); transition: width 0.3s; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; font-size: 0.9em; }
        .timestamp { color: #95a5a6; font-size: 14px; }
        img { max-width: 100%; height: auto; display: block; }

        /* ── Tab navigation ── */
        .tab-nav { display: flex; flex-wrap: wrap; gap: 4px; border-bottom: 2px solid #ecf0f1; padding-bottom: 0; margin-bottom: 0; position: sticky; top: 0; background: white; z-index: 100; padding-top: 15px; }
        .tab-btn { padding: 10px 22px; border: none; background: #f0f0f0; color: #7f8c8d; font-size: 14px; font-weight: 600;
                   cursor: pointer; border-radius: 6px 6px 0 0; transition: all 0.2s; position: relative; bottom: -2px; }
        .tab-btn:hover { background: #e0e7ff; color: #3498db; }
        .tab-btn.active { background: #3498db; color: white; }
        .tab-btn.sample-tab { background: #f9f0ff; color: #8e44ad; }
        .tab-btn.sample-tab:hover { background: #e8d5f5; }
        .tab-btn.sample-tab.active { background: #8e44ad; color: white; }
        .tab-pane { display: none; padding-top: 10px; }
        .tab-pane.active { display: block; }

        /* ── Sample response cards ── */
        .samples-section h3 { margin-top: 15px; }
        .sample-card { border: 1px solid #e0e0e0; border-radius: 8px; margin: 12px 0; overflow: hidden; }
        .sample-card.success { border-left: 4px solid #2ecc71; }
        .sample-card.danger { border-left: 4px solid #e74c3c; }
        .sample-card.warning { border-left: 4px solid #f39c12; }
        .sample-header { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: #fafafa; flex-wrap: wrap; }
        .sample-header .test-id { font-family: 'Courier New', monospace; font-size: 13px; color: #555; }
        .sample-body { padding: 14px 16px; }
        .sample-body .field { margin: 6px 0; }
        .sample-body .field strong { display: inline-block; min-width: 90px; }
        .collapsible-toggle { cursor: pointer; color: #3498db; font-size: 13px; font-weight: 600; margin-top: 10px; user-select: none; padding: 6px 0; }
        .collapsible-toggle:hover { color: #2980b9; text-decoration: underline; }
        .collapsible-content { display: none; margin-top: 10px; }
        .raw-response { background: #f8f8f8; border: 1px solid #e8e8e8; border-radius: 4px; padding: 14px; font-family: 'Courier New', monospace;
                        font-size: 12px; white-space: pre-wrap; word-break: break-word; max-height: 500px; overflow-y: auto; line-height: 1.5; }
        .prompt-section { margin-top: 12px; }
        .prompt-section summary { cursor: pointer; font-weight: 600; color: #7f8c8d; font-size: 13px; }
        .prompt-section pre { background: #f0f4ff; border: 1px solid #d0d8e8; border-radius: 4px; padding: 12px; font-size: 12px;
                              white-space: pre-wrap; word-break: break-word; max-height: 300px; overflow-y: auto; }
        .no-samples { color: #95a5a6; font-style: italic; padding: 20px 0; }

        /* ── Chart grid ── */
        .chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 30px; margin: 20px 0; }
        .chart-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .chart-card h4 { margin-top: 0; }

        /* ── Performance metrics (ungrouped) ── */
        .performance-metric { background: #f9f9f9; padding: 10px; margin: 5px 0; border-radius: 4px; }
        .error-critical { background: #ffe6e6; border: 1px solid #ffcccc; padding: 15px; border-radius: 4px; margin: 10px 0; }
        .accuracy-high { color: #27ae60; font-weight: bold; }
        .accuracy-low { color: #e74c3c; font-weight: bold; }
        .accuracy-med { color: #f39c12; font-weight: bold; }
        .task-breakdown { margin: 15px 0; }
        .task-breakdown table { font-size: 0.9em; }
"""


def _get_tab_js() -> str:
    """Return the JavaScript for tab switching and collapsible sections."""
    return """
    <script>
    function switchTab(tabId) {
        // Hide all panes, deactivate all buttons
        document.querySelectorAll('.tab-pane').forEach(function(p) { p.classList.remove('active'); });
        document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
        // Show target pane, activate its button
        var pane = document.getElementById(tabId);
        if (pane) pane.classList.add('active');
        var btn = document.querySelector('[data-tab="' + tabId + '"]');
        if (btn) btn.classList.add('active');
    }
    function toggleCollapsible(el) {
        var content = el.nextElementSibling;
        if (!content) return;
        var visible = content.style.display !== 'none';
        content.style.display = visible ? 'none' : 'block';
        // Swap arrow
        var arrow = visible ? '\\u25b6' : '\\u25bc';
        el.textContent = el.textContent.replace(/[\\u25b6\\u25bc]/, arrow);
    }
    </script>
"""


def _render_sample_cards(all_results_for_model: List[Dict], num_correct: int = 5, num_wrong: int = 5) -> str:
    """Render sample response cards (correct + wrong) for one model."""
    # Deduplicate results by test_id so repeated entries don't produce identical sample cards
    seen_ids: Dict[str, Dict] = {}
    for r in all_results_for_model:
        tid = r.get('test_id', id(r))
        seen_ids[tid] = r  # last-wins — keeps one copy per test_id
    deduped = list(seen_ids.values())

    # Separate correct vs wrong, skip error status results for wrong (show them separately if any)
    correct = []
    wrong = []
    errors = []
    for r in deduped:
        if r.get('status') != 'success':
            errors.append(r)
        elif r.get('evaluation', {}).get('correct'):
            correct.append(r)
        else:
            wrong.append(r)

    html = ''

    def _card(sample, label_class, label_text):
        """Build one sample card."""
        h = ''
        test_id = _html_escape(sample.get('test_id', '?'))
        # Detect task type from test_id
        tid = sample.get('test_id', '')
        task_badge = ''
        for tname in ['arithmetic', 'game_of_life', 'gol', 'linda', 'ascii_shapes',
                       'cellular_automata_1d', 'c14', 'object_tracking', 'sally_anne',
                       'carwash', 'inverted_cup', 'strawberry', 'measure_comparison', 'grid_tasks',
                       'misquote', 'time_arithmetic', 'false_premise', 'family_relations',
                       'encoding_cipher']:
            if tname in tid:
                nice = tname.replace('_', ' ').title()
                task_badge = f"<span class='badge badge-primary'>{nice}</span>"
                break

        duration = sample.get('duration', 0)
        tokens = sample.get('tokens', {})
        tok_in = tokens.get('input_tokens', 0)
        tok_out = tokens.get('output_tokens', 0)

        h += f"<div class='sample-card {label_class}'>\n"
        h += f"  <div class='sample-header'>\n"
        h += f"    <span class='badge badge-{label_class}'>{label_text}</span>\n"
        h += f"    {task_badge}\n"
        h += f"    <span class='test-id'>{test_id}</span>\n"
        if duration:
            h += f"    <span class='badge' style='background:#ecf0f1;color:#555'>{duration:.1f}s</span>\n"
        if tok_in or tok_out:
            h += f"    <span class='badge' style='background:#ecf0f1;color:#555'>{tok_in}+{tok_out} tok</span>\n"
        h += f"  </div>\n"

        h += f"  <div class='sample-body'>\n"
        if sample.get('status') == 'success':
            expected = _html_escape(sample['input']['task_params'].get('expected_answer', 'N/A'))
            parsed = _html_escape(sample['output'].get('parsed_answer', 'N/A'))
            h += f"    <div class='field'><strong>Expected:</strong> <code>{expected}</code></div>\n"
            h += f"    <div class='field'><strong>Parsed:</strong> <code>{parsed}</code></div>\n"

            raw = _html_escape(sample['output'].get('raw_response', ''))
            char_count = len(sample['output'].get('raw_response', ''))
            h += f"    <div class='collapsible-toggle' onclick='toggleCollapsible(this)'>&#9654; Show full response ({char_count} chars)</div>\n"
            h += f"    <div class='collapsible-content' style='display:none'>\n"
            h += f"      <div class='raw-response'>{raw}</div>\n"

            user_prompt = _html_escape(sample['input'].get('user_prompt', ''))
            sys_prompt = _html_escape(sample['input'].get('system_prompt', ''))
            if user_prompt:
                h += f"      <details class='prompt-section'><summary>User prompt</summary><pre>{user_prompt}</pre></details>\n"
            if sys_prompt:
                h += f"      <details class='prompt-section'><summary>System prompt</summary><pre>{sys_prompt}</pre></details>\n"
            h += f"    </div>\n"
        else:
            error_msg = _html_escape(sample.get('error', 'Unknown error'))
            h += f"    <div class='field'><strong>Error:</strong> <code>{error_msg}</code></div>\n"
        h += f"  </div>\n"
        h += f"</div>\n"
        return h

    # Random sample so we get a diverse mix across task types
    rng = _random.Random(42)  # fixed seed for reproducible reports
    if len(correct) > num_correct:
        correct = rng.sample(correct, num_correct)
    if len(wrong) > num_wrong:
        wrong = rng.sample(wrong, num_wrong)
    if len(errors) > 3:
        errors = rng.sample(errors, 3)

    # Correct samples
    if correct:
        html += f"<h3>Correct Responses ({len(correct)} shown)</h3>\n"
        for s in correct:
            html += _card(s, 'success', 'Correct')
    else:
        html += "<p class='no-samples'>No correct responses in this result set.</p>\n"

    # Wrong samples
    if wrong:
        html += f"<h3>Wrong Responses ({len(wrong)} shown)</h3>\n"
        for s in wrong:
            html += _card(s, 'danger', 'Wrong')
    else:
        html += "<p class='no-samples'>No wrong responses in this result set.</p>\n"

    # Errors (show up to 3)
    if errors:
        html += f"<h3>Error Responses ({len(errors)} shown)</h3>\n"
        for s in errors:
            html += _card(s, 'warning', 'Error')

    return html


def _render_chart_grid(charts_dir, output_path) -> str:
    """Render chart images as base64-embedded data URIs for self-contained HTML."""
    import base64 as _b64

    if not charts_dir or not Path(charts_dir).exists():
        return "<p class='no-samples'>No visualizations generated. Re-run with <code>--visualize</code> to generate charts.</p>\n"
    chart_files = sorted(Path(charts_dir).glob('*.png'))
    if not chart_files:
        return "<p class='no-samples'>No chart images found in the charts directory.</p>\n"
    html = "<div class='chart-grid'>\n"
    for chart_file in chart_files:
        chart_name = _html_escape(chart_file.stem.replace('_', ' ').title())
        try:
            img_bytes = chart_file.read_bytes()
            b64 = _b64.b64encode(img_bytes).decode('ascii')
            src = f"data:image/png;base64,{b64}"
        except Exception:
            src = chart_file.name  # fallback to filename if read fails
        html += f"  <div class='chart-card'>\n"
        html += f"    <h4>{chart_name}</h4>\n"
        html += f"    <img src='{src}' alt='{chart_name}' style='width:100%;height:auto;border-radius:4px;'>\n"
        html += f"  </div>\n"
    html += "</div>\n"
    return html


def generate_html_report(results: List[Dict], output_path: str, charts_dir: str = None, grouped_by_model: bool = False):
    """Generate interactive tabbed HTML report with sample responses per model."""

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ── Grouped mode (multi-model comparison) ──────────────────────────────
    if grouped_by_model and len(results) > 1:
        grouped_results = group_results_by_model(results)
        model_aggregates = {name: aggregate_model_stats(files)
                           for name, files in grouped_results.items()}
        sorted_models = sorted(model_aggregates.items(),
                               key=lambda x: x[1]['accuracy'], reverse=True)

        # Build tab list: fixed tabs + per-model sample tabs
        tabs = [
            ('tab-overview', '📊 Overview'),
            ('tab-detail',   '📋 Detailed Analysis'),
            ('tab-viz',      '📈 Visualizations'),
        ]
        for model_name, _ in sorted_models:
            slug = _make_slug(model_name)
            tabs.append((f'tab-samples-{slug}', f'🔍 {model_name}'))

        # ── Start HTML ──
        css = _get_shared_css()
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Model-Grouped Benchmark Analysis</title>
<style>{css}</style>
</head>
<body>
<div class="report-header">
  <h1>🎯 Model-Grouped Benchmark Analysis</h1>
  <p class="timestamp">Generated: {timestamp}</p>
</div>
<div class="container">
"""
        # ── Tab navigation ──
        html += "<div class='tab-nav'>\n"
        for i, (tab_id, tab_label) in enumerate(tabs):
            active = ' active' if i == 0 else ''
            extra = ' sample-tab' if tab_id.startswith('tab-samples-') else ''
            html += f"  <button class='tab-btn{active}{extra}' data-tab='{tab_id}' onclick=\"switchTab('{tab_id}')\">{_html_escape(tab_label)}</button>\n"
        html += "</div>\n"

        # ═══════════  TAB 1 — OVERVIEW  ═══════════
        total_files = len(results)
        total_models = len(grouped_results)
        total_tests = sum(a['total_tests'] for a in model_aggregates.values())

        html += "<div class='tab-pane active' id='tab-overview'>\n"
        html += f"""<div class="summary-grid">
  <div class="metric-card info"><div class="metric-label">Result Files</div><div class="metric-value">{total_files}</div></div>
  <div class="metric-card"><div class="metric-label">Models Analyzed</div><div class="metric-value">{total_models}</div></div>
  <div class="metric-card success"><div class="metric-label">Total Tests</div><div class="metric-value">{total_tests}</div></div>
</div>
<h2>Model Comparison</h2>
<table><thead><tr>
  <th>Model</th><th>Files</th><th>Tests</th><th>Accuracy</th>
  <th>Parse Errors</th><th>Avg Time</th><th>Tasks</th>
</tr></thead><tbody>
"""
        for model_name, agg in sorted_models:
            acc = agg['accuracy']
            badge = 'success' if acc >= 0.8 else 'warning' if acc >= 0.5 else 'danger'
            task_list = ", ".join(sorted(agg['task_types']))
            html += f"""<tr>
  <td><strong>{_html_escape(model_name)}</strong></td>
  <td><span class='badge badge-primary'>{agg['result_count']}</span></td>
  <td>{agg['total_tests']}</td>
  <td><span class='badge badge-{badge}'>{acc:.1%}</span></td>
  <td>{agg['parse_error_rate']:.1%}</td>
  <td>{agg['avg_time_per_test']:.2f}s</td>
  <td><small>{_html_escape(task_list)}</small></td>
</tr>
"""
        html += "</tbody></table>\n"
        html += "</div>\n"  # close tab-overview

        # ═══════════  TAB 2 — DETAILED MODEL ANALYSIS  ═══════════
        html += "<div class='tab-pane' id='tab-detail'>\n"
        for model_name, model_files in sorted(grouped_results.items()):
            agg = model_aggregates[model_name]
            html += f"""<div class="model-section">
  <h3>{_html_escape(model_name)}</h3>
  <p>Aggregated from <strong>{agg['result_count']}</strong> result file(s)</p>
  <div class="summary-grid">
    <div class="metric-card success">
      <div class="metric-label">Accuracy</div>
      <div class="metric-value">{agg['accuracy']:.1%}</div>
      <small>{agg['correct_responses']}/{agg['successful_tests']} correct</small>
    </div>
    <div class="metric-card warning">
      <div class="metric-label">Parse Errors</div>
      <div class="metric-value">{agg['parse_error_rate']:.1%}</div>
      <small>{agg['parse_errors']} errors</small>
    </div>
    <div class="metric-card info">
      <div class="metric-label">Avg Time</div>
      <div class="metric-value">{agg['avg_time_per_test']:.2f}s</div>
      <small>per test</small>
    </div>
  </div>
"""
            if agg['task_breakdown']:
                html += "  <h4>Performance by Task</h4>\n"
                for task_type in sorted(agg['task_breakdown'].keys()):
                    ts = agg['task_breakdown'][task_type]
                    pct = ts['accuracy'] * 100
                    html += f"""  <div class="task-card">
    <strong>{task_type.replace('_', ' ').title()}</strong> — {ts['total']} tests
    <div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div>
    <small>Accuracy: <strong>{ts['accuracy']:.1%}</strong> | Parse Errors: {ts['parse_error_rate']:.1%}</small>
  </div>
"""
            # Token stats if available
            if agg.get('total_input_tokens', 0) > 0:
                html += "  <h4>Token Usage</h4>\n"
                html += f"  <div class='performance-metric'><strong>Total Tokens:</strong> {agg.get('total_tokens', 0):,} ({agg.get('total_input_tokens', 0):,} in / {agg.get('total_output_tokens', 0):,} out)</div>\n"
                html += f"  <div class='performance-metric'><strong>Avg per Test:</strong> {agg.get('avg_input_tokens_per_test', 0):.0f} in / {agg.get('avg_output_tokens_per_test', 0):.0f} out</div>\n"

            html += "</div>\n"  # close model-section

        html += "</div>\n"  # close tab-detail

        # ═══════════  TAB 3 — VISUALIZATIONS  ═══════════
        html += "<div class='tab-pane' id='tab-viz'>\n"
        html += _render_chart_grid(charts_dir, output_path)
        html += "</div>\n"

        # ═══════════  TAB 4..N — PER-MODEL SAMPLES  ═══════════
        for model_name, model_files in sorted(grouped_results.items()):
            slug = _make_slug(model_name)
            # Collect all individual results across all files for this model
            all_results = []
            for mf in model_files:
                all_results.extend(mf.get('results', []))

            html += f"<div class='tab-pane' id='tab-samples-{slug}'>\n"
            html += f"<h2>Sample Responses — {_html_escape(model_name)}</h2>\n"
            html += f"<p>Randomly sampled up to 5 correct and 5 wrong responses from {len(all_results)} total tests.</p>\n"
            html += "<div class='samples-section'>\n"
            html += _render_sample_cards(all_results)
            html += "</div>\n"
            html += "</div>\n"

        # ── Close document ──
        html += _get_tab_js()
        html += "</div>\n</body>\n</html>"

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(html)
        print(f"✓ Model-grouped HTML report saved: {output_path}")
        return

    # ── Ungrouped mode (single / few result files) ─────────────────────────
    stats = [extract_summary_stats(r) for r in results]

    # Determine model names for sample tabs
    model_names = []
    for stat in stats:
        nm = stat['model_name']
        if stat.get('quantization'):
            nm += f" ({stat['quantization']})"
        if nm not in model_names:
            model_names.append(nm)

    tabs = [
        ('tab-overview', '📊 Overview'),
        ('tab-detail',   '📋 Detailed Analysis'),
        ('tab-viz',      '📈 Visualizations'),
    ]
    for nm in model_names:
        slug = _make_slug(nm)
        tabs.append((f'tab-samples-{slug}', f'🔍 {nm}'))

    css = _get_shared_css()
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Benchmark Analysis Report</title>
<style>{css}</style>
</head>
<body>
<div class="report-header">
  <h1>Benchmark Analysis Report</h1>
  <p class="timestamp">Generated: {timestamp}</p>
</div>
<div class="container">
"""
    # ── Tab navigation ──
    html += "<div class='tab-nav'>\n"
    for i, (tab_id, tab_label) in enumerate(tabs):
        active = ' active' if i == 0 else ''
        extra = ' sample-tab' if tab_id.startswith('tab-samples-') else ''
        html += f"  <button class='tab-btn{active}{extra}' data-tab='{tab_id}' onclick=\"switchTab('{tab_id}')\">{_html_escape(tab_label)}</button>\n"
    html += "</div>\n"

    # ═══════════  TAB 1 — OVERVIEW  ═══════════
    html += "<div class='tab-pane active' id='tab-overview'>\n"
    html += "<h2>Summary</h2>\n"
    html += "<table><thead><tr><th>Model</th><th>Provider</th><th>Task</th><th>Tests</th><th>Accuracy</th><th>Parse Errors</th><th>Avg Time</th><th>Avg Tokens</th><th>Duration</th></tr></thead><tbody>\n"

    for stat in stats:
        model_display = _html_escape(stat['model_name'])
        if stat['quantization']:
            model_display += f" ({_html_escape(stat['quantization'])})"
        acc_class = "accuracy-high" if stat['accuracy'] > 0.7 else "accuracy-low" if stat['accuracy'] < 0.3 else "accuracy-med"
        avg_tokens = stat.get('avg_input_tokens_per_test', 0) + stat.get('avg_output_tokens_per_test', 0)
        tokens_str = f"{avg_tokens/1000:.1f}K" if avg_tokens >= 1000 else f"{avg_tokens:.0f}"
        html += f"<tr><td>{model_display}</td><td>{_html_escape(stat['provider'])}</td><td>{_html_escape(stat['task_type'])}</td>"
        html += f"<td>{stat['successful_tests']}/{stat['total_tests']}</td>"
        html += f"<td class='{acc_class}'>{stat['accuracy']:.1%}</td>"
        html += f"<td>{stat['parse_error_rate']:.1%}</td>"
        html += f"<td>{stat['avg_time_per_test']:.1f}s</td><td>{tokens_str}</td><td>{stat['duration_seconds']:.0f}s</td></tr>\n"

    html += "</tbody></table>\n"

    # Multi-task overview
    for stat in stats:
        if stat.get('task_breakdown'):
            html += f"<h3>{_html_escape(stat['model_name'])} Task Breakdown</h3>\n"
            html += "<div class='task-breakdown'><table><thead><tr><th>Task Type</th><th>Tests</th><th>Accuracy</th><th>Parse Errors</th></tr></thead><tbody>\n"
            for task_type, ts in stat['task_breakdown'].items():
                html += f"<tr><td>{task_type.replace('_', ' ').title()}</td><td>{ts['total']}</td><td>{ts['accuracy']:.1%}</td><td>{ts['parse_error_rate']:.1%}</td></tr>\n"
            html += "</tbody></table></div>\n"

    html += "</div>\n"  # close tab-overview

    # ═══════════  TAB 2 — DETAILED ANALYSIS  ═══════════
    html += "<div class='tab-pane' id='tab-detail'>\n"

    for i, (result, stat) in enumerate(zip(results, stats)):
        html += "<div class='model-section'>\n"
        html += f"<h2>{_html_escape(stat['model_name'])} — {_html_escape(stat['task_type'])}</h2>\n"
        html += f"<p><strong>Testset:</strong> {_html_escape(stat['testset_name'] or 'N/A')}</p>\n"
        html += f"<p><strong>Provider:</strong> {_html_escape(stat['provider'] or 'N/A')}</p>\n"
        if stat['quantization']:
            html += f"<p><strong>Quantization:</strong> {_html_escape(stat['quantization'])}</p>\n"
        created = (stat['created_at'] or '')[:19] or 'N/A'
        hostname = stat['hostname'] or 'N/A'
        html += f"<p><strong>Execution:</strong> {_html_escape(created)} on {_html_escape(hostname)}</p>\n"

        acc_class = "accuracy-high" if stat['accuracy'] > 0.7 else "accuracy-low" if stat['accuracy'] < 0.3 else "accuracy-med"
        html += "<h3>Performance</h3>\n"
        html += f"<div class='performance-metric'><strong>Accuracy:</strong> <span class='{acc_class}'>{stat['accuracy']:.2%}</span> ({stat['correct_responses']}/{stat['successful_tests']})</div>\n"
        html += f"<div class='performance-metric'><strong>Parse Error Rate:</strong> {stat['parse_error_rate']:.2%} ({stat['parse_errors']}/{stat['successful_tests']})</div>\n"
        html += f"<div class='performance-metric'><strong>Success Rate:</strong> {stat['success_rate']:.2%} ({stat['successful_tests']}/{stat['total_tests']})</div>\n"
        if stat['avg_cell_accuracy'] is not None:
            html += f"<div class='performance-metric'><strong>Cell-level Accuracy:</strong> {stat['avg_cell_accuracy']:.2%}</div>\n"
        html += f"<div class='performance-metric'><strong>Average Time per Test:</strong> {stat['avg_time_per_test']:.2f}s</div>\n"
        html += f"<div class='performance-metric'><strong>Total Duration:</strong> {stat['duration_seconds']:.1f}s</div>\n"

        if stat.get('total_input_tokens', 0) > 0:
            html += "<h3>Token Usage</h3>\n"
            html += f"<div class='performance-metric'><strong>Total Input Tokens:</strong> {stat['total_input_tokens']:,}</div>\n"
            html += f"<div class='performance-metric'><strong>Total Output Tokens:</strong> {stat['total_output_tokens']:,}</div>\n"
            html += f"<div class='performance-metric'><strong>Total Tokens:</strong> {stat['total_tokens']:,}</div>\n"
            html += f"<div class='performance-metric'><strong>Avg Input per Test:</strong> {stat['avg_input_tokens_per_test']:.0f}</div>\n"
            html += f"<div class='performance-metric'><strong>Avg Output per Test:</strong> {stat['avg_output_tokens_per_test']:.0f}</div>\n"

        if stat.get('is_multi_task', False) and stat['task_breakdown']:
            html += "<h3>Task-Specific Performance</h3>\n"
            html += "<div class='task-breakdown'><table><thead><tr><th>Task Type</th><th>Tests</th><th>Accuracy</th><th>Parse Errors</th></tr></thead><tbody>\n"
            for task_type, ts in stat['task_breakdown'].items():
                html += f"<tr><td>{task_type.replace('_', ' ').title()}</td><td>{ts['total']}</td><td>{ts['accuracy']:.1%}</td><td>{ts['parse_error_rate']:.1%}</td></tr>\n"
            html += "</tbody></table></div>\n"

        # Error analysis
        if stat['parse_errors'] > 0 or stat['type_errors'] > 0:
            html += "<h3>Error Analysis</h3>\n"
            error_types = defaultdict(int)
            for r in result['results']:
                etype = r.get('evaluation', {}).get('match_type')
                if etype and etype not in ['exact', 'perfect']:
                    error_types[etype] += 1
            html += "<ul>\n"
            for etype, count in error_types.items():
                rate = count / max(stat['successful_tests'], 1) * 100
                html += f"  <li><strong>{etype.replace('_', ' ').title()}</strong>: {count} ({rate:.1f}%)</li>\n"
            html += "</ul>\n"
            if stat['parse_error_rate'] >= 1.0:
                html += "<div class='error-critical'><h4>⚠️ Critical Issue: 100% Parse Errors</h4>\n"
                html += "<p>All responses failed to parse. Check prompt format / parsing strategy.</p></div>\n"

        html += "</div>\n"  # close model-section

    html += "</div>\n"  # close tab-detail

    # ═══════════  TAB 3 — VISUALIZATIONS  ═══════════
    html += "<div class='tab-pane' id='tab-viz'>\n"
    html += _render_chart_grid(charts_dir, output_path)
    html += "</div>\n"

    # ═══════════  TAB 4..N — PER-MODEL SAMPLES  ═══════════
    # Group the raw result dicts by the same model key used for tabs
    model_result_map = defaultdict(list)
    for result, stat in zip(results, stats):
        nm = stat['model_name']
        if stat.get('quantization'):
            nm += f" ({stat['quantization']})"
        model_result_map[nm].extend(result.get('results', []))

    for nm in model_names:
        slug = _make_slug(nm)
        all_results = model_result_map.get(nm, [])
        html += f"<div class='tab-pane' id='tab-samples-{slug}'>\n"
        html += f"<h2>Sample Responses — {_html_escape(nm)}</h2>\n"
        html += f"<p>Randomly sampled up to 5 correct and 5 wrong responses from {len(all_results)} total tests.</p>\n"
        html += "<div class='samples-section'>\n"
        html += _render_sample_cards(all_results)
        html += "</div>\n"
        html += "</div>\n"

    # ── Close document ──
    html += _get_tab_js()
    html += "</div>\n</body>\n</html>"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)
    print(f"✓ HTML report saved: {output_path}")


def generate_visualizations(results: List[Dict], output_dir: str):
    """
    Generate comprehensive visualization suite with intelligent auto-detection.
    
    Automatically determines applicable comparisons:
    - Prompt combinations (user_style × system_style)
    - Task types
    - Models
    - Quantization variants
    - Multi-dimensional interactions
    
    Generates heatmaps, radar charts, bar charts, scatter plots based on data structure.
    """
    if not VISUALIZATION_AVAILABLE:
        print("✗ Visualization libraries not available. Skipping charts.")
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Extract data for plotting
    stats = [extract_summary_stats(r) for r in results]
    
    if not stats:
        print("No data to visualize")
        return
    
    print(f"\n{'='*70}")
    print(f"🎨 INTELLIGENT VISUALIZATION GENERATOR")
    print(f"{'='*70}")
    print(f"Analyzing {len(results)} result files...")
    
    # Auto-detect data dimensions
    dimensions = _detect_data_dimensions(results, stats)
    
    print(f"\n📊 Detected Data Dimensions:")
    print(f"  Models: {len(dimensions['models'])} unique ({', '.join(list(dimensions['models'])[:3])}{'...' if len(dimensions['models']) > 3 else ''})")
    print(f"  Tasks: {len(dimensions['tasks'])} unique ({', '.join(list(dimensions['tasks']))})")
    print(f"  Quantizations: {len(dimensions['quantizations'])} unique ({', '.join(list(dimensions['quantizations']))})")
    print(f"  Prompt Configs: {len(dimensions['prompt_configs'])} unique")
    if dimensions['prompt_configs']:
        sample_prompts = list(dimensions['prompt_configs'])[:2]
        print(f"    Examples: {', '.join(sample_prompts)}")
    print(f"  User Prompts: {len(dimensions['user_prompts'])} styles ({', '.join(list(dimensions['user_prompts']))})")
    print(f"  System Prompts: {len(dimensions['system_prompts'])} styles ({', '.join(list(dimensions['system_prompts']))})")
    
    # Set global plotting style
    sns.set_style("whitegrid")
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.size'] = 10
    
    # Generate applicable visualizations
    chart_count = 0
    
    print(f"\n🔥 Generating Comparison Charts...")
    print(f"{'-'*70}")
    
    # === PROMPT COMPARISONS ===
    if len(dimensions['prompt_configs']) > 1:
        print("\n📌 PROMPT ANALYSIS CHARTS")
        
        # 1. Prompt Performance Heatmap (user × system)
        if len(dimensions['user_prompts']) > 1 and len(dimensions['system_prompts']) > 1:
            chart_count += 1
            _generate_prompt_heatmap(results, stats, dimensions, output_path, chart_count)
        
        # 2. User Prompt Impact (averaged over system prompts)
        if len(dimensions['user_prompts']) > 1:
            chart_count += 1
            _generate_user_prompt_impact(results, stats, dimensions, output_path, chart_count)
        
        # 3. System Prompt Impact (averaged over user prompts)
        if len(dimensions['system_prompts']) > 1:
            chart_count += 1
            _generate_system_prompt_impact(results, stats, dimensions, output_path, chart_count)
        
        # 4. Prompt Configuration Radar (multi-dimensional comparison)
        if len(dimensions['prompt_configs']) >= 3:
            chart_count += 1
            _generate_prompt_radar(results, stats, dimensions, output_path, chart_count)
    
    # === TASK COMPARISONS ===
    if len(dimensions['tasks']) > 1:
        print("\n📌 TASK ANALYSIS CHARTS")
        
        # 5. Task Performance Heatmap (model × task)
        chart_count += 1
        _generate_task_heatmap(results, stats, dimensions, output_path, chart_count)
        
        # 6. Task Difficulty Analysis (bar chart with error analysis)
        chart_count += 1
        _generate_task_difficulty(results, stats, dimensions, output_path, chart_count)
        
        # 7. Per-Task Model Rankings (grouped bars)
        if len(dimensions['models']) > 1:
            chart_count += 1
            _generate_task_model_ranking(results, stats, dimensions, output_path, chart_count)
    
    # === MODEL COMPARISONS ===
    if len(dimensions['models']) > 1:
        print("\n📌 MODEL COMPARISON CHARTS")
        
        # 8. Model Performance Dashboard (multi-panel overview)
        chart_count += 1
        _generate_model_dashboard(results, stats, dimensions, output_path, chart_count)
        
        # 9. Model Efficiency Scatter (accuracy vs time)
        chart_count += 1
        _generate_model_efficiency(results, stats, dimensions, output_path, chart_count)
        
        # 10. Model Leaderboard with Confidence Intervals
        chart_count += 1
        _generate_model_leaderboard(results, stats, dimensions, output_path, chart_count)
    
    # === QUANTIZATION COMPARISONS ===
    if len(dimensions['quantizations']) > 1:
        print("\n📌 QUANTIZATION ANALYSIS CHARTS")
        
        # 11. Quantization Impact Heatmap (config × quantization)
        chart_count += 1
        _generate_quantization_heatmap(results, stats, dimensions, output_path, chart_count)
        
        # 12. Quantization Trade-off Analysis (compression vs accuracy)
        chart_count += 1
        _generate_quantization_tradeoff(results, stats, dimensions, output_path, chart_count)
        
        # 13. Quantization Distribution Box Plot
        chart_count += 1
        _generate_quantization_distribution(results, stats, dimensions, output_path, chart_count)
    
    # === MULTI-DIMENSIONAL COMPARISONS ===
    if len(dimensions['models']) > 1 and len(dimensions['tasks']) > 1:
        print("\n📌 MULTI-DIMENSIONAL ANALYSIS")
        
        # 14. 3D Interaction Heatmap (model × task × prompt)
        if len(dimensions['prompt_configs']) > 1:
            chart_count += 1
            _generate_3d_interaction_heatmap(results, stats, dimensions, output_path, chart_count)
        
        # 15. Best Configuration Finder (top-5 rankings)
        chart_count += 1
        _generate_best_worst_configs(results, stats, dimensions, output_path, chart_count)
    
    # === ERROR ANALYSIS ===
    print("\n📌 ERROR & RELIABILITY ANALYSIS")
    
    # 16. Parse Error Analysis (by dimension)
    chart_count += 1
    _generate_error_analysis_enhanced(results, stats, dimensions, output_path, chart_count)
    
    # 17. Variance & Stability Analysis
    if len(dimensions['models']) > 1 or len(dimensions['tasks']) > 1:
        chart_count += 1
        _generate_variance_analysis(results, stats, dimensions, output_path, chart_count)
    
    # === TOKEN USAGE ANALYSIS ===
    if any(stat.get('total_input_tokens', 0) > 0 for stat in stats):
        print("\n📌 TOKEN USAGE ANALYSIS")
        
        # 18. Token Usage Comparison (input vs output by model/task)
        chart_count += 1
        _generate_token_usage_chart(results, stats, dimensions, output_path, chart_count)
        
        # 19. Token Efficiency Scatter (tokens vs accuracy)
        chart_count += 1
        _generate_token_efficiency_scatter(results, stats, dimensions, output_path, chart_count)
    
    print(f"\n{'='*70}")
    print(f"✅ Generated {chart_count} visualizations")
    print(f"📁 Saved to: {output_path}")
    print(f"{'='*70}\n")


def _detect_data_dimensions(results: List[Dict], stats: List[Dict]) -> Dict[str, set]:
    """
    Auto-detect available data dimensions for intelligent chart generation.
    
    Returns dict with sets of unique values for each dimension:
    - models: unique model names
    - tasks: unique task types
    - quantizations: unique quantization formats
    - prompt_configs: unique prompt combinations
    - user_prompts: unique user prompt styles
    - system_prompts: unique system prompt styles
    """
    dimensions = {
        'models': set(),
        'tasks': set(),
        'quantizations': set(),
        'prompt_configs': set(),
        'user_prompts': set(),
        'system_prompts': set(),
        'providers': set(),
    }
    
    for result, stat in zip(results, stats):
        # Model info
        model_name = stat.get('model_name', 'unknown')
        dimensions['models'].add(model_name)
        
        # Task type - handle multi-task results
        task_type = stat.get('task_type', 'unknown')
        if task_type == 'multi-task' and 'task_breakdown' in stat:
            # Extract individual tasks from breakdown
            for task_name in stat['task_breakdown'].keys():
                dimensions['tasks'].add(task_name)
        else:
            dimensions['tasks'].add(task_type)
        
        # Quantization
        quant = stat.get('quantization')
        if quant:
            dimensions['quantizations'].add(quant)
        
        # Provider
        provider = stat.get('provider', 'unknown')
        dimensions['providers'].add(provider)
        
        # Prompt configuration from stats (already extracted)
        user_prompt = stat.get('user_prompt_style')
        system_prompt = stat.get('system_prompt_style')
        
        if user_prompt:
            dimensions['user_prompts'].add(user_prompt)
        if system_prompt:
            dimensions['system_prompts'].add(system_prompt)
        
        # Create combined config identifier
        if user_prompt and system_prompt:
            config_key = f"{user_prompt}_{system_prompt}"
            dimensions['prompt_configs'].add(config_key)
    
    return dimensions


def _save_chart(fig, output_path: Path, chart_num: int, name: str, print_size: bool = True):
    """Save figure with consistent formatting and progress reporting."""
    filename = f"{chart_num:02d}_{name}.png"
    filepath = output_path / filename
    
    fig.savefig(
        filepath,
        dpi=300,
        bbox_inches='tight',
        pad_inches=0.3,
        facecolor='white',
        edgecolor='none'
    )
    
    if print_size:
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"  ✓ {filename} ({size_mb:.2f} MB)")
    else:
        print(f"  ✓ {filename}")
    
    plt.close(fig)


# =============================================================================
# PROMPT COMPARISON CHARTS
# =============================================================================

def _generate_prompt_heatmap(results, stats, dimensions, output_path, chart_num):
    """1. Prompt Performance Heatmap: User × System accuracy matrix."""
    user_prompts = sorted(dimensions['user_prompts'])
    system_prompts = sorted(dimensions['system_prompts'])
    
    # Build matrix
    matrix = np.zeros((len(user_prompts), len(system_prompts)))
    counts = np.zeros((len(user_prompts), len(system_prompts)))
    
    for stat in stats:
        user = stat.get('user_prompt_style')
        system = stat.get('system_prompt_style')
        
        if user in user_prompts and system in system_prompts:
            u_idx = user_prompts.index(user)
            s_idx = system_prompts.index(system)
            matrix[u_idx, s_idx] += stat.get('accuracy', 0) * 100
            counts[u_idx, s_idx] += 1
    
    # Average
    matrix = np.divide(matrix, counts, where=counts > 0, out=matrix)
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(10, 8))
    
    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    
    # Labels
    ax.set_xticks(np.arange(len(system_prompts)))
    ax.set_yticks(np.arange(len(user_prompts)))
    ax.set_xticklabels([s.title() for s in system_prompts])
    ax.set_yticklabels([u.title() for u in user_prompts])
    
    # Rotate labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Annotate cells
    for i in range(len(user_prompts)):
        for j in range(len(system_prompts)):
            if counts[i, j] > 0:
                text = ax.text(j, i, f'{matrix[i, j]:.1f}%',
                             ha="center", va="center", color="black", fontsize=10, fontweight='bold')
    
    # Colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Accuracy (%)', rotation=-90, va="bottom", fontsize=11)
    
    ax.set_title('Prompt Configuration Performance Matrix', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('System Prompt Style', fontsize=12, fontweight='bold')
    ax.set_ylabel('User Prompt Style', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'prompt_heatmap')


def _generate_user_prompt_impact(results, stats, dimensions, output_path, chart_num):
    """2. User Prompt Impact: Averaged over system prompts."""
    user_prompts = sorted(dimensions['user_prompts'])
    
    # Calculate average accuracy for each user prompt (averaging over system prompts)
    user_scores = defaultdict(lambda: {'accuracies': []})
    
    for stat in stats:
        user = stat.get('user_prompt_style')
        if user:
            user_scores[user]['accuracies'].append(stat.get('accuracy', 0) * 100)
    
    # Average per user prompt
    avg_scores = {user: np.mean(data['accuracies']) for user, data in user_scores.items()}
    std_scores = {user: np.std(data['accuracies']) for user, data in user_scores.items()}
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x_pos = np.arange(len(user_prompts))
    means = [avg_scores.get(u, 0) for u in user_prompts]
    stds = [std_scores.get(u, 0) for u in user_prompts]
    
    # Color by performance
    colors = [SUCCESS_GREEN if m >= 70 else WARNING_ORANGE if m >= 50 else ERROR_RED for m in means]
    
    bars = ax.bar(x_pos, means, yerr=stds, capsize=5, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # Annotations
    for i, (bar, mean) in enumerate(zip(bars, means)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + stds[i] + 2,
               f'{mean:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    ax.set_xlabel('User Prompt Style', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('User Prompt Impact on Performance\\n(Averaged across System Prompts)', 
                fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([u.title() for u in user_prompts])
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'user_prompt_impact')


def _generate_system_prompt_impact(results, stats, dimensions, output_path, chart_num):
    """3. System Prompt Impact: Averaged over user prompts."""
    system_prompts = sorted(dimensions['system_prompts'])
    
    # Calculate average accuracy for each system prompt
    system_scores = defaultdict(lambda: {'accuracies': []})
    
    for stat in stats:
        system = stat.get('system_prompt_style')
        if system:
            system_scores[system]['accuracies'].append(stat.get('accuracy', 0) * 100)
    
    avg_scores = {s: np.mean(data['accuracies']) for s, data in system_scores.items()}
    std_scores = {s: np.std(data['accuracies']) for s, data in system_scores.items()}
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x_pos = np.arange(len(system_prompts))
    means = [avg_scores.get(s, 0) for s in system_prompts]
    stds = [std_scores.get(s, 0) for s in system_prompts]
    
    colors = [SUCCESS_GREEN if m >= 70 else WARNING_ORANGE if m >= 50 else ERROR_RED for m in means]
    
    bars = ax.bar(x_pos, means, yerr=stds, capsize=5, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    for i, (bar, mean) in enumerate(zip(bars, means)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + stds[i] + 2,
               f'{mean:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    ax.set_xlabel('System Prompt Style', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('System Prompt Impact on Performance\\n(Averaged across User Prompts)', 
                fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([s.title() for s in system_prompts])
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'system_prompt_impact')


def _generate_prompt_radar(results, stats, dimensions, output_path, chart_num):
    """4. Prompt Configuration Radar: Multi-dimensional comparison."""
    prompt_configs = sorted(dimensions['prompt_configs'])[:9]  # Limit to 9 for readability
    
    # Calculate average accuracy per config
    config_scores = defaultdict(list)
    for stat in stats:
        user = stat.get('user_prompt_style')
        system = stat.get('system_prompt_style')
        if user and system:
            config_key = f"{user}_{system}"
            if config_key in prompt_configs:
                config_scores[config_key].append(stat.get('accuracy', 0) * 100)
    
    # Average scores
    scores = [np.mean(config_scores[c]) if c in config_scores else 0 for c in prompt_configs]
    
    # Radar chart
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    angles = np.linspace(0, 2 * np.pi, len(prompt_configs), endpoint=False).tolist()
    scores_plot = scores + [scores[0]]  # Close the circle
    angles += angles[:1]
    
    ax.plot(angles, scores_plot, 'o-', linewidth=2, color=INFO_BLUE)
    ax.fill(angles, scores_plot, alpha=0.25, color=INFO_BLUE)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([c.replace('_', '\\n').title() for c in prompt_configs], fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_ylabel('Accuracy (%)', fontsize=10)
    ax.set_title('Prompt Configuration Performance Radar', fontsize=14, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'prompt_radar')


# =============================================================================
# TASK COMPARISON CHARTS
# =============================================================================

def _generate_task_heatmap(results, stats, dimensions, output_path, chart_num):
    """5. Task Performance Heatmap: Model × Task accuracy matrix."""
    models = sorted(dimensions['models'])
    tasks = sorted(dimensions['tasks'])
    
    # Build matrix
    matrix = np.zeros((len(models), len(tasks)))
    counts = np.zeros((len(models), len(tasks)))
    
    for stat in stats:
        model = stat.get('model_name')
        task = stat.get('task_type')
        
        if model in models and task in tasks:
            m_idx = models.index(model)
            t_idx = tasks.index(task)
            matrix[m_idx, t_idx] += stat.get('accuracy', 0) * 100
            counts[m_idx, t_idx] += 1
    
    # Average
    matrix = np.divide(matrix, counts, where=counts > 0, out=matrix)
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(max(10, len(tasks) * 1.5), max(8, len(models) * 1.2)))
    
    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    
    # Labels
    ax.set_xticks(np.arange(len(tasks)))
    ax.set_yticks(np.arange(len(models)))
    ax.set_xticklabels([t.replace('_', ' ').title() for t in tasks])
    ax.set_yticklabels(models)
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Annotate cells
    for i in range(len(models)):
        for j in range(len(tasks)):
            if counts[i, j] > 0:
                ax.text(j, i, f'{matrix[i, j]:.1f}%',
                       ha="center", va="center", color="black", fontsize=10, fontweight='bold')
    
    # Colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Accuracy (%)', rotation=-90, va="bottom", fontsize=11)
    
    ax.set_title('Model vs Task Performance Matrix', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Task Type', fontsize=12, fontweight='bold')
    ax.set_ylabel('Model', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'task_heatmap')


def _generate_task_difficulty(results, stats, dimensions, output_path, chart_num):
    """6. Task Difficulty Analysis: Bar chart with parse error overlays."""
    tasks = sorted(dimensions['tasks'])
    
    # Calculate average metrics per task
    task_metrics = defaultdict(lambda: {'accuracies': [], 'parse_errors': []})
    
    for stat in stats:
        task = stat.get('task_type')
        if task:
            task_metrics[task]['accuracies'].append(stat.get('accuracy', 0) * 100)
            task_metrics[task]['parse_errors'].append(stat.get('parse_error_rate', 0) * 100)
    
    # Average
    avg_acc = [np.mean(task_metrics[t]['accuracies']) if t in task_metrics else 0 for t in tasks]
    avg_err = [np.mean(task_metrics[t]['parse_errors']) if t in task_metrics else 0 for t in tasks]
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    x_pos = np.arange(len(tasks))
    width = 0.35
    
    # Accuracy bars
    colors_acc = [TASK_COLORS.get(t, INFO_BLUE) for t in tasks]
    bars1 = ax.bar(x_pos - width/2, avg_acc, width, label='Accuracy', color=colors_acc, alpha=0.8, edgecolor='black')
    
    # Parse error bars
    bars2 = ax.bar(x_pos + width/2, avg_err, width, label='Parse Errors', color=ERROR_RED, alpha=0.6, edgecolor='black')
    
    # Annotations
    for bar, val in zip(bars1, avg_acc):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    for bar, val in zip(bars2, avg_err):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{val:.1f}%', ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Task Type', fontsize=12, fontweight='bold')
    ax.set_ylabel('Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_title('Task Difficulty Analysis\\n(Accuracy vs Parse Error Rate)', fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([t.replace('_', ' ').title() for t in tasks], rotation=45, ha='right')
    ax.set_ylim(0, 105)
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'task_difficulty')


def _generate_task_model_ranking(results, stats, dimensions, output_path, chart_num):
    """7. Per-Task Model Rankings: Grouped bars showing model rank per task."""
    tasks = sorted(dimensions['tasks'])
    models = sorted(dimensions['models'])
    
    # Build data: task -> model -> accuracy
    task_model_data = defaultdict(lambda: defaultdict(list))
    
    for stat in stats:
        task = stat.get('task_type')
        model = stat.get('model_name')
        if task and model:
            task_model_data[task][model].append(stat.get('accuracy', 0) * 100)
    
    # Average per task-model pair
    for task in task_model_data:
        for model in task_model_data[task]:
            task_model_data[task][model] = np.mean(task_model_data[task][model])
    
    # Create grouped bar chart
    fig, ax = plt.subplots(figsize=(max(12, len(tasks) * 2), 8))
    
    x_pos = np.arange(len(tasks))
    width = 0.8 / len(models)
    colors = plt.cm.Set2(np.linspace(0, 1, len(models)))
    
    for i, model in enumerate(models):
        scores = [task_model_data[t].get(model, 0) for t in tasks]
        offset = (i - len(models)/2) * width + width/2
        bars = ax.bar(x_pos + offset, scores, width, label=model, color=colors[i], alpha=0.8, edgecolor='black')
        
        # Annotate
        for bar, score in zip(bars, scores):
            if score > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                       f'{score:.0f}', ha='center', va='bottom', fontsize=8)
    
    ax.set_xlabel('Task Type', fontsize=12, fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('Model Performance Comparison Across Tasks', fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([t.replace('_', ' ').title() for t in tasks], rotation=45, ha='right')
    ax.set_ylim(0, 105)
    ax.legend(loc='upper right', fontsize=9, ncol=2)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'task_model_ranking')


# =============================================================================
# MODEL COMPARISON CHARTS
# =============================================================================

def _generate_model_dashboard(results, stats, dimensions, output_path, chart_num):
    """8. Model Performance Dashboard: Comprehensive 2x2 grid."""
    models = sorted(dimensions['models'])
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # Top-left: Accuracy comparison
    accuracies = [np.mean([s['accuracy'] * 100 for s in stats if s['model_name'] == m]) 
                 for m in models]
    colors = [SUCCESS_GREEN if a >= 70 else WARNING_ORANGE if a >= 50 else ERROR_RED 
             for a in accuracies]
    
    bars1 = ax1.barh(models, accuracies, color=colors, alpha=0.8, edgecolor='black')
    for bar, acc in zip(bars1, accuracies):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{acc:.1f}%', va='center', fontweight='bold')
    ax1.set_xlabel('Accuracy (%)', fontweight='bold')
    ax1.set_title('Model Accuracy Comparison', fontweight='bold')
    ax1.set_xlim(0, 105)
    ax1.grid(axis='x', alpha=0.3)
    
    # Top-right: Parse error rates
    parse_rates = [np.mean([s['parse_error_rate'] * 100 for s in stats if s['model_name'] == m])
                  for m in models]
    bars2 = ax2.barh(models, parse_rates, color=ERROR_RED, alpha=0.6, edgecolor='black')
    for bar, rate in zip(bars2, parse_rates):
        ax2.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{rate:.1f}%', va='center', fontweight='bold')
    ax2.set_xlabel('Parse Error Rate (%)', fontweight='bold')
    ax2.set_title('Model Parse Error Rates', fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    
    # Bottom-left: Speed (tests per second)
    speeds = []
    for m in models:
        model_stats = [s for s in stats if s['model_name'] == m]
        avg_time = np.mean([s['avg_time_per_test'] for s in model_stats if s['avg_time_per_test'] > 0])
        speeds.append(1/avg_time if avg_time > 0 else 0)
    
    bars3 = ax3.barh(models, speeds, color=INFO_BLUE, alpha=0.8, edgecolor='black')
    for bar, speed in zip(bars3, speeds):
        ax3.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                f'{speed:.2f}', va='center', fontweight='bold')
    ax3.set_xlabel('Tests per Second', fontweight='bold')
    ax3.set_title('Model Speed', fontweight='bold')
    ax3.grid(axis='x', alpha=0.3)
    
    # Bottom-right: Test count
    test_counts = [sum(s['total_tests'] for s in stats if s['model_name'] == m)
                  for m in models]
    bars4 = ax3.barh(models, test_counts, color='#95a5a6', alpha=0.8, edgecolor='black')
    for bar, count in zip(bars4, test_counts):
        ax4.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
                f'{count}', va='center', fontweight='bold')
    ax4.set_xlabel('Total Tests', fontweight='bold')
    ax4.set_title('Test Coverage', fontweight='bold')
    ax4.grid(axis='x', alpha=0.3)
    
    fig.suptitle('Comprehensive Model Performance Dashboard', fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'model_dashboard')


def _generate_model_efficiency(results, stats, dimensions, output_path, chart_num):
    """9. Model Efficiency Scatter: Accuracy vs Speed trade-off."""
    models = sorted(dimensions['models'])
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Calculate metrics for each model
    model_data = []
    for model in models:
        model_stats = [s for s in stats if s['model_name'] == model]
        
        avg_acc = np.mean([s['accuracy'] * 100 for s in model_stats])
        avg_time = np.mean([s['avg_time_per_test'] for s in model_stats if s['avg_time_per_test'] > 0])
        total_tests = sum(s['total_tests'] for s in model_stats)
        
        model_data.append({
            'name': model,
            'accuracy': avg_acc,
            'time': avg_time,
            'tests': total_tests
        })
    
    # Scatter plot with bubble sizes
    for data in model_data:
        size = np.sqrt(data['tests']) * 20  # Scale bubble size
        color = SUCCESS_GREEN if data['accuracy'] >= 70 else WARNING_ORANGE if data['accuracy'] >= 50 else ERROR_RED
        
        ax.scatter(data['time'], data['accuracy'], s=size, color=color, alpha=0.6, 
                  edgecolor='black', linewidth=2)
        ax.text(data['time'], data['accuracy'], data['name'], 
               fontsize=9, ha='center', va='center', fontweight='bold')
    
    ax.set_xlabel('Average Time per Test (seconds)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('Model Efficiency: Accuracy vs Speed Trade-off\\n(Bubble size = test count)', 
                fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=0)
    ax.set_ylim(0, 105)
    
    # Add optimal region annotation
    if len(model_data) > 0:
        max_acc = max(d['accuracy'] for d in model_data)
        min_time = min(d['time'] for d in model_data if d['time'] > 0)
        ax.axhline(y=70, color=SUCCESS_GREEN, linestyle='--', alpha=0.3, label='Good accuracy threshold')
        
    ax.legend(loc='lower right')
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'model_efficiency')


def _generate_model_leaderboard(results, stats, dimensions, output_path, chart_num):
    """10. Model Leaderboard: Ranked performance table visualization."""
    models = sorted(dimensions['models'])
    
    # Calculate composite scores
    model_scores = []
    for model in models:
        model_stats = [s for s in stats if s['model_name'] == model]
        
        avg_acc = np.mean([s['accuracy'] for s in model_stats]) * 100
        avg_parse_err = np.mean([s['parse_error_rate'] for s in model_stats]) * 100
        avg_time = np.mean([s['avg_time_per_test'] for s in model_stats if s['avg_time_per_test'] > 0])
        
        # Composite score: accuracy - parse_errors - time_penalty
        composite = avg_acc - (avg_parse_err * 0.5) - (avg_time * 2)
        
        model_scores.append({
            'model': model,
            'accuracy': avg_acc,
            'parse_error': avg_parse_err,
            'speed': 1/avg_time if avg_time > 0 else 0,
            'composite': composite
        })
    
    # Sort by composite score
    model_scores.sort(key=lambda x: x['composite'], reverse=True)
    
    fig, ax = plt.subplots(figsize=(14, max(8, len(models) * 0.8)))
    
    # Create leaderboard bars
    y_pos = np.arange(len(model_scores))
    composites = [m['composite'] for m in model_scores]
    model_names = [m['model'] for m in model_scores]
    
    # Color by rank
    colors = [SUCCESS_GREEN if i < len(model_scores)//3 
             else WARNING_ORANGE if i < 2*len(model_scores)//3 
             else ERROR_RED 
             for i in range(len(model_scores))]
    
    bars = ax.barh(y_pos, composites, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # Annotations with detailed metrics
    for i, (bar, data) in enumerate(zip(bars, model_scores)):
        # Rank number
        ax.text(-5, bar.get_y() + bar.get_height()/2, f'#{i+1}',
               ha='right', va='center', fontsize=14, fontweight='bold', color='black')
        
        # Composite score
        ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2,
               f'{data["composite"]:.1f}', va='center', fontweight='bold', fontsize=11)
        
        # Detailed metrics (smaller text)
        details = f'Acc: {data["accuracy"]:.1f}% | Parse: {data["parse_error"]:.1f}% | Speed: {data["speed"]:.2f} t/s'
        ax.text(bar.get_width() / 2, bar.get_y() + bar.get_height()/2,
               details, ha='center', va='center', fontsize=8, style='italic')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(model_names)
    ax.set_xlabel('Composite Score', fontsize=12, fontweight='bold')
    ax.set_title('Model Leaderboard\\n(Score = Accuracy - 0.5×ParseErrors - 2×AvgTime)', 
                fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=1)
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'model_leaderboard')

def _generate_quantization_heatmap(results, stats, dimensions, output_path, chart_num):
    """11. Quantization Impact Heatmap: Model × Quantization level accuracy."""
    if not dimensions['quantizations']:
        print(f"  ⏭ Skipping chart {chart_num} (quantization_heatmap) - no quantization data")
        return
    
    models = sorted(dimensions['models'])
    quants = sorted(dimensions['quantizations'])
    
    # Build matrix
    matrix = np.zeros((len(models), len(quants)))
    counts = np.zeros((len(models), len(quants)))
    
    for stat in stats:
        model = stat.get('model_name')
        quant = stat.get('quantization')
        
        if model in models and quant and quant in quants:
            m_idx = models.index(model)
            q_idx = quants.index(quant)
            matrix[m_idx, q_idx] += stat.get('accuracy', 0) * 100
            counts[m_idx, q_idx] += 1
    
    # Average
    matrix = np.divide(matrix, counts, where=counts > 0, out=matrix)
    
    fig, ax = plt.subplots(figsize=(max(10, len(quants) * 1.5), max(8, len(models) * 1.2)))
    
    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    
    ax.set_xticks(np.arange(len(quants)))
    ax.set_yticks(np.arange(len(models)))
    ax.set_xticklabels(quants)
    ax.set_yticklabels(models)
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Annotate cells
    for i in range(len(models)):
        for j in range(len(quants)):
            if counts[i, j] > 0:
                ax.text(j, i, f'{matrix[i, j]:.1f}%',
                       ha="center", va="center", color="black", fontsize=10, fontweight='bold')
    
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Accuracy (%)', rotation=-90, va="bottom", fontsize=11)
    
    ax.set_title('Quantization Impact on Model Performance', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Quantization Level', fontsize=12, fontweight='bold')
    ax.set_ylabel('Model', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'quantization_heatmap')

def _generate_quantization_tradeoff(results, stats, dimensions, output_path, chart_num):
    """12. Quantization Trade-off: Quality vs efficiency scatter."""
    if not dimensions['quantizations']:
        print(f"  ⏭ Skipping chart {chart_num} (quantization_tradeoff) - no quantization data")
        return
    
    quants = sorted(dimensions['quantizations'])
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    quant_data = []
    for quant in quants:
        quant_stats = [s for s in stats if s.get('quantization') == quant]
        if quant_stats:
            avg_acc = np.mean([s['accuracy'] * 100 for s in quant_stats])
            avg_speed = np.mean([1/s['avg_time_per_test'] for s in quant_stats if s['avg_time_per_test'] > 0])
            
            quant_data.append({
                'name': quant,
                'accuracy': avg_acc,
                'speed': avg_speed
            })
    
    # Plot
    for data in quant_data:
        color = QUANTIZATION_COLORS.get(data['name'], INFO_BLUE)
        ax.scatter(data['speed'], data['accuracy'], s=500, color=color, alpha=0.7,
                  edgecolor='black', linewidth=2)
        ax.text(data['speed'], data['accuracy'], data['name'],
               ha='center', va='center', fontweight='bold', fontsize=10)
    
    ax.set_xlabel('Speed (tests/second)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('Quantization Trade-off: Accuracy vs Speed', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'quantization_tradeoff')

def _generate_quantization_distribution(results, stats, dimensions, output_path, chart_num):
    """13. Quantization Distribution: Box plots showing variance."""
    if not dimensions['quantizations']:
        print(f"  ⏭ Skipping chart {chart_num} (quantization_distribution) - no quantization data")
        return
    
    quants = sorted(dimensions['quantizations'])
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    data_for_box = []
    for quant in quants:
        quant_accuracies = [s['accuracy'] * 100 for s in stats if s.get('quantization') == quant]
        data_for_box.append(quant_accuracies)
    
    bp = ax.boxplot(data_for_box, labels=quants, patch_artist=True, notch=True)
    
    # Color boxes
    for patch, quant in zip(bp['boxes'], quants):
        patch.set_facecolor(QUANTIZATION_COLORS.get(quant, INFO_BLUE))
        patch.set_alpha(0.7)
    
    ax.set_xlabel('Quantization Level', fontsize=12, fontweight='bold')
    ax.set_ylabel('Accuracy Distribution (%)', fontsize=12, fontweight='bold')
    ax.set_title('Quantization Performance Variability', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, 105)
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'quantization_distribution')

def _generate_3d_interaction_heatmap(results, stats, dimensions, output_path, chart_num):
    """14. 3D Interaction Heatmap: Model × Task × Prompt interactions."""
    # Skip if insufficient dimensions
    if len(dimensions['models']) < 2 or len(dimensions['tasks']) < 2:
        print(f"  ⏭ Skipping chart {chart_num} (3d_interaction) - insufficient dimensions")
        return
    
    print(f"  ⏭ Skipping chart {chart_num} (3d_interaction) - complex 3D visualization not yet implemented")

def _generate_best_worst_configs(results, stats, dimensions, output_path, chart_num):
    """15. Best/Worst Configuration Finder: Top and bottom performers."""
    if len(stats) < 3:
        print(f"  ⏭ Skipping chart {chart_num} (best_worst_configs) - insufficient data")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Sort by accuracy
    sorted_stats = sorted(stats, key=lambda s: s['accuracy'], reverse=True)
    
    top_n = min(5, len(sorted_stats))
    bottom_n = min(5, len(sorted_stats))
    
    # Best performers
    best = sorted_stats[:top_n]
    best_labels = [f"{s['model_name'][:20]}\n{s.get('task_type', '')[:15]}" for s in best]
    best_scores = [s['accuracy'] * 100 for s in best]
    
    bars1 = ax1.barh(range(len(best)), best_scores, color=SUCCESS_GREEN, alpha=0.8, edgecolor='black')
    ax1.set_yticks(range(len(best)))
    ax1.set_yticklabels(best_labels, fontsize=9)
    ax1.set_xlabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax1.set_title('🏆 Top 5 Configurations', fontsize=14, fontweight='bold')
    ax1.set_xlim(0, 105)
    ax1.grid(axis='x', alpha=0.3)
    
    for bar, score in zip(bars1, best_scores):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{score:.1f}%', va='center', fontweight='bold')
    
    # Worst performers
    worst = sorted_stats[-bottom_n:][::-1]  # Reverse for display
    worst_labels = [f"{s['model_name'][:20]}\n{s.get('task_type', '')[:15]}" for s in worst]
    worst_scores = [s['accuracy'] * 100 for s in worst]
    
    bars2 = ax2.barh(range(len(worst)), worst_scores, color=ERROR_RED, alpha=0.8, edgecolor='black')
    ax2.set_yticks(range(len(worst)))
    ax2.set_yticklabels(worst_labels, fontsize=9)
    ax2.set_xlabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax2.set_title('⚠️  Bottom 5 Configurations', fontsize=14, fontweight='bold')
    ax2.set_xlim(0, 105)
    ax2.grid(axis='x', alpha=0.3)
    
    for bar, score in zip(bars2, worst_scores):
        ax2.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{score:.1f}%', va='center', fontweight='bold')
    
    fig.suptitle('Configuration Performance: Best vs Worst', fontsize=16, fontweight='bold')
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'best_worst_configs')

def _generate_error_analysis_enhanced(results, stats, dimensions, output_path, chart_num):
    """16. Enhanced Error Analysis: Parse errors vs type errors breakdown."""
    models = sorted(dimensions['models'])
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Calculate error rates per model
    model_errors = {}
    for model in models:
        model_stats = [s for s in stats if s['model_name'] == model]
        
        parse_rate = np.mean([s['parse_error_rate'] * 100 for s in model_stats])
        # Type errors (if available)
        type_rate = np.mean([s.get('type_error_rate', 0) * 100 for s in model_stats])
        success_rate = np.mean([s['success_rate'] * 100 for s in model_stats])
        
        model_errors[model] = {
            'parse': parse_rate,
            'type': type_rate,
            'success': success_rate
        }
    
    # Stacked bar chart
    x_pos = np.arange(len(models))
    width = 0.6
    
    parse_errors = [model_errors[m]['parse'] for m in models]
    type_errors = [model_errors[m]['type'] for m in models]
    success = [model_errors[m]['success'] for m in models]
    
    p1 = ax.bar(x_pos, success, width, label='Success', color=SUCCESS_GREEN, alpha=0.8, edgecolor='black')
    p2 = ax.bar(x_pos, parse_errors, width, bottom=success, 
               label='Parse Errors', color=ERROR_RED, alpha=0.8, edgecolor='black')
    p3 = ax.bar(x_pos, type_errors, width, bottom=[s+p for s,p in zip(success, parse_errors)],
               label='Type Errors', color=WARNING_ORANGE, alpha=0.8, edgecolor='black')
    
    ax.set_xlabel('Model', fontsize=12, fontweight='bold')
    ax.set_ylabel('Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_title('Error Analysis: Success vs Parse vs Type Errors', fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(models, rotation=45, ha='right')
    ax.set_ylim(0, 105)
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'error_analysis_enhanced')

def _generate_variance_analysis(results, stats, dimensions, output_path, chart_num):
    """17. Variance & Stability Analysis: Model consistency metrics."""
    models = sorted(dimensions['models'])
    
    if len(models) < 2:
        print(f"  ⏭ Skipping chart {chart_num} (variance_analysis) - insufficient models")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Calculate variance metrics per model
    model_variance = {}
    for model in models:
        model_stats = [s for s in stats if s['model_name'] == model]
        
        accuracies = [s['accuracy'] * 100 for s in model_stats]
        times = [s['avg_time_per_test'] for s in model_stats if s['avg_time_per_test'] > 0]
        
        model_variance[model] = {
            'acc_mean': np.mean(accuracies),
            'acc_std': np.std(accuracies),
            'time_mean': np.mean(times) if times else 0,
            'time_std': np.std(times) if times else 0
        }
    
    # Left: Accuracy stability
    means = [model_variance[m]['acc_mean'] for m in models]
    stds = [model_variance[m]['acc_std'] for m in models]
    
    colors = [SUCCESS_GREEN if std < 5 else WARNING_ORANGE if std < 10 else ERROR_RED for std in stds]
    
    bars1 = ax1.bar(range(len(models)), means, yerr=stds, capsize=8, 
                   color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    
    ax1.set_xticks(range(len(models)))
    ax1.set_xticklabels(models, rotation=45, ha='right')
    ax1.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Accuracy Stability (Mean ± StdDev)', fontsize=13, fontweight='bold')
    ax1.set_ylim(0, 105)
    ax1.grid(axis='y', alpha=0.3)
    
    # Add stability labels
    for i, (bar, std) in enumerate(zip(bars1, stds)):
        label = '✓ Stable' if std < 5 else '~ Variable' if std < 10 else '✗ Unstable'
        ax1.text(bar.get_x() + bar.get_width()/2, 5, label,
                ha='center', va='bottom', fontsize=8, rotation=90)
    
    # Right: Speed stability
    time_means = [model_variance[m]['time_mean'] for m in models]
    time_stds = [model_variance[m]['time_std'] for m in models]
    
    bars2 = ax2.bar(range(len(models)), time_means, yerr=time_stds, capsize=8,
                   color=INFO_BLUE, alpha=0.7, edgecolor='black', linewidth=2)
    
    ax2.set_xticks(range(len(models)))
    ax2.set_xticklabels(models, rotation=45, ha='right')
    ax2.set_ylabel('Time per Test (seconds)', fontsize=12, fontweight='bold')
    ax2.set_title('Speed Stability (Mean ± StdDev)', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    
    fig.suptitle('Model Consistency Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'variance_analysis')


def _generate_enhanced_multi_task_analysis(stats: List[Dict], output_path: Path):
    """Generate enhanced multi-task analysis visualization."""
    multi_task_stats = [s for s in stats if s.get('is_multi_task', False) and s['task_breakdown']]
    
    if not multi_task_stats:
        return
    
    # Create task performance breakdown charts
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Enhanced Multi-Task Analysis', fontsize=16, fontweight='bold')
    
    # 1. Task Accuracy Comparison (Bar Chart)
    task_types = set()
    for stat in multi_task_stats:
        task_types.update(stat['task_breakdown'].keys())
    task_types = sorted(task_types)
    
    x_pos = np.arange(len(task_types))
    width = 0.35
    
    for i, stat in enumerate(multi_task_stats):
        accuracies = [stat['task_breakdown'].get(task, {}).get('accuracy', 0) * 100 
                     for task in task_types]
        ax1.bar(x_pos + i * width, accuracies, width, 
               label=stat['model_name'], alpha=0.8)
    
    ax1.set_title('Task Accuracy Comparison', fontweight='bold')
    ax1.set_xlabel('Task Type')
    ax1.set_ylabel('Accuracy (%)')
    ax1.set_xticks(x_pos + width/2)
    ax1.set_xticklabels([t.replace('_', ' ').title() for t in task_types])
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Parse Error Rate Comparison
    for i, stat in enumerate(multi_task_stats):
        parse_rates = [stat['task_breakdown'].get(task, {}).get('parse_error_rate', 0) * 100 
                      for task in task_types]
        ax2.bar(x_pos + i * width, parse_rates, width, 
               label=stat['model_name'], alpha=0.8)
    
    ax2.set_title('Parse Error Rate by Task', fontweight='bold')
    ax2.set_xlabel('Task Type')
    ax2.set_ylabel('Parse Error Rate (%)')
    ax2.set_xticks(x_pos + width/2)
    ax2.set_xticklabels([t.replace('_', ' ').title() for t in task_types])
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Test Count Distribution
    for i, stat in enumerate(multi_task_stats):
        test_counts = [stat['task_breakdown'].get(task, {}).get('total', 0) 
                      for task in task_types]
        ax3.bar(x_pos + i * width, test_counts, width, 
               label=stat['model_name'], alpha=0.8)
    
    ax3.set_title('Test Distribution by Task', fontweight='bold')
    ax3.set_xlabel('Task Type')
    ax3.set_ylabel('Number of Tests')
    ax3.set_xticks(x_pos + width/2)
    ax3.set_xticklabels([t.replace('_', ' ').title() for t in task_types])
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Overall Performance Summary (Radar-like)
    models = [s['model_name'] for s in multi_task_stats]
    overall_acc = [s['accuracy'] * 100 for s in multi_task_stats]
    parse_err = [s['parse_error_rate'] * 100 for s in multi_task_stats]
    
    x_pos_overall = np.arange(len(models))
    
    ax4_twin = ax4.twinx()
    bars1 = ax4.bar(x_pos_overall - 0.2, overall_acc, 0.4, 
                   label='Overall Accuracy', color='green', alpha=0.7)
    bars2 = ax4_twin.bar(x_pos_overall + 0.2, parse_err, 0.4, 
                        label='Parse Error Rate', color='red', alpha=0.7)
    
    ax4.set_title('Overall Performance Summary', fontweight='bold')
    ax4.set_xlabel('Model')
    ax4.set_ylabel('Accuracy (%)', color='green')
    ax4_twin.set_ylabel('Parse Error Rate (%)', color='red')
    ax4.set_xticks(x_pos_overall)
    ax4.set_xticklabels(models, rotation=45)
    ax4.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
    
    for bar in bars2:
        height = bar.get_height()
        ax4_twin.text(bar.get_x() + bar.get_width()/2., height + 1,
                     f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    _save_figure_with_path(fig, output_path / 'enhanced_multi_task_analysis')


def _save_figure_with_path(fig, filepath: Path):
    """Save figure to specified path."""
    filepath = filepath.with_suffix('.png')
    fig.savefig(
        filepath,
        dpi=300,
        bbox_inches='tight',
        facecolor='white',
        edgecolor='none'
    )
    plt.close(fig)
    print(f"✓ Saved: {filepath}")


def _generate_accuracy_heatmap(stats: List[Dict], output_path: Path):
    """Generate accuracy heatmap for model/task comparison."""
    # Create matrix data
    models = [s['model_name'] for s in stats]
    tasks = sorted(set(s['task_type'] for s in stats))
    
    matrix_data = []
    for task in tasks:
        row = []
        for model in models:
            matching_stats = [s for s in stats if s['model_name'] == model and s['task_type'] == task]
            if matching_stats:
                row.append(matching_stats[0]['accuracy'] * 100)
            else:
                row.append(0)
        matrix_data.append(row)
    
    if not matrix_data:
        return
    
    fig, ax = plt.subplots(figsize=(max(10, len(models) * 1.5), max(6, len(tasks) * 1.5)))
    
    # Create heatmap
    im = ax.imshow(matrix_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    
    # Set ticks and labels
    ax.set_xticks(np.arange(len(models)))
    ax.set_yticks(np.arange(len(tasks)))
    ax.set_xticklabels(models)
    ax.set_yticklabels(tasks)
    
    # Rotate the tick labels and set their alignment
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('Accuracy (%)', rotation=-90, va="bottom")
    
    # Add text annotations
    for i in range(len(tasks)):
        for j in range(len(models)):
            text = ax.text(j, i, f'{matrix_data[i][j]:.1f}%', 
                          ha="center", va="center", color="black", fontweight='bold')
    
    ax.set_title('Model vs Task Accuracy Matrix', fontweight='bold', pad=20)
    plt.tight_layout()
    _save_figure_with_path(fig, output_path / 'accuracy_heatmap')


def _generate_performance_dashboard(stats: List[Dict], output_path: Path):
    """Generate comprehensive performance dashboard."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Performance Dashboard', fontsize=16, fontweight='bold')
    
    models = [s['model_name'] for s in stats]
    accuracies = [s['accuracy'] * 100 for s in stats]
    parse_errors = [s['parse_error_rate'] * 100 for s in stats]
    times = [s['avg_time_per_test'] for s in stats]
    
    # 1. Accuracy bar chart
    colors = ['green' if a >= 70 else 'orange' if a >= 30 else 'red' for a in accuracies]
    ax1.bar(models, accuracies, color=colors, alpha=0.7)
    ax1.set_title('Model Accuracy Comparison', fontweight='bold')
    ax1.set_ylabel('Accuracy (%)')
    ax1.set_ylim(0, 100)
    for i, v in enumerate(accuracies):
        ax1.text(i, v + 2, f'{v:.1f}%', ha='center', fontweight='bold')
    
    # 2. Parse error rates
    ax2.bar(models, parse_errors, color='red', alpha=0.7)
    ax2.set_title('Parse Error Rates', fontweight='bold')
    ax2.set_ylabel('Parse Error Rate (%)')
    for i, v in enumerate(parse_errors):
        ax2.text(i, v + 1, f'{v:.1f}%', ha='center', fontweight='bold')
    
    # 3. Response times
    ax3.bar(models, times, color='blue', alpha=0.7)
    ax3.set_title('Average Response Time', fontweight='bold')
    ax3.set_ylabel('Time (seconds)')
    for i, v in enumerate(times):
        ax3.text(i, v + 0.1, f'{v:.2f}s', ha='center', fontweight='bold')
    
    # 4. Success rates
    success_rates = [s['success_rate'] * 100 for s in stats]
    ax4.bar(models, success_rates, color='purple', alpha=0.7)
    ax4.set_title('Test Success Rates', fontweight='bold')
    ax4.set_ylabel('Success Rate (%)')
    ax4.set_ylim(0, 100)
    for i, v in enumerate(success_rates):
        ax4.text(i, v + 2, f'{v:.1f}%', ha='center', fontweight='bold')
    
    # Rotate x-axis labels
    for ax in [ax1, ax2, ax3, ax4]:
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    _save_figure_with_path(fig, output_path / 'performance_dashboard')


def _generate_error_analysis(stats: List[Dict], results: List[Dict], output_path: Path):
    """Generate error analysis visualization."""
    # Collect all error types across all results
    all_error_types = defaultdict(int)
    model_errors = defaultdict(lambda: defaultdict(int))
    
    for stat, result in zip(stats, results):
        model = stat['model_name']
        for r in result['results']:
            error_type = r.get('evaluation', {}).get('match_type')
            if error_type and error_type not in ['exact', 'perfect']:
                all_error_types[error_type] += 1
                model_errors[model][error_type] += 1
    
    if not all_error_types:
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('Error Analysis', fontsize=16, fontweight='bold')
    
    # 1. Overall error distribution pie chart
    error_types = list(all_error_types.keys())
    error_counts = list(all_error_types.values())
    
    ax1.pie(error_counts, labels=[et.replace('_', ' ').title() for et in error_types], 
           autopct='%1.1f%%', startangle=90)
    ax1.set_title('Overall Error Distribution')
    
    # 2. Error comparison by model
    models = list(model_errors.keys())
    error_type_list = list(all_error_types.keys())
    
    x_pos = np.arange(len(models))
    width = 0.8 / len(error_type_list) if error_type_list else 0.8
    
    for i, error_type in enumerate(error_type_list):
        counts = [model_errors[model][error_type] for model in models]
        ax2.bar(x_pos + i * width, counts, width, 
               label=error_type.replace('_', ' ').title())
    
    ax2.set_title('Error Distribution by Model')
    ax2.set_xlabel('Model')
    ax2.set_ylabel('Error Count')
    ax2.set_xticks(x_pos + width * len(error_type_list) / 2)
    ax2.set_xticklabels(models, rotation=45)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    _save_figure_with_path(fig, output_path / 'error_analysis')


def _generate_efficiency_analysis(stats: List[Dict], output_path: Path):
    """Generate time vs accuracy efficiency plot."""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    models = [s['model_name'] for s in stats]
    accuracies = [s['accuracy'] * 100 for s in stats]
    times = [s['avg_time_per_test'] for s in stats]
    
    # Create scatter plot
    scatter = ax.scatter(times, accuracies, s=100, alpha=0.7, c=range(len(models)), cmap='tab10')
    
    # Add model labels
    for i, model in enumerate(models):
        ax.annotate(model, (times[i], accuracies[i]), 
                   xytext=(5, 5), textcoords='offset points', fontsize=10)
    
    ax.set_title('Model Efficiency: Time vs Accuracy', fontweight='bold', fontsize=14)
    ax.set_xlabel('Average Time per Test (seconds)')
    ax.set_ylabel('Accuracy (%)')
    ax.grid(True, alpha=0.3)
    
    # Add efficiency quadrants
    mean_time = np.mean(times)
    mean_acc = np.mean(accuracies)
    ax.axhline(y=mean_acc, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=mean_time, color='gray', linestyle='--', alpha=0.5)
    
    # Label quadrants
    ax.text(0.02, 0.98, 'High Acc\nFast', transform=ax.transAxes, 
           verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
    ax.text(0.98, 0.98, 'High Acc\nSlow', transform=ax.transAxes, 
           verticalalignment='top', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    ax.text(0.02, 0.02, 'Low Acc\nFast', transform=ax.transAxes, 
           bbox=dict(boxstyle='round', facecolor='orange', alpha=0.7))
    ax.text(0.98, 0.02, 'Low Acc\nSlow', transform=ax.transAxes, 
           horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.7))
    
    plt.tight_layout()
    _save_figure_with_path(fig, output_path / 'efficiency_analysis')


def _generate_multi_task_analysis(stats: List[Dict], output_path: Path):
    """Generate multi-task analysis (legacy function for cross-task comparison)."""
    task_types = sorted(set(s['task_type'] for s in stats))
    models = sorted(set(s['model_name'] for s in stats))
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('Cross-Task Performance Analysis', fontsize=16, fontweight='bold')
    
    # 1. Task performance comparison
    x_pos = np.arange(len(task_types))
    width = 0.8 / len(models)
    
    for i, model in enumerate(models):
        accuracies = []
        for task in task_types:
            matching_stats = [s for s in stats if s['model_name'] == model and s['task_type'] == task]
            if matching_stats:
                accuracies.append(matching_stats[0]['accuracy'] * 100)
            else:
                accuracies.append(0)
        
        ax1.bar(x_pos + i * width, accuracies, width, label=model, alpha=0.8)
    
    ax1.set_title('Accuracy by Task Type')
    ax1.set_xlabel('Task Type')
    ax1.set_ylabel('Accuracy (%)')
    ax1.set_xticks(x_pos + width * len(models) / 2)
    ax1.set_xticklabels([t.replace('_', ' ').title() for t in task_types])
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Parse error comparison
    for i, model in enumerate(models):
        error_rates = []
        for task in task_types:
            matching_stats = [s for s in stats if s['model_name'] == model and s['task_type'] == task]
            if matching_stats:
                error_rates.append(matching_stats[0]['parse_error_rate'] * 100)
            else:
                error_rates.append(0)
        
        ax2.bar(x_pos + i * width, error_rates, width, label=model, alpha=0.8)
    
    ax2.set_title('Parse Error Rate by Task Type')
    ax2.set_xlabel('Task Type')
    ax2.set_ylabel('Parse Error Rate (%)')
    ax2.set_xticks(x_pos + width * len(models) / 2)
    ax2.set_xticklabels([t.replace('_', ' ').title() for t in task_types])
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    _save_figure_with_path(fig, output_path / 'multi_task_analysis')


def _generate_radar_comparison(stats: List[Dict], output_path: Path):
    """Generate radar chart comparison of models."""
    # Skip for now if too complex - placeholder implementation
    pass
    """Save figure to specified path."""
    filepath = filepath.with_suffix('.png')
    fig.savefig(
        filepath,
        dpi=300,
        bbox_inches='tight',
        facecolor='white',
        edgecolor='none'
    )
    plt.close(fig)
    print(f"✓ Saved: {filepath}")
    """Generate accuracy heatmap for model/task comparison."""
    # Create matrix data
    models = [s['model_name'] for s in stats]
    tasks = sorted(set(s['task_type'] for s in stats))
    
    matrix_data = []
    for task in tasks:
        row = []
        for model in models:
            matching_stats = [s for s in stats if s['model_name'] == model and s['task_type'] == task]
            if matching_stats:
                row.append(matching_stats[0]['accuracy'] * 100)
            else:
                row.append(0)
        matrix_data.append(row)
    
    if not matrix_data:
        return
    
    fig, ax = plt.subplots(figsize=(max(10, len(models) * 1.5), max(6, len(tasks) * 1.5)))
    
    sns.heatmap(
        matrix_data,
        annot=True,
        fmt='.1f',
        cmap='RdYlGn',
        center=50,
        xticklabels=models,
        yticklabels=tasks,
        cbar_kws={'label': 'Accuracy (%)'},
        ax=ax,
        linewidths=0.5,
        vmin=0,
        vmax=100
    )
    
    ax.set_title('Model Performance Heatmap', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Model', fontsize=12, fontweight='bold')
    ax.set_ylabel('Task Type', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path / 'accuracy_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Generated: accuracy_heatmap.png")


def _generate_performance_dashboard(stats: List[Dict], output_path: Path):
    """Generate comprehensive performance dashboard."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Performance Dashboard', fontsize=18, fontweight='bold', y=0.95)
    
    models = [s['model_name'] for s in stats]
    accuracies = [s['accuracy'] * 100 for s in stats]
    parse_errors = [s['parse_error_rate'] * 100 for s in stats]
    times = [s['avg_time_per_test'] for s in stats]
    
    # Subplot 1: Accuracy Bar Chart
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(models)))
    x_pos = np.arange(len(models))
    bars1 = axes[0, 0].bar(x_pos, accuracies, color=colors, alpha=0.8)
    axes[0, 0].set_title('Accuracy by Model', fontweight='bold')
    axes[0, 0].set_ylabel('Accuracy (%)')
    axes[0, 0].set_ylim(0, 100)
    axes[0, 0].set_xticks(x_pos)
    axes[0, 0].set_xticklabels(models, rotation=45, ha='right')
    
    # Add value labels
    for bar, acc in zip(bars1, accuracies):
        axes[0, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{acc:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    # Subplot 2: Parse Error Rates
    bars2 = axes[0, 1].bar(x_pos, parse_errors, color='red', alpha=0.7)
    axes[0, 1].set_title('Parse Error Rate by Model', fontweight='bold')
    axes[0, 1].set_ylabel('Parse Error Rate (%)')
    axes[0, 1].set_ylim(0, 100)
    axes[0, 1].set_xticks(x_pos)
    axes[0, 1].set_xticklabels(models, rotation=45, ha='right')
    
    for bar, err in zip(bars2, parse_errors):
        axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{err:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    # Subplot 3: Response Times
    bars3 = axes[1, 0].bar(x_pos, times, color='orange', alpha=0.8)
    axes[1, 0].set_title('Average Response Time', fontweight='bold')
    axes[1, 0].set_ylabel('Time (seconds)')
    axes[1, 0].set_xticks(x_pos)
    axes[1, 0].set_xticklabels(models, rotation=45, ha='right')
    
    for bar, time in zip(bars3, times):
        axes[1, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        f'{time:.1f}s', ha='center', va='bottom', fontweight='bold')
    
    # Subplot 4: Accuracy vs Time Scatter
    scatter = axes[1, 1].scatter(times, accuracies, s=200, c=accuracies, cmap='viridis', alpha=0.8)
    axes[1, 1].set_xlabel('Response Time (seconds)')
    axes[1, 1].set_ylabel('Accuracy (%)')
    axes[1, 1].set_title('Efficiency: Accuracy vs Time', fontweight='bold')
    
    # Add model labels
    for i, model in enumerate(models):
        axes[1, 1].annotate(model, (times[i], accuracies[i]), 
                           xytext=(5, 5), textcoords='offset points', fontsize=8)
    
    plt.colorbar(scatter, ax=axes[1, 1], label='Accuracy (%)')
    
    plt.tight_layout()
    plt.savefig(output_path / 'performance_dashboard.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Generated: performance_dashboard.png")
        


def _generate_error_analysis(stats: List[Dict], results: List[Dict], output_path: Path):
    """Generate detailed error analysis visualization."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Error Analysis', fontsize=16, fontweight='bold')
    
    models = [s['model_name'] for s in stats]
    parse_errors = [s['parse_error_rate'] * 100 for s in stats]
    accuracies = [s['accuracy'] * 100 for s in stats]
    
    # Subplot 1: Parse Error vs Accuracy
    colors = ['red' if pe > 50 else 'orange' if pe > 10 else 'green' for pe in parse_errors]
    y_pos = np.arange(len(models))
    
    bars = axes[0].barh(y_pos, parse_errors, color=colors, alpha=0.7)
    axes[0].set_xlabel('Parse Error Rate (%)')
    axes[0].set_title('Parse Error Rate by Model', fontweight='bold')
    axes[0].set_xlim(0, 100)
    axes[0].set_yticks(y_pos)
    axes[0].set_yticklabels(models)
    
    for i, (bar, pe) in enumerate(zip(bars, parse_errors)):
        axes[0].text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                    f'{pe:.1f}%', va='center', fontweight='bold')
    
    # Subplot 2: Success vs Parse Error Stacked Bar
    success_rates = [100 - pe for pe in parse_errors]
    
    axes[1].barh(y_pos, success_rates, label='Successful Parse', color='green', alpha=0.7)
    axes[1].barh(y_pos, parse_errors, left=success_rates, label='Parse Error', color='red', alpha=0.7)
    
    axes[1].set_xlabel('Percentage')
    axes[1].set_title('Parse Success vs Error Distribution', fontweight='bold')
    axes[1].legend()
    axes[1].set_xlim(0, 100)
    axes[1].set_yticks(y_pos)
    axes[1].set_yticklabels(models)
    
    plt.tight_layout()
    plt.savefig(output_path / 'error_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Generated: error_analysis.png")


def _generate_efficiency_analysis(stats: List[Dict], output_path: Path):
    """Generate efficiency analysis with performance ranges."""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    models = [s['model_name'] for s in stats]
    accuracies = [s['accuracy'] * 100 for s in stats]
    times = [s['avg_time_per_test'] for s in stats]
    
    # Create efficiency score (accuracy / time)
    efficiency_scores = [acc / max(time, 0.1) for acc, time in zip(accuracies, times)]
    
    # Bubble chart: x=time, y=accuracy, size=efficiency
    sizes = [score * 10 for score in efficiency_scores]  # Scale for visibility
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(models)))
    
    scatter = ax.scatter(times, accuracies, s=sizes, c=colors, alpha=0.7, edgecolors='black')
    
    # Add model labels
    for i, model in enumerate(models):
        ax.annotate(f'{model}\n({efficiency_scores[i]:.1f})', 
                   (times[i], accuracies[i]), 
                   xytext=(10, 10), textcoords='offset points',
                   fontsize=9, ha='left',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    ax.set_xlabel('Average Response Time (seconds)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('Model Efficiency Analysis\n(Bubble size = Accuracy/Time ratio)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    
    # Add quadrant lines
    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=np.median(times), color='gray', linestyle='--', alpha=0.5)
    
    # Add quadrant labels
    ax.text(0.02, 0.95, 'Fast & Accurate\n(Ideal)', transform=ax.transAxes, 
           bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7), fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path / 'efficiency_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Generated: efficiency_analysis.png")


def _generate_multi_task_analysis(stats: List[Dict], output_path: Path):
    """Generate multi-task performance comparison."""
    # Group by task type
    task_groups = defaultdict(list)
    for stat in stats:
        task_groups[stat['task_type']].append(stat)
    
    fig, axes = plt.subplots(1, len(task_groups), figsize=(6 * len(task_groups), 8))
    if len(task_groups) == 1:
        axes = [axes]
    
    fig.suptitle('Multi-Task Performance Analysis', fontsize=16, fontweight='bold')
    
    for i, (task_type, task_stats) in enumerate(task_groups.items()):
        models = [s['model_name'] for s in task_stats]
        accuracies = [s['accuracy'] * 100 for s in task_stats]
        
        colors = plt.cm.Set1(np.linspace(0, 1, len(models)))
        x_pos = np.arange(len(models))
        bars = axes[i].bar(x_pos, accuracies, color=colors, alpha=0.8)
        
        axes[i].set_title(f'{task_type.replace("_", " ").title()}', fontweight='bold')
        axes[i].set_ylabel('Accuracy (%)')
        axes[i].set_ylim(0, 100)
        axes[i].set_xticks(x_pos)
        axes[i].set_xticklabels(models, rotation=45, ha='right')
        
        # Add value labels
        for bar, acc in zip(bars, accuracies):
            axes[i].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{acc:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path / 'multi_task_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Generated: multi_task_analysis.png")


def _generate_radar_comparison(stats: List[Dict], output_path: Path):
    """Generate radar chart for model comparison."""
    if len(stats) < 2:
        return
    
    # Prepare metrics (normalized to 0-100)
    metrics = ['Accuracy', 'Speed', 'Reliability', 'Overall']
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]  # Complete the circle
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(stats)))
    
    for i, stat in enumerate(stats):
        # Calculate normalized metrics
        accuracy_norm = stat['accuracy'] * 100
        speed_norm = max(0, 100 - (stat['avg_time_per_test'] * 10))  # Inverse of time
        reliability_norm = 100 - (stat['parse_error_rate'] * 100)
        overall_norm = np.mean([accuracy_norm, speed_norm, reliability_norm])
        
        values = [accuracy_norm, speed_norm, reliability_norm, overall_norm]
        values += values[:1]  # Complete the circle
        
        ax.plot(angles, values, 'o-', linewidth=2, label=stat['model_name'], color=colors[i])
        ax.fill(angles, values, alpha=0.25, color=colors[i])
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, fontsize=12, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.set_title('Model Performance Radar\n(Higher values are better)', fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0))
    ax.grid(True)
    
    plt.tight_layout()
    plt.savefig(output_path / 'radar_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Generated: radar_comparison.png")


def analyze_results(result_files: List[str], **kwargs):
    """Main analysis function."""
    
    # Load all results
    print(f"Loading {len(result_files)} result files...")
    results = []
    
    for file_path in result_files:
        try:
            result = load_result_file(file_path)
            results.append(result)
        except Exception as e:
            print(f"✗ Failed to load {file_path}: {e}")
    
    if not results:
        print("No valid result files loaded.")
        return
    
    print(f"Successfully loaded {len(results)} results")
    
    # Check if grouping by model is requested
    grouped_by_model = kwargs.get('comparison', False) or kwargs.get('grouped_by_model', False)
    
    # Generate visualizations FIRST (before HTML report needs them)
    charts_dir = None
    if kwargs.get('visualize'):
        if 'output_dir' in kwargs:
            charts_dir = Path(kwargs['output_dir'])
        elif kwargs.get('output'):
            # Default: create charts directory next to the report
            output_path = Path(kwargs['output'])
            charts_dir = output_path.parent / 'charts'
        else:
            charts_dir = Path('reports/charts')
        
        # Generate charts before HTML report
        generate_visualizations(results, str(charts_dir))
    
    # Generate markdown report
    if kwargs.get('output'):
        generate_markdown_report(results, kwargs['output'], grouped_by_model=grouped_by_model)
        
        # Also generate HTML version with embedded charts
        output_path = Path(kwargs['output'])
        html_path = output_path.with_suffix('.html')
        generate_html_report(results, html_path, charts_dir, grouped_by_model=grouped_by_model)
    else:
        # Generate summary to console
        if grouped_by_model and len(results) > 1:
            # Print grouped summary
            grouped_results = group_results_by_model(results)
            model_aggregates = {name: aggregate_model_stats(files) 
                              for name, files in grouped_results.items()}
            
            print("\nModel-Grouped Summary:")
            print("=" * 80)
            for model_name, agg_stats in sorted(model_aggregates.items()):
                print(f"\n{model_name} ({agg_stats['result_count']} files):")
                print(f"  Total Tests: {agg_stats['total_tests']}")
                print(f"  Accuracy: {agg_stats['accuracy']:.1%}")
                print(f"  Parse Errors: {agg_stats['parse_error_rate']:.1%}")
                print(f"  Avg Time: {agg_stats['avg_time_per_test']:.1f}s/test")
                
                if agg_stats['task_breakdown']:
                    print("  Task Breakdown:")
                    for task_type, task_stats in sorted(agg_stats['task_breakdown'].items()):
                        print(f"    {task_type}: {task_stats['accuracy']:.1%} acc, {task_stats['total']} tests")
        else:
            # Original ungrouped summary
            stats = [extract_summary_stats(r) for r in results]
            print("\nSummary:")
            print("-" * 80)
            for stat in stats:
                print(f"{stat['model_name']} ({stat['task_type']}): "
                      f"{stat['accuracy']:.1%} accuracy, "
                      f"{stat['parse_error_rate']:.1%} parse errors, "
                      f"{stat['avg_time_per_test']:.1f}s/test")


def _generate_token_usage_chart(results, stats, dimensions, output_path, chart_num):
    """18. Token Usage Comparison: Input vs output tokens by model/task."""
    # Filter stats with token data
    token_stats = [s for s in stats if s.get('total_input_tokens', 0) > 0]
    
    if not token_stats:
        print(f"  ⏭ Skipping chart {chart_num} (token_usage) - no token data")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Determine grouping (by model or by task)
    if len(dimensions['models']) > 1:
        groups = sorted(dimensions['models'])
        group_key = 'model_name'
        title_suffix = 'by Model'
    elif len(dimensions['tasks']) > 1:
        groups = sorted(dimensions['tasks'])
        group_key = 'task_type'
        title_suffix = 'by Task'
    else:
        groups = ['All']
        group_key = None
        title_suffix = 'Overall'
    
    # Aggregate token counts per group
    input_tokens = []
    output_tokens = []
    
    for group in groups:
        if group_key:
            group_stats = [s for s in token_stats if s[group_key] == group]
        else:
            group_stats = token_stats
        
        if group_stats:
            avg_input = np.mean([s['avg_input_tokens_per_test'] for s in group_stats])
            avg_output = np.mean([s['avg_output_tokens_per_test'] for s in group_stats])
            input_tokens.append(avg_input)
            output_tokens.append(avg_output)
        else:
            input_tokens.append(0)
            output_tokens.append(0)
    
    # Left: Stacked bar chart (input + output)
    x_pos = np.arange(len(groups))
    width = 0.6
    
    bars1 = ax1.bar(x_pos, input_tokens, width, label='Input Tokens', 
                   color='#3498db', alpha=0.8, edgecolor='black', linewidth=1.5)
    bars2 = ax1.bar(x_pos, output_tokens, width, bottom=input_tokens,
                   label='Output Tokens', color='#e74c3c', alpha=0.8, 
                   edgecolor='black', linewidth=1.5)
    
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(groups, rotation=45, ha='right')
    ax1.set_ylabel('Avg Tokens per Test', fontsize=12, fontweight='bold')
    ax1.set_title(f'Token Usage {title_suffix}', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for i, (inp, out) in enumerate(zip(input_tokens, output_tokens)):
        total = inp + out
        if total > 0:
            ax1.text(i, total + max(input_tokens + output_tokens) * 0.02, 
                    f'{total:.0f}', ha='center', va='bottom', 
                    fontsize=9, fontweight='bold')
    
    # Right: Input vs Output ratio
    ratios = [out / inp if inp > 0 else 0 for inp, out in zip(input_tokens, output_tokens)]
    colors = ['#2ecc71' if r < 1 else '#f39c12' if r < 2 else '#e74c3c' for r in ratios]
    
    bars3 = ax2.bar(x_pos, ratios, width, color=colors, alpha=0.8, 
                   edgecolor='black', linewidth=1.5)
    
    ax2.axhline(y=1, color='gray', linestyle='--', linewidth=2, alpha=0.5, label='Equal I/O')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(groups, rotation=45, ha='right')
    ax2.set_ylabel('Output/Input Ratio', fontsize=12, fontweight='bold')
    ax2.set_title(f'Token Efficiency {title_suffix}', fontsize=13, fontweight='bold')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    # Add ratio labels
    for i, (bar, ratio) in enumerate(zip(bars3, ratios)):
        ax2.text(bar.get_x() + bar.get_width()/2, ratio + max(ratios) * 0.02,
                f'{ratio:.2f}x', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    fig.suptitle('Token Usage Analysis', fontsize=16, fontweight='bold')
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'token_usage')
    print(f"  ✓ Chart {chart_num}: Token usage comparison ({title_suffix})")


def _generate_token_efficiency_scatter(results, stats, dimensions, output_path, chart_num):
    """19. Token Efficiency Scatter: Correlation between tokens and accuracy."""
    # Filter stats with token data
    token_stats = [s for s in stats if s.get('total_input_tokens', 0) > 0]
    
    if not token_stats:
        print(f"  ⏭ Skipping chart {chart_num} (token_efficiency) - no token data")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Extract data
    input_tokens = [s['avg_input_tokens_per_test'] for s in token_stats]
    output_tokens = [s['avg_output_tokens_per_test'] for s in token_stats]
    total_tokens = [inp + out for inp, out in zip(input_tokens, output_tokens)]
    accuracies = [s['accuracy'] * 100 for s in token_stats]
    
    # Color by model or task
    if len(dimensions['models']) > 1:
        color_key = 'model_name'
        unique_values = sorted(dimensions['models'])
        legend_title = 'Model'
    elif len(dimensions['tasks']) > 1:
        color_key = 'task_type'
        unique_values = sorted(dimensions['tasks'])
        legend_title = 'Task'
    else:
        color_key = None
        unique_values = ['All']
        legend_title = None
    
    # Color map
    colors_map = {val: plt.cm.Set2(i) for i, val in enumerate(unique_values)}
    
    # Left: Input tokens vs accuracy
    for val in unique_values:
        if color_key:
            mask = [s[color_key] == val for s in token_stats]
        else:
            mask = [True] * len(token_stats)
        
        x = [input_tokens[i] for i, m in enumerate(mask) if m]
        y = [accuracies[i] for i, m in enumerate(mask) if m]
        
        ax1.scatter(x, y, s=100, alpha=0.6, 
                   color=colors_map[val], 
                   edgecolor='black', linewidth=1.5,
                   label=val if color_key else None)
    
    # Add trend line
    if len(input_tokens) > 2:
        z = np.polyfit(input_tokens, accuracies, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(min(input_tokens), max(input_tokens), 100)
        ax1.plot(x_trend, p(x_trend), "r--", alpha=0.8, linewidth=2, label='Trend')
        
        # Calculate correlation
        corr = np.corrcoef(input_tokens, accuracies)[0, 1]
        ax1.text(0.05, 0.95, f'Correlation: {corr:.3f}', 
                transform=ax1.transAxes, fontsize=11, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                verticalalignment='top')
    
    ax1.set_xlabel('Avg Input Tokens per Test', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Input Token Length vs Accuracy', fontsize=13, fontweight='bold')
    if color_key:
        ax1.legend(title=legend_title, loc='best')
    ax1.grid(True, alpha=0.3)
    
    # Right: Output tokens vs accuracy
    for val in unique_values:
        if color_key:
            mask = [s[color_key] == val for s in token_stats]
        else:
            mask = [True] * len(token_stats)
        
        x = [output_tokens[i] for i, m in enumerate(mask) if m]
        y = [accuracies[i] for i, m in enumerate(mask) if m]
        
        ax2.scatter(x, y, s=100, alpha=0.6,
                   color=colors_map[val],
                   edgecolor='black', linewidth=1.5,
                   label=val if color_key else None)
    
    # Add trend line
    if len(output_tokens) > 2:
        z = np.polyfit(output_tokens, accuracies, 1)
        p = np.poly1d(z)
        x_trend = np.linspace(min(output_tokens), max(output_tokens), 100)
        ax2.plot(x_trend, p(x_trend), "r--", alpha=0.8, linewidth=2, label='Trend')
        
        # Calculate correlation
        corr = np.corrcoef(output_tokens, accuracies)[0, 1]
        ax2.text(0.05, 0.95, f'Correlation: {corr:.3f}',
                transform=ax2.transAxes, fontsize=11,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                verticalalignment='top')
    
    ax2.set_xlabel('Avg Output Tokens per Test', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
    ax2.set_title('Output Token Length vs Accuracy', fontsize=13, fontweight='bold')
    if color_key:
        ax2.legend(title=legend_title, loc='best')
    ax2.grid(True, alpha=0.3)
    
    fig.suptitle('Token Efficiency Analysis: Correlation with Accuracy', 
                fontsize=16, fontweight='bold')
    plt.tight_layout()
    _save_chart(fig, output_path, chart_num, 'token_efficiency_scatter')
    print(f"  ✓ Chart {chart_num}: Token efficiency correlation analysis")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze benchmark results",
        epilog="Example: python -m src.stages.analyze_results results/**/results_*.json.gz --comparison --output reports/model_comparison.md --visualize"
    )
    parser.add_argument("results", nargs='+', help="Result files (supports glob patterns)")
    parser.add_argument("--output", help="Output markdown report path")
    parser.add_argument("--visualize", action='store_true', help="Generate visualizations")
    parser.add_argument("--output-dir", default="reports/charts", help="Visualization output dir")
    parser.add_argument("--comparison", action='store_true', 
                       help="Group results by model for unified comparison across multiple tasks and files")
    
    args = parser.parse_args()
    
    # Expand glob patterns
    result_files = []
    for pattern in args.results:
        matches = glob.glob(pattern)
        if matches:
            result_files.extend(matches)
        else:
            # Try as direct file path
            if os.path.exists(pattern):
                result_files.append(pattern)
            else:
                print(f"Warning: No files found for pattern: {pattern}")
    
    if not result_files:
        print("Error: No result files found")
        sys.exit(1)
    
    print(f"Found {len(result_files)} result files")
    
    # Check if comparison mode makes sense
    if args.comparison and len(result_files) < 2:
        print("Warning: --comparison mode is most useful with 2+ result files")
    
    analyze_results(
        result_files,
        output=args.output,
        visualize=args.visualize,
        output_dir=args.output_dir,
        comparison=args.comparison
    )


if __name__ == "__main__":
    main()