"""
Arithmetic Response Parser

Multi-strategy parser for extracting numeric answers from model responses.
Handles various response formats including LaTeX, keywords, and plain text.
"""

import json
import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ParsedAnswer, ResponseParser


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
                parse_strategy='failed',
                error='Empty response from model'
            )

        response = str(response).strip()
        original_response = response

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

        # Try each parsing strategy in order
        strategies = [
            ('latex_boxed', self._strategy_latex_boxed),
            ('keyword_search', self._strategy_keyword_search),
            ('equals_pattern', self._strategy_equals_pattern),
            ('last_number', self._strategy_last_number),
            ('answer_patterns', self._strategy_answer_patterns),
        ]

        for name, strategy_func in strategies:
            try:
                result = strategy_func(response)
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
            parse_strategy='failed',
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
        match_words = [
            'final result', 'result', 'final answer', 'answer', 'response',
            'therefore', '\\boxed', 'equals', '=',
            'final result:', 'answer:', 'result:', 'solution:'
        ]

        response_lines = response.lower().splitlines()
        response_lines.reverse()

        for i, line in enumerate(response_lines):
            if any(word in line for word in match_words):
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
        answer_patterns = [
            r'answer[:\s]+([+-]?(?:[0-9]*[.])?[0-9]+)',
            r'result[:\s]+([+-]?(?:[0-9]*[.])?[0-9]+)',
            r'solution[:\s]+([+-]?(?:[0-9]*[.])?[0-9]+)',
            r'final[:\s]+([+-]?(?:[0-9]*[.])?[0-9]+)'
        ]

        response_lower = response.lower()
        for pattern in answer_patterns:
            matches = re.findall(pattern, response_lower)
            if matches:
                try:
                    return float(matches[-1])
                except ValueError:
                    continue

        return None
