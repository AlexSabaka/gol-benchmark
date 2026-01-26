"""
Grid Tasks Benchmark Plugin

Tests LLM ability to read and reason about formatted text tables with various
data types (sales, HR, grades, inventory) and question types (lookups, sums, counts).
"""

from typing import TYPE_CHECKING

from src.plugins.base import BenchmarkPlugin

if TYPE_CHECKING:
    from src.plugins.base import TestCaseGenerator, ResponseParser, ResultEvaluator


class GridTasksPlugin(BenchmarkPlugin):
    """Plugin for grid-based table reasoning tasks."""
    
    @property
    def task_type(self) -> str:
        return "grid_tasks"
    
    @property
    def display_name(self) -> str:
        return "Grid Tasks (Table Reasoning)"
    
    @property
    def description(self) -> str:
        return "Test ability to read and reason about formatted tables with various data types"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def get_generator(self) -> "TestCaseGenerator":
        from src.plugins.grid_tasks.generator import GridTasksTestCaseGenerator
        return GridTasksTestCaseGenerator()
    
    def get_parser(self) -> "ResponseParser":
        from src.plugins.grid_tasks.parser import GridTasksResponseParser
        return GridTasksResponseParser()
    
    def get_evaluator(self) -> "ResultEvaluator":
        from src.plugins.grid_tasks.evaluator import GridTasksResultEvaluator
        return GridTasksResultEvaluator()


# Export plugin instance for auto-discovery
plugin = GridTasksPlugin()
