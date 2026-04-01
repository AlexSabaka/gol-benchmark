"""
Strawberry (Character-Level Reasoning) – Response Parser

Dispatches to sub-type–specific parsing pipelines:

  count       → integer extraction  (original 6-strategy pipeline)
  reverse     → reversed-word extraction
  nth_letter  → single-character extraction
  anagram     → boolean (yes/no) extraction
  pangram     → boolean (yes/no) extraction
  lipogram    → boolean (yes/no) extraction

All pipelines use end-first matching via ``re_search_last``.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from src.plugins.base import ResponseParser, ParsedAnswer
from src.plugins.parse_utils import (
    build_word_to_int,
    get_language,
    merge_keywords,
    re_search_last,
    strip_verification_tail,
    YES_WORDS,
    NO_WORDS,
)

_INT_PATTERN = re.compile(r"(?<![.\d])-?\d+(?![.\d])")


def _build_word_num_pattern(word_map: Dict[str, int]) -> re.Pattern:
    """Build a compiled regex matching any key in *word_map*."""
    return re.compile(
        r"\b(" + "|".join(re.escape(w) for w in word_map) + r")\b",
        re.IGNORECASE,
    )


def _try_parse_int(
    text: str,
    word_map: Dict[str, int],
    word_length: Optional[int] = None,
) -> Optional[int]:
    """Try to interpret *text* as a single integer, rejecting bad values."""
    text = text.strip().rstrip(".,;:!?)")
    m = re.fullmatch(r"-?\d+", text)
    if m:
        val = int(m.group())
        if val < 0:
            return None
        if word_length is not None and val > word_length:
            return None
        return val
    low = text.lower().strip(" .")
    if low in word_map:
        return word_map[low]
    return None


# ===================================================================
# Main parser
# ===================================================================

class StrawberryParser(ResponseParser):
    """Multi-strategy parser for character-level reasoning tasks."""

    def parse(
        self,
        response: str,
        task_params: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedAnswer:
        if not response or not response.strip():
            return ParsedAnswer(
                value=None, raw_response=response or "",
                parse_strategy="empty", confidence=0.0, error="Empty response",
            )

        sub_type = (task_params or {}).get("sub_type", "count")

        if sub_type == "count":
            return self._parse_count(response, task_params or {})
        elif sub_type == "reverse":
            return self._parse_reversed_word(response, task_params or {})
        elif sub_type == "nth_letter":
            return self._parse_nth_letter(response, task_params or {})
        elif sub_type in ("anagram", "pangram", "lipogram"):
            return self._parse_boolean(response, task_params or {})
        else:
            return self._parse_count(response, task_params or {})

    # ------------------------------------------------------------------
    # COUNT  (original pipeline, unchanged)
    # ------------------------------------------------------------------

    def _parse_count(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        text = response.strip()
        word_length = task_params.get("word_length")
        lang = get_language(task_params)
        word_map = build_word_to_int(lang)
        word_num_pattern = _build_word_num_pattern(word_map)

        # Strategy 1: LaTeX boxed (last match)
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text)
        if boxed:
            val = _try_parse_int(boxed.group(1), word_map, word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="boxed", confidence=0.95)

        # Strategy 2: Bold (last match)
        bold = re_search_last(r"\*\*([^*]{1,20})\*\*", text)
        if bold:
            val = _try_parse_int(bold.group(1), word_map, word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="bold", confidence=0.9)

        # Strategy 3: Labelled line (last match)
        label = re_search_last(
            r"(?:answer|count|result|total|there\s+(?:are|is))\s*[:：]?\s*(\S+)",
            text, re.IGNORECASE,
        )
        if not label:
            label = re_search_last(
                r"the\s+(?:answer|count|result|total)\s+is\s+(\S+)",
                text, re.IGNORECASE,
            )
        if label:
            val = _try_parse_int(label.group(1), word_map, word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="label_line", confidence=0.88)

        # Strategy 3b: "is N" / "are N" at EOL
        is_n = re_search_last(
            r"(?:is|are|=)\s+(\S+)\s*[.!]?\s*$",
            text, re.IGNORECASE | re.MULTILINE,
        )
        if is_n:
            val = _try_parse_int(is_n.group(1), word_map, word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="is_n_tail", confidence=0.85)

        # Strategy 4: Last standalone integer
        all_ints = _INT_PATTERN.findall(text)
        if all_ints:
            val = _try_parse_int(all_ints[-1], word_map, word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="last_number", confidence=0.75)

        # Strategy 5: First standalone integer
        if all_ints:
            val = _try_parse_int(all_ints[0], word_map, word_length)
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="first_number", confidence=0.6)

        # Strategy 6: Spelled-out number (last match)
        word_match = re_search_last(word_num_pattern, text)
        if word_match:
            val = word_map.get(word_match.group(1).lower())
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="spelled_out", confidence=0.55)

        return ParsedAnswer(
            value=None, raw_response=text, parse_strategy="fallback",
            confidence=0.1, error="Could not extract an integer count from response",
        )

    # ------------------------------------------------------------------
    # REVERSE
    # ------------------------------------------------------------------

    def _parse_reversed_word(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        text = response.strip()
        expected_len = task_params.get("word_length")

        def _valid(candidate: str) -> Optional[str]:
            c = candidate.strip().strip(".,;:!?'\"-").lower()
            if not c or not c.isalpha():
                return None
            if expected_len is not None and len(c) != expected_len:
                return None
            return c

        # Strategy 1: LaTeX boxed
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text)
        if boxed:
            v = _valid(boxed.group(1))
            if v:
                return ParsedAnswer(value=v, raw_response=text, parse_strategy="boxed", confidence=0.95)

        # Strategy 2: Bold
        bold = re_search_last(r"\*\*([^*]{1,40})\*\*", text)
        if bold:
            v = _valid(bold.group(1))
            if v:
                return ParsedAnswer(value=v, raw_response=text, parse_strategy="bold", confidence=0.90)

        # Strategy 3: Labelled ("Answer:", "Result:", "Reversed:", "The reverse is")
        label = re_search_last(
            r"(?:answer|result|reversed?|backwards?)\s*[:：]\s*[\"']?(\S+)[\"']?",
            text, re.IGNORECASE,
        )
        if not label:
            label = re_search_last(
                r"the\s+revers(?:e|ed)\s+(?:is|word\s+is)\s+[\"']?(\S+)[\"']?",
                text, re.IGNORECASE,
            )
        if label:
            v = _valid(label.group(1))
            if v:
                return ParsedAnswer(value=v, raw_response=text, parse_strategy="label_line", confidence=0.85)

        # Strategy 4: Quoted word (last)
        quoted = re_search_last(r"[\"'`]([a-zA-Z]+)[\"'`]", text)
        if quoted:
            v = _valid(quoted.group(1))
            if v:
                return ParsedAnswer(value=v, raw_response=text, parse_strategy="quoted", confidence=0.80)

        # Strategy 5: Last standalone alphabetic token
        alpha_tokens = re.findall(r"\b([a-zA-Z]+)\b", text)
        if alpha_tokens:
            v = _valid(alpha_tokens[-1])
            if v:
                return ParsedAnswer(value=v, raw_response=text, parse_strategy="last_alpha", confidence=0.65)

        return ParsedAnswer(
            value=None, raw_response=text, parse_strategy="fallback",
            confidence=0.1, error="Could not extract reversed word from response",
        )

    # ------------------------------------------------------------------
    # NTH LETTER
    # ------------------------------------------------------------------

    def _parse_nth_letter(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        text = response.strip()

        def _valid_char(candidate: str) -> Optional[str]:
            c = candidate.strip().strip(".,;:!?'\"-").lower()
            if len(c) == 1 and c.isalpha():
                return c
            return None

        # Strategy 1: LaTeX boxed
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text)
        if boxed:
            v = _valid_char(boxed.group(1))
            if v:
                return ParsedAnswer(value=v, raw_response=text, parse_strategy="boxed", confidence=0.95)

        # Strategy 2: Bold
        bold = re_search_last(r"\*\*([^*]{1,5})\*\*", text)
        if bold:
            v = _valid_char(bold.group(1))
            if v:
                return ParsedAnswer(value=v, raw_response=text, parse_strategy="bold", confidence=0.90)

        # Strategy 3: Labelled
        label = re_search_last(
            r"(?:answer|result|letter)\s*[:：]\s*[\"']?([a-zA-Z])[\"']?",
            text, re.IGNORECASE,
        )
        if not label:
            label = re_search_last(
                r"the\s+(?:\w+\s+)?letter\s+is\s+[\"']?([a-zA-Z])[\"']?",
                text, re.IGNORECASE,
            )
        if label:
            v = _valid_char(label.group(1))
            if v:
                return ParsedAnswer(value=v, raw_response=text, parse_strategy="label_line", confidence=0.85)

        # Strategy 4: Quoted single char
        quoted = re_search_last(r"[\"'`]([a-zA-Z])[\"'`]", text)
        if quoted:
            v = _valid_char(quoted.group(1))
            if v:
                return ParsedAnswer(value=v, raw_response=text, parse_strategy="quoted", confidence=0.80)

        # Strategy 5: "is X" at end of sentence
        is_char = re_search_last(
            r"is\s+[\"']?([a-zA-Z])[\"']?\s*[.!]?\s*$",
            text, re.IGNORECASE | re.MULTILINE,
        )
        if is_char:
            v = _valid_char(is_char.group(1))
            if v:
                return ParsedAnswer(value=v, raw_response=text, parse_strategy="is_tail", confidence=0.75)

        # Strategy 6: Last standalone single letter (excluding common articles)
        singles = re.findall(r"\b([a-zA-Z])\b", text)
        # Filter out 'a', 'I' (common articles/pronouns)
        candidates = [s for s in singles if s.lower() not in ("a", "i")]
        if candidates:
            v = candidates[-1].lower()
            return ParsedAnswer(value=v, raw_response=text, parse_strategy="last_single", confidence=0.60)

        return ParsedAnswer(
            value=None, raw_response=text, parse_strategy="fallback",
            confidence=0.1, error="Could not extract a single letter from response",
        )

    # ------------------------------------------------------------------
    # BOOLEAN  (shared by anagram / pangram / lipogram)
    # ------------------------------------------------------------------

    def _parse_boolean(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        text = strip_verification_tail(response.strip())
        lang = get_language(task_params)
        yes_words = set(merge_keywords(YES_WORDS, lang))
        no_words = set(merge_keywords(NO_WORDS, lang))

        def _to_bool(candidate: str) -> Optional[bool]:
            c = candidate.strip().strip(".,;:!?'\"-").lower()
            if c in yes_words:
                return True
            if c in no_words:
                return False
            return None

        # Strategy 1: LaTeX boxed
        boxed = re_search_last(r"\\boxed\{([^}]+)\}", text)
        if boxed:
            val = _to_bool(boxed.group(1))
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="boxed", confidence=0.95)

        # Strategy 2: Bold
        bold = re_search_last(r"\*\*([^*]{1,20})\*\*", text)
        if bold:
            val = _to_bool(bold.group(1))
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="bold", confidence=0.90)

        # Strategy 3: Labelled line
        label = re_search_last(
            r"(?:answer|result|verdict)\s*[:：]\s*(\S+)",
            text, re.IGNORECASE,
        )
        if label:
            val = _to_bool(label.group(1))
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="label_line", confidence=0.85)

        # Strategy 4: "the answer is yes/no"
        ans_is = re_search_last(
            r"the\s+answer\s+is\s+(\S+)",
            text, re.IGNORECASE,
        )
        if ans_is:
            val = _to_bool(ans_is.group(1))
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="answer_is", confidence=0.85)

        # Strategy 4b: First yes/no keyword in opening fragment
        # Models often state their answer first ("Yes.", "False."), then explain.
        # Check the first line / first sentence for an unambiguous keyword.
        yes_no_pattern = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in (yes_words | no_words)) + r")\b",
            re.IGNORECASE,
        )
        first_line = text.split('\n', 1)[0].strip()
        first_sent = re.split(r'[.!?\n]', text, maxsplit=1)[0].strip()
        for fragment in (first_line, first_sent):
            if fragment and len(fragment) < 80:
                first_kw = yes_no_pattern.search(fragment)
                if first_kw:
                    val = _to_bool(first_kw.group(1))
                    if val is not None:
                        return ParsedAnswer(
                            value=val, raw_response=text,
                            parse_strategy="first_keyword", confidence=0.78,
                        )

        # Strategy 5: Last yes/no keyword
        last_kw = re_search_last(yes_no_pattern, text)
        if last_kw:
            val = _to_bool(last_kw.group(1))
            if val is not None:
                return ParsedAnswer(value=val, raw_response=text, parse_strategy="last_keyword", confidence=0.70)

        return ParsedAnswer(
            value=None, raw_response=text, parse_strategy="fallback",
            confidence=0.1, error="Could not extract a yes/no answer from response",
        )
