"""
Picross (Nonogram) Response Parser

Multi-strategy parser for extracting solved grids from model responses.
Adapted from the Game of Life parser with additional marker normalization
for common nonogram notations (X/., ■/□).
"""

import re
from typing import Any, Dict, List, Optional

from src.plugins.base import ParsedAnswer, ResponseParser
from src.plugins.parse_utils import normalize_unicode

# Common filled/empty marker pairs the model might use regardless of prompt
_FILLED_ALIASES = {"1", "X", "x", "#", "■", "█", "●", "★"}
_EMPTY_ALIASES = {"0", ".", "□", "○", "☆", "_", "-"}


class PicrossParser(ResponseParser):
    """Multi-strategy parser for Picross model responses.

    Strategies (end-first):
    1. line_scan_reverse — scan from end of response for grid-shaped lines
    2. marker_search — look for 'solution:', 'grid:', 'answer:' keywords
    3. digit_extraction — find rectangular pattern of filled/empty markers
    4. last_resort — collect all markers and arrange into grid
    """

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        if not response:
            return ParsedAnswer(
                value=None, raw_response=response or "",
                parse_strategy="empty", error="Empty response from model",
            )

        response = normalize_unicode(response)

        # Expected dimensions
        grid_size = task_params.get("grid_size", [0, 0])
        expected_grid = task_params.get("expected_grid", [[]])
        expected_rows = grid_size[0] if grid_size[0] else len(expected_grid)
        expected_cols = grid_size[1] if grid_size[1] else (len(expected_grid[0]) if expected_grid else 0)

        if expected_rows == 0 or expected_cols == 0:
            return ParsedAnswer(
                value=None, raw_response=response,
                parse_strategy="fallback", error="Invalid expected shape in task_params",
            )

        filled = task_params.get("filled_cell", "1")
        empty = task_params.get("empty_cell", "0")

        strategies = [
            ("line_scan_reverse", self._strategy_line_scan_reverse),
            ("marker_search", self._strategy_marker_search),
            ("digit_extraction", self._strategy_digit_extraction),
            ("last_resort", self._strategy_last_resort),
        ]

        for name, fn in strategies:
            try:
                result = fn(response, expected_rows, expected_cols, filled, empty)
                if result is not None:
                    return ParsedAnswer(
                        value=result, raw_response=response, parse_strategy=name,
                    )
            except Exception:
                continue

        return ParsedAnswer(
            value=None, raw_response=response,
            parse_strategy="fallback", error="All parsing strategies failed",
        )

    def get_strategies(self) -> List[str]:
        return ["line_scan_reverse", "marker_search", "digit_extraction", "last_resort"]

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_line(line: str, filled: str, empty: str) -> Optional[List[int]]:
        """Try to extract a row of 0/1 values from a text line.

        Recognizes the configured markers plus common nonogram aliases.
        Returns a list of ints or None if the line doesn't look like a grid row.
        """
        # Build full sets from configured + alias markers
        fill_chars = {filled} | _FILLED_ALIASES
        empt_chars = {empty} | _EMPTY_ALIASES

        # Strip common row-label prefixes (e.g. "Row 3:" or "3 |")
        stripped = re.sub(r"^[\s]*(?:row\s*\d+\s*[:│|]?\s*)", "", line, flags=re.IGNORECASE)
        stripped = re.sub(r"^[\s]*\d+(?:\s+\d+)*\s*[│|]\s*", "", stripped)

        # Split by whitespace or common delimiters
        tokens = re.split(r"[\s,;|]+", stripped.strip())
        if not tokens or tokens == [""]:
            return None

        row: List[int] = []
        for tok in tokens:
            tok_stripped = tok.strip()
            if not tok_stripped:
                continue
            if tok_stripped in fill_chars:
                row.append(1)
            elif tok_stripped in empt_chars:
                row.append(0)
            else:
                # Not a recognized marker — abort this line
                return None
        return row if row else None

    # ── Strategy 1: Line Scan Reverse ─────────────────────────────────

    def _strategy_line_scan_reverse(
        self, response: str, expected_rows: int, expected_cols: int,
        filled: str, empty: str,
    ) -> Optional[List[List[int]]]:
        """Scan from end of response for a block of grid-shaped lines."""
        lines = response.strip().split("\n")

        for start_idx in range(len(lines) - expected_rows, -1, -1):
            candidate_lines = lines[start_idx : start_idx + expected_rows]
            if len(candidate_lines) != expected_rows:
                continue

            grid: List[List[int]] = []
            for line in candidate_lines:
                row = self._normalize_line(line, filled, empty)
                if row is None or len(row) != expected_cols:
                    break
                grid.append(row)

            if len(grid) == expected_rows:
                return grid

        return None

    # ── Strategy 2: Marker Search ─────────────────────────────────────

    def _strategy_marker_search(
        self, response: str, expected_rows: int, expected_cols: int,
        filled: str, empty: str,
    ) -> Optional[List[List[int]]]:
        """Look for keywords and extract grid after them (end-first)."""
        lines = response.strip().split("\n")
        markers = ["solution:", "grid:", "answer:", "result:", "output:", "resolved:"]

        for marker in markers:
            marker_idx = -1
            for i in range(len(lines) - 1, -1, -1):
                if marker in lines[i].lower():
                    marker_idx = i
                    break

            if marker_idx < 0:
                continue

            # Try parsing grid starting near the marker
            for start in range(marker_idx, min(marker_idx + 3, len(lines) - expected_rows + 1)):
                grid: List[List[int]] = []
                for line in lines[start : start + expected_rows]:
                    row = self._normalize_line(line, filled, empty)
                    if row is None or len(row) != expected_cols:
                        break
                    grid.append(row)
                if len(grid) == expected_rows:
                    return grid

        return None

    # ── Strategy 3: Digit Extraction ──────────────────────────────────

    def _strategy_digit_extraction(
        self, response: str, expected_rows: int, expected_cols: int,
        filled: str, empty: str,
    ) -> Optional[List[List[int]]]:
        """Find rectangular pattern of 0s/1s scanning from end."""
        lines = response.strip().split("\n")

        for start_idx in range(len(lines) - expected_rows, -1, -1):
            candidate_lines = lines[start_idx : start_idx + expected_rows]
            grid: List[List[int]] = []
            for line in candidate_lines:
                digits = re.findall(r"[01]", line)
                if len(digits) >= expected_cols:
                    grid.append([int(d) for d in digits[:expected_cols]])
                else:
                    break
            if len(grid) == expected_rows:
                total_cells = expected_rows * expected_cols
                ones = sum(sum(row) for row in grid)
                if 0 <= ones <= total_cells:
                    return grid

        return None

    # ── Strategy 4: Last Resort ───────────────────────────────────────

    def _strategy_last_resort(
        self, response: str, expected_rows: int, expected_cols: int,
        filled: str, empty: str,
    ) -> Optional[List[List[int]]]:
        """Collect all binary digits and arrange into grid shape."""
        all_digits = re.findall(r"[01]", response)
        required = expected_rows * expected_cols

        if len(all_digits) < required:
            return None

        # Try from end first (models put answer last)
        for start_pos in [len(all_digits) - required, 0]:
            if start_pos < 0:
                continue
            try:
                chunk = all_digits[start_pos : start_pos + required]
                grid = []
                for i in range(expected_rows):
                    s = i * expected_cols
                    grid.append([int(d) for d in chunk[s : s + expected_cols]])
                return grid
            except Exception:
                continue

        return None
