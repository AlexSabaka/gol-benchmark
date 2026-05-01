#!/usr/bin/env python3
"""
Re-analyze all results files using the current (fixed) plugin parsers and evaluators.

Identifies false negatives caused by:
  Bug 1: Falsy expected_answer (0, False) silently dropped by `or` operator
         → detected by re-evaluating with the ORIGINAL parsed_answer + fixed expected_answer
  Bug 2/3: Boolean parser last-keyword extracting contextual words
         → detected by re-parsing strawberry boolean responses only

Usage:
    python reanalyze_results.py [results_dir]
    python reanalyze_results.py --fix               # overwrite results with corrected evaluations
    python reanalyze_results.py --reparse-all       # re-parse ALL responses (shows full diff vs current parsers)
"""

import argparse
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.plugins import PluginRegistry
from src.plugins.base import ParsedAnswer


# ── Task-type inference ───────────────────────────────────────────────────

_TASK_TYPE_SUFFIXES = [
    "strawberry", "measure_comparison", "carwash", "inverted_cup",
    "object_tracking", "sally_anne", "time_arithmetic", "game_of_life",
    "arithmetic", "linda_fallacy", "cellular_automata_1d", "ascii_shapes",
    "grid_tasks", "misquote", "false_premise", "family_relations",
    "encoding_cipher", "symbol_arithmetic", "picross",
]


def infer_task_type(test_id: str, testset_task_type: str | None) -> str | None:
    """Infer the task type from test_id or testset metadata."""
    if testset_task_type and testset_task_type != "multi-task":
        return testset_task_type
    for suffix in _TASK_TYPE_SUFFIXES:
        if test_id.endswith(f"_{suffix}") or f"_{suffix}_" in test_id:
            return suffix
    for suffix in _TASK_TYPE_SUFFIXES:
        if test_id.startswith(f"{suffix}_"):
            return suffix
    return None


def infer_sub_type(task_type: str, task_params: dict) -> str | None:
    """Infer sub_type from task_params when not explicitly stored."""
    if task_params.get("sub_type"):
        return task_params["sub_type"]
    if task_type == "strawberry":
        if "letter" in task_params and "word" in task_params:
            return "count"
        if "word1" in task_params and "word2" in task_params:
            return "anagram"
        if "sentence" in task_params and "missing_letters" in task_params:
            return "pangram"
        if "sentence" in task_params and "avoided_letter" in task_params:
            return "lipogram"
        if "n" in task_params and "word" in task_params:
            return "nth_letter"
        if "word" in task_params and "letter" not in task_params and "n" not in task_params:
            return "reverse"
    return None


def _get_expected_answer_fixed(task_params: dict):
    """Get expected_answer with the Bug 1 fix (explicit None check)."""
    expected = task_params.get("expected_answer")
    if expected is None:
        expected = task_params.get("expected_next_state")
    return expected


def _get_expected_answer_buggy(task_params: dict):
    """Get expected_answer using the old buggy `or` logic."""
    return task_params.get("expected_answer") or task_params.get("expected_next_state")


# ── Re-evaluation strategies ─────────────────────────────────────────────

def eval_only(parsed_answer_value, task_type: str, task_params: dict, expected_answer) -> dict | None:
    """Re-evaluate using the ORIGINAL parsed_answer (no re-parsing).

    Isolates Bug 1: the falsy expected_answer issue.
    """
    plugin = PluginRegistry.get(task_type)
    if plugin is None:
        return None
    try:
        pa = ParsedAnswer(
            value=parsed_answer_value,
            raw_response="",
            parse_strategy="original",
        )
        evaluator = plugin.get_evaluator()
        result = evaluator.evaluate(pa, expected_answer, task_params)
        d = result.to_dict()
        d["_parsed_value"] = parsed_answer_value
        d["_parse_strategy"] = "original"
        d["_bug"] = "bug1_falsy_expected"
        return d
    except Exception as e:
        return {"_error": str(e)}


def reparse_and_eval(raw_response: str, task_type: str, task_params: dict, expected_answer) -> dict | None:
    """Re-parse and re-evaluate using current plugin parser.

    Catches Bug 2/3: parser improvements.
    """
    plugin = PluginRegistry.get(task_type)
    if plugin is None:
        return None
    try:
        parser = plugin.get_parser()
        parsed = parser.parse(raw_response, task_params)
        evaluator = plugin.get_evaluator()
        result = evaluator.evaluate(parsed, expected_answer, task_params)
        d = result.to_dict()
        d["_parsed_value"] = parsed.value
        d["_parse_strategy"] = parsed.parse_strategy
        d["_confidence"] = parsed.confidence
        d["_bug"] = "bug2_3_parser"
        return d
    except Exception as e:
        return {"_error": str(e)}


# ── File analysis ─────────────────────────────────────────────────────────

