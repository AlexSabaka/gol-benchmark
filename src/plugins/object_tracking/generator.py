"""
Object Tracking Test Case Generator

Generates test cases for the object tracking (grape test) benchmark
using the StepBuilder to create diverse scenarios.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import random

from src.plugins.base import TestCase, TestCaseGenerator, ConfigField
from src.plugins.parse_utils import safe_enum
from src.plugins.object_tracking.step_builder import StepBuilder, Scenario
from src.core.PromptEngine import PromptEngine, SystemPromptStyle, Language


# Default vocabulary for test generation
DEFAULT_OBJECTS = ['grape', 'marble', 'keys', 'coin', 'ring', 'pill', 'button', 'pebble']
DEFAULT_CONTAINERS = ['cup', 'bowl', 'bucket', 'mug', 'box', 'jar', 'glass']
DEFAULT_LOCATIONS = ['counter', 'table', 'shelf', 'desk', 'dresser', 'nightstand']
DEFAULT_SUBJECTS = ['I']
DEFAULT_DISTRACTOR_TYPES = ['irrelevant', 'spatial', 'temporal']


class ObjectTrackingTestCaseGenerator(TestCaseGenerator):
    """
    Test case generator for Object Tracking (Grape Test) benchmark.

    Generates scenarios where an object is placed in a container,
    the container is inverted (causing the object to fall), and
    optionally the container is moved to a new location.
    """

    def __init__(self):
        self._step_builder: Optional[StepBuilder] = None
        self._prompt_engine = PromptEngine()

    def _get_step_builder(self, seed: Optional[int] = None) -> StepBuilder:
        """Get or create a StepBuilder with the given seed."""
        if self._step_builder is None or seed is not None:
            self._step_builder = StepBuilder(seed)
        return self._step_builder

    def _compute_difficulty(self, scenario: Scenario, distractor_count: int) -> str:
        """
        Compute difficulty level based on scenario complexity.

        Factors:
        - Number of distractors
        - Number of post-inversion moves
        - Inversion position in sequence
        """
        complexity_score = 0

        # Distractor count factor
        complexity_score += distractor_count

        # Post-inversion moves (container moves after object falls)
        post_inv_moves = sum(
            1 for step in scenario.steps
            if step.action_type == 'move' and step.step_number > scenario.inversion_step_index + 1
        )
        complexity_score += post_inv_moves * 2  # Higher weight for moves

        # Late inversion is harder to track
        if scenario.inversion_step_index >= 4:
            complexity_score += 1

        if complexity_score <= 1:
            return 'easy'
        elif complexity_score <= 3:
            return 'medium'
        elif complexity_score <= 5:
            return 'hard'
        else:
            return 'nightmare'

    def _build_prompt_text(
        self,
        scenario: Scenario,
        style: str,
        question: str
    ) -> str:
        """
        Build the prompt text based on style.

        Args:
            scenario: The generated scenario
            style: User prompt style (casual, minimal, linguistic)
            question: The question to ask

        Returns:
            Complete prompt text
        """
        builder = self._get_step_builder()

        if style == 'minimal':
            steps_text = builder.format_steps_numbered(scenario.steps)
            return f"{steps_text}\n\n{question}\nAnswer:"

        elif style == 'linguistic':
            steps_text = builder.format_steps_numbered(scenario.steps)
            return f"""{steps_text}

Based on the sequence of actions described above, determine the current location of the {scenario.object}.

Apply logical reasoning to track the object through each step:
1. Identify where the object was initially placed
2. Track any movements or transfers
3. Pay special attention to any inversion or flipping of containers
4. Determine the final resting location

