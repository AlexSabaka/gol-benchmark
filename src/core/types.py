
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Dict, Optional, Literal, TypedDict
from pathlib import Path

from src.utils.logger import logger
from src.core.PromptEngine import Language, PromptStyle, SystemPromptStyle

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
class BaseTestConfig(ABC):
    """Abstract base configuration for all test runs with shared fields and validation"""
    models: List[str]
    batch_size: int = 10
    temperature: float = 0.1
    no_think: Optional[bool] = None
    ctx_len: int = 2048
    num_predict: int = 1024
    top_k: int = 40
    min_k: int = 1
    min_p: float = 0.05
    verbose: bool = False
    seed: Optional[int] = None
    examples_count: int = 10
    interface_type: Literal["ollama", "huggingface"] = "ollama"
    prompt_language: Language = Language.EN
    prompt_style: str = 'linguistic'  # Will be validated by task-specific configs
    system_prompt_style: SystemPromptStyle = SystemPromptStyle.ANALYTICAL
    results_dir: str = "results"

    def __post_init__(self):
        """Validate configuration values"""
        if self.batch_size < 1:
            raise ValueError("Batch size must be at least 1")
        if not (0 <= self.temperature <= 2):
            raise ValueError("Temperature must be between 0 and 2")
        if self.top_k < 1:
            raise ValueError("Top-k must be at least 1")
        
        # Validate system prompt style
        if not isinstance(self.system_prompt_style, SystemPromptStyle):
            try:
                self.system_prompt_style = SystemPromptStyle(self.system_prompt_style)
            except ValueError:
                raise ValueError(f"Invalid system_prompt_style: {self.system_prompt_style}")
        
        # Validate language
        if not isinstance(self.prompt_language, Language):
            try:
                self.prompt_language = Language(self.prompt_language)
            except ValueError:
                raise ValueError(f"Invalid prompt_language: {self.prompt_language}")

        # Create results directory if it doesn't exist
        Path(self.results_dir).mkdir(parents=True, exist_ok=True)

@dataclass
class GameOfLifeTestConfig(BaseTestConfig):
    """Configuration for Game of Life test runs"""
    difficulty: DifficultyLevel = DifficultyLevel.EASY
    density: float = 0.3
    iterations: int = 1
    known_patterns_ratio: float = 0.3
    known_patterns_dir: Optional[str] = None
    live_dead_cell_markers: Tuple[str, str] = ('1', '0')  # (live, dead)
    prompt_style: Literal['linguistic', 'casual', 'minimal', 'examples', 'rules_math'] = 'linguistic'
    
    def __post_init__(self):
        """Validate Game of Life specific configuration"""
        super().__post_init__()
        
        # Validate prompt_style for Game of Life
        valid_styles = ['linguistic', 'casual', 'minimal', 'examples', 'rules_math']
        if self.prompt_style not in valid_styles:
            raise ValueError(f"Invalid prompt_style '{self.prompt_style}'. Must be one of: {valid_styles}")
        
        # Validate density
        if not (0 <= self.density <= 1):
            raise ValueError("Density must be between 0 and 1")

@dataclass
class AriTestConfig(BaseTestConfig):
    """Configuration for ARI (Math Expression) test runs"""
    difficulties: List[int] = field(default_factory=lambda: [3])
    target_values: List[int] = field(default_factory=lambda: [3])
    random_target: bool = False
    variables: List[str] = field(default_factory=lambda: ['x'])
    mode: Literal["expression", "equation"] = "expression"
    prompt_style: Literal['linguistic', 'casual', 'minimal', 'examples', 'rules_math'] = 'linguistic'
    prompt_language: Language = Language.EN
    
    def __post_init__(self):
        """Validate ARI specific configuration"""
        super().__post_init__()
        
        # Validate prompt_style for ARI
        valid_styles = ['linguistic', 'casual', 'minimal', 'examples', 'rules_math']
        if self.prompt_style not in valid_styles:
            raise ValueError(f"Invalid prompt_style '{self.prompt_style}'. Must be one of: {valid_styles}")

@dataclass
class C14TestConfig(BaseTestConfig):
    """Configuration for C14 (Cellular Automata) test runs"""
    difficulties: List[int] = field(default_factory=lambda: [3])
    target_values: List[int] = field(default_factory=lambda: [3])
    prompt_style: Literal['linguistic', 'casual', 'minimal', 'examples', 'rules_math'] = 'linguistic'
    prompt_language: Literal["en"] = "en"

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
