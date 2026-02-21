"""
Inverted Cup Plugin

Tests whether a model can solve a simple physical orientation puzzle:
a cup with a *sealed top* and an *open bottom* is, by definition, already
inverted.  The correct (and only practical) action is to flip/turn it over.

Models often become confused or suggest impractical alternatives (drilling,
cutting, returning), missing the obvious.

task_type: "inverted_cup"
"""
from src.plugins.base import BenchmarkPlugin
from .generator import InvertedCupGenerator
from .parser import InvertedCupParser
from .evaluator import InvertedCupEvaluator


class InvertedCupPlugin(BenchmarkPlugin):
    @property
    def task_type(self) -> str:
        return "inverted_cup"

    @property
    def display_name(self) -> str:
        return "Inverted Cup"

    @property
    def description(self) -> str:
        return (
            "A cup with a sealed top and open bottom — how do you use it? "
            "The correct answer is to flip it over. "
            "Tests spatial reasoning and object-orientation understanding."
        )

    def get_generator(self):
        return InvertedCupGenerator()

    def get_parser(self):
        return InvertedCupParser()

    def get_evaluator(self):
        return InvertedCupEvaluator()


# Auto-discovered by PluginRegistry
plugin = InvertedCupPlugin()
