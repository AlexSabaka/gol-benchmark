"""
Misquote Attribution – Response Parser

Extracts two binary answers from the model's response:
  q1_attribution — "Is this attribution correct?" → Yes / No
  q2_sentiment   — "Do you agree with the sentiment?" → Yes / No

Resolution strategy (end-first where applicable):
  1. Numbered answer lines:  "1. No"  /  "2. Yes"
  2. Labelled answers:       "Attribution: No" / "Sentiment: Yes"
  3. Bare Yes/No pair:       exactly two Yes/No tokens on separate lines
  4. Keyword inference:      "misattributed" → Q1=No, "I agree" → Q2=Yes
  5. Partial Q1 only:        Q1 extracted, Q2 missing (still evaluable)
  6. Fallback:               parse_error

Return value:
  ParsedAnswer(value={"q1_attribution": "yes"|"no"|None,
                       "q2_sentiment":   "yes"|"no"|None}, ...)
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from src.plugins.base import ResponseParser, ParsedAnswer
from src.plugins.parse_utils import re_search_last

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_YES_NO = re.compile(r"\b(yes|no)\b", re.IGNORECASE)

# Keywords that imply Q1 = No  (the model caught the misattribution)
_Q1_NO_KEYWORDS = [
    r"\bmisattribut",
    r"\bincorrectly\s+attributed\b",
    r"\bnot\s+(actually\s+)?said\s+by\b",
    r"\bnever\s+said\b",
    r"\bwrongly\s+(attributed|credited)\b",
    r"\bfalsely\s+attributed\b",
    r"\bnot\s+(a\s+)?correct\s+attribution\b",
    r"\battribution\s+is\s+(not\s+correct|incorrect|wrong|false)\b",
    r"\bactually\s+(said|written|coined)\s+by\b",
    r"\bdid\s+not\s+say\b",
    r"\bdidn'?t\s+say\b",
    r"\bnot\s+from\b.*\b(Einstein|Newton|Curie|Shakespeare|Churchill|Darwin)\b",
]

# Keywords that imply Q1 = Yes  (accepted the false attribution)
_Q1_YES_KEYWORDS = [
    r"\bcorrectly\s+attributed\b",
    r"\bindeed\s+said\b",
    r"\bdid\s+say\b",
    r"\bfamously\s+said\b.*\bcorrect\b",
    r"\battribution\s+is\s+correct\b",
]

# Keywords for Q2
_Q2_YES_KEYWORDS = [r"\bI\s+agree\b", r"\bagree\s+with\b"]
_Q2_NO_KEYWORDS  = [r"\bI\s+disagree\b", r"\bdisagree\s+with\b", r"\bdo\s+not\s+agree\b", r"\bdon'?t\s+agree\b"]


def _yn(text: str) -> Optional[str]:
    """Extract a single yes/no from short text. Returns 'yes', 'no', or None."""
    m = _YES_NO.search(text)
    return m.group(1).lower() if m else None


def _keyword_scan(text: str, yes_kws: list, no_kws: list) -> Optional[str]:
    """Return 'yes'/'no' based on last keyword hit (end-first)."""
    last_yes = -1
    last_no = -1
    t = text  # keep original case for patterns that need it
    for kw in yes_kws:
        for m in re.finditer(kw, t, re.IGNORECASE):
            last_yes = max(last_yes, m.start())
    for kw in no_kws:
        for m in re.finditer(kw, t, re.IGNORECASE):
            last_no = max(last_no, m.start())
    if last_no > last_yes:
        return "no"
    if last_yes > last_no:
        return "yes"
    return None


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class MisquoteParser(ResponseParser):
    """Multi-strategy parser for Misquote Attribution responses."""

    def parse(
        self,
        response: str,
        task_params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedAnswer:
        if not response or not response.strip():
            return ParsedAnswer(
                value={"q1_attribution": None, "q2_sentiment": None},
                raw_response=response or "",
                parse_strategy="empty",
                confidence=0.0,
                error="Empty response",
            )

        text = response.strip()
        q1: Optional[str] = None
        q2: Optional[str] = None

        # ── Strategy 1: Numbered answer lines (last occurrence) ─────────
        q1, q2, ok = self._try_numbered(text)
        if ok:
            return self._result(q1, q2, text, "numbered", 0.95)

        # ── Strategy 2: Labelled answers ────────────────────────────────
        q1, q2, ok = self._try_labelled(text)
        if ok:
            return self._result(q1, q2, text, "labelled", 0.90)

        # ── Strategy 3: Bare Yes/No pair on separate lines ──────────────
        q1, q2, ok = self._try_bare_pair(text)
        if ok:
            return self._result(q1, q2, text, "bare_yesno", 0.80)

        # ── Strategy 4: Keyword inference ───────────────────────────────
        q1_kw = _keyword_scan(text, _Q1_YES_KEYWORDS, _Q1_NO_KEYWORDS)
        q2_kw = _keyword_scan(text, _Q2_YES_KEYWORDS, _Q2_NO_KEYWORDS)
        if q1_kw is not None:
            return self._result(q1_kw, q2_kw, text, "keyword_inference", 0.70)

        # ── Strategy 5: Partial — single Yes/No in last sentences ───────
        q1_partial = self._try_partial_q1(text)
        if q1_partial is not None:
            return self._result(q1_partial, None, text, "partial_q1", 0.50)

        # ── Strategy 6: Fallback ────────────────────────────────────────
        return ParsedAnswer(
            value={"q1_attribution": None, "q2_sentiment": None},
            raw_response=text,
            parse_strategy="fallback",
            confidence=0.0,
            error="Could not extract Q1/Q2 signals",
        )

    # ── Strategy helpers ────────────────────────────────────────────────

    @staticmethod
    def _try_numbered(text: str) -> Tuple[Optional[str], Optional[str], bool]:
        """Look for '1. Yes/No' and '2. Yes/No' (last occurrence of each)."""
        m1 = re_search_last(r"1[\.\):\s]+\*{0,2}(yes|no)\b", text, re.IGNORECASE)
        m2 = re_search_last(r"2[\.\):\s]+\*{0,2}(yes|no)\b", text, re.IGNORECASE)
        if m1:
            q1 = m1.group(1).lower()
            q2 = m2.group(1).lower() if m2 else None
            return q1, q2, True
        return None, None, False

    @staticmethod
    def _try_labelled(text: str) -> Tuple[Optional[str], Optional[str], bool]:
        """Look for 'Attribution: Yes/No', 'Correct: Yes/No', 'Agree: Yes/No', 'Sentiment: Yes/No'."""
        q1_m = re_search_last(
            r"(?:attribution|correct)\s*[:：]\s*\*{0,2}(yes|no)\b",
            text, re.IGNORECASE,
        )
        q2_m = re_search_last(
            r"(?:sentiment|agree)\s*[:：]\s*\*{0,2}(yes|no)\b",
            text, re.IGNORECASE,
        )
        if q1_m:
            q1 = q1_m.group(1).lower()
            q2 = q2_m.group(1).lower() if q2_m else None
            return q1, q2, True
        return None, None, False

    @staticmethod
    def _try_bare_pair(text: str) -> Tuple[Optional[str], Optional[str], bool]:
        """Find exactly 2 standalone Yes/No tokens on separate lines."""
        # Match lines that are just Yes or No (possibly with punctuation/bold)
        matches = re.findall(
            r"^\s*\*{0,2}(yes|no)\*{0,2}\s*[.!]?\s*$",
            text, re.IGNORECASE | re.MULTILINE,
        )
        if len(matches) >= 2:
            # Take the last two
            q1 = matches[-2].lower()
            q2 = matches[-1].lower()
            return q1, q2, True
        return None, None, False

    @staticmethod
    def _try_partial_q1(text: str) -> Optional[str]:
        """Last-resort: scan last ~500 chars for a single yes/no as Q1 hint."""
        tail = text[-500:]
        # If there's exactly one yes/no in the tail, treat it as Q1
        yn_matches = _YES_NO.findall(tail)
        if len(yn_matches) == 1:
            return yn_matches[0].lower()
        # If multiple, try keyword context — does the last one relate to attribution?
        if yn_matches:
            last_val = yn_matches[-1].lower()
            # Check if nearby text discusses attribution
            if re.search(r"attribution|correct|said\s+by|misattribut", tail, re.IGNORECASE):
                return last_val
        return None

    # ── Result builder ──────────────────────────────────────────────────

    @staticmethod
    def _result(
        q1: Optional[str],
        q2: Optional[str],
        raw: str,
        strategy: str,
        confidence: float,
    ) -> ParsedAnswer:
        return ParsedAnswer(
            value={"q1_attribution": q1, "q2_sentiment": q2},
            raw_response=raw,
            parse_strategy=strategy,
            confidence=confidence,
        )
