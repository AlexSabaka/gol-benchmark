"""
Arithmetic Response Parser

Multi-strategy parser for extracting numeric answers from model responses.
Handles various response formats including LaTeX, keywords, and plain text.
"""

import json
import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import (
    build_answer_label_re,
    get_language,
    merge_keywords,
    normalize_unicode,
    strip_verification_tail,
)


# Arithmetic-specific label terms layered on top of the shared ANSWER_LABELS
# (answer / result / final answer / solution / response).  `therefore` is a
# common intro in arithmetic explanations; `equals` / `=` capture symbolic
# arithmetic conclusions.  Keep per-language so the keyword_search strategy
# activates correctly on non-English responses too.
_EXTRA_LABELS: Dict[str, List[str]] = {
    "en": ["therefore", "equals"],
    "es": ["por lo tanto", "es igual", "igual a"],
    "fr": ["donc", "est égal", "égale"],
    "de": ["daher", "also", "ist gleich"],
    "zh": ["所以", "因此", "等于"],
    "ua": ["отже", "тому", "дорівнює"],
}


def _build_label_pattern(lang: str) -> str:
    """Return a regex alternation of answer labels for *lang*.

    Combines shared multilingual `ANSWER_LABELS` with arithmetic-specific
    `_EXTRA_LABELS` above.  Always includes English as fallback.
    """
    base = build_answer_label_re(lang)
    extra = merge_keywords(_EXTRA_LABELS, lang)
    extra_alt = "|".join(re.escape(e) for e in extra) if extra else ""
    if base and extra_alt:
        return f"{base}|{extra_alt}"
    return base or extra_alt


