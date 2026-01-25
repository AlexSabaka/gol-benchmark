"""
Game of Life Test Case Generator

Generates test cases for the Game of Life benchmark by creating
initial grid states and computing their expected next generation.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.plugins.base import TestCase, TestCaseGenerator
from src.core.PromptEngine import (
    PromptEngine,
    PromptContext,
    Language,
    PromptStyle,
    SystemPromptStyle,
    TaskType,
)
from src.core.types import DifficultyLevel
from src.engine.GameOfLifeEngine import GameOfLifeEngine


def format_grid(grid: List[List[int]], live_cell: str = '1', dead_cell: str = '0') -> str:
    """Format grid into string representation."""
    return "\n".join(
        [" ".join(map(str, row)) for row in grid]
    ).replace('1', live_cell).replace('0', dead_cell)


class GoLTestCaseGenerator(TestCaseGenerator):
    """
    Test case generator for Game of Life benchmark.

    Generates grid states with configurable difficulty (grid size),
    density (ratio of live cells), and support for known patterns.
    """

    def __init__(self):
        self._engine = GameOfLifeEngine()
        self._prompt_engine = PromptEngine()
        self._test_generator = None

    def _get_test_generator(self, seed: Optional[int] = None):
        """Lazy-load TestGenerator to avoid circular imports."""
        if self._test_generator is None or seed is not None:
            from src.core.TestGenerator import TestGenerator
            from src.core.types import BaseTestConfig
            from dataclasses import dataclass, field
            from typing import List

            @dataclass
            class MinimalConfig(BaseTestConfig):
                """Minimal config for test generation."""
                models: List[str] = field(default_factory=lambda: ["dummy"])
                seed: int = 42
                known_patterns_dir: str = "data/conways_life/known_patterns"

                def __post_init__(self):
                    super().__post_init__()

            config = MinimalConfig(seed=seed or 42)
            self._test_generator = TestGenerator(config)

        return self._test_generator

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None
    ) -> List[TestCase]:
        """
        Generate a batch of Game of Life test cases.

        Args:
            config: Generation configuration with keys:
                - difficulty_levels: List of difficulty strings ('EASY', 'MEDIUM', etc.)
                - density: Float ratio of live cells (default 0.5)
                - known_patterns_ratio: Float ratio of known patterns (default 0.3)
                - grids_per_difficulty: Number of grids per difficulty level
                - cell_markers: List [live_cell, dead_cell] markers
            prompt_config: Prompt configuration with keys:
                - user_style: User prompt style ('minimal', 'casual', 'linguistic')
                - system_style: System prompt style ('analytical', 'casual', 'adversarial')
                - name: Configuration name
                - language: Language code (default 'en')
            count: Total number of test cases to generate
            seed: Random seed for reproducibility

        Returns:
            List of TestCase objects
        """
        test_generator = self._get_test_generator(seed)
        tests = []
        test_id = 0

        # Extract configuration
        difficulty_levels = config.get('difficulty_levels', ['MEDIUM'])
        density = config.get('density', 0.5)
        known_patterns_ratio = config.get('known_patterns_ratio', 0.3)
        grids_per_difficulty = config.get('grids_per_difficulty', count // len(difficulty_levels) or 1)
        cell_markers = config.get('cell_markers', ['1', '0'])
        live_cell = cell_markers[0] if cell_markers else '1'
        dead_cell = cell_markers[1] if len(cell_markers) > 1 else '0'

        # Parse prompt configuration
        language_str = prompt_config.get('language', 'en')
        user_style_str = prompt_config.get('user_style', 'linguistic')
        system_style_str = prompt_config.get('system_style', 'analytical')
        config_name = prompt_config.get('name', f"{user_style_str}_{system_style_str}")

        # Map strings to enums
        try:
            language = Language(language_str)
        except ValueError:
            language = Language.EN

        try:
            user_style = PromptStyle(user_style_str)
        except ValueError:
            user_style = PromptStyle.LINGUISTIC

        try:
            system_style = SystemPromptStyle(system_style_str)
        except ValueError:
            system_style = SystemPromptStyle.ANALYTICAL

        # Generate tests for each difficulty level
        for difficulty_str in difficulty_levels:
            try:
                difficulty = DifficultyLevel[difficulty_str.upper()]
            except KeyError:
                difficulty = DifficultyLevel.from_string(difficulty_str.lower())

            for _ in range(grids_per_difficulty):
                if test_id >= count:
                    break

                # Generate a test grid
                game_states = test_generator.create_test_batch(
                    difficulty=difficulty,
                    batch_size=1,
                    density=density,
                    known_patterns_ratio=known_patterns_ratio
                )

                if not game_states:
                    continue

                game_state = game_states[0]
                initial_grid = game_state.grid

                # Compute expected next state
                next_state = self._engine.next_state(initial_grid)

                # Create prompt context
                context = PromptContext(
                    task_type=TaskType.GAME_OF_LIFE,
                    language=language,
                    style=user_style,
                    system_style=system_style
                )

                # Set grid context
                grid_str = format_grid(initial_grid, live_cell, dead_cell)
                context.set('initial_grid', initial_grid)
                context.set('live_cell', live_cell)
                context.set('dead_cell', dead_cell)
                context.set('grid_str', grid_str)
                context.set('l', live_cell)
                context.set('d', dead_cell)

                # Generate prompts
                result = self._prompt_engine.generate(context)

                # Create test case
                test_case = TestCase(
                    test_id=f"gol_{test_id:04d}",
                    task_type='game_of_life',
                    config_name=config_name,
                    prompts={
                        'system': result.system_prompt,
                        'user': result.user_prompt,
                        'full': f"{result.system_prompt}\n\n{result.user_prompt}"
                    },
                    task_params={
                        'difficulty': difficulty_str,
                        'initial_grid': initial_grid,
                        'expected_next_state': next_state,
                        'live_cell': live_cell,
                        'dead_cell': dead_cell,
                        'density': density,
                        'known_pattern': getattr(game_state, 'pattern_name', None)
                    },
                    prompt_metadata={
                        'user_style': user_style_str,
                        'system_style': system_style_str,
                        'language': language_str
                    },
                    generation_metadata={
                        'seed': seed,
                        'generator_version': "1.0.0",
                        'created_at': datetime.now().isoformat()
                    }
                )

                tests.append(test_case)
                test_id += 1

            if test_id >= count:
                break

        return tests

    def get_default_config(self) -> Dict[str, Any]:
        """Return default generation configuration."""
        return {
            'difficulty_levels': ['MEDIUM'],
            'density': 0.5,
            'known_patterns_ratio': 0.3,
            'grids_per_difficulty': 10,
            'cell_markers': ['1', '0'],
        }
