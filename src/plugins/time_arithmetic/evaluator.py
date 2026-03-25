"""
Time Arithmetic – Result Evaluator

Match types:
  correct          — exact match on time / day / duration
  wrong            — incorrect answer to a valid question
  correct_refusal  — correctly identified an impossible date/time
  wrong_compliance — confidently answered an impossible question (hallucination)
  wrong_refusal    — falsely refused a valid question
  parse_error      — could not extract an answer from the response
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator

# ── time normalization ───────────────────────────────────────────────

_TIME_12H_RE = re.compile(
    r"(\d{1,2})\s*[:\.]\s*(\d{2})\s*(a\.?m\.?|p\.?m\.?|AM|PM)",
    re.IGNORECASE,
)
_TIME_24H_RE = re.compile(r"(\d{1,2})\s*[:\.]\s*(\d{2})")


def _time_to_minutes(s: str) -> Optional[int]:
    """Convert a time string to minutes-since-midnight, or None."""
    if not s:
        return None
    m = _TIME_12H_RE.search(s)
    if m:
        h, mn, period = int(m.group(1)), int(m.group(2)), m.group(3).replace(".", "").upper()
        if h < 1 or h > 12 or mn > 59:
            return None
        if period == "AM":
            h = h % 12
        else:
            h = h % 12 + 12
        return h * 60 + mn
    m = _TIME_24H_RE.search(s)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return h * 60 + mn
    return None


# ── day normalization ────────────────────────────────────────────────

_CANONICAL_DAYS = {
    "monday": "Monday", "mon": "Monday",
    "tuesday": "Tuesday", "tue": "Tuesday", "tues": "Tuesday",
    "wednesday": "Wednesday", "wed": "Wednesday",
    "thursday": "Thursday", "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday",
    "friday": "Friday", "fri": "Friday",
    "saturday": "Saturday", "sat": "Saturday",
    "sunday": "Sunday", "sun": "Sunday",
    # ES
    "lunes": "Monday", "martes": "Tuesday", "miércoles": "Wednesday",
    "jueves": "Thursday", "viernes": "Friday", "sábado": "Saturday", "domingo": "Sunday",
    # FR
    "lundi": "Monday", "mardi": "Tuesday", "mercredi": "Wednesday",
    "jeudi": "Thursday", "vendredi": "Friday", "samedi": "Saturday", "dimanche": "Sunday",
    # DE
    "montag": "Monday", "dienstag": "Tuesday", "mittwoch": "Wednesday",
    "donnerstag": "Thursday", "freitag": "Friday", "samstag": "Saturday", "sonntag": "Sunday",
    # UA
    "понеділок": "Monday", "вівторок": "Tuesday", "середа": "Wednesday",
    "четвер": "Thursday", "п'ятниця": "Friday", "субота": "Saturday", "неділя": "Sunday",
    # ZH
    "星期一": "Monday", "星期二": "Tuesday", "星期三": "Wednesday",
    "星期四": "Thursday", "星期五": "Friday", "星期六": "Saturday", "星期日": "Sunday",
}


def _normalize_day(s: str) -> Optional[str]:
    if not s:
        return None
    return _CANONICAL_DAYS.get(s.strip().lower())


# ── evaluator ────────────────────────────────────────────────────────

class TimeArithmeticEvaluator(ResultEvaluator):

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any],
    ) -> EvaluationResult:
        tp = task_params or {}
        expected = str(expected_answer or tp.get("expected_answer", ""))
        is_impossible = tp.get("is_impossible", False)
        question_mode = tp.get("question_mode", "result_time")

        # Parse-error path
        if parsed_answer.error and parsed_answer.value is None:
            return EvaluationResult(
                correct=False,
                match_type="parse_error",
                accuracy=0.0,
                details=self._details(None, expected, parsed_answer, tp),
            )

        predicted = str(parsed_answer.value) if parsed_answer.value is not None else ""
        pred_lower = predicted.strip().lower()

        pred_is_refusal = pred_lower in ("impossible", "")
        # If the parser extracted "impossible", that's a refusal signal
        if pred_lower == "impossible":
            pred_is_refusal = True

        if is_impossible:
            if pred_is_refusal:
                return EvaluationResult(
                    correct=True,
                    match_type="correct_refusal",
                    accuracy=1.0,
                    details=self._details(predicted, expected, parsed_answer, tp),
                )
            return EvaluationResult(
                correct=False,
                match_type="wrong_compliance",
                accuracy=0.0,
                details=self._details(predicted, expected, parsed_answer, tp),
            )

        # Valid question — model should NOT refuse
        if pred_is_refusal and predicted.strip().lower() == "impossible":
            return EvaluationResult(
                correct=False,
                match_type="wrong_refusal",
                accuracy=0.0,
                details=self._details(predicted, expected, parsed_answer, tp),
            )

        # Match based on question mode
        correct = False
        if question_mode == "result_time":
            correct = self._times_match(predicted, expected)
        elif question_mode == "duration":
            correct = self._durations_match(predicted, expected)
        elif question_mode == "day":
            correct = self._days_match(predicted, expected)
        elif question_mode == "date_validity":
            correct = pred_lower == expected.lower()

        return EvaluationResult(
            correct=correct,
            match_type="correct" if correct else "wrong",
            accuracy=1.0 if correct else 0.0,
            details=self._details(predicted, expected, parsed_answer, tp),
        )

    # ── matching helpers ─────────────────────────────────────────────

    @staticmethod
    def _times_match(predicted: str, expected: str, tolerance: int = 1) -> bool:
        """Compare two time strings. Allow ±tolerance minutes."""
        p = _time_to_minutes(predicted)
        e = _time_to_minutes(expected)
        if p is None or e is None:
            return False
        diff = abs(p - e)
        # Handle midnight wraparound
        diff = min(diff, 1440 - diff)
        return diff <= tolerance

    @staticmethod
    def _durations_match(predicted: str, expected: str) -> bool:
        """Compare durations as integer minutes."""
        try:
            p = int(re.search(r"\d+", predicted).group())  # type: ignore[union-attr]
            e = int(re.search(r"\d+", expected).group())    # type: ignore[union-attr]
            return abs(p - e) <= 1
        except (AttributeError, ValueError):
            return False

    @staticmethod
    def _days_match(predicted: str, expected: str) -> bool:
        p = _normalize_day(predicted)
        e = _normalize_day(expected)
        if p and e:
            return p == e
        # Fallback: direct case-insensitive on canonical expected
        return predicted.strip().lower() == expected.strip().lower()

    # ── details ──────────────────────────────────────────────────────

    @staticmethod
    def _details(predicted, expected, pa: ParsedAnswer, tp: Dict) -> Dict[str, Any]:
        return {
            "predicted": predicted,
            "expected": expected,
            "sub_type": tp.get("sub_type", ""),
            "question_mode": tp.get("question_mode", ""),
            "direction": tp.get("direction", ""),
            "time_format": tp.get("time_format", ""),
            "is_impossible": tp.get("is_impossible", False),
            "parse_strategy": pa.parse_strategy,
            "confidence": pa.confidence,
        }

    # ── aggregation ──────────────────────────────────────────────────

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        base = super().aggregate_results(results)

        sub_type_stats: Dict[str, Dict[str, int]] = {}
        direction_stats: Dict[str, Dict[str, int]] = {}
        fmt_stats: Dict[str, Dict[str, int]] = {}
        impossible_total = 0
        impossible_correct = 0
        wrong_compliance_count = 0
        valid_total = 0
        wrong_refusal_count = 0

        for r in results:
            d = r.details

            # By sub_type
            st = d.get("sub_type", "unknown")
            if st not in sub_type_stats:
                sub_type_stats[st] = {"correct": 0, "total": 0}
            sub_type_stats[st]["total"] += 1
            if r.correct:
                sub_type_stats[st]["correct"] += 1

            # By direction
            dr = d.get("direction", "")
            if dr:
                if dr not in direction_stats:
                    direction_stats[dr] = {"correct": 0, "total": 0}
                direction_stats[dr]["total"] += 1
                if r.correct:
                    direction_stats[dr]["correct"] += 1

            # By time_format
            tf = d.get("time_format", "")
            if tf:
                if tf not in fmt_stats:
                    fmt_stats[tf] = {"correct": 0, "total": 0}
                fmt_stats[tf]["total"] += 1
                if r.correct:
                    fmt_stats[tf]["correct"] += 1

            # Impossible-question tracking
            if d.get("is_impossible"):
                impossible_total += 1
                if r.match_type == "correct_refusal":
                    impossible_correct += 1
                elif r.match_type == "wrong_compliance":
                    wrong_compliance_count += 1
            else:
                valid_total += 1
                if r.match_type == "wrong_refusal":
                    wrong_refusal_count += 1

        def _acc(s):
            return {**s, "accuracy": s["correct"] / s["total"] if s["total"] else 0.0}

        base["sub_type_breakdown"] = {k: _acc(v) for k, v in sub_type_stats.items()}
        base["direction_breakdown"] = {k: _acc(v) for k, v in direction_stats.items()}
        base["time_format_breakdown"] = {k: _acc(v) for k, v in fmt_stats.items()}
        base["impossible_detection_rate"] = (
            impossible_correct / impossible_total if impossible_total else None
        )
        base["hallucination_rate"] = (
            wrong_compliance_count / impossible_total if impossible_total else None
        )
        base["false_refusal_rate"] = (
            wrong_refusal_count / valid_total if valid_total else None
        )
        base["impossible_total"] = impossible_total
        base["valid_total"] = valid_total

        return base
