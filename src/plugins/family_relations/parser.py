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
from src.plugins.parse_utils import (
    re_search_last,
    build_word_to_int,
    build_answer_label_re,
    get_language,
)

_INT_PATTERN = re.compile(r"(?<![.\d])\d+(?![.\d])")


def _try_parse_int(text: str, word_map: Optional[Dict[str, int]] = None) -> Optional[int]:
    """Try to interpret *text* as a single non-negative integer."""
    text = text.strip().rstrip(".,;:!?)")
    m = re.fullmatch(r"\d+", text)
    if m:
        return int(m.group())
    low = text.lower().strip(" .")
    if word_map and low in word_map:
        return word_map[low]
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
        lang = get_language(task_params or {})
        word_map = build_word_to_int(lang)

        # Strategy 1: LaTeX \boxed{N} (last match)
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text)
        if boxed:
            val = _try_parse_int(boxed.group(1), word_map)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="boxed", confidence=0.95)

        # Strategy 2: Bold **N** (last match)
        bold = re_search_last(r"\*\*([^*]{1,20})\*\*", text)
        if bold:
            val = _try_parse_int(bold.group(1), word_map)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="bold", confidence=0.90)

        # Strategy 3: Labelled line (last match) — multilingual labels
        label_alt = build_answer_label_re(lang)
        label = re_search_last(
            r"(?:" + label_alt + r"|total|count|number\s+of\s+\w+)"
            r"(?:\s+is|\s*=|\s*[:：])\s*(\S+)",
            text, re.IGNORECASE,
        )
        if label:
            val = _try_parse_int(label.group(1), word_map)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="label_line", confidence=0.85)

        # Strategy 4: "is N" / "are N" at end of line (last match)
        is_n = re_search_last(
            r"(?:is|are|=)\s+(\S+)\s*[.!]?\s*$",
            text, re.IGNORECASE | re.MULTILINE,
        )
        if is_n:
            val = _try_parse_int(is_n.group(1), word_map)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="is_n_tail", confidence=0.82)

        # Strategy 5: Last standalone integer
        all_ints = _INT_PATTERN.findall(text)
        if all_ints:
            val = _try_parse_int(all_ints[-1], word_map)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="last_number", confidence=0.70)

        # Strategy 6: Spelled-out number word (last match) — multilingual
        word_num_pattern = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in word_map) + r")\b",
            re.IGNORECASE,
        )
        word_match = re_search_last(word_num_pattern, text)
        if word_match:
            val = word_map.get(word_match.group(1).lower())
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text,
                                    parse_strategy="spelled_out", confidence=0.55)

        return ParsedAnswer(
            value=None,
            raw_response=text,
            parse_strategy="parse_error",
            confidence=0.1,
            error="Could not extract an integer from response",
        )
