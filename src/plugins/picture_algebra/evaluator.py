"""Picture Algebra Result Evaluator.

Classifies parsed answers into eight match types that separate *did the model
solve the algebra* from *did it detect an impossible system*:

    correct                         — all requested values right
    wrong_value                     — right variables, at least one wrong number
    wrong_variable                  — answered for different variables than asked
    partial                         — some right, some wrong (question_scope=all only)
    system_error                    — correctly refused an impossible system
    system_error_missed             — gave a confident answer to an impossible system
    system_error_false_positive     — refused a solvable system (hallucinated impossibility)
    parse_error                     — parser could not extract an answer

Also emits a ``semantic_interference_delta`` at aggregation time when the
batch contains both alpha and emoji surface forms — the GSM-Symbolic score
this plugin exists to measure.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator

SENTINEL_CANNOT_DETERMINE = "CANNOT_BE_DETERMINED"
SENTINEL_NO_SOLUTION = "NO_SOLUTION"
_SENTINELS = {SENTINEL_CANNOT_DETERMINE, SENTINEL_NO_SOLUTION}


class PictureAlgebraEvaluator(ResultEvaluator):
    """Match-type-rich evaluator for picture_algebra."""

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any],
    ) -> EvaluationResult:
        if expected_answer is None:
            expected_answer = task_params.get("expected_answer")

        # ── parse error ────────────────────────────────────────────
        if not parsed_answer.success:
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=_details(parsed_answer, expected_answer, task_params),
                error=parsed_answer.error,
            )

        predicted = parsed_answer.value
        expected_is_sentinel = isinstance(expected_answer, str) and expected_answer in _SENTINELS
        predicted_is_sentinel = isinstance(predicted, str) and predicted in _SENTINELS

        # ── trick cases (expected is a sentinel) ───────────────────
        if expected_is_sentinel:
            if predicted_is_sentinel:
                # Accept any sentinel match as system_error.  Being strict
                # (distinguishing "cannot determine" from "no solution") would
                # over-penalize — the point is that the model refused.
                return EvaluationResult(
                    correct=True, match_type="system_error", accuracy=1.0,
                    details=_details(parsed_answer, expected_answer, task_params),
                )
            return EvaluationResult(
                correct=False, match_type="system_error_missed", accuracy=0.0,
                details=_details(parsed_answer, expected_answer, task_params),
            )

        # ── predicted refusal on a solvable system ─────────────────
        if predicted_is_sentinel:
            return EvaluationResult(
                correct=False, match_type="system_error_false_positive",
                accuracy=0.0,
                details=_details(parsed_answer, expected_answer, task_params),
            )

        # ── non-sentinel case: numeric dict expected ───────────────
        if not isinstance(predicted, dict) or not isinstance(expected_answer, dict):
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=_details(parsed_answer, expected_answer, task_params),
                error="Predicted or expected is not a dict",
            )

        expected_map: Dict[str, int] = {
            k: int(v) for k, v in expected_answer.items()
        }
        requested_keys = set(expected_map.keys())
        predicted_keys = set(predicted.keys())

        # ── wrong_variable: model solved for keys that don't overlap ───
        overlap = requested_keys & predicted_keys
        if not overlap:
            return EvaluationResult(
                correct=False, match_type="wrong_variable", accuracy=0.0,
                details=_details(parsed_answer, expected_answer, task_params),
            )

        # ── compare values on overlapping keys ─────────────────────
        # Compare as floats so that a non-integer prediction (e.g. 22.2 vs
        # expected 22) is correctly graded *wrong* instead of silently
        # truncating via ``int(22.2) == 22``.
        correct_count = 0
        wrong_count = 0
        missing_count = 0
        non_integer_prediction = False
        for key, exp_val in expected_map.items():
            if key not in predicted:
                missing_count += 1
                continue
            pred_raw = predicted[key]
            if isinstance(pred_raw, bool):
                wrong_count += 1
                continue
            try:
                pred_num = float(pred_raw)
            except (ValueError, TypeError):
                wrong_count += 1
                continue
            if isinstance(pred_raw, float) and not pred_raw.is_integer():
                non_integer_prediction = True
            if pred_num == float(exp_val):
                correct_count += 1
            else:
                wrong_count += 1

        total_requested = len(expected_map)
        question_scope = str(task_params.get("question_scope", "all"))
        extra_details: Dict[str, Any] = {
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "missing_count": missing_count,
        }
        if non_integer_prediction:
            extra_details["non_integer_prediction"] = True
        if parsed_answer.parse_strategy == "foreign_labels_aliased":
            extra_details["alias_remap_applied"] = True

        if correct_count == total_requested and wrong_count == 0 and missing_count == 0:
            return EvaluationResult(
                correct=True, match_type="correct", accuracy=1.0,
                details=_details(parsed_answer, expected_answer, task_params,
                                 **extra_details),
            )

        # Partial only applies when the user asked for all variables; otherwise
        # a single requested var graded as wrong is just wrong_value.
        if (
            question_scope == "all"
            and total_requested > 1
            and correct_count > 0
            and correct_count < total_requested
        ):
            accuracy = correct_count / total_requested
            return EvaluationResult(
                correct=False, match_type="partial", accuracy=accuracy,
                details=_details(parsed_answer, expected_answer, task_params,
                                 **extra_details),
            )

        return EvaluationResult(
            correct=False, match_type="wrong_value", accuracy=0.0,
            details=_details(parsed_answer, expected_answer, task_params,
                             **extra_details),
        )

    # ── aggregation ────────────────────────────────────────────────

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        if not results:
            return {"accuracy": 0.0, "correct": 0, "total": 0, "error_count": 0}

        total = len(results)
        correct = sum(1 for r in results if r.correct)
        accuracy_sum = sum(r.accuracy for r in results)
        match_types = self._count_match_types(results)
        n_parse = match_types.get("parse_error", 0)

        surface_breakdown = _breakdown(results, "surface_form")
        emoji_cat_breakdown = _breakdown(results, "emoji_category")
        operations_breakdown = _breakdown(results, "operations")
        num_vars_breakdown = _breakdown(results, "num_variables")
        determinacy_breakdown = _breakdown(results, "determinacy")
        scope_breakdown = _breakdown(results, "question_scope")

        out: Dict[str, Any] = {
            "accuracy": correct / total,
            "mean_accuracy": accuracy_sum / total,  # counts partial credit
            "correct": correct,
            "total": total,
            "error_count": n_parse,
            "match_types": match_types,
            "parse_error_rate": n_parse / total,
            "surface_form_breakdown": surface_breakdown,
            "emoji_category_breakdown": emoji_cat_breakdown,
            "operations_breakdown": operations_breakdown,
            "num_variables_breakdown": num_vars_breakdown,
            "determinacy_breakdown": determinacy_breakdown,
            "question_scope_breakdown": scope_breakdown,
        }

        delta = _semantic_interference_delta(surface_breakdown)
        if delta is not None:
            out["semantic_interference_delta"] = delta

        return out


# ── helpers ────────────────────────────────────────────────────────────

def _details(
    pa: ParsedAnswer,
    expected: Any,
    tp: Dict[str, Any],
    **extra: Any,
) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "predicted": pa.value,
        "expected": expected,
        "parse_strategy": pa.parse_strategy,
        "determinacy": tp.get("determinacy"),
        "surface_form": tp.get("surface_form"),
        "emoji_category": tp.get("emoji_category"),
        "operations": tp.get("operations"),
        "num_variables": tp.get("num_variables"),
        "num_equations": tp.get("num_equations"),
        "question_scope": tp.get("question_scope"),
        "queried_variable": tp.get("queried_variable"),
    }
    d.update(extra)
    return d


def _breakdown(results: List[EvaluationResult], key: str) -> Dict[str, Dict[str, Any]]:
    buckets: Dict[str, List[EvaluationResult]] = {}
    for r in results:
        raw_val = r.details.get(key, "unknown") if r.details else "unknown"
        # Use "null" label when the dimension was not set for this case
        val = "null" if raw_val is None else str(raw_val)
        buckets.setdefault(val, []).append(r)
    return {
        k: {
            "correct": sum(1 for r in rs if r.correct),
            "total": len(rs),
            "accuracy": sum(1 for r in rs if r.correct) / len(rs),
            "mean_accuracy": sum(r.accuracy for r in rs) / len(rs),
        }
        for k, rs in buckets.items()
    }


def _semantic_interference_delta(
    surface_breakdown: Dict[str, Dict[str, Any]],
) -> Optional[float]:
    """alpha accuracy − emoji accuracy, or ``None`` if either is absent."""
    alpha = surface_breakdown.get("alpha")
    emoji = surface_breakdown.get("emoji")
    if not alpha or not emoji:
        return None
    if alpha["total"] == 0 or emoji["total"] == 0:
        return None
    return round(alpha["accuracy"] - emoji["accuracy"], 4)
