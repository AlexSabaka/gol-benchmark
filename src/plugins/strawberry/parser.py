"""
Strawberry (Letter Counting) – Response Parser

Extracts an integer from a model's free-form response.

Strategy pipeline (tried in order):
 1. Boxed answer   \\boxed{N}
 2. Bold answer    **N**
 3. Labelled line  Answer: N / Count: N / Result: N / The answer is N
 4. Last number    last standalone integer in the response
 5. First number   first standalone integer in the response
 6. Fallback       → None with parse error

Also handles spelled-out numbers: "zero" → 0, "three" → 3, etc.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from src.plugins.base import ResponseParser, ParsedAnswer
from src.plugins.parse_utils import re_search_last

# ---------------------------------------------------------------------------
# Spelled-out number map (0–20 + common larger ones)
# ---------------------------------------------------------------------------

_WORD_TO_INT: Dict[str, int] = {
    "zero": 0, "no": 0, "none": 0,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}

# Pattern that matches a spelled-out number as a whole word
_WORD_NUM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _WORD_TO_INT) + r")\b",
    re.IGNORECASE,
)

# Standalone integer (possibly negative)
_INT_PATTERN = re.compile(r"(?<![.\d])-?\d+(?![.\d])")


def _try_parse_int(text: str, word_length: Optional[int] = None) -> Optional[int]:
    """Try to interpret *text* as a single integer, rejecting bad values."""
    text = text.strip().rstrip(".,;:!?)")

    # Numeric literal
    m = re.fullmatch(r"-?\d+", text)
    if m:
        val = int(m.group())
        if val < 0:
            return None
        if word_length is not None and val > word_length:
            return None
        return val

    # Spelled-out number
    low = text.lower().strip(" .")
    if low in _WORD_TO_INT:
        return _WORD_TO_INT[low]

    return None


class StrawberryParser(ResponseParser):
    """Multi-strategy parser for letter-counting responses."""

    def parse(
        self,
        response: str,
        task_params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedAnswer:
        if not response or not response.strip():
            return ParsedAnswer(
                value=None,
                raw_response=response or "",
                parse_strategy="empty",
                confidence=0.0,
                error="Empty response",
            )

        text = response.strip()
        word_length = (task_params or {}).get("word_length")

        # --- Strategy 1: LaTeX boxed (last match) ---
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text)
        if boxed:
            val = _try_parse_int(boxed.group(1), word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="boxed", confidence=0.95)

        # --- Strategy 2: Bold (last match) ---
        bold = re_search_last(r"\*\*([^*]{1,20})\*\*", text)
        if bold:
            val = _try_parse_int(bold.group(1), word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="bold", confidence=0.9)

        # --- Strategy 3: Labelled line (last match) ---
        label = re_search_last(
            r"(?:answer|count|result|total|there\s+(?:are|is))\s*[:：]?\s*(\S+)",
            text,
            re.IGNORECASE,
        )
        if not label:
            # "The answer is N" / "the count is N"
            label = re_search_last(
                r"the\s+(?:answer|count|result|total)\s+is\s+(\S+)",
                text,
                re.IGNORECASE,
            )
        if label:
            val = _try_parse_int(label.group(1), word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="label_line", confidence=0.88)

        # --- Strategy 3b: "is N" / "are N" at end of sentence (last match) ---
        is_n = re_search_last(
            r"(?:is|are|=)\s+(\S+)\s*[.!]?\s*$",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if is_n:
            val = _try_parse_int(is_n.group(1), word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="is_n_tail", confidence=0.85)

        # --- Strategy 4: Last standalone integer ---
        all_ints = _INT_PATTERN.findall(text)
        if all_ints:
            # Try last number first
            val = _try_parse_int(all_ints[-1], word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="last_number", confidence=0.75)

        # --- Strategy 5: First standalone integer ---
        if all_ints:
            val = _try_parse_int(all_ints[0], word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="first_number", confidence=0.6)

        # --- Strategy 6: Spelled-out number (last match) ---
        word_match = re_search_last(_WORD_NUM_PATTERN, text)
        if word_match:
            val = _WORD_TO_INT.get(word_match.group(1).lower())
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="spelled_out", confidence=0.55)

        # --- Fallback ---
        return ParsedAnswer(
            value=None,
            raw_response=text,
            parse_strategy="fallback",
            confidence=0.1,
            error="Could not extract an integer count from response",
        )
