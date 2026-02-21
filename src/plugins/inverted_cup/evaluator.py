"""
Inverted Cup – Result Evaluator

Match types:
  correct       — model said "flip" / turn it over (correct physical insight)
  wrong         — model gave a wrong / impractical suggestion
  parse_error   — could not extract a clear answer
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.plugins.base import ResultEvaluator, EvaluationResult, ParsedAnswer


class InvertedCupEvaluator(ResultEvaluator):
    """Evaluates Inverted Cup responses."""

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: str,
        task_params: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        task_params = task_params or {}
        predicted = (parsed_answer.value or "").strip().lower()
        expected = (expected_answer or "flip").strip().lower()

        # --- Match type resolution ---
        if parsed_answer.error and predicted in ("wrong", ""):
            # Distinguish genuine parse failures from confident wrong answers
            if parsed_answer.parse_strategy in ("empty", "fallback"):
                match_type = "parse_error"
                correct = False
                accuracy = 0.0
            else:
                match_type = "wrong"
                correct = False
                accuracy = 0.0
        elif predicted == expected:          # "flip"
            match_type = "correct"
            correct = True
            accuracy = 1.0
        else:
            match_type = "wrong"
            correct = False
            accuracy = 0.0

        details = {
            "predicted": predicted,
            "expected": expected,
            "parse_strategy": parsed_answer.parse_strategy,
            "confidence": parsed_answer.confidence,
            "description_tag": task_params.get("description_tag", ""),
            "source": task_params.get("source", ""),
            "question": task_params.get("question", ""),
        }

        return EvaluationResult(
            correct=correct,
            accuracy=accuracy,
            match_type=match_type,
            details=details,
        )
