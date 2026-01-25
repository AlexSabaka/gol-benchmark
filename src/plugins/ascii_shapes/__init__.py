"""
ASCII Shapes Benchmark Plugin

Tests LLM spatial reasoning abilities on ASCII-rendered shapes
with questions about dimensions, counts, and positions.
"""

from typing import Type

from src.plugins.base import (
    BenchmarkPlugin,
    TestCaseGenerator,
    ResponseParser,
    ResultEvaluator,
)
from src.plugins.ascii_shapes.generator import AsciiShapesTestCaseGenerator
from src.plugins.ascii_shapes.parser import AsciiShapesResponseParser
from src.plugins.ascii_shapes.evaluator import AsciiShapesResultEvaluator


class AsciiShapesPlugin(BenchmarkPlugin):
    """
    ASCII Shapes benchmark plugin.

    Tests LLM spatial reasoning on ASCII art shapes with questions
    about dimensions, symbol counts, and position queries.
    """

    @property
    def task_type(self) -> str:
        return "ascii_shapes"

    @property
    def display_name(self) -> str:
        return "ASCII Shapes Spatial Reasoning"

    @property
    def description(self) -> str:
        return (
            "Tests LLM spatial reasoning on ASCII art shapes. "
            "Three question types: dimensions (WxH), symbol counts, "
            "and position queries (is there a symbol at x,y)."
        )

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self) -> TestCaseGenerator:
        return AsciiShapesTestCaseGenerator()

    def get_parser(self) -> ResponseParser:
        return AsciiShapesResponseParser()

    def get_evaluator(self) -> ResultEvaluator:
        return AsciiShapesResultEvaluator()

    def get_config_class(self) -> Type:
        from src.core.types import AsciiShapesTestConfig
        return AsciiShapesTestConfig


# Plugin instance for auto-discovery
plugin = AsciiShapesPlugin()
