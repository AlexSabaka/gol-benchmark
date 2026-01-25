"""
Linda Conjunction Fallacy Benchmark Plugin

Tests LLM susceptibility to the conjunction fallacy,
a cognitive bias where people judge a conjunction of events
as more probable than one of its components.
"""

from typing import Type

from src.plugins.base import (
    BenchmarkPlugin,
    TestCaseGenerator,
    ResponseParser,
    ResultEvaluator,
)
from src.plugins.linda_fallacy.generator import LindaTestCaseGenerator
from src.plugins.linda_fallacy.parser import LindaResponseParser
from src.plugins.linda_fallacy.evaluator import LindaResultEvaluator


class LindaFallacyPlugin(BenchmarkPlugin):
    """
    Linda Conjunction Fallacy benchmark plugin.

    Tests whether LLMs fall for the conjunction fallacy when
    ranking probability of statements about a person.
    """

    @property
    def task_type(self) -> str:
        return "linda_fallacy"

    @property
    def display_name(self) -> str:
        return "Linda Conjunction Fallacy"

    @property
    def description(self) -> str:
        return (
            "Tests LLM susceptibility to the conjunction fallacy. "
            "Given a persona description, models rank statements by probability. "
            "The fallacy occurs when a conjunction (A and B) is ranked higher than "
            "one of its components (A or B alone)."
        )

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self) -> TestCaseGenerator:
        return LindaTestCaseGenerator()

    def get_parser(self) -> ResponseParser:
        return LindaResponseParser()

    def get_evaluator(self) -> ResultEvaluator:
        return LindaResultEvaluator()

    def get_config_class(self) -> Type:
        from src.core.types import LindaFallacyTestConfig
        return LindaFallacyTestConfig


# Plugin instance for auto-discovery
plugin = LindaFallacyPlugin()
