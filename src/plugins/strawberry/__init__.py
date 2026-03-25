"""
Strawberry (Character-Level Reasoning) — Benchmark Plugin

A family of character-level reasoning tasks:

  count       — How many R's in strawberry?  (the classic)
  reverse     — Spell "banana" backwards
  nth_letter  — What is the 3rd letter of "algorithm"?
  anagram     — Are "listen" and "silent" anagrams?
  pangram     — Does this sentence use every letter of the alphabet?
  lipogram    — Does this sentence avoid the letter 'e'?

All sub-types are configurable via the `sub_types` multi-select field.
Defaults to ["count"] for backward compatibility.
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
        return "Strawberry (Character Reasoning)"

    @property
    def description(self) -> str:
        return (
            "Character-level reasoning: letter counting, word reversal, "
            "nth-letter extraction, anagram detection, pangram checking, "
            "and lipogram verification."
        )

    def get_generator(self):
        return StrawberryGenerator()

    def get_parser(self):
        return StrawberryParser()

    def get_evaluator(self):
        return StrawberryEvaluator()


plugin = StrawberryPlugin()
