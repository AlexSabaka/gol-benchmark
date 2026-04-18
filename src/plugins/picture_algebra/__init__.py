"""Picture Algebra Benchmark Plugin.

System-of-equations puzzles whose variables are rendered as emoji, alpha
letters, or nonsense words.  Operationalizes the GSM-Symbolic experiment
inside this benchmark suite: run the same seed across different
`surface_form` values and measure how semantic associations of emoji
variables corrupt integer-solving accuracy.
"""

from src.plugins.base import (
    BenchmarkPlugin,
    ResponseParser,
    ResultEvaluator,
    TestCaseGenerator,
)
from src.plugins.picture_algebra.evaluator import PictureAlgebraEvaluator
from src.plugins.picture_algebra.generator import PictureAlgebraGenerator
from src.plugins.picture_algebra.parser import PictureAlgebraParser


class PictureAlgebraPlugin(BenchmarkPlugin):

    @property
    def task_type(self) -> str:
        return "picture_algebra"

    @property
    def display_name(self) -> str:
        return "Picture Algebra"

    @property
    def description(self) -> str:
        return (
            "System-of-equations puzzles using emoji/icon variables — "
            "measures arithmetic degradation under semantic surface noise "
            "(the GSM-Symbolic experiment in miniature)."
        )

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_generator(self) -> TestCaseGenerator:
        return PictureAlgebraGenerator()

    def get_parser(self) -> ResponseParser:
        return PictureAlgebraParser()

    def get_evaluator(self) -> ResultEvaluator:
        return PictureAlgebraEvaluator()


plugin = PictureAlgebraPlugin()
