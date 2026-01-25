"""
Arithmetic Expression Benchmark Plugin

Tests LLM ability to evaluate mathematical expressions
with varying complexity levels.
"""

from typing import Type

from src.plugins.base import (
    BenchmarkPlugin,
    TestCaseGenerator,
    ResponseParser,
    ResultEvaluator,
)
from src.plugins.arithmetic.generator import ArithmeticTestCaseGenerator
from src.plugins.arithmetic.parser import ArithmeticResponseParser
from src.plugins.arithmetic.evaluator import ArithmeticResultEvaluator


class ArithmeticPlugin(BenchmarkPlugin):
    """
    Arithmetic expression benchmark plugin.

    Tests whether LLMs can correctly evaluate mathematical expressions
    with varying complexity levels and operations.
    """

    @property
    def task_type(self) -> str:
        return "arithmetic"

    @property
    def display_name(self) -> str:
        return "Arithmetic Expression Evaluation"

    @property
    def description(self) -> str:
        return (
            "Tests LLM ability to evaluate mathematical expressions. "
            "Expressions are generated with configurable complexity levels, "
            "target values, and operation types."
        )

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self) -> TestCaseGenerator:
        return ArithmeticTestCaseGenerator()

    def get_parser(self) -> ResponseParser:
        return ArithmeticResponseParser()

    def get_evaluator(self) -> ResultEvaluator:
        return ArithmeticResultEvaluator()

    def get_config_class(self) -> Type:
        from src.core.types import AriTestConfig
        return AriTestConfig


# Plugin instance for auto-discovery
plugin = ArithmeticPlugin()
