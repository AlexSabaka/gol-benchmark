"""
Abstract base classes for the benchmark plugin system.

This module defines the core interfaces that all benchmark plugins must implement:
- BenchmarkPlugin: Main plugin interface
- TestCaseGenerator: Generates test cases for a benchmark
- ResponseParser: Parses model responses
- ResultEvaluator: Evaluates parsed answers against expected answers

Example usage:
    from src.plugins import PluginRegistry

    plugin = PluginRegistry.get('game_of_life')
    generator = plugin.get_generator()
    test_cases = generator.generate_batch(config, prompt_config, count=10, seed=42)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
from datetime import datetime


@dataclass
class TestCase:
    """
    Standard test case format for all benchmarks.

    This is the common data structure produced by all generators
    and consumed by the 3-stage pipeline.

    Attributes:
        test_id: Unique identifier for this test case (e.g., 'gol_0001')
        task_type: The benchmark type (e.g., 'game_of_life', 'arithmetic')
        config_name: Name of the prompt configuration used
        prompts: Dictionary containing 'system', 'user', and 'full' prompts
        task_params: Task-specific parameters and expected answer
        prompt_metadata: Information about prompt style, language, etc.
        generation_metadata: Information about generation (seed, timestamp, etc.)
    """
    test_id: str
    task_type: str
    config_name: str
    prompts: Dict[str, str]
    task_params: Dict[str, Any]
    prompt_metadata: Dict[str, str]
    generation_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'test_id': self.test_id,
            'task_type': self.task_type,
            'config_name': self.config_name,
            'prompts': self.prompts,
            'task_params': self.task_params,
            'prompt_metadata': self.prompt_metadata,
            'generation_metadata': self.generation_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create TestCase from dictionary."""
        return cls(
            test_id=data['test_id'],
            task_type=data['task_type'],
            config_name=data['config_name'],
            prompts=data['prompts'],
            task_params=data['task_params'],
            prompt_metadata=data['prompt_metadata'],
            generation_metadata=data.get('generation_metadata', {}),
        )


@dataclass
class ParsedAnswer:
    """
    Standard parsed answer format.

    Represents the result of parsing a model's response.

    Attributes:
        value: The parsed answer value (type depends on task)
        raw_response: The original model response
        parse_strategy: Name of the strategy that successfully parsed
        confidence: Confidence score (0.0-1.0), default 1.0
        error: Error message if parsing failed
    """
    value: Any
    raw_response: str
    parse_strategy: str
    confidence: float = 1.0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if parsing was successful."""
        return self.error is None and self.value is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'value': self.value,
            'raw_response': self.raw_response,
            'parse_strategy': self.parse_strategy,
            'confidence': self.confidence,
            'error': self.error,
        }


@dataclass
class EvaluationResult:
    """
    Standard evaluation result format.

    Represents the result of evaluating a parsed answer against expected.

    Attributes:
        correct: Whether the answer is correct
        match_type: Type of match (e.g., 'exact', 'partial', 'cell_by_cell')
        accuracy: Accuracy score (0.0-1.0)
        details: Additional task-specific details
        error: Error message if evaluation failed
    """
    correct: bool
    match_type: str
    accuracy: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'correct': self.correct,
            'match_type': self.match_type,
            'accuracy': self.accuracy,
            'details': self.details,
            'error': self.error,
        }


@dataclass
class ConfigField:
    """
    Describes a single configurable field for a plugin generator.

    Used by the web UI to dynamically render configuration forms.
    Each generator returns a list of these from get_config_schema().
    """
    name: str               # Config dict key (matches what generate_batch reads)
    label: str              # Human-readable label for the UI
    field_type: str         # "number" | "select" | "multi-select" | "text" | "boolean" | "range" | "weight_map"
    default: Any            # Default value
    help: str = ""          # Tooltip / help text
    group: str = "basic"    # "basic" (visible) or "advanced" (collapsed)
    # Number fields
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    # Select / multi-select fields
    options: Optional[List[Any]] = None
    # Range fields (for tuple-like min/max pairs, e.g. width_range)
    range_min_default: Optional[float] = None
    range_max_default: Optional[float] = None
    # Weight map fields (for dicts like mixed_weights)
    weight_keys: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-friendly dict for the API."""
        d: Dict[str, Any] = {
            "name": self.name,
            "label": self.label,
            "type": self.field_type,
            "default": self.default,
        }
        if self.help:
            d["help"] = self.help
        if self.group != "basic":
            d["group"] = self.group
        if self.min_value is not None:
            d["min"] = self.min_value
        if self.max_value is not None:
            d["max"] = self.max_value
        if self.step is not None:
            d["step"] = self.step
        if self.options is not None:
            d["options"] = self.options
        if self.range_min_default is not None:
            d["range_min_default"] = self.range_min_default
        if self.range_max_default is not None:
            d["range_max_default"] = self.range_max_default
        if self.weight_keys is not None:
            d["weight_keys"] = self.weight_keys
        return d


