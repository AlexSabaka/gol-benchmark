#!/usr/bin/env python3
"""
Re-parse existing result files with updated parsers.

Loads .json.gz result files, re-parses raw_response fields using the
updated plugin parsers, re-evaluates, and reports before/after differences.

Usage:
    python scripts/reparse_results.py [results_dir]
    python scripts/reparse_results.py results/
"""
import gzip
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Mock heavy deps that aren't needed for parsing
import unittest.mock
for mod in ('torch', 'transformers', 'turtle', '_tkinter', 'tkinter'):
    sys.modules.setdefault(mod, unittest.mock.MagicMock())

from src.plugins import PluginRegistry
from src.plugins.base import ParsedAnswer


def load_result_file(filepath: str) -> dict:
    """Load a gzipped JSON result file."""
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        return json.load(f)


def detect_task_type(test_id: str, testset_task_type: str) -> str:
    """Detect task type from test_id or fallback to testset-level type."""
    task_patterns = {
        'arithmetic': '_arithmetic',
        'game_of_life': '_game_of_life',
        'linda_fallacy': '_linda_fallacy',
        'ascii_shapes': '_ascii_shapes',
        'cellular_automata_1d': '_cellular_automata_1d',
        'carwash': '_carwash',
        'inverted_cup': '_inverted_cup',
        'strawberry': '_strawberry',
        'measure_comparison': '_measure_comparison',
        'grid_tasks': '_grid_tasks',
        'object_tracking': '_object_tracking',
        'sally_anne': '_sally_anne',
    }
    for task_type, pattern in task_patterns.items():
        if pattern in test_id or test_id.startswith(task_type):
            return task_type
    return testset_task_type


def reparse_file(filepath: str) -> dict:
    """Re-parse a single result file and report changes."""
    data = load_result_file(filepath)
    testset_task_type = data.get('testset_metadata', {}).get('task_type', 'unknown')
    results = data.get('results', [])

    stats = defaultdict(lambda: {
        'total': 0, 'improved': 0, 'regressed': 0, 'unchanged': 0,
        'parse_changed': 0, 'old_correct': 0, 'new_correct': 0,
    })

    for r in results:
        if r.get('status') != 'success':
            continue

        test_id = r.get('test_id', '')
        task_type = detect_task_type(test_id, testset_task_type)
        raw_response = r.get('output', {}).get('raw_response', '')
        task_params = r.get('input', {}).get('task_params', {})
        old_parsed = r.get('output', {}).get('parsed_answer')
        old_correct = r.get('evaluation', {}).get('correct', False)

        if not raw_response:
            continue

        plugin = PluginRegistry.get(task_type)
        if plugin is None:
            continue

        s = stats[task_type]
        s['total'] += 1
        if old_correct:
            s['old_correct'] += 1

        try:
            parser = plugin.get_parser()
            new_parsed = parser.parse(raw_response, task_params)

            if not new_parsed.success:
                # Parser failed — keep old
                s['unchanged'] += 1
                if old_correct:
                    s['new_correct'] += 1
                continue

            # Re-evaluate
            expected = task_params.get('expected_answer') or task_params.get('expected_next_state')
            evaluator = plugin.get_evaluator()
            new_eval = evaluator.evaluate(new_parsed, expected, task_params)
            new_correct = new_eval.correct

            if new_correct:
                s['new_correct'] += 1

            # Compare
            old_val_str = str(old_parsed) if old_parsed is not None else ''
            new_val_str = str(new_parsed.value) if new_parsed.value is not None else ''
            if old_val_str != new_val_str:
                s['parse_changed'] += 1

            if old_correct and new_correct:
                s['unchanged'] += 1
            elif not old_correct and new_correct:
                s['improved'] += 1
            elif old_correct and not new_correct:
                s['regressed'] += 1
            else:
                s['unchanged'] += 1

        except Exception as e:
            s['unchanged'] += 1
            if old_correct:
                s['new_correct'] += 1

    return dict(stats)


def main():
    results_dir = sys.argv[1] if len(sys.argv) > 1 else 'results'
    result_files = []

    for root, dirs, files in os.walk(results_dir):
        for f in files:
            if f.startswith('results_') and f.endswith('.json.gz'):
                result_files.append(os.path.join(root, f))

    if not result_files:
        print(f"No result files found in {results_dir}")
        return

    print(f"Found {len(result_files)} result files\n")

    global_stats = defaultdict(lambda: {
        'total': 0, 'improved': 0, 'regressed': 0, 'unchanged': 0,
        'parse_changed': 0, 'old_correct': 0, 'new_correct': 0,
    })

    for filepath in sorted(result_files):
        fname = os.path.basename(filepath)
        try:
            file_stats = reparse_file(filepath)
            for task_type, s in file_stats.items():
                g = global_stats[task_type]
                for k in s:
                    g[k] += s[k]
            total_in_file = sum(s['total'] for s in file_stats.values())
            improved = sum(s['improved'] for s in file_stats.values())
            regressed = sum(s['regressed'] for s in file_stats.values())
            changed = sum(s['parse_changed'] for s in file_stats.values())
            if changed > 0 or improved > 0 or regressed > 0:
                print(f"  {fname}: {total_in_file} tests, {changed} parse changes, +{improved}/-{regressed}")
            else:
                print(f"  {fname}: {total_in_file} tests, no changes")
        except Exception as e:
            print(f"  {fname}: ERROR - {e}")

    print("\n" + "=" * 70)
    print("SUMMARY BY TASK TYPE")
    print("=" * 70)
    print(f"{'Task Type':<25} {'Total':>6} {'Changed':>8} {'Improved':>9} {'Regressed':>10} {'Old Acc':>8} {'New Acc':>8}")
    print("-" * 70)

    total_improved = 0
    total_regressed = 0
    total_tests = 0

    for task_type in sorted(global_stats):
        s = global_stats[task_type]
        old_acc = s['old_correct'] / s['total'] * 100 if s['total'] > 0 else 0
        new_acc = s['new_correct'] / s['total'] * 100 if s['total'] > 0 else 0
        print(f"{task_type:<25} {s['total']:>6} {s['parse_changed']:>8} {s['improved']:>+9} {s['regressed']:>10} {old_acc:>7.1f}% {new_acc:>7.1f}%")
        total_improved += s['improved']
        total_regressed += s['regressed']
        total_tests += s['total']

    print("-" * 70)
    total_old = sum(s['old_correct'] for s in global_stats.values())
    total_new = sum(s['new_correct'] for s in global_stats.values())
    old_pct = total_old / total_tests * 100 if total_tests > 0 else 0
    new_pct = total_new / total_tests * 100 if total_tests > 0 else 0
    print(f"{'TOTAL':<25} {total_tests:>6} {'':>8} {total_improved:>+9} {total_regressed:>10} {old_pct:>7.1f}% {new_pct:>7.1f}%")
    print(f"\nNet improvement: {total_improved - total_regressed:+d} tests")


if __name__ == '__main__':
    main()
