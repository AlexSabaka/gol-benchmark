"""Result evaluator for the fancy_unicode plugin.

Implements a 7-type failure taxonomy:

  correct              — exact match after NFKD normalization
  bypassed_decode      — decode_and_act: correct word but no decoding evidence
                         (world-knowledge bypass — model knew the answer without decoding)
  hallucinated_decode  — decode_and_act: wrong word + confident wrong decode narrative
                         (model invented a plausible but incorrect decoded string)
  paranoid_refusal     — model refused to process the text
  runaway_refusal      — response hit max_tokens without a usable answer
  wrong_decode         — answer extracted but incorrect
  parse_error          — no usable answer could be extracted
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator
from .parser import REFUSAL_SENTINEL, RUNAWAY_SENTINEL
from .families import decode_to_ascii

# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def _nfkd_ascii(s: Any) -> str:
    """Decode fancy Unicode, lowercase, collapse whitespace for comparison.

    Uses the full reverse-map from families.py so that small_caps and
    Tier-3 emoji families (which NFKD alone does not handle) are correctly
    normalised before evaluation.
    """
    text = str(s).lower().strip()
    # Strip leading markdown artifacts (e.g. Grok's "** sentence", "# sentence")
    text = re.sub(r"^[\*#\s]+", "", text)
    text = text.strip(".,;:!?\"'`")
    decoded = decode_to_ascii(text)
    return re.sub(r"\s+", " ", decoded).strip()


def _strip_for_compare(s: str) -> str:
    """Aggressively strip punctuation and markdown for secondary comparison.

    Used as a fallback in decode_only evaluation to handle models that add
    inter-sentence periods, surround answers in quotes/bold, prefix with '#'
    or '**', or use different casing than the expected ground truth.
    """
    # Strip leading markdown
    s = re.sub(r"^[\*#\s]+", "", s)
    # Strip all punctuation characters
    s = re.sub(r"""[.,;:!?"'`\*#]""", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# Plaintext evidence helpers (shared logic with encoding_cipher)
# ---------------------------------------------------------------------------

def _plaintext_evidence(raw_response: str, plaintext: str, threshold: float = 0.40) -> bool:
    """Return True if a substantial portion of *plaintext* appears in *raw_response*.

    Used to distinguish genuine decoding (correct word AND decode visible in
    response) from world-knowledge bypass (correct word, no decode evidence).
    """
    response_lower = raw_response.lower()
    plain_words = plaintext.lower().split()
    if not plain_words:
        return False
    # Check if full plaintext appears verbatim
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


_DECODE_CLAIM_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bdecoded?\s*(?:text|message|string)?\s*[:=\-]", re.IGNORECASE),
    re.compile(r"\bthe\s+(?:message|text|word|phrase)\s+(?:is|says|reads)\b", re.IGNORECASE),
    re.compile(r"\bplaintext\s*[:=\-]", re.IGNORECASE),
    re.compile(r"\boriginal\s+(?:text|message)\s*[:=\-]", re.IGNORECASE),
    re.compile(r"\btranslat(?:es?|ion|ed)\s*[:=\-]", re.IGNORECASE),
    re.compile(r"\bconvert(?:s|ed)?\s+(?:to|back\s+to)\s+", re.IGNORECASE),
]


