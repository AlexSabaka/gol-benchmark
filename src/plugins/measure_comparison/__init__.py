"""
Measure Comparison — Benchmark Plugin

Tests an LLM's ability to compare two quantities with units.

The classic failure: "Which is longer, 0.1 mm or 1 mm?" — many models
get tripped up by decimal precision, digit counts, or unit conversions.

Comparison types:
  - same_unit:     both values share a unit (pure numerical comparison)
  - mixed_unit:    compatible units, requires conversion (e.g. cm vs inch)
  - equal:         trick — values are equivalent after conversion (e.g. 1000 g vs 1 kg)
  - incomparable:  trick — different physical dimensions (e.g. 98 °C vs 2 kg)

Number formats:  integer, decimal (with adversarial traps), fraction

Unit categories: length, mass, temperature, volume, speed, time
"""
from src.plugins.base import BenchmarkPlugin
from src.plugins.measure_comparison.generator import MeasureComparisonGenerator
from src.plugins.measure_comparison.parser import MeasureComparisonParser
from src.plugins.measure_comparison.evaluator import MeasureComparisonEvaluator


class MeasureComparisonPlugin(BenchmarkPlugin):
    @property
    def task_type(self) -> str:
        return "measure_comparison"

    @property
    def display_name(self) -> str:
        return "Measure Comparison"

    @property
    def description(self) -> str:
        return (
            "Which is longer: 0.1 mm or 1 mm? "
            "Tests a model's ability to compare two quantities with measurement "
            "units. Supports same-unit, mixed-unit, equal-value tricks, "
            "incomparable-unit tricks, and decimal-trap adversarial pairs."
        )

    def get_generator(self):
        return MeasureComparisonGenerator()

    def get_parser(self):
        return MeasureComparisonParser()

    def get_evaluator(self):
        return MeasureComparisonEvaluator()


plugin = MeasureComparisonPlugin()
