"""
Measure Comparison – Result Evaluator

Match types:
  correct               — predicted answer matches the correct measurement
  wrong                 — predicted answer is wrong
  parse_error           — could not extract an answer from the response
  correct_equal         — correctly identified equal values
  correct_incomparable  — correctly identified incomparable units
  missed_equal          — failed to identify equal values
  missed_incomparable   — failed to identify incomparable units
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.plugins.base import ResultEvaluator, EvaluationResult, ParsedAnswer


def _normalise_answer(s: str) -> str:
    """Lowercase, strip, collapse spaces."""
    return " ".join(s.lower().split())


class MeasureComparisonEvaluator(ResultEvaluator):
    """Evaluates measurement comparison responses."""

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        tp = task_params or {}
        expected = str(expected_answer)
        ctype = tp.get("comparison_type", "same_unit")

        # Parse-error path
        if parsed_answer.error and parsed_answer.value is None:
            mt = "parse_error"
            if ctype == "equal":
                mt = "missed_equal"
            elif ctype == "incomparable":
                mt = "missed_incomparable"
            return EvaluationResult(
                correct=False,
                match_type=mt,
                accuracy=0.0,
                details=self._details(None, expected, parsed_answer, tp),
            )

        predicted = str(parsed_answer.value) if parsed_answer.value is not None else ""

        if ctype == "equal":
            return self._eval_equal(predicted, expected, parsed_answer, tp)
        if ctype == "incomparable":
            return self._eval_incomparable(predicted, expected, parsed_answer, tp)

        return self._eval_normal(predicted, expected, parsed_answer, tp)

    # ------------------------------------------------------------------
    # Normal comparison (same_unit / mixed_unit)
    # ------------------------------------------------------------------

    def _eval_normal(
        self, predicted: str, expected: str, pa: ParsedAnswer, tp: Dict,
    ) -> EvaluationResult:
        correct = self._answers_match(predicted, expected, tp)
        return EvaluationResult(
            correct=correct,
            match_type="correct" if correct else "wrong",
            accuracy=1.0 if correct else 0.0,
            details=self._details(predicted, expected, pa, tp),
        )

    # ------------------------------------------------------------------
    # Equal trick
    # ------------------------------------------------------------------

    def _eval_equal(
        self, predicted: str, expected: str, pa: ParsedAnswer, tp: Dict,
    ) -> EvaluationResult:
        pred_norm = _normalise_answer(predicted)
        is_equal_answer = pred_norm in {
            "equal", "same", "equivalent", "they are equal",
            "both are equal", "equal value", "they're equal",
            "igual", "iguales", "égal", "gleich", "相等", "相同", "рівні",
        }
        return EvaluationResult(
            correct=is_equal_answer,
            match_type="correct_equal" if is_equal_answer else "missed_equal",
            accuracy=1.0 if is_equal_answer else 0.0,
            details=self._details(predicted, expected, pa, tp),
        )

    # ------------------------------------------------------------------
    # Incomparable trick
    # ------------------------------------------------------------------

    def _eval_incomparable(
        self, predicted: str, expected: str, pa: ParsedAnswer, tp: Dict,
    ) -> EvaluationResult:
        pred_norm = _normalise_answer(predicted)
        keywords = [
            "incomparable", "cannot compare", "can't compare",
            "not comparable", "different dimensions", "different categories",
            "impossible to compare", "cannot be compared", "can't be compared",
            "no se puede comparar", "no se pueden comparar",
            "incomparable", "nicht vergleichbar",
            "无法比较", "不能比较", "不可比较",
            "непорівнянні", "неможливо порівняти",
        ]
        is_incomparable = any(kw in pred_norm for kw in keywords)
        return EvaluationResult(
            correct=is_incomparable,
            match_type="correct_incomparable" if is_incomparable else "missed_incomparable",
            accuracy=1.0 if is_incomparable else 0.0,
            details=self._details(predicted, expected, pa, tp),
        )

    # ------------------------------------------------------------------
    # Answer matching
    # ------------------------------------------------------------------

    @staticmethod
    def _answers_match(predicted: str, expected: str, tp: Dict) -> bool:
        """Check if predicted matches expected, with fuzzy normalisation."""
        p = _normalise_answer(predicted)
        e = _normalise_answer(expected)

        # Direct match
        if p == e:
            return True

        # Without spaces
        if p.replace(" ", "") == e.replace(" ", ""):
            return True

        # Check if predicted matches the correct position's value+unit
        correct_pos = tp.get("correct_position", "")
        if correct_pos == "first":
            v = tp.get("value1", "")
            u = tp.get("unit1_symbol", "")
        elif correct_pos == "second":
            v = tp.get("value2", "")
            u = tp.get("unit2_symbol", "")
        else:
            return False

        alt = _normalise_answer(f"{v} {u}")
        if p == alt or p.replace(" ", "") == alt.replace(" ", ""):
            return True

        return False

    # ------------------------------------------------------------------
    # Details
    # ------------------------------------------------------------------

    @staticmethod
    def _details(
        predicted: Any,
        expected: str,
        pa: ParsedAnswer,
        tp: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "predicted": predicted,
            "expected": expected,
            "value1": tp.get("value1", ""),
            "unit1": tp.get("unit1", ""),
            "unit1_symbol": tp.get("unit1_symbol", ""),
            "value2": tp.get("value2", ""),
            "unit2": tp.get("unit2", ""),
            "unit2_symbol": tp.get("unit2_symbol", ""),
            "category": tp.get("category", ""),
            "comparison_type": tp.get("comparison_type", ""),
            "number_format": tp.get("number_format", ""),
            "question_direction": tp.get("question_direction", ""),
            "correct_position": tp.get("correct_position", ""),
            "is_decimal_trap": tp.get("is_decimal_trap", False),
            "parse_strategy": pa.parse_strategy,
            "confidence": pa.confidence,
        }

    # ------------------------------------------------------------------
    # Aggregate
    # ------------------------------------------------------------------

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        base = super().aggregate_results(results)

        # --- Breakdown by comparison_type ---
        ctype_stats: Dict[str, Dict[str, int]] = {}
        nfmt_stats: Dict[str, Dict[str, int]] = {}
        cat_stats: Dict[str, Dict[str, int]] = {}
        trap_correct = 0
        trap_total = 0
        pos_first_total = 0
        pos_first_predicted = 0
        pos_second_total = 0
        pos_second_predicted = 0

        for r in results:
            d = r.details

            # By comparison type
            ct = d.get("comparison_type", "unknown")
            if ct not in ctype_stats:
                ctype_stats[ct] = {"correct": 0, "total": 0}
            ctype_stats[ct]["total"] += 1
            if r.correct:
                ctype_stats[ct]["correct"] += 1

            # By number format
            nf = d.get("number_format", "unknown")
            if nf not in nfmt_stats:
                nfmt_stats[nf] = {"correct": 0, "total": 0}
            nfmt_stats[nf]["total"] += 1
            if r.correct:
                nfmt_stats[nf]["correct"] += 1

            # By category
            cat = d.get("category", "unknown")
            if cat not in cat_stats:
                cat_stats[cat] = {"correct": 0, "total": 0}
            cat_stats[cat]["total"] += 1
            if r.correct:
                cat_stats[cat]["correct"] += 1

            # Decimal trap accuracy
            if d.get("is_decimal_trap"):
                trap_total += 1
                if r.correct:
                    trap_correct += 1

            # Position bias
            cp = d.get("correct_position", "")
            pred = d.get("predicted", "")
            if cp == "first":
                pos_first_total += 1
            elif cp == "second":
                pos_second_total += 1
            # Track what the model actually chose
            if isinstance(pred, str):
                pred_norm = pred.lower()
                v1 = str(d.get("value1", "")).lower()
                v2 = str(d.get("value2", "")).lower()
                u1 = str(d.get("unit1_symbol", "")).lower()
                u2 = str(d.get("unit2_symbol", "")).lower()
                if v1 and u1 and (f"{v1} {u1}" in pred_norm or f"{v1}{u1}" in pred_norm):
                    pos_first_predicted += 1
                elif v2 and u2 and (f"{v2} {u2}" in pred_norm or f"{v2}{u2}" in pred_norm):
                    pos_second_predicted += 1

        def _acc(d):
            return {**d, "accuracy": d["correct"] / d["total"] if d["total"] else 0.0}

        base["comparison_type_breakdown"] = {k: _acc(v) for k, v in ctype_stats.items()}
        base["number_format_breakdown"] = {k: _acc(v) for k, v in nfmt_stats.items()}
        base["category_breakdown"] = {k: _acc(v) for k, v in cat_stats.items()}
        base["decimal_trap_accuracy"] = (
            trap_correct / trap_total if trap_total else None
        )
        base["decimal_trap_total"] = trap_total
        base["position_bias"] = {
            "first_correct_total": pos_first_total,
            "first_predicted_total": pos_first_predicted,
            "second_correct_total": pos_second_total,
            "second_predicted_total": pos_second_predicted,
        }

        return base
