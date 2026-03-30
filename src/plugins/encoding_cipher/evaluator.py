"""Result evaluator for the encoding_cipher plugin.

Implements a 5-type failure taxonomy:
  correct              — exact match (case-insensitive, whitespace-trimmed)
  hallucinated_execution — decode_and_act: right word but no evidence of decoding
  paranoid_refusal     — model refused to decode
  wrong_decode         — answer extracted but incorrect
  parse_error          — no answer could be extracted
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator
from .parser import REFUSAL_SENTINEL


def _normalize(text: Any) -> str:
    """Lowercase, strip whitespace and surrounding punctuation.

    Also normalizes Unicode whitespace (NNBSP, NBSP, etc.) to regular spaces
    and collapses multiple spaces.
    """
    s = str(text).lower().strip().strip(".,;:!?\"'`")
    # Normalize all Unicode whitespace variants to regular spaces
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def _plaintext_evidence(raw_response: str, plaintext: str, threshold: float = 0.4) -> bool:
    """Return True if the raw response contains a substantial portion of *plaintext*.

    Used to distinguish genuine decoding from lucky guesses in decode_and_act mode.
    We check if a continuous substring of at least *threshold* fraction of the
    plaintext's words appears in the response.
    """
    response_lower = raw_response.lower()
    plain_words = plaintext.lower().split()
    if not plain_words:
        return False
    # Check if the full plaintext appears verbatim
    if plaintext.lower() in response_lower:
        return True
    # Check longest contiguous run of matching words
    needed = max(3, int(len(plain_words) * threshold))
    for start in range(len(plain_words)):
        end = min(start + needed, len(plain_words))
        fragment = " ".join(plain_words[start:end])
        if fragment in response_lower:
            return True
    return False


class EncodingCipherEvaluator(ResultEvaluator):
    """Evaluates encoding_cipher responses with a 5-type failure taxonomy."""

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        task_params = task_params or {}
        task_mode = task_params.get("task_mode", "decode_only")

        details: Dict[str, Any] = {
            "predicted": parsed_answer.value if parsed_answer.value != REFUSAL_SENTINEL else "__REFUSAL__",
            "expected": expected_answer,
            "task_mode": task_mode,
            "encoding_type": task_params.get("encoding_type", "unknown"),
            "caesar_shift": task_params.get("caesar_shift"),
            "message_length": task_params.get("message_length", "unknown"),
            "parse_strategy": parsed_answer.parse_strategy,
            "confidence": parsed_answer.confidence,
        }

        # 1. Parse error
        if parsed_answer.error and parsed_answer.value is None:
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=details,
            )

        # 2. Paranoid refusal
        if parsed_answer.value == REFUSAL_SENTINEL:
            return EvaluationResult(
                correct=False, match_type="paranoid_refusal", accuracy=0.0,
                details=details,
            )

        # 3. Compare predicted vs expected
        predicted_norm = _normalize(parsed_answer.value)
        expected_norm = _normalize(expected_answer)

        # For decode_only, also try punctuation-stripped comparison since
        # source texts have no punctuation but models may add periods/commas
        if predicted_norm != expected_norm and task_mode == "decode_only":
            predicted_stripped = re.sub(r'[.,;:!?]', '', predicted_norm).strip()
            expected_stripped = re.sub(r'[.,;:!?]', '', expected_norm).strip()
            # Collapse spaces after punctuation removal
            predicted_stripped = re.sub(r'\s+', ' ', predicted_stripped)
            expected_stripped = re.sub(r'\s+', ' ', expected_stripped)
            if predicted_stripped == expected_stripped:
                predicted_norm = expected_norm  # treat as match

        if predicted_norm == expected_norm:
            # Check for hallucinated execution (decode_and_act only)
            if task_mode == "decode_and_act":
                plaintext = task_params.get("plaintext", "")
                if not _plaintext_evidence(parsed_answer.raw_response, plaintext):
                    return EvaluationResult(
                        correct=True, match_type="hallucinated_execution", accuracy=1.0,
                        details=details,
                    )
            return EvaluationResult(
                correct=True, match_type="correct", accuracy=1.0,
                details=details,
            )

        # 4. Wrong decode
        return EvaluationResult(
            correct=False, match_type="wrong_decode", accuracy=0.0,
            details=details,
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        base = super().aggregate_results(results)
        total = base.get("total", 0) or 1  # avoid div-by-zero

        # Per-mode breakdown
        mode_stats: Dict[str, Dict[str, int]] = {}
        # Per-encoding breakdown
        encoding_stats: Dict[str, Dict[str, int]] = {}
        # Per-shift breakdown (caesar only)
        shift_stats: Dict[int, Dict[str, int]] = {}

        for r in results:
            d = r.details or {}

            # Mode
            mode = d.get("task_mode", "unknown")
            ms = mode_stats.setdefault(mode, {"correct": 0, "total": 0})
            ms["total"] += 1
            if r.correct:
                ms["correct"] += 1

            # Encoding
            enc = d.get("encoding_type", "unknown")
            es = encoding_stats.setdefault(enc, {"correct": 0, "total": 0})
            es["total"] += 1
            if r.correct:
                es["correct"] += 1

            # Caesar shift
            if enc == "caesar" and d.get("caesar_shift") is not None:
                shift = d["caesar_shift"]
                ss = shift_stats.setdefault(shift, {"correct": 0, "total": 0})
                ss["total"] += 1
                if r.correct:
                    ss["correct"] += 1

        def _with_accuracy(stats: Dict[str, int]) -> Dict[str, Any]:
            t = stats["total"] or 1
            return {**stats, "accuracy": stats["correct"] / t}

        base["mode_breakdown"] = {k: _with_accuracy(v) for k, v in mode_stats.items()}
        base["encoding_breakdown"] = {k: _with_accuracy(v) for k, v in encoding_stats.items()}
        base["caesar_shift_breakdown"] = {k: _with_accuracy(v) for k, v in shift_stats.items()}

        # Failure-taxonomy rates
        match_types = base.get("match_types", {})
        base["refusal_rate"] = match_types.get("paranoid_refusal", 0) / total
        base["hallucination_rate"] = match_types.get("hallucinated_execution", 0) / total
        base["wrong_decode_rate"] = match_types.get("wrong_decode", 0) / total
        base["parse_error_rate"] = match_types.get("parse_error", 0) / total

        return base
