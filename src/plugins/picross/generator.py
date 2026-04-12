"""
Picross (Nonogram) Test Case Generator

Generates test cases with configurable difficulty, density, clue format,
and optional partial-solution mode.
"""

import json
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.plugins.base import ConfigField, TestCase, TestCaseGenerator
from src.plugins.picross.grid_gen import difficulty_to_size, generate_puzzle


# ── Clue formatting helpers ──────────────────────────────────────────────


def _normalize_cell_markers(raw) -> List[str]:
    """Normalize cell_markers from any input format to a two-element list."""
    if isinstance(raw, str):
        parts = raw.split(",")
        return [parts[0].strip(), parts[1].strip() if len(parts) > 1 else "0"]
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        return [str(raw[0]), str(raw[1])]
    return ["1", "0"]


def format_grid(grid: List[List[int]], filled: str = "1", empty: str = "0") -> str:
    """Format a binary grid with the given markers."""
    return "\n".join(
        " ".join(filled if cell else empty for cell in row) for row in grid
    )


# ── Localized clue labels ────────────────────────────────────────────────

_CLUE_LABELS = {
    "en": {"rows": "Rows",    "row": "Row",    "columns": "Columns",    "col": "Col",    "json_header": "Row clues (JSON)"},
    "es": {"rows": "Filas",   "row": "Fila",   "columns": "Columnas",   "col": "Col",    "json_header": "Pistas (JSON)"},
    "fr": {"rows": "Lignes",  "row": "Ligne",  "columns": "Colonnes",   "col": "Col",    "json_header": "Indices (JSON)"},
    "de": {"rows": "Zeilen",  "row": "Zeile",  "columns": "Spalten",    "col": "Sp",     "json_header": "Hinweise (JSON)"},
    "zh": {"rows": "\u884c",  "row": "\u884c", "columns": "\u5217",     "col": "\u5217", "json_header": "\u63d0\u793a (JSON)"},
    "ua": {"rows": "\u0420\u044f\u0434\u043a\u0438",  "row": "\u0420\u044f\u0434\u043e\u043a",  "columns": "\u0421\u0442\u043e\u0432\u043f\u0446\u0456",  "col": "\u0421\u0442\u043e\u0432\u043f",  "json_header": "\u041f\u0456\u0434\u043a\u0430\u0437\u043a\u0438 (JSON)"},
}


def _get_labels(language: str) -> dict:
    return _CLUE_LABELS.get(language, _CLUE_LABELS["en"])


def format_clues_inline(
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    language: str = "en",
) -> tuple:
    """Format clues in inline style with localized labels.

    Returns (row_string, col_string).
    """
    labels = _get_labels(language)

    def _fmt(clue_list, label, name):
        lines = []
        for i, clue in enumerate(clue_list):
            lines.append(f"  {name} {i + 1}: {' '.join(str(n) for n in clue)}")
        return f"{label}:\n" + "\n".join(lines)

    row_str = _fmt(row_clues, labels["rows"], labels["row"])
    col_str = _fmt(col_clues, labels["columns"], labels["col"])
    return row_str, col_str


def format_clues_json(
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    language: str = "en",
) -> tuple:
    """Format clues as JSON with a localized header."""
    labels = _get_labels(language)
    obj = {"rows": row_clues, "cols": col_clues}
    return f"{labels['json_header']}:", json.dumps(obj)


