"""
Cellular Automata 1D Response Parser

Multi-strategy parser for extracting 1D binary states from model responses.
"""

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ParsedAnswer, ResponseParser


class C14ResponseParser(ResponseParser):
    """
    Multi-strategy parser for 1D Cellular Automata model responses.

    Parsing Strategies:
    1. Marker search: Look for "Final Answer:", "Next state:", etc.
    2. Line scan: Find lines with space-separated 0s and 1s
    3. Digit extraction: Extract all 0s and 1s from response
    4. Code block: Extract from code blocks
    """

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        """
        Parse a model response to extract the predicted next state.

        Args:
            response: Raw model response string
            task_params: Task parameters containing expected_state for size reference

        Returns:
            ParsedAnswer with extracted state list or error
        """
        if not response:
            return ParsedAnswer(
                value=None,
                raw_response=response or "",
                parse_strategy='failed',
                error='Empty response from model'
            )

        response = response.strip()

        # Get expected size from task params
        expected_state = task_params.get('expected_state', [])
        expected_size = len(expected_state) if expected_state else task_params.get('width', 16)

        # Try each parsing strategy in order
        strategies = [
            ('marker_search', self._strategy_marker_search),
            ('line_scan', self._strategy_line_scan),
            ('code_block', self._strategy_code_block),
            ('digit_extraction', self._strategy_digit_extraction),
        ]

        for name, strategy_func in strategies:
            try:
                result = strategy_func(response, expected_size)
                if result is not None and len(result) >= 8:
                    return ParsedAnswer(
                        value=result,
                        raw_response=response,
                        parse_strategy=name
                    )
            except Exception:
                continue

        return ParsedAnswer(
            value=None,
            raw_response=response,
            parse_strategy='failed',
            error='All parsing strategies failed'
        )

    def get_strategies(self) -> List[str]:
        """Return list of available parsing strategies."""
        return [
            'marker_search',
            'line_scan',
            'code_block',
            'digit_extraction'
        ]

    def _extract_state(self, text: str, expected_size: int) -> Optional[List[int]]:
        """
        Extract a 1D CA state from a text snippet.

        Args:
            text: Text that might contain a state
            expected_size: Expected state size

        Returns:
            List of integers if valid state found, None otherwise
        """
        if not text:
            return None

        text = text.strip()

        # Remove common prefixes
        text = re.sub(
            r'^(?:state|row|generation|answer|result)\s*:?\s*',
            '', text, flags=re.IGNORECASE
        )
        text = text.strip()

        # Try different formats:

        # Format 1: Space-separated "0 1 1 0"
        space_separated = re.findall(r'\b[01]\b', text)
        if 8 <= len(space_separated) <= 64:
            return [int(d) for d in space_separated]

        # Format 2: Comma-separated "0, 1, 1, 0" or "[0, 1, 1, 0]"
        comma_separated = re.findall(r'[01]', text.replace('[', '').replace(']', ''))
        if 8 <= len(comma_separated) <= 64:
            return [int(d) for d in comma_separated]

        # Format 3: Continuous "0110" (no spaces)
        continuous = re.sub(r'[^01]', '', text)
        if 8 <= len(continuous) <= 64:
            return [int(d) for d in continuous]

        return None

    def _strategy_marker_search(self, response: str, expected_size: int) -> Optional[List[int]]:
        """Strategy 1: Look for explicit markers."""
        marker_patterns = [
            r'(?:final\s+answer|next\s+state|next\s+row|next|answer|result)\s*:?\s*(.+?)(?:\n|$)',
            r'(?:the\s+)?(?:next|resulting|final)\s+(?:state|row|generation)\s+(?:is|=|:)?\s*(.+?)(?:\n|$)',
        ]

        for pattern in marker_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                extracted = match.group(1).strip()
                parsed = self._extract_state(extracted, expected_size)
                if parsed:
                    return parsed

        return None

    def _strategy_line_scan(self, response: str, expected_size: int) -> Optional[List[int]]:
        """Strategy 2: Find lines with space-separated 0s and 1s."""
        lines = response.split('\n')

        # Scan from end (answer usually at end)
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            parsed = self._extract_state(line, expected_size)
            if parsed:
                return parsed

        return None

    def _strategy_code_block(self, response: str, expected_size: int) -> Optional[List[int]]:
        """Strategy 3: Extract from code blocks."""
        code_block_pattern = r'```(?:python|text)?\s*\n?(.+?)\n?```'
        code_matches = re.findall(code_block_pattern, response, re.DOTALL)

        for code in code_matches:
            parsed = self._extract_state(code, expected_size)
            if parsed:
                return parsed

        return None

    def _strategy_digit_extraction(self, response: str, expected_size: int) -> Optional[List[int]]:
        """Strategy 4: Extract all 0s and 1s from response."""
        all_digits = re.findall(r'\b[01]\b', response)

        if len(all_digits) >= 8:
            # Cap at 64 cells max
            return [int(d) for d in all_digits[:min(64, len(all_digits))]]

        return None
