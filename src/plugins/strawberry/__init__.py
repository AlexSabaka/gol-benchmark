"""
Strawberry (Letter Counting) — Benchmark Plugin

Tests the classic "How many R's in strawberry?" task: counting
occurrences of a specific letter in a word.

Modes:
  - real:          word from curated list, letter present in the word
  - absent_letter: word from curated list, letter NOT in the word (answer = 0)
  - random:        random character sequence, any letter query
  - mixed:         weighted blend of the above (default)
"""
from src.plugins.base import BenchmarkPlugin
from src.plugins.strawberry.generator import StrawberryGenerator
from src.plugins.strawberry.parser import StrawberryParser
from src.plugins.strawberry.evaluator import StrawberryEvaluator


class StrawberryPlugin(BenchmarkPlugin):
    @property
    def task_type(self) -> str:
        return "strawberry"

    @property
    def display_name(self) -> str:
        return "Strawberry (Letter Counting)"

    @property
    def description(self) -> str:
        return (
            "How many R's in strawberry? "
            "Tests a model's ability to count occurrences of a given letter "
            "in a word. Supports real words, absent-letter traps, and random strings."
        )

    def get_generator(self):
        return StrawberryGenerator()

    def get_parser(self):
        return StrawberryParser()

    def get_evaluator(self):
        return StrawberryEvaluator()


plugin = StrawberryPlugin()