{question}
Provide your answer as a single word indicating the location."""

        else:  # casual (default)
            steps_text = builder.format_steps_narrative(scenario.steps)
            return f"{steps_text} {question} Give single word answer."

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None
    ) -> List[TestCase]:
        """
        Generate a batch of Object Tracking test cases.

        Args:
            config: Generation configuration with keys:
                - object: List of objects to choose from
                - container: List of containers
                - location_initial: List of initial locations
                - subject: List of subjects (I, you, names)
                - critical_step_position: List of positions for inversion step
                - distractor_count: List of distractor counts
                - distractor_types: List of distractor types to use
                - sticky_objects: List of objects that don't fall
                - post_inversion_moves: Range for container moves after inversion
            prompt_config: Prompt configuration with keys:
                - user_style: User prompt style
                - system_style: System prompt style
                - name: Configuration name
                - language: Language code (default 'en')
            count: Total number of test cases to generate
            seed: Random seed for reproducibility

        Returns:
            List of TestCase objects
        """
        tests = []
        builder = self._get_step_builder(seed)

        # Extract generation configuration with defaults
        objects = config.get('object', DEFAULT_OBJECTS)
        containers = config.get('container', DEFAULT_CONTAINERS)
        locations = config.get('location_initial', DEFAULT_LOCATIONS)
        subjects = config.get('subject', DEFAULT_SUBJECTS)
        distractor_counts = config.get('distractor_count', [0, 1, 2])
        distractor_types = config.get('distractor_types', DEFAULT_DISTRACTOR_TYPES)
        sticky_objects = set(config.get('sticky_objects', []))
        post_inv_move_range = config.get('post_inversion_moves', [0, 1, 2])

        # Parse prompt configuration
        language_str = prompt_config.get('language', 'en')
        user_style_str = prompt_config.get('user_style', 'casual')
        system_style_str = prompt_config.get('system_style', 'none')
        config_name = prompt_config.get('name', f"{user_style_str}_{system_style_str}")

        for i in range(count):
            # Sample scenario parameters
            obj = builder.rng.choice(objects)
            container = builder.rng.choice(containers)
            location = builder.rng.choice(locations)
            subject = builder.rng.choice(subjects)
            distractor_count = builder.rng.choice(distractor_counts)
            post_inv_moves = builder.rng.choice(post_inv_move_range)

            # Determine if object is sticky
            is_sticky = obj in sticky_objects

            # Split distractors between pre and post inversion
            pre_inv_distractors = distractor_count // 2
            post_inv_distractors = distractor_count - pre_inv_distractors

            # Build scenario
            scenario = builder.build_scenario(
                obj=obj,
                container=container,
                subject=subject,
                initial_location=location,
                pre_inversion_distractors=pre_inv_distractors,
                post_inversion_distractors=post_inv_distractors,
                post_inversion_moves=post_inv_moves,
                distractor_types=distractor_types,
                is_sticky=is_sticky,
                add_final_interact=(post_inv_moves > 0)
            )

            # Generate question
            question = builder.generate_question(obj)

            # Build prompts
            user_prompt = self._build_prompt_text(scenario, user_style_str, question)
            sys_enum = safe_enum(SystemPromptStyle, system_style_str, SystemPromptStyle.ANALYTICAL)
            lang_enum = safe_enum(Language, language_str, Language.EN)
            system_prompt = self._prompt_engine.get_system_prompt_by_enum(sys_enum, lang_enum)

            # Determine difficulty
            difficulty = self._compute_difficulty(scenario, distractor_count)

            # Create test case
            test_case = TestCase(
                test_id=f"tracking_{i:04d}",
                task_type='object_tracking',
                config_name=config_name,
                prompts={
                    'system': system_prompt,
                    'user': user_prompt,
                    'full': f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
                },
                task_params={
                    'object': obj,
                    'container': container,
                    'subject': subject,
                    'initial_location': location,
                    'steps': [s.to_dict() for s in scenario.steps],
                    'inversion_step_index': scenario.inversion_step_index,
                    'expected_answer': scenario.final_object_location,
                    'sticky_object': is_sticky,
                    'distractor_count': distractor_count,
                    'post_inversion_moves': post_inv_moves,
                    'post_inversion_container_location': scenario.post_inversion_container_location,
                    'difficulty': difficulty,
                    'question': question
                },
                prompt_metadata={
                    'user_style': user_style_str,
                    'system_style': system_style_str,
                    'language': language_str
                },
                generation_metadata={
                    'seed': seed,
                    'generator_version': '1.0.0',
                    'created_at': datetime.now().isoformat()
                }
            )

            tests.append(test_case)

        return tests

    def get_default_config(self) -> Dict[str, Any]:
        """Return default generation configuration."""
        return {
            'object': DEFAULT_OBJECTS,
            'container': DEFAULT_CONTAINERS,
            'location_initial': DEFAULT_LOCATIONS,
            'subject': DEFAULT_SUBJECTS,
            'distractor_count': [0, 1, 2],
            'distractor_types': DEFAULT_DISTRACTOR_TYPES,
            'sticky_objects': [],
            'post_inversion_moves': [0, 1, 2]
        }

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='distractor_count', label='Distractor count', field_type='multi-select',
                        default=[0, 1, 2], options=[0, 1, 2, 3, 4]),
            ConfigField(name='post_inversion_moves', label='Post-inversion moves', field_type='multi-select',
                        default=[0, 1, 2], options=[0, 1, 2, 3],
                        help='Number of container moves after object falls'),
            ConfigField(name='distractor_types', label='Distractor types', field_type='multi-select',
                        default=list(DEFAULT_DISTRACTOR_TYPES),
                        options=['irrelevant', 'spatial', 'temporal'], group='advanced'),
            ConfigField(name='object', label='Objects', field_type='multi-select',
                        default=list(DEFAULT_OBJECTS), options=list(DEFAULT_OBJECTS),
                        group='advanced', help='Objects to include in scenarios'),
            ConfigField(name='container', label='Containers', field_type='multi-select',
                        default=list(DEFAULT_CONTAINERS), options=list(DEFAULT_CONTAINERS),
                        group='advanced'),
            ConfigField(name='sticky_objects', label='Sticky objects', field_type='multi-select',
                        default=[], options=list(DEFAULT_OBJECTS), group='advanced',
                        help='Objects that do not fall when container is inverted'),
        ]
