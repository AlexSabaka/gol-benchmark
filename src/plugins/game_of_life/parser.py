"""
Game of Life Response Parser

Multi-strategy parser for extracting grid states from model responses.
Uses several fallback strategies to handle various response formats.
"""

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import normalize_unicode


class GoLResponseParser(ResponseParser):
    """
    Multi-strategy parser for Game of Life model responses.

    Parsing Strategies:
    1. Line scan (reverse): Scan from end looking for grid pattern
    2. Marker search: Look for keywords like 'next:', 'result:', 'grid:'
    3. Digit extraction: Extract any rectangular pattern of 0s and 1s
    4. Last resort: Arrange all digits into expected grid shape
    """

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        """
        Parse a model response to extract the predicted next grid state.

        Args:
            response: Raw model response string
            task_params: Task parameters containing:
                - expected_next_state: Expected grid for shape reference
                - live_cell: Live cell marker (default '1')
                - dead_cell: Dead cell marker (default '0')

        Returns:
            ParsedAnswer with extracted grid or error
        """
        if not response:
            return ParsedAnswer(
                value=None,
                raw_response=response or "",
                parse_strategy='empty',
                error='Empty response from model'
            )

        response = normalize_unicode(response)

        # Get expected shape from task params
        expected_state = task_params.get('expected_next_state', [[]])
        expected_rows = len(expected_state)
        expected_cols = len(expected_state[0]) if expected_state else 0

        if expected_rows == 0 or expected_cols == 0:
            return ParsedAnswer(
                value=None,
                raw_response=response,
                parse_strategy='fallback',
                error='Invalid expected shape in task_params'
            )

        # Get cell markers
        live_cell = task_params.get('live_cell', '1')
        dead_cell = task_params.get('dead_cell', '0')

        # Try each parsing strategy in order
        strategies = [
            ('line_scan_reverse', self._strategy_line_scan_reverse),
            ('marker_search', self._strategy_marker_search),
            ('digit_extraction', self._strategy_digit_extraction),
            ('last_resort', self._strategy_last_resort),
        ]

        for name, strategy_func in strategies:
            try:
                result = strategy_func(
                    response, expected_rows, expected_cols,
                    live_cell, dead_cell
                )
                if result is not None:
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
            parse_strategy='fallback',
            error='All parsing strategies failed'
        )

    def get_strategies(self) -> List[str]:
        """Return list of available parsing strategies."""
        return [
            'line_scan_reverse',
            'marker_search',
            'digit_extraction',
            'last_resort'
        ]

    def _strategy_line_scan_reverse(
        self,
        response: str,
        expected_rows: int,
        expected_cols: int,
        live_cell: str,
        dead_cell: str
    ) -> Optional[List[List[int]]]:
        """
        Strategy 1: Scan from end of response looking for grid pattern.

        This is the most reliable strategy as models often place the answer
        at the end of their response.
        """
        lines = response.strip().split('\n')

        for start_idx in range(len(lines) - expected_rows + 1, -1, -1):
            candidate_lines = lines[start_idx:start_idx + expected_rows]
            if len(candidate_lines) != expected_rows:
                continue

            grid = []
            for line in candidate_lines:
                # Clean the line - remove non-marker characters except spaces
                cleaned_line = ''
                for char in line.strip():
                    if char in (live_cell, dead_cell, ' ', '\t'):
                        cleaned_line += char
                    elif char.isdigit():
                        # Convert any digit to appropriate marker
                        cleaned_line += '1' if char != '0' else '0'

                # Normalize whitespace and convert markers
                cleaned_line = re.sub(r'\s+', ' ', cleaned_line.strip())
                cleaned_line = cleaned_line.replace(live_cell, '1').replace(dead_cell, '0')

                # Extract row values
                row = []
                for char in cleaned_line.split():
                    if char in ('0', '1'):
                        row.append(int(char))

                if len(row) != expected_cols:
                    break

                grid.append(row)

                if len(grid) == expected_rows:
                    return grid

        return None

    def _strategy_marker_search(
        self,
        response: str,
        expected_rows: int,
        expected_cols: int,
        live_cell: str,
        dead_cell: str
    ) -> Optional[List[List[int]]]:
        """
        Strategy 2: Look for grid sections marked with keywords.

        Searches for markers like 'next:', 'result:', 'grid:', 'state:'
        scanning from the END of the response (end-first principle).
        """
        lines = response.strip().split('\n')
        grid_markers = ['next:', 'result:', 'grid:', 'state:', 'generation:', 'output:']

        for marker in grid_markers:
            # Find the LAST occurrence of this marker (end-first)
            marker_idx = -1
            for i in range(len(lines) - 1, -1, -1):
                if marker in lines[i].lower():
                    marker_idx = i
                    break

            if marker_idx >= 0:
                # Try to parse grid starting from marker line
                for start_idx in range(marker_idx, min(marker_idx + 3, len(lines) - expected_rows + 1)):
                    candidate_lines = lines[start_idx:start_idx + expected_rows]

                    grid = []
                    for line in candidate_lines:
                        # Extract 0s and 1s from line
                        digits = re.findall(r'[01]', line)
                        if len(digits) == expected_cols:
                            grid.append([int(d) for d in digits])
                        else:
                            break

                    if len(grid) == expected_rows:
                        return grid

        return None

    def _strategy_digit_extraction(
        self,
        response: str,
        expected_rows: int,
        expected_cols: int,
        live_cell: str,
        dead_cell: str
    ) -> Optional[List[List[int]]]:
        """
        Strategy 3: Find any rectangular pattern of 0s and 1s.

        Scans from the END of the response (end-first principle) looking
        for any sequence of lines with the expected number of binary digits.
        """
        lines = response.strip().split('\n')

        # Scan from end to start
        for start_idx in range(len(lines) - expected_rows, -1, -1):
            candidate_lines = lines[start_idx:start_idx + expected_rows]

            grid = []
            for line in candidate_lines:
                # Extract all 0s and 1s
                digits = re.findall(r'[01]', line)
                if len(digits) >= expected_cols:
                    # Take first expected_cols digits
                    grid.append([int(d) for d in digits[:expected_cols]])
                else:
                    break

            if len(grid) == expected_rows:
                # Verify this looks like a reasonable grid
                total_cells = expected_rows * expected_cols
                ones_count = sum(sum(row) for row in grid)
                if 0 <= ones_count <= total_cells:  # Basic sanity check
                    return grid

        return None

    def _strategy_last_resort(
        self,
        response: str,
        expected_rows: int,
        expected_cols: int,
        live_cell: str,
        dead_cell: str
    ) -> Optional[List[List[int]]]:
        """
        Strategy 4: Last resort - extract all digits and arrange into grid.

        Collects all binary digits from the response and attempts to
        arrange them into the expected grid shape.
        """
        all_digits = re.findall(r'[01]', response)
        required_count = expected_rows * expected_cols

        if len(all_digits) < required_count:
            return None

        # Try from the end first (models often put answer last)
        start_positions = [
            len(all_digits) - required_count,  # From end
            0,  # From start
        ]

        for start_pos in start_positions:
            if start_pos < 0:
                continue

            try:
                grid_digits = all_digits[start_pos:start_pos + required_count]
                grid = []
                for i in range(expected_rows):
                    row_start = i * expected_cols
                    row_end = row_start + expected_cols
                    row = [int(d) for d in grid_digits[row_start:row_end]]
                    grid.append(row)

                return grid
            except Exception:
                continue

        return None
