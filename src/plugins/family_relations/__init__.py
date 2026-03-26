"""
Family Relations Plugin

Procedural family counting puzzles requiring perspective-aware reasoning.

Sub-types:
  sibling_count      — "Sally has 3 brothers. Each brother has 2 sisters.
                         How many sisters does Sally have?" (answer: 1)
  shared_children    — "A man has 2 daughters. Each daughter has exactly one
                         brother. How many children does he have?" (answer: 3)
  generational       — grandparent / cousin counting with shared nodes
  perspective_shift  — constraint-based puzzles viewed from different
                         family members' perspectives

task_type: "family_relations"
"""
from src.plugins.base import BenchmarkPlugin


class FamilyRelationsPlugin(BenchmarkPlugin):
    @property
    def task_type(self) -> str:
        return "family_relations"

    @property
    def display_name(self) -> str:
        return "Family Relations"

    @property
    def description(self) -> str:
        return (
            "Procedural family counting puzzles that test perspective-aware "
            "reasoning.  Models must avoid the classic trap of counting the "
            "subject as their own sibling."
        )

    def get_generator(self):
        from .generator import FamilyRelationsGenerator
        return FamilyRelationsGenerator()

    def get_parser(self):
        from .parser import FamilyRelationsParser
        return FamilyRelationsParser()

    def get_evaluator(self):
        from .evaluator import FamilyRelationsEvaluator
        return FamilyRelationsEvaluator()


# Auto-discovered by PluginRegistry
plugin = FamilyRelationsPlugin()
