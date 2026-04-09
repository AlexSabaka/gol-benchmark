"""
Picross Puzzle Grid Generator

Generates random nonogram puzzles at a target density, with optional
validation for line-solvability and uniqueness.
"""

import logging
import random
from typing import Any, Dict, Optional

from src.plugins.picross.solver import (
    Grid,
    backtrack_solve,
    derive_clues,
    is_line_solvable,
)

logger = logging.getLogger(__name__)

# Grid sizes by difficulty level
DIFFICULTY_SIZES = {
    "trivial": 3,
    "easy": 5,
    "hard": 10,
    "nightmare": 15,
}

MAX_RETRIES = 200


def generate_puzzle(
    size: int,
    density: float,
    rng: random.Random,
    require_line_solvable: bool = True,
    require_unique: bool = True,
) -> Dict[str, Any]:
    """Generate a valid nonogram puzzle.

    Args:
        size: Grid dimension (rows == cols).
        density: Target density of filled cells (0.0–1.0).
        rng: Seeded random.Random instance.
        require_line_solvable: Reject puzzles not solvable by pure line logic.
        require_unique: Reject puzzles with multiple solutions (when
            *require_line_solvable* is False).

    Returns:
        Dict with keys: grid, row_clues, col_clues, actual_density,
        is_line_solvable.

    Raises:
        RuntimeError: If no valid puzzle is found after MAX_RETRIES attempts.
    """
    for attempt in range(MAX_RETRIES):
        grid = _random_grid(size, density, rng)
        row_clues, col_clues = derive_clues(grid)
        actual_density = sum(c for row in grid for c in row) / (size * size)

        if require_line_solvable:
            if not is_line_solvable(row_clues, col_clues):
                continue
        elif require_unique:
            solutions = backtrack_solve(row_clues, col_clues, max_solutions=2)
            if len(solutions) != 1:
                continue

        return {
            "grid": grid,
            "row_clues": row_clues,
            "col_clues": col_clues,
            "actual_density": round(actual_density, 3),
            "is_line_solvable": require_line_solvable or is_line_solvable(row_clues, col_clues),
        }

    logger.warning(
        "Failed to generate a valid %dx%d puzzle after %d attempts "
        "(density=%.2f, line_solvable=%s, unique=%s)",
        size, size, MAX_RETRIES, density,
        require_line_solvable, require_unique,
    )
    raise RuntimeError(
        f"Could not generate a valid {size}×{size} picross puzzle after "
        f"{MAX_RETRIES} attempts (density={density:.2f}, "
        f"line_solvable={require_line_solvable}, unique={require_unique})"
    )


def _random_grid(size: int, density: float, rng: random.Random) -> Grid:
    """Generate a random binary grid with density variance ±0.1."""
    # Add ±0.1 variance to avoid degenerate grids
    actual_density = max(0.05, min(0.95, density + rng.uniform(-0.1, 0.1)))
    return [
        [1 if rng.random() < actual_density else 0 for _ in range(size)]
        for _ in range(size)
    ]


def difficulty_to_size(difficulty: str) -> int:
    """Map difficulty string to grid size."""
    return DIFFICULTY_SIZES.get(difficulty.lower(), 5)
