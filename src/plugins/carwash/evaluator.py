"""
Carwash Paradox – Result Evaluator

Match types:
  correct      — model said "drive" (correct insight: car must be there)
  naive_trap   — model said "walk" (fell for the proximity trap)
  parse_error  — could not extract a clear answer
  wrong        — other / unclear
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.plugins.base import ResultEvaluator, EvaluationResult, ParsedAnswer


class CarwashEvaluator(ResultEvaluator):
    """Evaluates Carwash Paradox responses."""

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: str,
        task_params: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        task_params = task_params or {}
        predicted = (parsed_answer.value or "").strip().lower()
        expected = (expected_answer or "drive").strip().lower()

        # --- Match type resolution ---
        if parsed_answer.error and predicted in ("other", ""):
            match_type = "parse_error"
            correct = False
            accuracy = 0.0
        elif predicted == expected:          # "drive"
            match_type = "correct"
            correct = True
            accuracy = 1.0
        elif predicted == "walk":
            match_type = "naive_trap"
            correct = False
            accuracy = 0.0
        elif predicted == "other":
            match_type = "wrong"
            correct = False
            accuracy = 0.0
        else:
            match_type = "wrong"
            correct = False
            accuracy = 0.0

        details = {
            "predicted": predicted,
            "expected": expected,
            "parse_strategy": parsed_answer.parse_strategy,
            "confidence": parsed_answer.confidence,
            "distance_label": task_params.get("distance_label", ""),
            "distance_desc": task_params.get("distance_desc", ""),
            "framing": task_params.get("framing", ""),
            "naive_trap_value": task_params.get("naive_trap", "walk"),
        }

        return EvaluationResult(
            correct=correct,
            accuracy=accuracy,
            match_type=match_type,
            details=details,
        )
