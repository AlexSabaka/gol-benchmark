"""
Strawberry (Letter Counting) – Result Evaluator

Match types:
  correct      — predicted count == expected count
  wrong        — predicted count != expected count
  parse_error  — could not extract a number from the response
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.plugins.base import ResultEvaluator, EvaluationResult, ParsedAnswer


class StrawberryEvaluator(ResultEvaluator):
    """Evaluates letter-counting responses by exact integer match."""

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        task_params = task_params or {}
        expected = int(expected_answer)

        # Parse-error path
        if parsed_answer.error and parsed_answer.value is None:
            return EvaluationResult(
                correct=False,
                match_type="parse_error",
                accuracy=0.0,
                details=self._details(None, expected, parsed_answer, task_params),
            )

        predicted = parsed_answer.value
        try:
            predicted = int(predicted)
        except (TypeError, ValueError):
            return EvaluationResult(
                correct=False,
                match_type="parse_error",
                accuracy=0.0,
                details=self._details(predicted, expected, parsed_answer, task_params),
                error=f"Non-integer parsed value: {predicted!r}",
            )

        correct = predicted == expected
        return EvaluationResult(
            correct=correct,
            match_type="correct" if correct else "wrong",
            accuracy=1.0 if correct else 0.0,
            details=self._details(predicted, expected, parsed_answer, task_params),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _details(
        predicted: Any,
        expected: int,
        parsed_answer: ParsedAnswer,
        task_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        off_by = abs(int(predicted) - expected) if isinstance(predicted, (int, float)) else None
        return {
            "predicted": predicted,
            "expected": expected,
            "off_by": off_by,
            "word": task_params.get("word", ""),
            "letter": task_params.get("letter", ""),
            "mode": task_params.get("mode", ""),
            "word_length": task_params.get("word_length", 0),
            "parse_strategy": parsed_answer.parse_strategy,
            "confidence": parsed_answer.confidence,
        }

    # ------------------------------------------------------------------

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        base = super().aggregate_results(results)

        # Add strawberry-specific breakdowns
        mode_stats: Dict[str, Dict[str, int]] = {}
        off_by_sum = 0
        off_by_n = 0

        for r in results:
            m = r.details.get("mode", "unknown")
            if m not in mode_stats:
                mode_stats[m] = {"correct": 0, "total": 0}
            mode_stats[m]["total"] += 1
            if r.correct:
                mode_stats[m]["correct"] += 1
            if r.details.get("off_by") is not None:
                off_by_sum += r.details["off_by"]
                off_by_n += 1

        base["mode_breakdown"] = {
            m: {**s, "accuracy": s["correct"] / s["total"] if s["total"] else 0.0}
            for m, s in mode_stats.items()
        }
        base["mean_off_by"] = off_by_sum / off_by_n if off_by_n else None
        return base
