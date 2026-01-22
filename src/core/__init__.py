"""
Core Logic and Types

Contains fundamental types, prompt engine, and test generation logic.
"""

from src.core.types import (
    DifficultyLevel,
    ParseError,
    TestResult,
    BaseTestConfig,
    GameOfLifeTestConfig,
    AriTestConfig,
    C14TestConfig,
    GameState,
)

from src.core.PromptEngine import (
    PromptEngine,
    Language,
    PromptStyle,
    SystemPromptStyle,
    TaskType,
    PromptContext,
    PromptResult,
    create_gol_context,
    create_math_context,
)

from src.core.PROMPT_STYLES import get_prompt_style

from src.core.TestGenerator import (
    TestGenerator,
    EXAMPLE_PATTERNS,
)

__all__ = [
    # Types
    "DifficultyLevel",
    "ParseError",
    "TestResult",
    "BaseTestConfig",
    "GameOfLifeTestConfig",
    "AriTestConfig",
    "C14TestConfig",
    "GameState",
    # Prompt Engine
    "PromptEngine",
    "Language",
    "PromptStyle",
    "SystemPromptStyle",
    "TaskType",
    "PromptContext",
    "PromptResult",
    "create_gol_context",
    "create_math_context",
    "get_prompt_style",
    # Test Generation
    "TestGenerator",
    "EXAMPLE_PATTERNS",
]
