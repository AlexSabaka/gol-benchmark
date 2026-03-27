from src.utils.logger import logger
from src.core.types import DifficultyLevel, GameState, BaseTestConfig

from pathlib import Path

import os
import random
import numpy as np

import re
from typing import Dict, List, Optional, Tuple


# Directory containing {W}x{H}.txt pattern files (O=live, .=dead)
_SORTED_PATTERNS_DIR = Path(__file__).resolve().parent.parent.parent / 'data' / 'conways_life' / 'sorted_patterns'

# Module-level cache: (max_width, max_height) → list of pattern grids
_sorted_patterns_cache: Dict[Tuple[int, int], List[List[List[int]]]] = {}

EXAMPLE_PATTERNS = [
    [
        [1],
    ],
    [
        [1, 1],
    ],
    [
        [1],
        [1],
    ],
    [
        [0, 1],
        [1, 0],
    ],
    [
        [1, 0],
        [0, 1],
    ],
    [
        [1, 1, 1],
    ],
    [
        [1],
        [1],
        [1],
    ],
    [
        [1, 1],
        [1, 1]
    ],
    [
        [0, 1],
        [1, 1]
    ],
    [
        [1, 1],
        [1, 0]
    ],
    [
        [1, 0],
        [1, 1]
    ],
    [
        [1, 1],
        [0, 1]
    ],
    [
        [0, 1, 0],
        [1, 0, 1],
    ],
    [
        [1, 0, 1],
        [0, 0, 0],
        [0, 0, 1],
    ],
    [
        [1, 0, 0],
        [0, 0, 0],
        [1, 0, 1],
    ],
    [
        [0, 0, 1],
        [0, 0, 0],
        [1, 0, 1],
    ],
    [
        [1, 0, 1],
        [0, 0, 0],
        [1, 0, 0],
    ],
    [
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
    ],
    [
        [1, 0, 1],
        [0, 1, 0],
        [1, 0, 1],
    ],
    [
        [1, 1, 1],
        [1, 1, 1],
        [1, 1, 1],
    ],
    [
        [1, 1, 1],
        [1, 1, 1],
        [0, 1, 0],
    ]
]

BASIC_KNOWN_PATTERNS = {
    # Stable patterns
    "block": [
        [1,1],
        [1,1]
    ],
    "beehive": [
        [0,1,1,0],
        [1,0,0,1],
        [0,1,1,0]
    ],
    "loaf": [
        [0,1,1,0],
        [1,0,0,1],
        [1,0,0,1],
        [0,1,1,0]
    ],
    # Oscillators (Period 2)
    "blinker": [
        [0,1,0],
        [0,1,0],
        [0,1,0]
    ],
    "toad": [
        [0,1,1,1],
        [1,1,1,0]
    ],
    "beacon": [
        [1,1,0,0],
        [1,1,0,0],
        [0,0,1,1],
        [0,0,1,1]
    ],
    # Moving patterns
    "glider": [
        [0,1,0],
        [0,0,1],
        [1,1,1]
    ],
}

class TestGenerator:
    """Generates diverse Game of Life test cases with better pattern handling"""

    def __init__(self, config: BaseTestConfig):
        self.config = config
        if self.config.seed is not None:
            random.seed(self.config.seed)
            np.random.seed(self.config.seed)

    @staticmethod
    def _load_sorted_patterns(max_width: int, max_height: int) -> List[List[List[int]]]:
        """Load patterns from sorted_patterns/ that fit within (max_width, max_height).

        Results are cached per (max_width, max_height) to avoid re-reading files.
        """
        key = (max_width, max_height)
        if key in _sorted_patterns_cache:
            return _sorted_patterns_cache[key]

        patterns: List[List[List[int]]] = []
        if not _SORTED_PATTERNS_DIR.is_dir():
            _sorted_patterns_cache[key] = patterns
            return patterns

        dim_re = re.compile(r'^(\d+)x(\d+)\.txt$')
        for fname in os.listdir(_SORTED_PATTERNS_DIR):
            m = dim_re.match(fname)
            if not m:
                continue
            pw, ph = int(m.group(1)), int(m.group(2))
            if pw > max_width or ph > max_height:
                continue
            filepath = _SORTED_PATTERNS_DIR / fname
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    grid = []
                    for line in f:
                        row_str = line.rstrip('\n').rstrip('\r')
                        if not row_str:
                            continue
                        grid.append([1 if ch == 'O' else 0 for ch in row_str])
                    if grid and all(len(row) == len(grid[0]) for row in grid):
                        patterns.append(grid)
            except (OSError, ValueError):
                continue

        _sorted_patterns_cache[key] = patterns
        logger.info(f"Loaded {len(patterns)} sorted patterns for grid ≤{max_width}x{max_height}")
        return patterns

    def generate_random_grid(self, width: int, height: int, density: float = 0.3) -> List[List[int]]:
        """Generate random initial state with given density"""
        if not (0 <= density <= 1):
            raise ValueError("Density must be between 0 and 1")

        return [[1 if np.random.rand() < density else 0
                for _ in range(width)]
                for _ in range(height)]

    def generate_known_pattern(self, width: int = 0, height: int = 0) -> List[List[int]]:
        """Generate known patterns for targeted testing.

        When *width* and *height* are provided, prefers real-world patterns
        from ``sorted_patterns/`` that fit within those dimensions.
        Falls back to ``BASIC_KNOWN_PATTERNS`` when no sorted patterns are available.
        """
        if width > 0 and height > 0:
            sorted_pats = self._load_sorted_patterns(width, height)
            if sorted_pats:
                return random.choice(sorted_pats)

        return random.choice(list(BASIC_KNOWN_PATTERNS.values()))

    def create_test_batch(self, difficulty: DifficultyLevel, batch_size: int = 10, density: float = 0.3, known_patterns_ratio: float = 0.3, exclude_empty: bool = False) -> List[GameState]:
        """Create a batch of test cases with better pattern distribution"""
        width, height = difficulty.value
        tests = []

        for i in range(batch_size):
            if i < batch_size * known_patterns_ratio:  # Known patterns
                base_grid = self.generate_known_pattern(width, height)
                
                # Create properly sized grid
                grid = [[0 for _ in range(width)] for _ in range(height)]

                # Select random position to place the pattern
                start_row = random.randint(0, max(0, height - len(base_grid)))
                start_col = random.randint(0, max(0, width - len(base_grid[0])))

                for r in range(min(len(base_grid), height - start_row)):
                    for c in range(min(len(base_grid[0]), width - start_col)):
                        grid[start_row + r][start_col + c] = base_grid[r][c]

            else:  # Random patterns
                grid = self.generate_random_grid(width, height, density)

            if exclude_empty and not any(c for row in grid for c in row):
                # Retry once with slightly higher density to avoid empty grids
                grid = self.generate_random_grid(width, height, max(density, 0.3))

            tests.append(GameState(grid))

        return tests