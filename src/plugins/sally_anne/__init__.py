"""
Sally-Anne False Belief Test Plugin

Tests Theory of Mind reasoning through false belief scenarios:
- Subject A places object in container_a
- Subject A leaves
- Subject B moves object to container_b (while A is absent)
- Subject A returns
- Question: Where will Subject A look for the object?

Correct answer: container_a (where A believes it is - false belief)
Common error: container_b (where it actually is - reality trap)

Key differences from object_tracking (grape test):
- Tests mental state attribution vs physical causality
- Correct answer is belief location, not actual location
- Focuses on absence and knowledge states
"""

from typing import Dict, Any, List
from ..base import BenchmarkPlugin, TestCaseGenerator, ResponseParser, ResultEvaluator
from .scenario_builder import SallyAnneScenarioBuilder
from .generator import SallyAnneTestCaseGenerator
from .parser import SallyAnneResponseParser
from .evaluator import SallyAnneResultEvaluator


class SallyAnnePlugin(BenchmarkPlugin):
    """Sally-Anne false belief test plugin for Theory of Mind assessment."""
    
    @property
    def task_type(self) -> str:
        return "sally_anne"
    
    @property
    def display_name(self) -> str:
        return "Sally-Anne Test"
    
    @property
    def description(self) -> str:
        return "Theory of Mind false belief reasoning test"
    
    def get_generator(self) -> TestCaseGenerator:
        """Create test case generator."""
        return SallyAnneTestCaseGenerator()
    
    def get_parser(self) -> ResponseParser:
        """Create response parser for Sally-Anne answers."""
        return SallyAnneResponseParser()
    
    def get_evaluator(self) -> ResultEvaluator:
        """Create result evaluator for Sally-Anne tests."""
        return SallyAnneResultEvaluator()
    
    # Backward compatibility methods
    def create_generator(self, config: Dict[str, Any]) -> TestCaseGenerator:
        """Create test case generator with configuration (backward compat)."""
        return SallyAnneTestCaseGenerator()
    
    def create_parser(self) -> ResponseParser:
        """Create response parser for Sally-Anne answers."""
        return self.get_parser()
    
    def create_evaluator(self) -> ResultEvaluator:
        """Create result evaluator for Sally-Anne tests."""
        return self.get_evaluator()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for Sally-Anne tests."""
        return {
            'cases_per_config': 5,
            'subject_pairs': [
                # Classic pair
                ('Sally', 'female', 'Anne', 'female'),
            ],
            'objects': ['marble', 'ball', 'toy', 'book', 'keys'],
            'containers': [
                ('basket', 'box'),
                ('drawer', 'cupboard'),
                ('bag', 'pocket'),
            ],
            'distractor_count': 0,
            'leave_activities': [
                'goes for a walk',
                'goes outside',
                'leaves the room',
                'goes to the kitchen',
            ],
            'include_observer': False,
        }
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate Sally-Anne test configuration."""
        errors = []
        
        # Required fields
        if 'cases_per_config' not in config:
            errors.append("Missing 'cases_per_config' parameter")
        
        # Subject pairs validation
        if 'subject_pairs' in config:
            pairs = config['subject_pairs']
            if not isinstance(pairs, list) or len(pairs) == 0:
                errors.append("'subject_pairs' must be non-empty list")
            else:
                for pair in pairs:
                    if not isinstance(pair, (tuple, list)) or len(pair) != 4:
                        errors.append(f"Invalid subject pair: {pair}. Expected (name1, gender1, name2, gender2)")
        
        # Objects validation
        if 'objects' in config:
            if not isinstance(config['objects'], list) or len(config['objects']) == 0:
                errors.append("'objects' must be non-empty list")
        
        # Containers validation
        if 'containers' in config:
            containers = config['containers']
            if not isinstance(containers, list) or len(containers) == 0:
                errors.append("'containers' must be non-empty list")
            else:
                for container in containers:
                    if not isinstance(container, (tuple, list)) or len(container) != 2:
                        errors.append(f"Invalid container pair: {container}. Expected (container_a, container_b)")
        
        # Leave activities validation
        if 'leave_activities' in config:
            if not isinstance(config['leave_activities'], list) or len(config['leave_activities']) == 0:
                errors.append("'leave_activities' must be non-empty list")
        
        return errors


# Create and register plugin instance
plugin = SallyAnnePlugin()
