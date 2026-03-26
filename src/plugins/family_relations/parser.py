"""
Family Relations – Response Parser

Extracts an integer answer from a model's free-form response using
end-first multi-strategy parsing (same pipeline as strawberry/count).

Strategies (tried in order, each picks the LAST match):
  1. LaTeX  \\boxed{N}
  2. Bold   **N**
  3. Labelled line  "Answer: N" / "Total: N"
  4. "is N" / "are N" at end of line
  5. Last standalone integer
  6. Spelled-out number word (last match)
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from src.plugins.base import ResponseParser, ParsedAnswer
from src.plugins.parse_utils import re_search_last

# ---------------------------------------------------------------------------
# Spelled-out numbers (0–20)
# ---------------------------------------------------------------------------

_WORD_TO_INT: Dict[str, int] = {
    "zero": 0, "no": 0, "none": 0,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}

_WORD_NUM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _WORD_TO_INT) + r")\b",
    re.IGNORECASE,
)

_INT_PATTERN = re.compile(r"(?<![.\d])\d+(?![.\d])")


def _try_parse_int(text: str) -> Optional[int]:
    """Try to interpret *text* as a single non-negative integer."""
    text = text.strip().rstrip(".,;:!?)")
    m = re.fullmatch(r"\d+", text)
    if m:
        return int(m.group())
    low = text.lower().strip(" .")
    if low in _WORD_TO_INT:
        return _WORD_TO_INT[low]
    return None


# ===================================================================
# Parser
# ===================================================================

class FamilyRelationsParser(ResponseParser):
    """Multi-strategy integer parser for family-relations puzzles."""

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

        # Strategy 1: LaTeX \boxed{N} (last match)
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text)
        if boxed:
            val = _try_parse_int(boxed.group(1))
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="boxed", confidence=0.95)

        # Strategy 2: Bold **N** (last match)
        bold = re_search_last(r"\*\*([^*]{1,20})\*\*", text)
        if bold:
            val = _try_parse_int(bold.group(1))
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="bold", confidence=0.90)

        # Strategy 3: Labelled line (last match)
        label = re_search_last(
            r"(?:answer|total|result|count|number\s+of\s+\w+)\s*[:：]\s*(\S+)",
            text, re.IGNORECASE,
        )
        if not label:
            label = re_search_last(
                r"the\s+(?:answer|total|result)\s+is\s+(\S+)",
                text, re.IGNORECASE,
            )
        if label:
            val = _try_parse_int(label.group(1))
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="label_line", confidence=0.88)

        # Strategy 4: "is N" / "are N" at end of line (last match)
        is_n = re_search_last(
            r"(?:is|are|=)\s+(\S+)\s*[.!]?\s*$",
            text, re.IGNORECASE | re.MULTILINE,
        )
        if is_n:
            val = _try_parse_int(is_n.group(1))
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="is_n_tail", confidence=0.85)

        # Strategy 5: Last standalone integer
        all_ints = _INT_PATTERN.findall(text)
        if all_ints:
            val = _try_parse_int(all_ints[-1])
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="last_number", confidence=0.70)

        # Strategy 6: Spelled-out number word (last match)
        word_match = re_search_last(_WORD_NUM_PATTERN, text)
        if word_match:
            val = _WORD_TO_INT.get(word_match.group(1).lower())
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="spelled_out", confidence=0.55)

        return ParsedAnswer(
            value=None,
            raw_response=text,
            parse_strategy="fallback",
            confidence=0.1,
            error="Could not extract an integer from response",
        )
