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


def generate_markdown_report(results: List[Dict], output_path: str):
    """Generate comprehensive markdown report with enhanced multi-task analysis."""
    
    # Extract stats from all results
    stats = [extract_summary_stats(r) for r in results]
    
    # Generate timestamp for consistent use
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    report = []
    report.append("# Benchmark Analysis Report\n")
    report.append(f"Generated: {timestamp}\n\n")
    
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
    report.append("| Model | Provider | Task | Tests | Accuracy | Parse Errors | Avg Time | Duration |\n")
    report.append("|-------|----------|------|-------|----------|--------------|----------|----------|\n")
    
    for stat in stats:
        model_display = f"{stat['model_name']}"
        if stat['quantization']:
            model_display += f" ({stat['quantization']})"
            
        report.append(
            f"| {model_display} | {stat['provider']} | {stat['task_type']} | "
            f"{stat['successful_tests']}/{stat['total_tests']} | "
            f"{stat['accuracy']:.1%} | {stat['parse_error_rate']:.1%} | "
            f"{stat['avg_time_per_test']:.1f}s | {stat['duration_seconds']:.0f}s |\n"
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


def generate_html_report(results: List[Dict], output_path: str, charts_dir: str = None):
    """Generate HTML version of the report with embedded charts."""
    stats = [extract_summary_stats(r) for r in results]
    
    # Generate timestamp for consistent use in both HTML and Markdown
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Benchmark Analysis Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .summary-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        .summary-table th, .summary-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        .summary-table th {{ background-color: #f2f2f2; font-weight: bold; }}
        .model-section {{ margin: 30px 0; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; }}
        .performance-metric {{ background: #f9f9f9; padding: 10px; margin: 5px 0; border-radius: 4px; }}
        .error-critical {{ background: #ffe6e6; border: 1px solid #ffcccc; padding: 15px; border-radius: 4px; margin: 10px 0; }}
        .chart-container {{ text-align: center; margin: 20px 0; }}
        .chart-container img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; font-family: 'Courier New', monospace; }}
        .accuracy-high {{ color: #27ae60; font-weight: bold; }}
        .accuracy-low {{ color: #e74c3c; font-weight: bold; }}
        .accuracy-med {{ color: #f39c12; font-weight: bold; }}
        .task-breakdown {{ margin: 15px 0; }}
        .task-breakdown table {{ border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 0.9em; }}
        .task-breakdown th, .task-breakdown td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .task-breakdown th {{ background-color: #f8f8f8; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Benchmark Analysis Report</h1>
        <p><strong>Generated:</strong> {timestamp}</p>
    </div>
"""
    
    # Summary table
    html += "    <h2>Summary</h2>\n"
    html += "    <table class='summary-table'>\n"
    html += "        <tr><th>Model</th><th>Provider</th><th>Task</th><th>Tests</th><th>Accuracy</th><th>Parse Errors</th><th>Avg Time</th><th>Duration</th></tr>\n"
    
    for stat in stats:
        model_display = f"{stat['model_name']}"
        if stat['quantization']:
            model_display += f" ({stat['quantization']})"
        
        # Color-code accuracy
        acc_class = "accuracy-high" if stat['accuracy'] > 0.7 else "accuracy-low" if stat['accuracy'] < 0.3 else "accuracy-med"
        
        html += f"        <tr>"
        html += f"<td>{model_display}</td>"
        html += f"<td>{stat['provider']}</td>"
        html += f"<td>{stat['task_type']}</td>"
        html += f"<td>{stat['successful_tests']}/{stat['total_tests']}</td>"
        html += f"<td class='{acc_class}'>{stat['accuracy']:.1%}</td>"
        html += f"<td>{stat['parse_error_rate']:.1%}</td>"
        html += f"<td>{stat['avg_time_per_test']:.1f}s</td>"
        html += f"<td>{stat['duration_seconds']:.0f}s</td>"
        html += f"</tr>\n"
    
    html += "    </table>\n"
    
    # Multi-task performance overview if applicable
    multi_task_results = [s for s in stats if s.get('is_multi_task', False)]
    if multi_task_results:
        html += "    <h2>Multi-Task Performance Overview</h2>\n"
        for stat in stats:
            if stat['task_breakdown']:
                html += f"    <h3>{stat['model_name']} Task Breakdown</h3>\n"
                html += "    <div class='task-breakdown'>\n"
                html += "        <table>\n"
                html += "            <tr><th>Task Type</th><th>Tests</th><th>Accuracy</th><th>Parse Errors</th></tr>\n"
                for task_type, task_stats in stat['task_breakdown'].items():
                    html += f"            <tr>"
                    html += f"<td>{task_type.replace('_', ' ').title()}</td>"
                    html += f"<td>{task_stats['total']}</td>"
                    html += f"<td>{task_stats['accuracy']:.1%}</td>"
                    html += f"<td>{task_stats['parse_error_rate']:.1%}</td>"
                    html += f"</tr>\n"
                html += "        </table>\n"
                html += "    </div>\n"
    
    # Include charts if available
    if charts_dir and Path(charts_dir).exists():
        chart_files = list(Path(charts_dir).glob('*.png'))
        if chart_files:
            html += "    <h2>Visualizations</h2>\n"
            for chart_file in sorted(chart_files):
                chart_name = chart_file.stem.replace('_', ' ').title()
                # Calculate relative path from HTML file to chart
                html_dir = Path(output_path).parent
                try:
                    rel_path = chart_file.relative_to(html_dir)
                except ValueError:
                    # If relative path fails, use just the chart name (assumes same directory)
                    rel_path = chart_file.name
                html += f"    <div class='chart-container'>\n"
                html += f"        <h3>{chart_name}</h3>\n"
                html += f"        <img src='{rel_path}' alt='{chart_name}'>\n"
                html += f"    </div>\n"
    
    # Detailed sections
    for i, (result, stat) in enumerate(zip(results, stats)):
        html += f"    <div class='model-section'>\n"
        html += f"        <h2>{stat['model_name']} - {stat['task_type']}</h2>\n"
        html += f"        <p><strong>Testset:</strong> {stat['testset_name']}</p>\n"
        html += f"        <p><strong>Provider:</strong> {stat['provider']}</p>\n"
        if stat['quantization']:
            html += f"        <p><strong>Quantization:</strong> {stat['quantization']}</p>\n"
        html += f"        <p><strong>Execution:</strong> {stat['created_at'][:19]} on {stat['hostname']}</p>\n"
        
        # Performance metrics
        html += f"        <h3>Performance</h3>\n"
        acc_class = "accuracy-high" if stat['accuracy'] > 0.7 else "accuracy-low" if stat['accuracy'] < 0.3 else "accuracy-med"
        html += f"        <div class='performance-metric'><strong>Accuracy:</strong> <span class='{acc_class}'>{stat['accuracy']:.2%}</span> ({stat['correct_responses']}/{stat['successful_tests']})</div>\n"
        html += f"        <div class='performance-metric'><strong>Parse Error Rate:</strong> {stat['parse_error_rate']:.2%} ({stat['parse_errors']}/{stat['successful_tests']})</div>\n"
        html += f"        <div class='performance-metric'><strong>Success Rate:</strong> {stat['success_rate']:.2%} ({stat['successful_tests']}/{stat['total_tests']})</div>\n"
        
        if stat['avg_cell_accuracy'] is not None:
            html += f"        <div class='performance-metric'><strong>Cell-level Accuracy:</strong> {stat['avg_cell_accuracy']:.2%}</div>\n"
        
        html += f"        <div class='performance-metric'><strong>Average Time per Test:</strong> {stat['avg_time_per_test']:.2f} seconds</div>\n"
        html += f"        <div class='performance-metric'><strong>Total Duration:</strong> {stat['duration_seconds']:.1f} seconds</div>\n"
        
        # Task breakdown for multi-task results
        if stat.get('is_multi_task', False) and stat['task_breakdown']:
            html += f"        <h3>Task-Specific Performance</h3>\n"
            html += "        <div class='task-breakdown'>\n"
            html += "            <table>\n"
            html += "                <tr><th>Task Type</th><th>Tests</th><th>Accuracy</th><th>Parse Errors</th></tr>\n"
            for task_type, task_stats in stat['task_breakdown'].items():
                html += f"                <tr>"
                html += f"<td>{task_type.replace('_', ' ').title()}</td>"
                html += f"<td>{task_stats['total']}</td>"
                html += f"<td>{task_stats['accuracy']:.1%}</td>"
                html += f"<td>{task_stats['parse_error_rate']:.1%}</td>"
                html += f"</tr>\n"
            html += "        </div>\n"
        
        # Error analysis matching Markdown structure
        if stat['parse_errors'] > 0 or stat['type_errors'] > 0:
            html += "        <h3>Error Analysis</h3>\n"
            
            error_types = defaultdict(int)
            for r in result['results']:
                error_type = r.get('evaluation', {}).get('match_type')
                if error_type and error_type not in ['exact', 'perfect']:
                    error_types[error_type] += 1
            
            html += "        <ul>\n"
            for error_type, count in error_types.items():
                rate = count / max(stat['successful_tests'], 1) * 100
                html += f"            <li><strong>{error_type.replace('_', ' ').title()}</strong>: {count} ({rate:.1f}%)</li>\n"
            html += "        </ul>\n"
            
            # Add specific handling for 100% parse errors
            if stat['parse_error_rate'] >= 1.0:
                html += "        <div class='error-critical'>\n"
                html += "            <h4>⚠️ Critical Issue: 100% Parse Errors</h4>\n"
                html += "            <p>All responses failed to parse. This typically indicates:</p>\n"
                html += "            <ul>\n"
                html += "                <li>Model output format doesn't match expected pattern</li>\n"
                html += "                <li>Prompt engineering may need adjustment</li>\n"
                html += "                <li>Model may require different parsing approach</li>\n"
                html += "            </ul>\n"
                html += "        </div>\n"
        
        # Sample responses (first few) matching Markdown structure
        sample_results = result['results'][:3]
        if sample_results:
            html += "        <h3>Sample Results</h3>\n"
            for j, sample in enumerate(sample_results):
                html += f"        <h4>Test {j+1} (<code>{sample['test_id']}</code>)</h4>\n"
                html += "        <ul>\n"
                html += f"            <li><strong>Input:</strong> <code>{sample['input']['user_prompt'][:100]}...</code></li>\n"
                if sample['status'] == 'success':
                    expected = sample['input']['task_params'].get('expected_answer', 'N/A')
                    parsed = sample['output']['parsed_answer']
                    correct = sample['evaluation']['correct']
                    html += f"            <li><strong>Expected:</strong> <code>{expected}</code></li>\n"
                    html += f"            <li><strong>Parsed:</strong> <code>{parsed}</code></li>\n"
                    html += f"            <li><strong>Correct:</strong> {correct}</li>\n"
                else:
                    error_msg = sample.get('error', 'Unknown')
                    html += f"            <li><strong>Error:</strong> <code>{error_msg}</code></li>\n"
                html += "        </ul>\n"
        
        html += "    </div>\n"
        
        # Add separator between models except for the last one
        if i < len(results) - 1:
            html += "    <hr style='margin: 40px 0; border: none; border-top: 2px solid #e0e0e0;'>\n"
    
    html += "</body>\n</html>"
    
    # Write HTML report
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"✓ HTML report saved: {output_path}")


def generate_visualizations(results: List[Dict], output_dir: str):
    """Generate comprehensive visualization suite."""
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
    
    print(f"Generating {len(stats)} model visualizations...")
    
    # Set style for all plots
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (14, 8)
    plt.rcParams['font.size'] = 11
    plt.rcParams['font.family'] = 'sans-serif'
    
    # 1. Accuracy Comparison Matrix (Heatmap)
    if len(stats) > 1:
        _generate_accuracy_heatmap(stats, output_path)
    
    # 2. Performance Overview Dashboard
    _generate_performance_dashboard(stats, output_path)
    
    # 3. Error Analysis Breakdown
    _generate_error_analysis(stats, results, output_path)
    
    # 4. Time vs Accuracy Efficiency Plot
    _generate_efficiency_analysis(stats, output_path)
    
    # 5. Enhanced Task-specific Analysis (if multi-task or cross-task comparison)
    multi_task_results = [s for s in stats if s.get('is_multi_task', False)]
    if multi_task_results:
        _generate_enhanced_multi_task_analysis(stats, output_path)
    elif len(set(s['task_type'] for s in stats)) > 1:
        _generate_multi_task_analysis(stats, output_path)
    
    # 6. Model Comparison Radar Chart
    if len(stats) > 1:
        _generate_radar_comparison(stats, output_path)
    
    print(f"✓ Visualizations saved to: {output_dir}")


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
    
    # Generate markdown report
    if kwargs.get('output'):
        generate_markdown_report(results, kwargs['output'])
        
        # Also generate HTML version if requested
        output_path = Path(kwargs['output'])
        html_path = output_path.with_suffix('.html')
        
        # For charts directory, create it relative to the output HTML file
        if kwargs.get('visualize'):
            # If output_dir is specified, create charts subdirectory within the same parent
            if 'output_dir' in kwargs:
                charts_dir = Path(kwargs['output_dir'])
            else:
                # Default: create charts directory next to the HTML report
                charts_dir = output_path.parent / 'charts'
        else:
            charts_dir = None
            
        generate_html_report(results, html_path, charts_dir)
    else:
        # Generate summary to console
        stats = [extract_summary_stats(r) for r in results]
        print("\\nSummary:")
        print("-" * 80)
        for stat in stats:
            print(f"{stat['model_name']} ({stat['task_type']}): "
                  f"{stat['accuracy']:.1%} accuracy, "
                  f"{stat['parse_error_rate']:.1%} parse errors, "
                  f"{stat['avg_time_per_test']:.1f}s/test")
    
    # Generate visualizations
    if kwargs.get('visualize'):
        generate_visualizations(results, kwargs.get('output_dir', 'reports/charts'))


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze benchmark results")
    parser.add_argument("results", nargs='+', help="Result files (supports glob patterns)")
    parser.add_argument("--output", help="Output markdown report path")
    parser.add_argument("--visualize", action='store_true', help="Generate visualizations")
    parser.add_argument("--output-dir", default="reports/charts", help="Visualization output dir")
    parser.add_argument("--comparison", action='store_true', help="Multi-model comparison mode")
    
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
    
    analyze_results(
        result_files,
        output=args.output,
        visualize=args.visualize,
        output_dir=args.output_dir,
        comparison=args.comparison
    )


if __name__ == "__main__":
    main()