def _has_confident_decode_narrative(response: str, plaintext: str) -> bool:
    """Return True if the response contains a confident decode claim that
    does NOT match the real plaintext.

    Condition: response has decode-claim language AND < 40 % of real plaintext
    words appear in the response.
    """
    has_claim = any(p.search(response) for p in _DECODE_CLAIM_PATTERNS)
    if not has_claim:
        return False
    # The claim is about a different (fictional) text
    return not _plaintext_evidence(response, plaintext, threshold=0.40)


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class FancyUnicodeEvaluator(ResultEvaluator):
    """Evaluates fancy_unicode responses using a 7-type failure taxonomy."""

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        task_params = task_params or {}
        task_mode = task_params.get("task_mode", "decode_only")
        family = task_params.get("encoding_family", "unknown")
        message_length = task_params.get("message_length", "medium")

        details: Dict[str, Any] = {
            "predicted": None,  # filled below
            "expected": expected_answer,
            "task_mode": task_mode,
            "encoding_family": family,
            "message_length": message_length,
            "parse_strategy": parsed_answer.parse_strategy,
            "confidence": parsed_answer.confidence,
        }

        # 1. Runaway refusal — response hit max_tokens
        if parsed_answer.parse_strategy == "runaway_refusal":
            details["predicted"] = "__RUNAWAY__"
            return EvaluationResult(
                correct=False, match_type="runaway_refusal", accuracy=0.0,
                details=details,
            )

        # 2. Parse error — no value could be extracted
        if parsed_answer.error and parsed_answer.value is None:
            details["predicted"] = None
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details=details,
            )

        # 3. Paranoid refusal
        if parsed_answer.value == REFUSAL_SENTINEL:
            details["predicted"] = "__REFUSAL__"
            return EvaluationResult(
                correct=False, match_type="paranoid_refusal", accuracy=0.0,
                details=details,
            )

        details["predicted"] = parsed_answer.value

        # Normalise both sides for comparison
        predicted_norm = _nfkd_ascii(parsed_answer.value)
        expected_norm = _nfkd_ascii(expected_answer)

        if task_mode == "decode_only":
            return self._evaluate_decode_only(
                predicted_norm, expected_norm, details,
            )
        else:
            return self._evaluate_decode_and_act(
                predicted_norm, expected_norm, parsed_answer, task_params, details,
            )

    # ------------------------------------------------------------------
    # decode_only evaluation
    # ------------------------------------------------------------------

    def _evaluate_decode_only(
        self,
        predicted_norm: str,
        expected_norm: str,
        details: Dict[str, Any],
    ) -> EvaluationResult:
        # Level 1: exact match after NFKD + fancy-decode normalization
        if predicted_norm == expected_norm:
            return EvaluationResult(
                correct=True, match_type="correct", accuracy=1.0,
                details=details,
            )
        # Level 2: punctuation-stripped match — handles:
        #   A) model adds inter-sentence periods (expected has none)
        #   B) Grok "** sentence" leading prefix
        #   C) outer quotes surviving extraction
        #   D) bold **answer** asterisks
        #   F) case differences after fancy-decode
        pred_stripped = _strip_for_compare(predicted_norm)
        exp_stripped = _strip_for_compare(expected_norm)
        if pred_stripped and pred_stripped == exp_stripped:
            return EvaluationResult(
                correct=True, match_type="correct", accuracy=1.0,
                details=details,
            )
        return EvaluationResult(
            correct=False, match_type="wrong_decode", accuracy=0.0,
            details={**details, "got": predicted_norm, "expected_norm": expected_norm},
        )

    # ------------------------------------------------------------------
    # decode_and_act evaluation (5 possible outcomes)
    # ------------------------------------------------------------------

    def _evaluate_decode_and_act(
        self,
        predicted_norm: str,
        expected_norm: str,
        parsed_answer: ParsedAnswer,
        task_params: Dict[str, Any],
        details: Dict[str, Any],
    ) -> EvaluationResult:
        word_correct = (predicted_norm == expected_norm)
        plaintext = task_params.get("plaintext", "")
        raw_response = parsed_answer.raw_response

        # Compute plaintext evidence in the response
        has_evidence = _plaintext_evidence(raw_response, plaintext)
        # Fix E: model may echo the answer still in fancy Unicode encoding.
        # A still-encoded response IS evidence of having decoded the text —
        # decode the raw response and check again.
        if not has_evidence and not raw_response.isascii():
            decoded_raw = decode_to_ascii(raw_response).strip()
            # If the decoded response contains the expected word, the model decoded
            if expected_norm in decoded_raw.lower():
                has_evidence = True
        plain_word_count = len(plaintext.split())

        details["plaintext_coverage"] = (
            "present" if has_evidence else "absent"
        )

        # (a) correct + evidence → genuine decode
        if word_correct and has_evidence:
            return EvaluationResult(
                correct=True, match_type="correct", accuracy=1.0,
                details=details,
            )

        # (b) correct word, no plaintext evidence → world-knowledge bypass
        if word_correct and not has_evidence:
            # Very short instructions (≤4 content words) are ambiguous; treat as correct.
            if plain_word_count <= 4:
                return EvaluationResult(
                    correct=True, match_type="correct", accuracy=1.0,
                    details=details,
                )
            return EvaluationResult(
                correct=False, match_type="bypassed_decode", accuracy=0.0,
                details=details,
            )

        # (c) wrong word + confident decode narrative (wrong content) → hallucinated_decode
        if _has_confident_decode_narrative(raw_response, plaintext):
            return EvaluationResult(
                correct=False, match_type="hallucinated_decode", accuracy=0.0,
                details={**details, "got": predicted_norm, "expected_norm": expected_norm},
            )

        # (d) wrong word, no confident narrative → wrong_decode
        return EvaluationResult(
            correct=False, match_type="wrong_decode", accuracy=0.0,
            details={**details, "got": predicted_norm, "expected_norm": expected_norm},
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        base = super().aggregate_results(results)
        total = max(base.get("total", 0), 1)

        # Per-family breakdown (primary research output)
        by_family: Dict[str, List[EvaluationResult]] = defaultdict(list)
        by_mode: Dict[str, List[EvaluationResult]] = defaultdict(list)

        for r in results:
            d = r.details or {}
            by_family[d.get("encoding_family", "unknown")].append(r)
            by_mode[d.get("task_mode", "unknown")].append(r)

        def _family_stats(fam_results: List[EvaluationResult]) -> Dict[str, Any]:
            n = len(fam_results) or 1
            mt = Counter(r.match_type for r in fam_results)
            return {
                "count": len(fam_results),
                "accuracy": sum(1 for r in fam_results if r.correct) / n,
                "bypassed_decode_rate":   mt.get("bypassed_decode", 0) / n,
                "hallucinated_decode_rate": mt.get("hallucinated_decode", 0) / n,
                "paranoid_refusal_rate":  mt.get("paranoid_refusal", 0) / n,
                "runaway_refusal_rate":   mt.get("runaway_refusal", 0) / n,
                "wrong_decode_rate":      mt.get("wrong_decode", 0) / n,
                "parse_error_rate":       mt.get("parse_error", 0) / n,
            }

        base["by_family"] = {
            fam: _family_stats(fam_results)
            for fam, fam_results in sorted(by_family.items())
        }

        base["by_mode"] = {
            mode: {
                "count":    len(mode_results),
                "accuracy": sum(1 for r in mode_results if r.correct) / max(len(mode_results), 1),
            }
            for mode, mode_results in sorted(by_mode.items())
        }

        # Suite-level rates
        mt_total = base.get("match_types", {})
        base["bypassed_decode_rate"]     = mt_total.get("bypassed_decode", 0) / total
        base["hallucinated_decode_rate"] = mt_total.get("hallucinated_decode", 0) / total
        base["paranoid_refusal_rate"]    = mt_total.get("paranoid_refusal", 0) / total
        base["runaway_refusal_rate"]     = mt_total.get("runaway_refusal", 0) / total
        base["wrong_decode_rate"]        = mt_total.get("wrong_decode", 0) / total
        base["parse_error_rate"]         = mt_total.get("parse_error", 0) / total

        return base