def analyze_file(filepath: Path, fix: bool = False, reparse_all: bool = False) -> dict:
    """Re-analyze a single results file."""
    with gzip.open(filepath, "rt") as f:
        data = json.load(f)

    testset_task_type = data.get("testset_metadata", {}).get("task_type")
    model = data.get("model_info", {}).get("model_name", "unknown")
    results = data.get("results", [])

    stats = {
        "file": filepath.name,
        "model": model,
        "total": 0,
        "re_evaluated": 0,
        "false_negatives_fixed": 0,
        "false_positives_found": 0,
        "unchanged": 0,
        "skipped": 0,
        "corrections": [],
    }

    modified = False

    for r in results:
        if r.get("status") != "success":
            continue

        stats["total"] += 1
        test_id = r.get("test_id", "")
        task_params = r.get("input", {}).get("task_params", {})
        raw_response = r.get("output", {}).get("raw_response", "")
        original_parsed = r.get("output", {}).get("parsed_answer")
        original_eval = r.get("evaluation", {})
        orig_correct = original_eval.get("correct", False)
        orig_match_type = original_eval.get("match_type", "")

        # Infer task type
        task_type = task_params.get("task_type") or infer_task_type(test_id, testset_task_type)
        if not task_type:
            stats["skipped"] += 1
            continue

        # Ensure sub_type
        sub_type = infer_sub_type(task_type, task_params)
        enriched_params = dict(task_params)
        if sub_type and "sub_type" not in enriched_params:
            enriched_params["sub_type"] = sub_type

        # Fixed expected_answer
        expected_fixed = _get_expected_answer_fixed(enriched_params)
        expected_buggy = _get_expected_answer_buggy(enriched_params)

        new_eval = None
        bug_label = None

        # ── Strategy 1: Bug 1 detection (falsy expected_answer) ──
        # If the old `or` logic would produce a different expected_answer,
        # this result was affected by Bug 1.
        if expected_fixed is not None and expected_buggy is None and expected_fixed != expected_buggy:
            new_eval = eval_only(original_parsed, task_type, enriched_params, expected_fixed)
            bug_label = "bug1_falsy_expected"

        # ── Strategy 2: Bug 2/3 detection (strawberry boolean parser) ──
        # Re-parse strawberry boolean sub-types where the original was wrong
        elif (task_type == "strawberry"
              and sub_type in ("anagram", "pangram", "lipogram")
              and not orig_correct):
            new_eval = reparse_and_eval(raw_response, task_type, enriched_params, expected_fixed)
            bug_label = "bug2_3_parser"

        # ── Strategy 3: match_type "unknown" (plugin eval failed) ──
        # Even if expected wasn't falsy, the plugin eval may have thrown
        elif orig_match_type == "unknown":
            new_eval = reparse_and_eval(raw_response, task_type, enriched_params, expected_fixed)
            bug_label = "eval_unknown"

        # ── Strategy 4 (optional): full re-parse everything ──
        elif reparse_all and not orig_correct:
            new_eval = reparse_and_eval(raw_response, task_type, enriched_params, expected_fixed)
            bug_label = "reparse_all"

        if new_eval is None or "_error" in new_eval:
            if new_eval and "_error" in new_eval and bug_label:
                stats["skipped"] += 1
            else:
                stats["unchanged"] += 1
            continue

        stats["re_evaluated"] += 1
        new_correct = new_eval.get("correct", False)

        if orig_correct == new_correct:
            stats["unchanged"] += 1
        elif not orig_correct and new_correct:
            stats["false_negatives_fixed"] += 1
            correction = {
                "test_id": test_id,
                "task_type": task_type,
                "sub_type": sub_type,
                "type": "false_negative",
                "bug": bug_label,
                "original_match_type": orig_match_type,
                "new_match_type": new_eval.get("match_type"),
                "parsed_answer": original_parsed,
                "new_parsed": new_eval.get("_parsed_value"),
                "expected_answer": expected_fixed,
                "parse_strategy": new_eval.get("_parse_strategy"),
            }
            stats["corrections"].append(correction)
            if fix:
                write_eval = {k: v for k, v in new_eval.items() if not k.startswith("_")}
                r["evaluation"] = write_eval
                if new_eval.get("_parsed_value") is not None:
                    r["output"]["parsed_answer"] = new_eval["_parsed_value"]
                modified = True
        elif orig_correct and not new_correct:
            stats["false_positives_found"] += 1
            correction = {
                "test_id": test_id,
                "task_type": task_type,
                "sub_type": sub_type,
                "type": "regression",
                "bug": bug_label,
                "original_match_type": orig_match_type,
                "new_match_type": new_eval.get("match_type"),
                "parsed_answer": original_parsed,
                "new_parsed": new_eval.get("_parsed_value"),
                "expected_answer": expected_fixed,
                "parse_strategy": new_eval.get("_parse_strategy"),
            }
            stats["corrections"].append(correction)

    if fix and modified:
        with gzip.open(filepath, "wt") as f:
            json.dump(data, f)

    return stats


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Re-analyze results files with fixed parsers/evaluators"
    )
    ap.add_argument(
        "results_dir", nargs="?", default="results",
        help="Directory containing results .json.gz files (default: results/)",
    )
    ap.add_argument("--fix", action="store_true", help="Overwrite results with corrections")
    ap.add_argument("--reparse-all", action="store_true",
                    help="Re-parse ALL incorrect responses (shows full diff vs current parsers)")
    ap.add_argument("--verbose", "-v", action="store_true", help="Per-correction details")
    args = ap.parse_args()

    results_dir = Path(args.results_dir)
    if not results_dir.is_dir():
        print(f"Error: {results_dir} is not a directory")
        sys.exit(1)

    files = sorted(results_dir.glob("*.json.gz"))
    if not files:
        print(f"No .json.gz files found in {results_dir}")
        sys.exit(1)

    totals = defaultdict(int)
    all_corrections = []

    mode = "targeted (Bug 1 + Bug 2/3 + unknown match_type)"
    if args.reparse_all:
        mode = "full re-parse of all incorrect results"
    print(f"Re-analyzing {len(files)} results files in {results_dir}/")
    print(f"  Mode: {mode}")
    if args.fix:
        print("  ** FIX MODE: results files will be updated **")
    print()

    for filepath in files:
        try:
            stats = analyze_file(filepath, fix=args.fix, reparse_all=args.reparse_all)
        except Exception as e:
            print(f"  ERROR: {filepath.name}: {e}")
            continue

        for key in ("total", "re_evaluated", "false_negatives_fixed",
                     "false_positives_found", "unchanged", "skipped"):
            totals[key] += stats[key]
        all_corrections.extend(stats["corrections"])

        if stats["false_negatives_fixed"] > 0 or stats["false_positives_found"] > 0:
            fn = stats["false_negatives_fixed"]
            fp = stats["false_positives_found"]
            label = []
            if fn: label.append(f"+{fn} FN fixed")
            if fp: label.append(f"-{fp} regressions")
            print(f"  {stats['file'][:80]}: {', '.join(label)}")

    # ── Summary ───────────────────────────────────────────────────────

    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(f"  Files scanned:          {len(files)}")
    print(f"  Total results:          {totals['total']}")
    print(f"  Re-evaluated:           {totals['re_evaluated']}")
    print(f"  Skipped:                {totals['skipped']}")
    print(f"  Unchanged:              {totals['unchanged']}")
    print()
    print(f"  FALSE NEGATIVES FIXED:  {totals['false_negatives_fixed']}")
    print(f"  REGRESSIONS:            {totals['false_positives_found']}")
    print()

    if all_corrections:
        # By bug type
        by_bug = defaultdict(lambda: {"false_negative": 0, "regression": 0})
        for c in all_corrections:
            by_bug[c.get("bug", "?")][c["type"]] += 1

        print("By root cause:")
        for bug, counts in sorted(by_bug.items()):
            parts = []
            if counts["false_negative"]: parts.append(f"{counts['false_negative']} FN")
            if counts["regression"]: parts.append(f"{counts['regression']} regressions")
            print(f"  {bug:30s} {', '.join(parts)}")

        # By task type
        by_task = defaultdict(lambda: {"false_negative": 0, "regression": 0})
        for c in all_corrections:
            by_task[c["task_type"]][c["type"]] += 1

        print()
        print("By task type:")
        for task, counts in sorted(by_task.items()):
            parts = []
            if counts["false_negative"]: parts.append(f"{counts['false_negative']} FN")
            if counts["regression"]: parts.append(f"{counts['regression']} regressions")
            print(f"  {task:30s} {', '.join(parts)}")

        # By original match_type (for FN only)
        by_match = defaultdict(int)
        for c in all_corrections:
            if c["type"] == "false_negative":
                by_match[c.get("original_match_type", "?")] += 1
        if by_match:
            print()
            print("FN fixes by original match_type:")
            for mt, count in sorted(by_match.items(), key=lambda x: -x[1]):
                print(f"  {mt:30s} {count}")

        if args.verbose:
            print()
            print("Detailed corrections:")
            print("-" * 72)
            for c in all_corrections:
                print(f"  [{c['type'].upper():14s}] {c['test_id']}")
                print(f"    task={c['task_type']}, sub={c.get('sub_type')}, bug={c.get('bug')}")
                print(f"    match_type: {c['original_match_type']} → {c['new_match_type']}")
                print(f"    parsed: {c['parsed_answer']} → {c.get('new_parsed')}, "
                      f"expected: {c['expected_answer']}")
                print()

    if args.fix and totals["false_negatives_fixed"] > 0:
        print(f"Done — {totals['false_negatives_fixed']} results corrected in-place.")
    elif totals["false_negatives_fixed"] > 0:
        print(f"Run with --fix to apply corrections to results files.")


if __name__ == "__main__":
    main()
