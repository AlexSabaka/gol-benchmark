"""
Carwash Paradox Plugin

Tests whether a model understands the practical constraint that you need to
*drive* to a carwash — even if it is very close — because your car must be
physically present there.  Models naively say "walk" because the distance is
short, completely missing the point that the whole purpose of the trip is to
wash the car.

task_type: "carwash"
"""
from src.plugins.base import BenchmarkPlugin
from .generator import CarwashGenerator
from .parser import CarwashParser
from .evaluator import CarwashEvaluator


class CarwashPlugin(BenchmarkPlugin):
    @property
    def task_type(self) -> str:
        return "carwash"

    @property
    def display_name(self) -> str:
        return "Carwash Paradox"

    @property
    def description(self) -> str:
        return (
            "The carwash is only N metres away — should you walk or drive? "
            "Correct answer is always DRIVE (to bring the car there). "
            "Tests whether the model keeps track of the *goal* of the trip."
        )

    def get_generator(self):
        return CarwashGenerator()

    def get_parser(self):
        return CarwashParser()

    def get_evaluator(self):
        return CarwashEvaluator()


# Auto-discovered by PluginRegistry
plugin = CarwashPlugin()