def format_clues_grid_header(
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    rows: int,
    cols: int,
) -> tuple:
    """Format clues as a visual grid header with vertically-aligned column clues.

    Produces output like:
           1     2
         1 2 3 1 1
        ──────────
    2  │ . . . . .
    1 1│ . . . . .
    3  │ . . . . .
    """
    # Determine column clue heights (max runs in any column clue)
    max_col_runs = max(len(c) for c in col_clues) if col_clues else 0

    # Pad column clues to uniform height (top-aligned with leading blanks)
    padded_col_clues = []
    for clue in col_clues:
        padded = [""] * (max_col_runs - len(clue)) + [str(n) for n in clue]
        padded_col_clues.append(padded)

    # Width of each column cell (accommodate multi-digit clue numbers)
    col_widths = []
    for c_idx in range(cols):
        max_w = 1  # minimum width for grid cells (single marker)
        for row_idx in range(max_col_runs):
            max_w = max(max_w, len(padded_col_clues[c_idx][row_idx]))
        col_widths.append(max_w)

    # Width of the row-clue margin
    row_clue_strs = [" ".join(str(n) for n in rc) for rc in row_clues]
    margin_width = max(len(s) for s in row_clue_strs) if row_clue_strs else 0

    lines = []

    # Column clue rows
    for level in range(max_col_runs):
        cells = []
        for c_idx in range(cols):
            val = padded_col_clues[c_idx][level]
            cells.append(val.rjust(col_widths[c_idx]))
        prefix = " " * margin_width + "  "  # margin + "│ " placeholder
        lines.append(prefix + " ".join(cells))

    # Separator line
    grid_content_width = sum(col_widths) + cols - 1  # cells + spaces between
    lines.append(" " * margin_width + "─┼" + "─" * grid_content_width)

    # Grid rows (empty cells for the model to fill)
    for r_idx in range(rows):
        rc_str = row_clue_strs[r_idx].rjust(margin_width)
        cells = []
        for c_idx in range(cols):
            cells.append(".".center(col_widths[c_idx]))
        lines.append(rc_str + " │" + " ".join(cells))

    header = "\n".join(lines)
    return "Puzzle:", header


# ── Generator ────────────────────────────────────────────────────────────


