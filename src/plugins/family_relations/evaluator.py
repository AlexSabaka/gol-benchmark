"""
Family Relations – Result Evaluator

Exact integer match with diagnostic error taxonomy:

  correct        — predicted == expected
  overcounting   — predicted > expected (classic trap: counted self as sibling)
  undercounting  — predicted < expected (missed a family member)
  parse_error    — could not extract an integer from the response
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.plugins.base import ResultEvaluator, EvaluationResult, ParsedAnswer


class FamilyRelationsEvaluator(ResultEvaluator):
    """Evaluates family-relations puzzle answers by exact integer match."""

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        task_params = task_params or {}

        # --- Parse-error path ---
        if parsed_answer.error and parsed_answer.value is None:
            return EvaluationResult(
                correct=False,
                match_type="parse_error",
                accuracy=0.0,
                details=self._details(None, expected_answer, parsed_answer, task_params),
            )

        # --- Normalise values ---
        try:
            expected = int(expected_answer)
        except (TypeError, ValueError):
            return EvaluationResult(
                correct=False,
                match_type="parse_error",
                accuracy=0.0,
                details=self._details(parsed_answer.value, expected_answer, parsed_answer, task_params),
                error=f"Bad expected value: {expected_answer!r}",
            )

        try:
            predicted = int(parsed_answer.value)
        except (TypeError, ValueError):
            return EvaluationResult(
                correct=False,
                match_type="parse_error",
                accuracy=0.0,
                details=self._details(parsed_answer.value, expected, parsed_answer, task_params),
                error=f"Non-integer parsed value: {parsed_answer.value!r}",
            )

        # --- Match-type resolution ---
        if predicted == expected:
            match_type = "correct"
            correct = True
        elif predicted > expected:
            match_type = "overcounting"
            correct = False
        else:
            match_type = "undercounting"
            correct = False

        return EvaluationResult(
            correct=correct,
            match_type=match_type,
            accuracy=1.0 if correct else 0.0,
            details=self._details(predicted, expected, parsed_answer, task_params),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _details(
        predicted: Any,
        expected: Any,
        parsed_answer: ParsedAnswer,
        task_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "predicted": predicted,
            "expected": expected,
            "parse_strategy": parsed_answer.parse_strategy,
            "confidence": parsed_answer.confidence,
            "sub_type": task_params.get("sub_type", ""),
            "template": task_params.get("template", ""),
            "trap": task_params.get("trap", ""),
            "difficulty": task_params.get("difficulty", ""),
        }
