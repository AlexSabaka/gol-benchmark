"""
Time Arithmetic — Benchmark Plugin

Temporal reasoning: intervals, calendar math, and impossible/trick dates.

Sub-types:
  interval           — straightforward add/subtract duration to a time
  crossing_midnight  — duration that crosses the midnight boundary
  noon_midnight_trap — tricky AM/PM boundary (11:50 AM to 12:10 PM = 20 min)
  day_of_week        — modular day-of-week arithmetic over large offsets
  impossible_date    — dates that don't exist (Feb 30, Apr 31, …)
  leap_year          — Feb 29 validity with century/400-year rule traps
  dst_trap           — (advanced) DST spring-forward / fall-back holes

task_type: "time_arithmetic"
"""
from src.plugins.base import BenchmarkPlugin
from .generator import TimeArithmeticGenerator
from .parser import TimeArithmeticParser
from .evaluator import TimeArithmeticEvaluator


class TimeArithmeticPlugin(BenchmarkPlugin):
    @property
    def task_type(self) -> str:
        return "time_arithmetic"

    @property
    def display_name(self) -> str:
        return "Time Arithmetic"

    @property
    def description(self) -> str:
        return (
            "Temporal reasoning: interval arithmetic, midnight/noon boundary "
            "traps, day-of-week modular math, impossible-date detection, "
            "and leap-year edge cases."
        )

    def get_generator(self):
        return TimeArithmeticGenerator()

    def get_parser(self):
        return TimeArithmeticParser()

    def get_evaluator(self):
        return TimeArithmeticEvaluator()


# Auto-discovered by PluginRegistry
plugin = TimeArithmeticPlugin()
