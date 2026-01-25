"""
Cellular Automata 1D Benchmark Plugin

Tests LLM ability to apply Wolfram cellular automaton rules
to predict the next state of a 1D binary array.
"""

from typing import Type

from src.plugins.base import (
    BenchmarkPlugin,
    TestCaseGenerator,
    ResponseParser,
    ResultEvaluator,
)
from src.plugins.cellular_automata_1d.generator import C14TestCaseGenerator
from src.plugins.cellular_automata_1d.parser import C14ResponseParser
from src.plugins.cellular_automata_1d.evaluator import C14ResultEvaluator


class CellularAutomata1DPlugin(BenchmarkPlugin):
    """
    1D Cellular Automata benchmark plugin.

    Tests whether LLMs can correctly apply Wolfram cellular automaton
    rules to predict the next generation of a 1D binary state.
    """

    @property
    def task_type(self) -> str:
        return "cellular_automata_1d"

    @property
    def display_name(self) -> str:
        return "1D Cellular Automata"

    @property
    def description(self) -> str:
        return (
            "Tests LLM ability to apply Wolfram cellular automaton rules. "
            "Given a rule number (0-255) and initial state, the model must "
            "predict the next generation by applying neighborhood-based rules."
        )

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self) -> TestCaseGenerator:
        return C14TestCaseGenerator()

    def get_parser(self) -> ResponseParser:
        return C14ResponseParser()

    def get_evaluator(self) -> ResultEvaluator:
        return C14ResultEvaluator()

    def get_config_class(self) -> Type:
        from src.core.types import C14TestConfig
        return C14TestConfig


# Plugin instance for auto-discovery
plugin = CellularAutomata1DPlugin()
