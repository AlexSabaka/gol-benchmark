from src.plugins.base import (
    BenchmarkPlugin,
    TestCaseGenerator,
    ResponseParser,
    ResultEvaluator,
)
from src.plugins.picross.generator import PicrossGenerator
from src.plugins.picross.parser import PicrossParser
from src.plugins.picross.evaluator import PicrossEvaluator


class PicrossPlugin(BenchmarkPlugin):
    """Picross (Nonogram) benchmark plugin.

    Tests LLM spatial constraint-satisfaction: given row and column
    run-length clues, the model must reconstruct the complete binary grid.
    """

    @property
    def task_type(self) -> str:
        return "picross"

    @property
    def display_name(self) -> str:
        return "Picross (Nonogram)"

    @property
    def description(self) -> str:
        return (
            "Tests LLM spatial constraint-satisfaction on nonogram puzzles. "
            "Given row and column clues (run-length sequences of filled cells), "
            "the model must reconstruct the complete grid by propagating "
            "constraints across both axes."
        )

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self) -> TestCaseGenerator:
        return PicrossGenerator()

    def get_parser(self) -> ResponseParser:
        return PicrossParser()

    def get_evaluator(self) -> ResultEvaluator:
        return PicrossEvaluator()


# Plugin instance for auto-discovery
plugin = PicrossPlugin()
