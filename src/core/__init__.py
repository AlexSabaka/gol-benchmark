"""
Core Logic and Types

Contains fundamental types, prompt engine, and test generation logic.
"""

from .types import (
    DifficultyLevel,
    ParseError,
    TestResult,
    BaseTestConfig,
    GameOfLifeTestConfig,
    AriTestConfig,
    C14TestConfig,
    GameState,
)

from .PromptEngine import (
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

from .PROMPT_STYLES import get_system_prompt_style

from .TestGenerator import (
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
    "get_system_prompt_style",
    # Test Generation
    "TestGenerator",
    "EXAMPLE_PATTERNS",
]
