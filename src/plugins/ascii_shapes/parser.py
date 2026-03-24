"""
ASCII Shapes Response Parser

Multi-strategy parser for extracting answers from model responses.
Supports three answer types: dimensions, counts, and positions.
"""

import re
from typing import Any, Dict, List, Optional, Union

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import re_search_last


class AsciiShapesResponseParser(ResponseParser):
    """
    Multi-strategy parser for ASCII Shapes model responses.

    Supports three answer types:
    - Dimensions: "WxH", "width: N, height: M", "W by H"
    - Count: numeric answer
    - Position: yes/no/true/false
    """

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        """
        Parse a model response based on question type.

        Args:
            response: Raw model response string
            task_params: Task parameters containing question_type

        Returns:
            ParsedAnswer with appropriate answer type
        """
        if not response:
            return ParsedAnswer(
                value=None,
                raw_response=response or "",
                parse_strategy='failed',
                error='Empty response from model'
            )

        # Normalize Unicode spaces to regular spaces
        response = re.sub(r'[\u00A0\u202F\u2009\u200B]', ' ', response)
        
        question_type = task_params.get('question_type', 'dimensions')
        response_lower = response.strip().lower()
        response_original = response.strip()

        # Route to appropriate parser
        if question_type == 'dimensions':
            return self._parse_dimensions(response_original, response_lower)
        elif question_type == 'count':
            return self._parse_count(response_original, response_lower)
        elif question_type == 'position':
            return self._parse_position(response_original, response_lower)
        else:
            # Try all parsers
            result = self._parse_dimensions(response_original, response_lower)
            if result.value is not None:
                return result

            result = self._parse_count(response_original, response_lower)
            if result.value is not None:
                return result

            return self._parse_position(response_original, response_lower)

    def get_strategies(self) -> List[str]:
        """Return list of available parsing strategies."""
        return [
            'dimensions_wxh',
            'dimensions_by',
            'dimensions_keywords',
            'count_keywords',
            'count_number',
            'position_boolean'
        ]

    def _parse_dimensions(self, response: str, response_lower: str) -> ParsedAnswer:
        """Parse dimensions answer (WxH format, last match — end-first)."""
        dimension_patterns = [
            r'(\d+)\s*[x×✕✖]\s*(\d+)',  # "8x5", "8 × 5" (includes Unicode multiplication)
            r'(\d+)\s*by\s*(\d+)',  # "8 by 5"
            r'width\s*[=:]\s*(\d+).*?height\s*[=:]\s*(\d+)',  # "width = 8, height = 5"
            r'(\d+)\s*wide.*?(\d+)\s*(?:tall|high)',  # "8 wide and 5 tall"
            r'(\d+)\s*columns.*?(\d+)\s*rows',  # "8 columns, 5 rows"
            r'width.*?(\d+).*?height.*?(\d+)',  # "width is 8 ... height is 5"
            # Natural language patterns
            r'(\d+)\s*(?:characters?|symbols?|[a-z]+s?)\s*(?:across|wide).*?(\d+)\s*(?:lines?|rows?|tall|down|high)',  # "8 chars across, 5 lines"
        ]

        for pattern in dimension_patterns:
            match = re_search_last(pattern, response_lower)
            if match:
                try:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    return ParsedAnswer(
                        value=f"{width}x{height}",
                        raw_response=response,
                        parse_strategy='dimensions_wxh'
                    )
                except ValueError:
                    continue

        # Fallback: find last two numbers
        all_numbers = re.findall(r'\d+', response)
        if len(all_numbers) == 2:
            try:
                return ParsedAnswer(
                    value=f"{all_numbers[0]}x{all_numbers[1]}",
                    raw_response=response,
                    parse_strategy='dimensions_fallback'
                )
            except ValueError:
                pass

        return ParsedAnswer(
            value=None,
            raw_response=response,
            parse_strategy='failed',
            error='Could not parse dimensions'
        )

    def _parse_count(self, response: str, response_lower: str) -> ParsedAnswer:
        """Parse count answer (numeric, last match — end-first)."""
        count_patterns = [
            r'(?:answer|count|total|number)\s*:?\s*(\d+)',
            r'(?:there are|there\'s|has)\s*(\d+)',
            r'(?:=|equals)\s*(\d+)',
            r'^\s*(\d+)\s*$',  # Just a number alone
        ]

        for pattern in count_patterns:
            match = re_search_last(pattern, response_lower)
            if match:
                try:
                    return ParsedAnswer(
                        value=int(match.group(1)),
                        raw_response=response,
                        parse_strategy='count_keywords'
                    )
                except ValueError:
                    continue

        # Fallback: take the last number (end-first)
        all_numbers = re.findall(r'\d+', response)
        if all_numbers:
            try:
                return ParsedAnswer(
                    value=int(all_numbers[-1]),
                    raw_response=response,
                    parse_strategy='count_fallback'
                )
            except ValueError:
                pass

        return ParsedAnswer(
            value=None,
            raw_response=response,
            parse_strategy='failed',
            error='Could not parse count'
        )

    def _parse_position(self, response: str, response_lower: str) -> ParsedAnswer:
        """Parse position answer (boolean)."""
        # Check for positive indicators
        positive_words = ['yes', 'true', 'present', 'exists', 'there is', 'correct']
        negative_words = ['no', 'false', 'not present', 'absent', "doesn't exist", 'incorrect', 'not', "isn't"]

        # Check for negation first
        has_negation = any(word in response_lower for word in negative_words)
        has_positive = any(word in response_lower for word in positive_words)

        if has_negation and not has_positive:
            return ParsedAnswer(
                value=False,
                raw_response=response,
                parse_strategy='position_boolean'
            )

        if has_positive and not has_negation:
            return ParsedAnswer(
                value=True,
                raw_response=response,
                parse_strategy='position_boolean'
            )

        # Ambiguous — use last occurrence to determine final stance (end-first)
        # Use END position of phrases so "not present" (ending at 69) beats
        # the "present" substring within it (at 62).
        if has_positive and has_negation:
            last_neg_end = max(
                (response_lower.rfind(neg) + len(neg) for neg in negative_words if neg in response_lower),
                default=-1,
            )
            last_pos_end = max(
                (response_lower.rfind(pos) + len(pos) for pos in positive_words if pos in response_lower),
                default=-1,
            )
            # Whichever ends later is the model's final answer
            return ParsedAnswer(
                value=last_pos_end > last_neg_end,
                raw_response=response,
                parse_strategy='position_boolean'
            )

        return ParsedAnswer(
            value=None,
            raw_response=response,
            parse_strategy='failed',
            error='Could not parse position answer'
        )