class ArithmeticResponseParser(ResponseParser):
    """
    Multi-strategy parser for arithmetic model responses.

    Parsing Strategies:
    0. JSON unescape: Handle escaped LaTeX in JSON responses
    1. LaTeX boxed: Extract from \\boxed{number} patterns
    2. Keyword search: Look for keywords like 'answer', 'result', etc.
    3. Equals pattern: Find "= number" patterns
    4. Last number: Extract the last number in response
    5. Answer patterns: Regex patterns for answer formats
    """

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        """
        Parse a model response to extract the numeric answer.

        Args:
            response: Raw model response string
            task_params: Task parameters (not heavily used for arithmetic)

        Returns:
            ParsedAnswer with extracted number or error
        """
        if not response:
            return ParsedAnswer(
                value=None,
                raw_response=response or "",
                parse_strategy='empty',
                error='Empty response from model'
            )

        response = normalize_unicode(str(response).strip())
        original_response = response
        # Cache the multilingual label alternation for the strategy methods.
        # Computed once per parse() call so the sub-methods don't have to
        # re-derive the language or rebuild the regex.
        self._label_alt = _build_label_pattern(get_language(task_params or {}))

        # Strategy 0: Handle JSON escaping
        response, strategy_0_applied = self._strategy_json_unescape(response)
        if strategy_0_applied:
            # Try LaTeX parsing first on unescaped response
            result = self._strategy_latex_boxed(response)
            if result is not None:
                return ParsedAnswer(
                    value=result,
                    raw_response=original_response,
                    parse_strategy='json_unescape_latex'
                )

        # Weaker keyword / pattern strategies run on a verification-stripped
        # copy.  Models often write "42 is the answer.  Let me verify: 42 + 0
        # = 42.  So the answer is 42." — the end-first strategies would grab
        # an intermediate value from the verification.  LaTeX boxed is kept
        # on the RAW text because `\boxed{}` is a high-signal anchor that
        # usually comes BEFORE the verification section.
        response_clean = strip_verification_tail(response)

        # (name, func, text) tuples.  `text` is None → use the raw response.
        strategies = [
            ('latex_boxed', self._strategy_latex_boxed, None),
            ('keyword_search', self._strategy_keyword_search, response_clean),
            ('equals_pattern', self._strategy_equals_pattern, response_clean),
            ('last_number', self._strategy_last_number, response_clean),
            ('answer_patterns', self._strategy_answer_patterns, response_clean),
        ]

        for name, strategy_func, strategy_text in strategies:
            try:
                result = strategy_func(strategy_text if strategy_text is not None else response)
                if result is not None:
                    return ParsedAnswer(
                        value=result,
                        raw_response=original_response,
                        parse_strategy=name
                    )
            except Exception:
                continue

        return ParsedAnswer(
            value=None,
            raw_response=original_response,
            parse_strategy='fallback',
            error='All parsing strategies failed'
        )

    def get_strategies(self) -> List[str]:
        """Return list of available parsing strategies."""
        return [
            'json_unescape_latex',
            'latex_boxed',
            'keyword_search',
            'equals_pattern',
            'last_number',
            'answer_patterns'
        ]

    def _strategy_json_unescape(self, response: str) -> tuple:
        """
        Strategy 0: Handle JSON escaping.

        Returns (unescaped_response, was_applied)
        """
        try:
            if '\\\\boxed' in response or '\\\\[' in response:
                unescaped = json.loads(f'"{response}"')
                return unescaped, True
        except Exception:
            pass
        return response, False

    def _strategy_latex_boxed(self, response: str) -> Optional[float]:
        """
        Strategy 1: Extract from LaTeX \\boxed{number} patterns.

        This is the most reliable pattern for mathematical responses.
        """
        boxed_patterns = [
            r'\\boxed\{([+-]?(?:[0-9]*[.])?[0-9]+)\}',
            r'\\boxed\{\s*([+-]?(?:[0-9]*[.])?[0-9]+)\s*\}',
            r'boxed\{([+-]?(?:[0-9]*[.])?[0-9]+)\}',
        ]

        for pattern in boxed_patterns:
            matches = re.findall(pattern, response)
            if matches:
                try:
                    return float(matches[-1])
                except ValueError:
                    continue

        return None

    def _strategy_keyword_search(self, response: str) -> Optional[float]:
        """
        Strategy 2: Search for keywords and extract nearby numbers.
        """
        # Use the multilingual label alternation built in parse().  A
        # line-containment check is sufficient here because the alternation
        # is substring-safe (every label is a literal keyword, and common
        # false-positive substrings like "answer" are part of the benchmark
        # domain anyway — they should trigger the number scan).
        label_re = re.compile(self._label_alt, re.IGNORECASE)

        response_lines = response.lower().splitlines()
        response_lines.reverse()

        for i, line in enumerate(response_lines):
            if label_re.search(line) or '\\boxed' in line or '=' in line:
                # Look for number in this line and following lines
                for j in range(i, min(i + 3, len(response_lines))):
                    current_line = response_lines[j]

                    # Try to extract number after equals sign
                    parts = current_line.split('=')
                    if len(parts) > 1:
                        number_match = re.search(r'[+-]?([0-9]*[.])?[0-9]+', parts[-1].strip())
                        if number_match:
                            try:
                                return float(number_match.group())
                            except ValueError:
                                continue

                    # Extract any number from the line
                    number_match = re.search(r'[+-]?([0-9]*[.])?[0-9]+', current_line)
                    if number_match:
                        try:
                            return float(number_match.group())
                        except ValueError:
                            continue

        return None

    def _strategy_equals_pattern(self, response: str) -> Optional[float]:
        """
        Strategy 3: Find "= number" patterns.
        """
        equals_pattern = r'=\s*([+-]?(?:[0-9]*[.])?[0-9]+)(?:\s|$)'
        matches = re.findall(equals_pattern, response)
        if matches:
            try:
                return float(matches[-1])
            except ValueError:
                pass
        return None

    def _strategy_last_number(self, response: str) -> Optional[float]:
        """
        Strategy 4: Extract the last number in the response.

        Skips numbers that appear in percentage/confidence contexts
        (e.g. "I'm 99% confident") to avoid false positives.
        """
        all_matches = list(re.finditer(r'[+-]?(?:[0-9]*[.])?[0-9]+', response))
        if all_matches:
            for m in reversed(all_matches):
                num_str = m.group()
                # Skip if followed by % or in a confidence context
                after = response[m.end():m.end() + 10]
                before = response[max(0, m.start() - 25):m.start()]
                if re.match(r'\s*%', after):
                    continue
                if re.search(r'(?:confident|certain|sure|probability|chance)\s*$', before, re.IGNORECASE):
                    continue
                try:
                    return float(num_str)
                except ValueError:
                    continue
        return None

    def _strategy_answer_patterns(self, response: str) -> Optional[float]:
        """
        Strategy 5: Look for specific answer patterns.
        """
        # Build a single multilingual pattern: `<label>[:\s]+<number>`.
        # The alternation already covers answer / result / solution / final
        # answer across six languages plus arithmetic-specific extras.
        pattern = rf'(?:{self._label_alt})[:\s]+([+-]?(?:[0-9]*[.])?[0-9]+)'
        response_lower = response.lower()
        matches = re.findall(pattern, response_lower)
        if matches:
            try:
                return float(matches[-1])
            except ValueError:
                pass

        return None
