
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Dict, Optional, Literal, TypedDict
from pathlib import Path

from src.utils.logger import logger

class DifficultyLevel(Enum):
    """Game difficulty levels with associated grid sizes"""
    EASY = (3, 3)
    MEDIUM = (5, 5)
    HARD = (8, 8)
    NIGHTMARE = (10, 10)

    @classmethod
    def from_string(cls, value: str) -> 'DifficultyLevel':
        """Parse difficulty from string with error handling"""
        mapping = {
            "easy": cls.EASY,
            "medium": cls.MEDIUM,
            "hard": cls.HARD,
            "nightmare": cls.NIGHTMARE
        }
        try:
            return mapping[value.lower()]
        except KeyError:
            logger.warning(f"Unknown difficulty '{value}', defaulting to EASY")
            return cls.EASY

class ParseError(Exception):
    """Custom exception for response parsing failures"""
    def __init__(self, message: str, response: str):
        self.response = response
        super().__init__(message)

class TestResult(TypedDict):
    """Type definition for test results"""
    accuracy: float
    correct_cells: int
    total_cells: int
    parse_error: bool
    cell_by_cell: List[Dict]
    raw_response: str
    error_details: Optional[str]

@dataclass
class TestConfig:
    """Configuration for the test run with validation"""
    models: List[str]
    difficulty: DifficultyLevel
    batch_size: int = 10
    density: float = 0.3
    iterations: int = 1
    known_patterns_ratio: float = 0.3
    known_patterns_dir: Optional[str] = None
    temperature: float = 0.1
    no_think: Optional[bool] = None
    ctx_len: int = 2048
    num_predict: int = 1024
    top_k: int = 40
    min_k: int = 1
    min_p: float = 0.05
    verbose: bool = False
    seed: Optional[int] = None
    live_dead_cell_markers: Tuple[str, str] = ('1', '0')  # (live, dead)
    examples_count: int = 10
    prompt_style: Literal['linguistic', 'casual', 'minimal', 'examples_linguistic', 'examples', 'example_rules_math', 'rules_math'] = 'linguistic'
    system_prompt_style: Literal['analytical', 'casual', 'adversarial', 'none'] = 'analytical'
    prompt_language: Literal["en", "fr", "es", "de", "zh", "ua"] = "en"
    interface_type: Literal["ollama", "huggingface"] = "ollama"
    results_dir: str = "results"

    def __post_init__(self):
        """Validate configuration values"""
        if self.batch_size < 1:
            raise ValueError("Batch size must be at least 1")
        if not (0 <= self.temperature <= 2):
            raise ValueError("Temperature must be between 0 and 2")
        if self.top_k < 1:
            raise ValueError("Top-k must be at least 1")

        # Create results directory if it doesn't exist
        Path(self.results_dir).mkdir(parents=True, exist_ok=True)

@dataclass
class GameState:
    """Represents a Game of Life grid state with validation"""
    grid: List[List[int]]
    width: int = field(init=False)
    height: int = field(init=False)

    def __post_init__(self):
        """Validate and set dimensions"""
        if not self.grid or not all(self.grid):
            raise ValueError("Grid cannot be empty")

        self.height = len(self.grid)
        self.width = len(self.grid[0]) if self.height > 0 else 0

        # Validate all rows have same width
        if any(len(row) != self.width for row in self.grid):
            raise ValueError("All grid rows must have the same width")

        # Validate cell values
        if any(cell not in (0, 1) for row in self.grid for cell in row):
            raise ValueError("Grid cells must be 0 or 1")