class PicrossGenerator(TestCaseGenerator):
    """Test case generator for Picross (Nonogram) benchmark."""

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None,
    ) -> List[TestCase]:
        rng = random.Random(seed)
        tests: List[TestCase] = []
        test_id = 0

        # Extract config
        difficulties = config.get("difficulty", ["easy"])
        if isinstance(difficulties, str):
            difficulties = [difficulties]
        puzzles_per = config.get("puzzles_per_difficulty", count // len(difficulties) or 1)
        density = config.get("density", 0.5)
        require_line_solvable = config.get("require_line_solvable", True)
        require_unique = config.get("require_unique", True)
        cell_markers = _normalize_cell_markers(config.get("cell_markers", ["1", "0"]))
        filled_cell, empty_cell = cell_markers[0], cell_markers[1]
        clue_format = config.get("clue_format", "inline")
        partial_solution = config.get("partial_solution", False)

        # Prompt config
        language = prompt_config.get("language", "en")
        user_style = prompt_config.get("user_style", "linguistic")
        system_style = prompt_config.get("system_style", "analytical")
        config_name = prompt_config.get("name", f"{user_style}_{system_style}")

        for diff_str in difficulties:
            size = difficulty_to_size(diff_str)

            for _ in range(puzzles_per):
                if test_id >= count:
                    break

                puzzle = generate_puzzle(
                    size=size,
                    density=density,
                    rng=rng,
                    require_line_solvable=require_line_solvable,
                    require_unique=require_unique,
                )

                # Format clues
                row_clues_str, col_clues_str = self._format_clues(
                    puzzle["row_clues"], puzzle["col_clues"],
                    size, size, clue_format, language,
                )

                # Optional partial grid
                partial_grid = None
                partial_grid_str = ""
                if partial_solution:
                    partial_grid = self._make_partial(puzzle["grid"], rng)
                    partial_grid_str = format_grid(partial_grid, filled_cell, empty_cell)

                # Build prompts
                template_vars = {
                    "row_clues": row_clues_str,
                    "col_clues": col_clues_str,
                    "rows": str(size),
                    "cols": str(size),
                    "f": filled_cell,
                    "e": empty_cell,
                }

                user_prompt, system_prompt, full_prompt = self._build_prompts_yaml(
                    "picross",
                    language=language,
                    user_style=user_style,
                    system_style=system_style,
                    **template_vars,
                )

                # Append partial grid to user prompt if applicable
                if partial_solution and partial_grid_str:
                    user_prompt += f"\n\nPartial solution (? = unknown):\n{partial_grid_str}"
                    full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

                task_params: Dict[str, Any] = {
                    "expected_grid": puzzle["grid"],
                    "row_clues": puzzle["row_clues"],
                    "col_clues": puzzle["col_clues"],
                    "difficulty": diff_str,
                    "density": puzzle["actual_density"],
                    "clue_format": clue_format,
                    "filled_cell": filled_cell,
                    "empty_cell": empty_cell,
                    "grid_size": [size, size],
                    "is_line_solvable": puzzle["is_line_solvable"],
                }
                if partial_grid is not None:
                    task_params["partial_grid"] = partial_grid

                test_case = TestCase(
                    test_id=f"picross_{test_id:04d}",
                    task_type="picross",
                    config_name=config_name,
                    prompts={
                        "system": system_prompt,
                        "user": user_prompt,
                        "full": full_prompt,
                    },
                    task_params=task_params,
                    prompt_metadata={
                        "user_style": user_style,
                        "system_style": system_style,
                        "language": language,
                    },
                    generation_metadata={
                        "seed": seed,
                        "generator_version": "1.0.0",
                        "created_at": datetime.now().isoformat(),
                    },
                )

                tests.append(test_case)
                test_id += 1

            if test_id >= count:
                break

        return tests

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _format_clues(row_clues, col_clues, rows, cols, fmt, language="en"):
        if fmt == "json":
            return format_clues_json(row_clues, col_clues, language)
        if fmt == "grid_header":
            return format_clues_grid_header(row_clues, col_clues, rows, cols)
        return format_clues_inline(row_clues, col_clues, language)

    @staticmethod
    def _make_partial(grid: List[List[int]], rng: random.Random) -> List[List[int]]:
        """Create a partial grid by blanking ~50% of cells (marked as -1)."""
        return [
            [cell if rng.random() > 0.5 else -1 for cell in row]
            for row in grid
        ]

    # ── Config schema ─────────────────────────────────────────────────

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "difficulty": ["easy"],
            "puzzles_per_difficulty": 10,
            "density": 0.5,
            "require_line_solvable": True,
            "require_unique": True,
            "cell_markers": "1,0",
            "clue_format": "inline",
            "partial_solution": False,
        }

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(
                name="difficulty", label="Difficulty", field_type="multi-select",
                default=["easy"],
                options=["trivial", "easy", "hard", "nightmare"],
            ),
            ConfigField(
                name="puzzles_per_difficulty", label="Puzzles per difficulty",
                field_type="number", default=10, min_value=1, max_value=200,
            ),
            ConfigField(
                name="density", label="Cell density", field_type="number",
                default=0.5, min_value=0.2, max_value=0.8, step=0.05,
            ),
            ConfigField(
                name="require_line_solvable", label="Require line-solvable",
                field_type="boolean", default=True,
                help="Only emit puzzles solvable by pure line logic (no guessing). Guarantees unique solution.",
            ),
            ConfigField(
                name="clue_format", label="Clue format", field_type="select",
                default="inline",
                options=["inline", "grid_header", "json"],
            ),
            ConfigField(
                name="require_unique", label="Require unique solution",
                field_type="boolean", default=True, group="advanced",
                help="Reject puzzles with multiple solutions (relevant when line-solvable is off).",
            ),
            ConfigField(
                name="cell_markers", label="Cell markers", field_type="text",
                default="1,0", group="advanced",
                help="Filled,empty cell markers (comma-separated)",
            ),
            ConfigField(
                name="partial_solution", label="Partial solution mode",
                field_type="boolean", default=False, group="advanced",
                help="Give model a partially-filled grid to complete (~50% cells revealed).",
            ),
        ]
