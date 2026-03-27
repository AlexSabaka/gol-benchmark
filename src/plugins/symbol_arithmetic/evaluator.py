"""
Symbol Arithmetic Result Evaluator

Classifies answers into 8 match types that reveal *which* algebraic
assumptions a model imported from training:

    correct                   — right symbol
    wrong_assumed_commutative — wrong, but matches a commuted variant
    wrong_assumed_associative — wrong, but matches a regrouped variant
    wrong_arbitrary           — wrong, no classifiable assumption
    undefined_correct         — correctly flagged an undefined lookup
    undefined_wrong           — invented an answer for an undefined operation
    undefined_missed          — falsely claimed a defined operation is undefined
    parse_error               — could not extract an answer
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator


class SymbolArithmeticEvaluator(ResultEvaluator):

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any],
    ) -> EvaluationResult:
        if expected_answer is None:
            expected_answer = task_params.get("expected_answer")

        # ── parse error ─────────────────────────────────────────────
        if not parsed_answer.success:
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=_details(parsed_answer, expected_answer, task_params),
                error=parsed_answer.error,
            )

        predicted = parsed_answer.value
        expected = str(expected_answer)

        # ── undefined handling ──────────────────────────────────────
        if expected == "UNDEFINED":
            if predicted == "UNDEFINED":
                return EvaluationResult(
                    correct=True, match_type="undefined_correct", accuracy=1.0,
                    details=_details(parsed_answer, expected, task_params),
                )
            return EvaluationResult(
                correct=False, match_type="undefined_wrong", accuracy=0.0,
                details=_details(parsed_answer, expected, task_params),
            )

        if predicted == "UNDEFINED":
            return EvaluationResult(
                correct=False, match_type="undefined_missed", accuracy=0.0,
                details=_details(parsed_answer, expected, task_params),
            )

        # ── correct ─────────────────────────────────────────────────
        if predicted == expected:
            return EvaluationResult(
                correct=True, match_type="correct", accuracy=1.0,
                details=_details(parsed_answer, expected, task_params),
            )

        # ── wrong — classify assumption ─────────────────────────────
        commuted: List[str] = task_params.get("commuted_answers", [])
        regrouped: List[str] = task_params.get("regrouped_answers", [])

        in_commuted = predicted in commuted
        in_regrouped = predicted in regrouped

        if in_commuted:
            mt = "wrong_assumed_commutative"
        elif in_regrouped:
            mt = "wrong_assumed_associative"
        else:
            mt = "wrong_arbitrary"

        return EvaluationResult(
            correct=False, match_type=mt, accuracy=0.0,
            details=_details(parsed_answer, expected, task_params),
        )

    # ── aggregation ─────────────────────────────────────────────────

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        if not results:
            return {"accuracy": 0.0, "correct": 0, "total": 0, "error_count": 0}

        total = len(results)
        correct = sum(1 for r in results if r.correct)
        match_types = self._count_match_types(results)

        # Per-dimension breakdowns
        op_class_stats = _breakdown(results, "operation_class")
        depth_stats = _breakdown(results, "expression_depth")
        format_stats = _breakdown(results, "table_format")
        symbol_stats = _breakdown(results, "symbol_type")

        # Derived rates
        n_comm = match_types.get("wrong_assumed_commutative", 0)
        n_assoc = match_types.get("wrong_assumed_associative", 0)
        n_parse = match_types.get("parse_error", 0)
        n_undef_correct = match_types.get("undefined_correct", 0)
        n_undef_wrong = match_types.get("undefined_wrong", 0)
        n_undef_missed = match_types.get("undefined_missed", 0)
        n_undef_total = n_undef_correct + n_undef_wrong + n_undef_missed
        wrong_total = total - correct - n_parse

        return {
            "accuracy": correct / total,
            "correct": correct,
            "total": total,
            "error_count": n_parse,
            "match_types": match_types,
            "assumption_violation_profile": {
                k: v for k, v in match_types.items() if k.startswith("wrong_")
            },
            "commutativity_assumption_rate": (
                n_comm / wrong_total if wrong_total else 0.0
            ),
            "associativity_assumption_rate": (
                n_assoc / wrong_total if wrong_total else 0.0
            ),
            "undefined_detection_rate": (
                n_undef_correct / n_undef_total if n_undef_total else 0.0
            ),
            "parse_error_rate": n_parse / total,
            "operation_class_breakdown": op_class_stats,
            "expression_depth_breakdown": depth_stats,
            "table_format_breakdown": format_stats,
            "symbol_type_breakdown": symbol_stats,
        }


# ── helpers ─────────────────────────────────────────────────────────────

def _details(pa: ParsedAnswer, expected: Any, tp: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "predicted": pa.value,
        "expected": expected,
        "parse_strategy": pa.parse_strategy,
        "expression": tp.get("expression", ""),
        "operation_class": tp.get("operation_class", ""),
        "expression_depth": tp.get("expression_depth", 0),
        "table_format": tp.get("table_format", ""),
        "symbol_type": tp.get("symbol_type", ""),
        "table_completeness": tp.get("table_completeness", ""),
    }


def _breakdown(results: List[EvaluationResult], key: str) -> Dict[str, Dict[str, Any]]:
    """Compute per-dimension accuracy breakdown."""
    buckets: Dict[str, List[bool]] = {}
    for r in results:
        val = str(r.details.get(key, "unknown"))
        buckets.setdefault(val, []).append(r.correct)
    return {
        k: {"correct": sum(v), "total": len(v), "accuracy": sum(v) / len(v)}
        for k, v in buckets.items()
    }
