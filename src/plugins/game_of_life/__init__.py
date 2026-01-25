"""
Game of Life Benchmark Plugin

Conway's Game of Life cellular automaton benchmark for testing
LLM reasoning capabilities on rule-based grid transformations.
"""

from typing import Type

from src.plugins.base import (
    BenchmarkPlugin,
    TestCaseGenerator,
    ResponseParser,
    ResultEvaluator,
)
from src.plugins.game_of_life.generator import GoLTestCaseGenerator
from src.plugins.game_of_life.parser import GoLResponseParser
from src.plugins.game_of_life.evaluator import GoLResultEvaluator


class GameOfLifePlugin(BenchmarkPlugin):
    """
    Game of Life benchmark plugin.

    Tests whether LLMs can correctly predict the next state of a
    Conway's Game of Life grid by applying cellular automaton rules.
    """

    @property
    def task_type(self) -> str:
        return "game_of_life"

    @property
    def display_name(self) -> str:
        return "Conway's Game of Life"

    @property
    def description(self) -> str:
        return (
            "Tests LLM reasoning on Conway's Game of Life cellular automaton. "
            "Given an initial grid state, the model must predict the next generation "
            "by correctly applying birth and survival rules to each cell."
        )

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self) -> TestCaseGenerator:
        return GoLTestCaseGenerator()

    def get_parser(self) -> ResponseParser:
        return GoLResponseParser()

    def get_evaluator(self) -> ResultEvaluator:
        return GoLResultEvaluator()

    def get_config_class(self) -> Type:
        from src.core.types import GameOfLifeTestConfig
        return GameOfLifeTestConfig


# Plugin instance for auto-discovery
plugin = GameOfLifePlugin()
