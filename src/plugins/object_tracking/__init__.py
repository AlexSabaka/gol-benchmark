"""
Object Tracking (Grape Test) Benchmark Plugin

Tests LLM's ability to track an object's location through a series
of steps. The critical challenge is recognizing that when a container
is inverted, the object falls out and remains at that location even
if the container is subsequently moved.

Example scenario:
1. I put a grape in a cup on the counter.
2. I set the timer on a microwave to 30 seconds.
3. I turn the cup upside down.
4. I place the cup in the microwave.
5. I start the microwave.

Question: Where is the grape?
Answer: counter (NOT microwave)

The grape falls out when the cup is inverted (step 3), landing on the
counter. When the cup is moved to the microwave (step 4), the grape
stays on the counter.
"""

from typing import Type

from src.plugins.base import (
    BenchmarkPlugin,
    TestCaseGenerator,
    ResponseParser,
    ResultEvaluator,
)
from src.plugins.object_tracking.generator import ObjectTrackingTestCaseGenerator
from src.plugins.object_tracking.parser import ObjectTrackingResponseParser
from src.plugins.object_tracking.evaluator import ObjectTrackingResultEvaluator


class ObjectTrackingPlugin(BenchmarkPlugin):
    """
    Object Tracking (Grape Test) benchmark plugin.

    Tests whether LLMs correctly track object location through
    a sequence of steps including container inversions.

    This tests:
    - Spatial reasoning
    - State tracking across multiple steps
    - Understanding of physical causality (gravity, container inversion)
    - Resistance to distractor information
    """

    @property
    def task_type(self) -> str:
        """Unique identifier for this benchmark."""
        return "object_tracking"

    @property
    def display_name(self) -> str:
        """Human-readable name."""
        return "Object Tracking (Grape Test)"

    @property
    def description(self) -> str:
        """Detailed description of the benchmark."""
        return (
            "Tests LLM's ability to track an object's location through "
            "a series of steps. The critical challenge is recognizing that "
            "when a container is inverted, the object falls out and remains "
            "at that location even if the container is subsequently moved."
        )

    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"

    def get_generator(self) -> TestCaseGenerator:
        """Get the test case generator."""
        return ObjectTrackingTestCaseGenerator()

    def get_parser(self) -> ResponseParser:
        """Get the response parser."""
        return ObjectTrackingResponseParser()

    def get_evaluator(self) -> ResultEvaluator:
        """Get the result evaluator."""
        return ObjectTrackingResultEvaluator()

    def get_default_config(self):
        """Get default configuration for this benchmark."""
        return {
            'object': ['grape', 'marble', 'keys', 'coin', 'ring', 'pill', 'button', 'pebble'],
            'container': ['cup', 'bowl', 'bucket', 'mug', 'box', 'jar', 'glass'],
            'location_initial': ['counter', 'table', 'shelf', 'desk', 'dresser', 'nightstand'],
            'subject': ['I'],
            'distractor_count': [0, 1, 2],
            'distractor_types': ['irrelevant', 'spatial', 'temporal'],
            'sticky_objects': [],
            'post_inversion_moves': [0, 1, 2]
        }


# Plugin instance for auto-discovery
# This MUST be named 'plugin' for the PluginRegistry to find it
plugin = ObjectTrackingPlugin()
