from conways_life.parser import ConwayPatternParser
from src.utils.logger import logger
from src.core.types import DifficultyLevel, GameState, BaseTestConfig

from pathlib import Path

import os
import random
import numpy as np

from typing import List, Optional

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

    def generate_random_grid(self, width: int, height: int, density: float = 0.3) -> List[List[int]]:
        """Generate random initial state with given density"""
        if not (0 <= density <= 1):
            raise ValueError("Density must be between 0 and 1")

        return [[1 if np.random.rand() < density else 0
                for _ in range(width)]
                for _ in range(height)]

    def generate_known_pattern(self) -> List[List[int]]:
        """Generate known patterns for targeted testing"""
        
        # Select random known pattern from PATTERNS_DATABASE_PATH
        pattern_files = [f for f in os.listdir(self.config.known_patterns_dir) if f.endswith(('.rle', '.cells'))]
        if pattern_files:
            selected_file = random.choice(pattern_files)
            parser = ConwayPatternParser()
            try:
                pattern_grid, _ = parser.parse_file(str(Path(self.config.known_patterns_dir) / selected_file))
                return pattern_grid.grid
            except Exception as e:
                logger.warning(f"Failed to parse pattern file {selected_file}: {e}")

        # Fallback to basic known patterns
        return random.choice(list(BASIC_KNOWN_PATTERNS.values()))

    def create_test_batch(self, difficulty: DifficultyLevel, batch_size: int = 10, density: float = 0.3, known_patterns_ratio: float = 0.3) -> List[GameState]:
        """Create a batch of test cases with better pattern distribution"""
        width, height = difficulty.value
        tests = []

        for i in range(batch_size):
            if i < batch_size * known_patterns_ratio:  # Known patterns
                base_grid = self.generate_known_pattern()
                
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

            tests.append(GameState(grid))

        return tests