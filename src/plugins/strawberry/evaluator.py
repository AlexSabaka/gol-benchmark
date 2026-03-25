"""
Strawberry (Character-Level Reasoning) – Result Evaluator

Dispatches on ``sub_type`` in task_params:

  count       — integer exact match
  reverse     — case-insensitive string exact match
  nth_letter  — case-insensitive single-char match
  anagram     — boolean match
  pangram     — boolean match
  lipogram    — boolean match

Match types:
  correct      — predicted == expected
  wrong        — predicted != expected
  parse_error  — could not extract an answer from the response
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.plugins.base import ResultEvaluator, EvaluationResult, ParsedAnswer


class StrawberryEvaluator(ResultEvaluator):
    """Evaluates character-level reasoning responses by exact match."""

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        task_params = task_params or {}
        sub_type = task_params.get("sub_type", "count")

        # Parse-error path
        if parsed_answer.error and parsed_answer.value is None:
            return EvaluationResult(
                correct=False,
                match_type="parse_error",
                accuracy=0.0,
                details=self._details(None, expected_answer, parsed_answer, task_params),
            )

        predicted = parsed_answer.value

        if sub_type == "count":
            return self._eval_count(predicted, expected_answer, parsed_answer, task_params)
        elif sub_type == "reverse":
            return self._eval_string(predicted, expected_answer, parsed_answer, task_params)
        elif sub_type == "nth_letter":
            return self._eval_char(predicted, expected_answer, parsed_answer, task_params)
        elif sub_type in ("anagram", "pangram", "lipogram"):
            return self._eval_boolean(predicted, expected_answer, parsed_answer, task_params)
        else:
            return self._eval_count(predicted, expected_answer, parsed_answer, task_params)

    # ------------------------------------------------------------------
    # COUNT
    # ------------------------------------------------------------------

    def _eval_count(self, predicted, expected, pa, tp) -> EvaluationResult:
        try:
            expected = int(expected)
        except (TypeError, ValueError):
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=self._details(predicted, expected, pa, tp),
                error=f"Bad expected value: {expected!r}",
            )
        try:
            predicted = int(predicted)
        except (TypeError, ValueError):
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=self._details(predicted, expected, pa, tp),
                error=f"Non-integer parsed value: {predicted!r}",
            )
        correct = predicted == expected
        return EvaluationResult(
            correct=correct,
            match_type="correct" if correct else "wrong",
            accuracy=1.0 if correct else 0.0,
            details=self._details(predicted, expected, pa, tp),
        )

    # ------------------------------------------------------------------
    # REVERSE (case-insensitive string)
    # ------------------------------------------------------------------

    def _eval_string(self, predicted, expected, pa, tp) -> EvaluationResult:
        if predicted is None:
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=self._details(predicted, expected, pa, tp),
            )
        correct = str(predicted).lower().strip() == str(expected).lower().strip()
        return EvaluationResult(
            correct=correct,
            match_type="correct" if correct else "wrong",
            accuracy=1.0 if correct else 0.0,
            details=self._details(predicted, expected, pa, tp),
        )

    # ------------------------------------------------------------------
    # NTH_LETTER (single char)
    # ------------------------------------------------------------------

    def _eval_char(self, predicted, expected, pa, tp) -> EvaluationResult:
        if predicted is None:
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=self._details(predicted, expected, pa, tp),
            )
        correct = str(predicted).lower().strip() == str(expected).lower().strip()
        return EvaluationResult(
            correct=correct,
            match_type="correct" if correct else "wrong",
            accuracy=1.0 if correct else 0.0,
            details=self._details(predicted, expected, pa, tp),
        )

    # ------------------------------------------------------------------
    # BOOLEAN (anagram / pangram / lipogram)
    # ------------------------------------------------------------------

    def _eval_boolean(self, predicted, expected, pa, tp) -> EvaluationResult:
        if predicted is None:
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=self._details(predicted, expected, pa, tp),
            )
        # Normalize both to bool
        expected_bool = self._to_bool(expected)
        predicted_bool = self._to_bool(predicted)
        if predicted_bool is None:
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=self._details(predicted, expected, pa, tp),
                error=f"Cannot interpret parsed value as boolean: {predicted!r}",
            )
        correct = predicted_bool == expected_bool
        return EvaluationResult(
            correct=correct,
            match_type="correct" if correct else "wrong",
            accuracy=1.0 if correct else 0.0,
            details=self._details(predicted, expected, pa, tp),
        )

    @staticmethod
    def _to_bool(val: Any) -> Optional[bool]:
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            low = val.strip().lower()
            if low in ("true", "yes", "1", "correct", "right"):
                return True
            if low in ("false", "no", "0", "incorrect", "wrong"):
                return False
        return None

    # ------------------------------------------------------------------
    # Detail builder
    # ------------------------------------------------------------------

    @staticmethod
    def _details(
        predicted: Any,
        expected: Any,
        parsed_answer: ParsedAnswer,
        task_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        sub_type = task_params.get("sub_type", "count")
        d: Dict[str, Any] = {
            "predicted": predicted,
            "expected": expected,
            "sub_type": sub_type,
            "parse_strategy": parsed_answer.parse_strategy,
            "confidence": parsed_answer.confidence,
        }
        # Sub-type specific fields
        if sub_type == "count":
            off_by = abs(int(predicted) - int(expected)) if isinstance(predicted, (int, float)) and isinstance(expected, (int, float)) else None
            d["off_by"] = off_by
            d["word"] = task_params.get("word", "")
            d["letter"] = task_params.get("letter", "")
            d["mode"] = task_params.get("mode", "")
            d["word_length"] = task_params.get("word_length", 0)
        elif sub_type == "reverse":
            d["word"] = task_params.get("word", "")
            d["word_length"] = task_params.get("word_length", 0)
        elif sub_type == "nth_letter":
            d["word"] = task_params.get("word", "")
            d["n"] = task_params.get("n", 0)
            d["word_length"] = task_params.get("word_length", 0)
        elif sub_type == "anagram":
            d["word1"] = task_params.get("word1", "")
            d["word2"] = task_params.get("word2", "")
        elif sub_type == "pangram":
            d["sentence"] = task_params.get("sentence", "")
            d["missing_letters"] = task_params.get("missing_letters", "")
        elif sub_type == "lipogram":
            d["sentence"] = task_params.get("sentence", "")
            d["avoided_letter"] = task_params.get("avoided_letter", "")
        return d

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        base = super().aggregate_results(results)

        # Sub-type breakdown
        sub_type_stats: Dict[str, Dict[str, int]] = {}
        # Mode breakdown (count sub-type only)
        mode_stats: Dict[str, Dict[str, int]] = {}
        off_by_sum = 0
        off_by_n = 0

        for r in results:
            st = r.details.get("sub_type", "count")
            if st not in sub_type_stats:
                sub_type_stats[st] = {"correct": 0, "total": 0}
            sub_type_stats[st]["total"] += 1
            if r.correct:
                sub_type_stats[st]["correct"] += 1

            # Count-specific: mode breakdown, off_by
            if st == "count":
                m = r.details.get("mode", "unknown")
                if m not in mode_stats:
                    mode_stats[m] = {"correct": 0, "total": 0}
                mode_stats[m]["total"] += 1
                if r.correct:
                    mode_stats[m]["correct"] += 1
                if r.details.get("off_by") is not None:
                    off_by_sum += r.details["off_by"]
                    off_by_n += 1

        base["sub_type_breakdown"] = {
            st: {**s, "accuracy": s["correct"] / s["total"] if s["total"] else 0.0}
            for st, s in sub_type_stats.items()
        }
        base["mode_breakdown"] = {
            m: {**s, "accuracy": s["correct"] / s["total"] if s["total"] else 0.0}
            for m, s in mode_stats.items()
        }
        base["mean_off_by"] = off_by_sum / off_by_n if off_by_n else None
        return base
