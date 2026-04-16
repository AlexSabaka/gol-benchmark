"""Reanalysis utilities — re-parse and re-evaluate result files using current plugins."""
from __future__ import annotations

import gzip
import json
import os
import tempfile
from pathlib import Path

from src.plugins import PluginRegistry
from src.plugins.base import ParsedAnswer


# ── Task-type inference ──────────────────────────────────────────────────

# Task types removed from the plugin system that may still appear in old result files.
_LEGACY_TASK_TYPE_SUFFIXES = ["fancy_unicode"]

# Derived from the plugin registry so new plugins are automatically included.
# Sorted longest-first so specific names (e.g. "time_arithmetic") match before
# shorter names they contain (e.g. "arithmetic").
_TASK_TYPE_SUFFIXES: list = sorted(
    PluginRegistry.list_task_types() + [t for t in _LEGACY_TASK_TYPE_SUFFIXES if t not in PluginRegistry.list_task_types()],
    key=len,
    reverse=True,
)


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


def _get_expected_answer(task_params: dict):
    """Get expected_answer with explicit None check (Bug 1 fix)."""
    expected = task_params.get("expected_answer")
    if expected is None:
        expected = task_params.get("expected_next_state")
    return expected


def reparse_and_eval(raw_response: str, task_type: str, task_params: dict, expected_answer) -> dict | None:
    """Re-parse and re-evaluate using current plugin parser+evaluator."""
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
        return d
    except Exception as e:
        return {"_error": str(e)}


# ── File-level reanalysis ────────────────────────────────────────────────

def reanalyze_result_file(filepath: Path) -> dict:
    """Load a result .json.gz, re-parse+re-evaluate all entries, save atomically.

    Returns dict with {filename, total_results, changes, old_accuracy, new_accuracy}.
    """
    with gzip.open(str(filepath), "rt", encoding="utf-8") as f:
        data = json.load(f)

    testset_task_type = data.get("testset_metadata", {}).get("task_type")
    results = data.get("results", [])
    old_stats = data.get("summary_statistics", {})
    old_accuracy = old_stats.get("accuracy", 0)

    changes = 0
    correct_count = 0
    total_evaluated = 0

    for r in results:
        if r.get("status") != "success":
            continue

        total_evaluated += 1
        test_id = r.get("test_id", "")
        task_params = r.get("input", {}).get("task_params", {})
        prompt_metadata = r.get("input", {}).get("prompt_metadata", {})
        raw_response = r.get("output", {}).get("raw_response", "")
        original_eval = r.get("evaluation", {})
        orig_correct = original_eval.get("correct", False)

        # Infer task type
        task_type = task_params.get("task_type") or infer_task_type(test_id, testset_task_type)
        if not task_type:
            if orig_correct:
                correct_count += 1
            continue

        # Ensure sub_type
        sub_type = infer_sub_type(task_type, task_params)
        enriched_params = dict(task_params)
        # Merge prompt_metadata so parser gets language, user_style, etc.
        if prompt_metadata:
            for key in ("language", "user_style", "system_style"):
                if key in prompt_metadata and key not in enriched_params:
                    enriched_params[key] = prompt_metadata[key]
        if sub_type and "sub_type" not in enriched_params:
            enriched_params["sub_type"] = sub_type

        expected = _get_expected_answer(enriched_params)
        new_eval = reparse_and_eval(raw_response, task_type, enriched_params, expected)

        if new_eval is None or "_error" in new_eval:
            if orig_correct:
                correct_count += 1
            continue

        new_correct = new_eval.get("correct", False)
        if new_correct:
            correct_count += 1

        if new_correct != orig_correct:
            changes += 1

        # Always update with fresh parse/eval results
        write_eval = {k: v for k, v in new_eval.items() if not k.startswith("_")}
        r["evaluation"] = write_eval
        if new_eval.get("_parsed_value") is not None:
            r["output"]["parsed_answer"] = new_eval["_parsed_value"]
        # Persist strategy + confidence so the Human Review aggregator can
        # attribute parser_false_positive cases to the strategy that fired.
        if new_eval.get("_parse_strategy") is not None:
            r["output"]["parse_strategy"] = new_eval["_parse_strategy"]
        if new_eval.get("_confidence") is not None:
            r["output"]["parse_confidence"] = new_eval["_confidence"]

    # Recalculate summary statistics
    new_accuracy = correct_count / total_evaluated if total_evaluated > 0 else 0
    data.setdefault("summary_statistics", {})["accuracy"] = new_accuracy
    data["summary_statistics"]["correct_responses"] = correct_count

    # Recalculate parse error rate
    parse_errors = sum(
        1 for r in results
        if r.get("status") == "success"
        and r.get("output", {}).get("parsed_answer") is None
    )
    data["summary_statistics"]["parse_error_rate"] = (
        parse_errors / total_evaluated if total_evaluated > 0 else 0
    )

    # Atomic write: temp file + rename
    fd, tmp_path = tempfile.mkstemp(suffix=".json.gz", dir=filepath.parent)
    try:
        os.close(fd)
        with gzip.open(tmp_path, "wt", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp_path, str(filepath))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return {
        "filename": filepath.name,
        "total_results": total_evaluated,
        "changes": changes,
        "old_accuracy": old_accuracy,
        "new_accuracy": new_accuracy,
    }
