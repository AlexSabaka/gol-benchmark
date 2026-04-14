"""LLM-as-a-Judge worker — classifies incorrect model responses.

Runs each incorrect result through a judge LLM to determine if it's a
true incorrect, false negative, or parser failure.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import tempfile
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional


# ── Default prompts ──────────────────────────────────────────────────────

DEFAULT_SYSTEM_PROMPT = """You are an evaluation auditor reviewing model responses that were marked INCORRECT by an automated scoring pipeline. Your job is to determine WHY each response was marked incorrect.

You will receive:
- QUESTION: the original prompt given to the model
- RESPONSE: the model's full raw response
- PARSED: what the automated parser extracted as the model's answer
- EXPECTED: the ground-truth correct answer

## Your task

Classify each case into exactly one verdict:

**true_incorrect** — The model's reasoning and/or final answer is genuinely wrong. The expected answer is correct and the model failed to reach it.

**false_negative** — The model actually produced a correct or defensibly correct answer, but the scorer marked it wrong (e.g. the expected answer is too strict, the model's answer is equivalent but phrased differently, or the task has multiple valid answers).

**parser_failure** — The model's response contains the correct answer (or clearly implies it), but the parser extracted the wrong token. The model itself is not at fault; the extraction logic failed.

## Parser issue types
If verdict is `parser_failure`, also classify the failure mode:

- `format_mismatch` — answer is present but in an unexpected format (e.g. "twelve" vs "12", "12:23am" vs "12:23 AM")
- `wrong_occurrence` — correct answer appears in the response but parser grabbed a different occurrence (e.g. from a wrong intermediate step rather than the final answer)
- `answer_buried` — correct answer exists but is not in the expected location (e.g. inside a table, list, or verification block rather than at the end)
- `hedged_correct` — model gives the right answer but wraps it in so much hedging/alternatives that the parser picks up noise
- `other` — parser failure that doesn't fit above categories

## Output format
Respond ONLY with a JSON object. No prose, no markdown fences. Example:

{"verdict": "parser_failure", "parser_issue": "wrong_occurrence", "confidence": "high", "notes": "Model correctly computed 12:23 AM in step 3 but self-corrected to wrong value in conclusion"}

{"verdict": "true_incorrect", "parser_issue": null, "confidence": "high", "notes": "Model recommends walking but car is needed at the destination"}

{"verdict": "false_negative", "parser_issue": null, "confidence": "medium", "notes": "Model answer '3' is correct; expected '3' — possible case sensitivity or whitespace issue in parser"}

## Confidence field
- `high` — unambiguous
- `medium` — defensible but could be argued either way
- `low` — genuinely unclear, edge case

Keep notes under 25 words."""

DEFAULT_USER_TEMPLATE = (
    "QUESTION:\n{user_prompt}\n\n"
    "RESPONSE:\n{raw_response}\n\n"
    "PARSED:\n{parsed_answer}\n\n"
    "EXPECTED:\n{expected_answer}"
)


# ── Worker function ──────────────────────────────────────────────────────

def _parse_judge_response(content: str) -> Dict[str, Any]:
    """Parse the judge model's JSON response with fallback."""
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try extracting JSON from prose
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {
            "verdict": "parse_error",
            "parser_issue": None,
            "confidence": "low",
            "notes": content[:200],
        }


def run_judge_worker(
    result_paths: List[str],
    model_name: str,
    provider: str,
    system_prompt: str,
    user_prompt_template: str,
    temperature: float,
    max_tokens: int,
    only_incorrect: bool,
    api_key: str,
    api_base: str,
    ollama_host: str,
    output_dir: str,
    job_id: str,
    progress_dict: dict,
) -> Dict[str, Optional[str]]:
    """Judge model results using an LLM. Runs in a subprocess.

    Returns the path to the judge output file.
    """
    import time as _time
    from src.models import create_model_interface

    # Note: progress helpers below mirror the module-level helpers in jobs.py.
    # They cannot be shared without a circular import (jobs ↔ judge), so the
    # logic is intentionally kept local to this subprocess-worker function.
    def _set_progress(**updates: Any) -> None:
        current = dict(progress_dict.get(job_id, {}))
        cancel_requested = bool(current.get("cancel_requested")) or bool(updates.get("cancel_requested"))
        merged = {**current, **updates, "cancel_requested": cancel_requested}
        if cancel_requested and merged.get("state") in (None, "pending", "running"):
            merged["state"] = "cancelled"
        progress_dict[job_id] = merged

    def _cancel_requested() -> bool:
        current = dict(progress_dict.get(job_id, {}))
        return bool(current.get("cancel_requested")) or current.get("state") == "cancelled"

    start_time = _time.time()

    # Create model interface
    kwargs: Dict[str, Any] = {}
    if provider == "openai_compatible":
        kwargs["api_key"] = api_key
        kwargs["base_url"] = api_base
    elif provider == "ollama":
        kwargs["ollama_host"] = ollama_host

    interface = create_model_interface(provider, model_name, **kwargs)

    # Collect items to judge
    items: List[Dict[str, Any]] = []
    source_files: List[str] = []

    for path in result_paths:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)

        filename = os.path.basename(path)
        source_files.append(filename)
        model = data.get("model_info", {}).get("model_name", "unknown")

        for r in data.get("results", []):
            if r.get("status") != "success":
                continue

            raw_response = r.get("output", {}).get("raw_response", "")
            if not raw_response or raw_response.strip().lower() == "timed out":
                continue

            is_correct = r.get("evaluation", {}).get("correct", False)
            if only_incorrect and is_correct:
                continue

            # Extract metadata for richer reporting
            prompt_meta = r.get("input", {}).get("prompt_metadata", {})
            task_params = r.get("input", {}).get("task_params", {})
            eval_details = r.get("evaluation", {}).get("details", {})
            test_id = r.get("test_id", "")

            # Infer task type from test_id if not in task_params
            task_type = task_params.get("task_type", "")
            if not task_type:
                from src.stages.analyze_results import _infer_task_type_from_id
                task_type = _infer_task_type_from_id(test_id)

            items.append({
                "source_file": filename,
                "test_id": test_id,
                "model": model,
                "user_prompt": r.get("input", {}).get("user_prompt", ""),
                "raw_response": raw_response,
                "parsed_answer": str(r.get("output", {}).get("parsed_answer", "")),
                "expected_answer": str(task_params.get("expected_answer", "")),
                "language": prompt_meta.get("language", "en"),
                "task_type": task_type,
                "user_style": prompt_meta.get("user_style", ""),
                "system_style": prompt_meta.get("system_style", ""),
                "parse_strategy": eval_details.get("parse_strategy", ""),
            })

    total = len(items)
    _set_progress(current=0, total=total, state="running")

    # Judge each item
    judgments: List[Dict[str, Any]] = []
    summary = defaultdict(int)
    parser_issues = defaultdict(int)

    for idx, item in enumerate(items):
        if _cancel_requested():
            _set_progress(current=idx, total=total, state="cancelled")
            return {"status": "cancelled", "result_path": None}

        prompt = user_prompt_template.format(
            user_prompt=item["user_prompt"],
            raw_response=item["raw_response"],
            parsed_answer=item["parsed_answer"],
            expected_answer=item["expected_answer"],
        )

        try:
            resp = interface.query(prompt, params={
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            })
            verdict = _parse_judge_response(resp.get("response", ""))
        except Exception as e:
            verdict = {
                "verdict": "error",
                "parser_issue": None,
                "confidence": "low",
                "notes": str(e)[:200],
            }

        judgment_entry = {
            **item,
            "verdict": verdict.get("verdict", "error"),
            "parser_issue": verdict.get("parser_issue"),
            "confidence": verdict.get("confidence", "low"),
            "notes": verdict.get("notes", ""),
        }
        judgments.append(judgment_entry)

        v = verdict.get("verdict", "error")
        summary[v] += 1
        if v == "parser_failure" and verdict.get("parser_issue"):
            parser_issues[verdict["parser_issue"]] += 1

        _set_progress(current=idx + 1, total=total, state="running")

    if _cancel_requested():
        _set_progress(current=total, total=total, state="cancelled")
        return {"status": "cancelled", "result_path": None}

    duration = _time.time() - start_time

    # Build output
    output_data = {
        "format_version": "1.0.0",
        "metadata": {
            "judge_id": job_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "judge_model": model_name,
            "judge_provider": provider,
            "duration_seconds": round(duration, 1),
            "only_incorrect": only_incorrect,
        },
        "source_results": source_files,
        "summary": {
            "total_judged": total,
            **dict(summary),
            "parser_issues": dict(parser_issues),
        },
        "judgments": judgments,
    }

    # Save output
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_filename = f"judge_{model_name.replace('/', '_').replace(':', '_')}_{ts}.json.gz"
    out_path = os.path.join(output_dir, out_filename)
    os.makedirs(output_dir, exist_ok=True)

    if _cancel_requested():
        _set_progress(current=total, total=total, state="cancelled")
        return {"status": "cancelled", "result_path": None}

    fd, tmp_path = tempfile.mkstemp(suffix=".json.gz", dir=output_dir)
    try:
        os.close(fd)
        with gzip.open(tmp_path, "wt", encoding="utf-8") as f:
            json.dump(output_data, f)
        os.replace(tmp_path, out_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    _set_progress(current=total, total=total, state="completed", result_path=out_path)
    return {"status": "completed", "result_path": out_path}
