"""
Sally-Anne Test Case Generator

Generates test cases for false belief reasoning assessment.
"""

import random
import itertools
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..base import TestCaseGenerator, TestCase, ConfigField
from .scenario_builder import SallyAnneScenarioBuilder


class SallyAnneTestCaseGenerator(TestCaseGenerator):
    """Generates Sally-Anne false belief test cases."""
    
    def __init__(self):
        """Initialize generator with scenario builder."""
        self.scenario_builder = SallyAnneScenarioBuilder()
    
    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None
    ) -> List[TestCase]:
        """
        Generate a batch of Sally-Anne test cases.
        
        Args:
            config: Task-specific configuration with:
                - subject_pairs: List of (name_a, gender_a, name_b, gender_b) tuples (empty = random)
                - objects: List of objects to use
                - containers: List of (container_a, container_b) tuples
                - distractor_count: Number of distractor elements (default: 0)
                - leave_activities: List of activities for subject A's departure
                - include_observer: Whether to include observer (default: False)
            prompt_config: Prompt configuration (not used directly, handled by pipeline)
            count: Number of test cases to generate
            seed: Random seed for reproducibility
            
        Returns:
            List of TestCase objects
        """
        if seed is not None:
            random.seed(seed)
        
        # Extract configuration
        subject_pairs = config.get('subject_pairs', [])
        objects = config.get('objects', ['marble', 'ball', 'toy'])
        containers = config.get('containers', [('basket', 'box')])
        distractor_count = config.get('distractor_count', 0)
        leave_activities = config.get('leave_activities', ['goes for a walk'])
        include_observer = config.get('include_observer', False)
        
        # Use random subject pairs if none provided
        use_random_pairs = len(subject_pairs) == 0
        
        test_cases = []
        
        # If using specific subject pairs, create combinations with other parameters
        if not use_random_pairs and subject_pairs:
            # Create all combinations
            combinations = list(itertools.product(
                subject_pairs,
                objects,
                containers,
                leave_activities,
            ))
            
            # Sample or repeat to reach count
            if len(combinations) >= count:
                selected = random.sample(combinations, count)
            else:
                # Repeat combinations to reach count
                selected = random.choices(combinations, k=count)
            
            for idx, (subject_pair, obj, container_pair, leave_activity) in enumerate(selected):
                scenario = self.scenario_builder.generate_scenario(
                    subject_pair=subject_pair,
                    obj=obj,
                    containers=container_pair,
                    leave_activity=leave_activity,
                    distractor_count=distractor_count,
                    include_observer=include_observer,
                    seed=seed + idx if seed else None,
                )
                
                test_case = self._create_test_case(scenario, idx, prompt_config)
                test_cases.append(test_case)
        
        else:
            # Use random subject pairs
            for idx in range(count):
                # Random selections
                obj = random.choice(objects)
                container_pair = random.choice(containers)
                leave_activity = random.choice(leave_activities)
                
                scenario = self.scenario_builder.generate_scenario(
                    subject_pair=None,  # Generate random pair
                    obj=obj,
                    containers=container_pair,
                    leave_activity=leave_activity,
                    distractor_count=distractor_count,
                    include_observer=include_observer,
                    seed=seed + idx if seed else None,
                )
                
                test_case = self._create_test_case(scenario, idx, prompt_config)
                test_cases.append(test_case)
        
        return test_cases
    
    def _create_test_case(self, scenario: Dict[str, Any], idx: int, prompt_config: Dict[str, str]) -> TestCase:
        """
        Create a TestCase object from a scenario.
        
        Args:
            scenario: Scenario dictionary from scenario_builder
            idx: Test case index
            prompt_config: Prompt configuration with name, user_style, system_style
            
        Returns:
            TestCase object
        """
        # Build narrative and question
        narrative = self.scenario_builder.build_narrative(scenario)
        question = self.scenario_builder.build_question(scenario)
        
        # Combine into prompt
        prompt = f"{narrative}\n\n{question}"
        
        # Expected answer is the belief location (container_a)
        expected_answer = scenario['correct_answer']
        
        # Create test ID with config name
        config_name = prompt_config.get('name', 'default')
        test_id = f"sally_anne_{config_name}_{idx:03d}"
        
        # Build task_params with all test information
        task_params = {
            'expected_answer': expected_answer,
            'subject_a': scenario['subject_a_name'],
            'subject_a_gender': scenario['subject_a_gender'],
            'subject_b': scenario['subject_b_name'],
            'subject_b_gender': scenario['subject_b_gender'],
            'object': scenario['object'],
            'container_a': scenario['container_a'],  # Belief location (correct)
            'container_b': scenario['container_b'],  # Actual location (reality trap)
            'leave_activity': scenario['leave_activity'],
            'distractor_count': len(scenario['distractor_elements']),
            'has_observer': scenario['observer'] is not None,
            'correct_answer': expected_answer,
            'reality_trap': scenario['container_b'],
        }
        
        if scenario['observer']:
            task_params['observer'] = scenario['observer']['name']
            task_params['observer_gender'] = scenario['observer']['gender']
        
        system_style_str = prompt_config.get('system_style', '')
        language_str = prompt_config.get('language', 'en')
        system_prompt = self._get_system_prompt(system_style_str, language_str)

        return TestCase(
            test_id=test_id,
            task_type='sally_anne',
            config_name=config_name,
            prompts={
                'system': system_prompt,
                'user': prompt,
                'full': f"{system_prompt}\n\n{prompt}" if system_prompt else prompt,
            },
            task_params=task_params,
            prompt_metadata={
                'user_style': prompt_config.get('user_style', ''),
                'system_style': prompt_config.get('system_style', ''),
            },
            generation_metadata={
                'generator_version': '1.0.0',
                'timestamp': datetime.now().isoformat(),
            }
        )
    
    def get_task_type(self) -> str:
        """Return task type identifier."""
        return "sally_anne"

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='cases_per_config', label='Cases per config', field_type='number',
                        default=5, min_value=1, max_value=200),
            ConfigField(name='distractor_count', label='Distractor count', field_type='number',
                        default=0, min_value=0, max_value=5,
                        help='Number of distractor elements in the scenario'),
            ConfigField(name='include_observer', label='Include observer', field_type='boolean',
                        default=False, group='advanced',
                        help='Add a third-party observer to the scenario'),
            ConfigField(name='objects', label='Objects', field_type='text',
                        default='marble,ball,toy,book,keys', group='advanced',
                        help='Comma-separated list of objects'),
            ConfigField(name='leave_activities', label='Leave activities', field_type='text',
                        default='goes for a walk,goes outside,leaves the room,goes to the kitchen',
                        group='advanced', help='Comma-separated departure activities'),
        ]