class TestCaseGenerator(ABC):
    """
    Abstract base class for test case generators.

    Each benchmark plugin provides a generator that creates test cases
    according to the benchmark's specific requirements.
    """

    @abstractmethod
    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None
    ) -> List[TestCase]:
        """
        Generate a batch of test cases.

        Args:
            config: Task-specific generation configuration
            prompt_config: Prompt style configuration with keys:
                - 'user_style': User prompt style
                - 'system_style': System prompt style
                - 'name': Configuration name
            count: Number of test cases to generate
            seed: Random seed for reproducibility

        Returns:
            List of TestCase objects
        """
        pass

    def get_default_config(self) -> Dict[str, Any]:
        """
        Return default configuration for this generator.

        Override this to provide sensible defaults.
        """
        return {}

    def get_config_schema(self) -> List['ConfigField']:
        """
        Return structured field descriptors for this generator's configuration.

        Override this to provide UI-friendly metadata for all configurable
        options. The web UI uses this to dynamically render configuration forms.
        If not overridden, the API falls back to hardcoded schemas.

        Returns:
            List of ConfigField objects describing each config parameter.
        """
        return []


class ResponseParser(ABC):
    """
    Abstract base class for response parsers.

    Each benchmark plugin provides a parser that extracts answers
    from model responses using task-specific parsing strategies.
    """

    @abstractmethod
    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        """
        Parse a model response into a structured answer.

        Args:
            response: Raw model response string
            task_params: Task parameters from the test case

        Returns:
            ParsedAnswer object with extracted value or error
        """
        pass

    def get_strategies(self) -> List[str]:
        """
        Return list of parsing strategy names.

        Override this to document available parsing strategies.
        """
        return ['default']


class ResultEvaluator(ABC):
    """
    Abstract base class for result evaluators.

    Each benchmark plugin provides an evaluator that compares
    parsed answers against expected answers.
    """

    @abstractmethod
    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate a parsed answer against expected.

        Args:
            parsed_answer: The parsed answer from ResponseParser
            expected_answer: The expected answer from test case
            task_params: Task parameters for context

        Returns:
            EvaluationResult object with correctness and details
        """
        pass

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Aggregate multiple results into summary statistics.

        Args:
            results: List of EvaluationResult objects

        Returns:
            Dictionary with aggregated statistics
        """
        if not results:
            return {
                'accuracy': 0.0,
                'correct': 0,
                'total': 0,
                'error_count': 0,
            }

        correct = sum(1 for r in results if r.correct)
        errors = sum(1 for r in results if r.error is not None)

        return {
            'accuracy': correct / len(results),
            'correct': correct,
            'total': len(results),
            'error_count': errors,
            'match_types': self._count_match_types(results),
        }

    def _count_match_types(self, results: List[EvaluationResult]) -> Dict[str, int]:
        """Count occurrences of each match type."""
        counts: Dict[str, int] = {}
        for r in results:
            counts[r.match_type] = counts.get(r.match_type, 0) + 1
        return counts


class BenchmarkPlugin(ABC):
    """
    Main interface for a benchmark plugin.

    Each benchmark (Game of Life, Arithmetic, Linda, etc.) implements
    this interface to register with the plugin system.

    Example:
        class GameOfLifePlugin(BenchmarkPlugin):
            @property
            def task_type(self) -> str:
                return "game_of_life"

            @property
            def display_name(self) -> str:
                return "Conway's Game of Life"

            def get_generator(self) -> TestCaseGenerator:
                return GoLTestCaseGenerator()

            def get_parser(self) -> ResponseParser:
                return GoLResponseParser()

            def get_evaluator(self) -> ResultEvaluator:
                return GoLResultEvaluator()

        # In __init__.py:
        plugin = GameOfLifePlugin()  # Auto-discovered by registry
    """

    @property
    @abstractmethod
    def task_type(self) -> str:
        """
        Unique identifier for this task.

        This should match the task_type used in YAML configs and test sets.
        Examples: 'game_of_life', 'arithmetic', 'linda_fallacy'
        """
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable name for this benchmark.

        Examples: "Conway's Game of Life", "Arithmetic Expression Evaluation"
        """
        pass

    @property
    def description(self) -> str:
        """
        Detailed description of the benchmark.

        Override to provide more context about what the benchmark tests.
        """
        return f"{self.display_name} benchmark"

    @property
    def version(self) -> str:
        """
        Version of this plugin.

        Override to track plugin changes.
        """
        return "1.0.0"

    @abstractmethod
    def get_generator(self) -> TestCaseGenerator:
        """
        Return the test case generator for this benchmark.
        """
        pass

    @abstractmethod
    def get_parser(self) -> ResponseParser:
        """
        Return the response parser for this benchmark.
        """
        pass

    @abstractmethod
    def get_evaluator(self) -> ResultEvaluator:
        """
        Return the result evaluator for this benchmark.
        """
        pass

    def get_config_class(self) -> Optional[Type]:
        """
        Return the config class for this benchmark, if any.

        Override to provide task-specific configuration validation.
        """
        return None

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate a configuration dictionary.

        Args:
            config: Configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        return []
