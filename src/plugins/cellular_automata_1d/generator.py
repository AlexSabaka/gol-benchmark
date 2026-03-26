"""
Cellular Automata 1D Test Case Generator

Generates test cases for the 1D cellular automaton benchmark
using Wolfram rule numbers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.plugins.base import TestCase, TestCaseGenerator, ConfigField
from src.plugins.cellular_automata_1d.prompts import (
    USER_PROMPT_TEMPLATES,
    BOUNDARY_DESCRIPTIONS,
)


class C14TestCaseGenerator(TestCaseGenerator):
    """
    Test case generator for 1D Cellular Automata benchmark.

    Uses the CellularAutomataTestGenerator from existing implementation
    to generate test cases with various Wolfram rules.
    """

    def __init__(self):
        self._ca_generator = None

    def _get_ca_generator(self, seed: Optional[int] = None):
        """Lazy-load CellularAutomataTestGenerator."""
        from src.engine.CellularAutomata1DEngine import (
            CellularAutomata1DEngine,
            CellularAutomataTestGenerator
        )
        return CellularAutomataTestGenerator(seed=seed or 42)

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None
    ) -> List[TestCase]:
        """
        Generate a batch of 1D CA test cases.

        Args:
            config: Generation configuration with keys:
                - rules: List of Wolfram rule numbers (default [110, 30, 90])
                - width: State width (default 16)
                - steps: Evolution steps (default 1)
                - boundary: Boundary condition ('wrap' or 'zero')
                - tests_per_rule: Number of tests per rule
            prompt_config: Prompt configuration
            count: Total number of test cases to generate
            seed: Random seed for reproducibility

        Returns:
            List of TestCase objects
        """
        from src.engine.CellularAutomata1DEngine import CellularAutomata1DEngine

        ca_generator = self._get_ca_generator(seed)
        tests = []
        test_id = 0

        # Extract configuration
        rules = config.get('rules', [110, 30, 90])
        if isinstance(rules, int):
            rules = [rules]

        width = config.get('width', 16)
        steps = config.get('steps', 1)
        boundary = config.get('boundary', 'wrap')
        tests_per_rule = config.get('tests_per_rule', count // len(rules) or 1)

        # Parse prompt configuration
        language_str = prompt_config.get('language', 'en')
        user_style_str = prompt_config.get('user_style', 'linguistic')
        system_style_str = prompt_config.get('system_style', 'analytical')
        config_name = prompt_config.get('name', f"{user_style_str}_{system_style_str}")

        # Generate tests for each rule
        for rule in rules:
            # Pre-compute rule table (same for all cases with this rule)
            rule_table = CellularAutomata1DEngine.format_rule_table(rule)
            # Boundary description
            lang_boundaries = BOUNDARY_DESCRIPTIONS.get(language_str, BOUNDARY_DESCRIPTIONS['en'])
            boundary_description = lang_boundaries.get(boundary, boundary)

            for _ in range(tests_per_rule):
                if test_id >= count:
                    break

                # Generate a test case using CA generator
                try:
                    test_data = ca_generator.generate_test_case(
                        rule_number=rule,
                        width=width,
                        steps=steps,
                        boundary=boundary
                    )
                except Exception:
                    continue

                initial_state = test_data['initial_state']
                expected_states = test_data['expected_states']

                # Format state for prompt
                state_str = ' '.join(str(x) for x in initial_state)

                # Generate prompts
                user_prompt, system_prompt, full_prompt = self._build_prompts(
                    USER_PROMPT_TEMPLATES,
                    language=language_str,
                    user_style=user_style_str,
                    system_style=system_style_str,
                    rule_number=rule,
                    rule_table=rule_table,
                    state_str=state_str,
                    boundary_description=boundary_description,
                )

                # Create test case
                test_case = TestCase(
                    test_id=f"c14_{test_id:04d}",
                    task_type='cellular_automata_1d',
                    config_name=config_name,
                    prompts={
                        'system': system_prompt,
                        'user': user_prompt,
                        'full': full_prompt
                    },
                    task_params={
                        'rule': rule,
                        'initial_state': initial_state,
                        'expected_state': expected_states,
                        'width': width,
                        'steps': steps,
                        'boundary': boundary,
                        'difficulty': test_data.get('difficulty', 'medium')
                    },
                    prompt_metadata={
                        'user_style': user_style_str,
                        'system_style': system_style_str,
                        'language': language_str
                    },
                    generation_metadata={
                        'seed': seed,
                        'generator_version': "1.0.0",
                        'created_at': datetime.now().isoformat()
                    }
                )

                tests.append(test_case)
                test_id += 1

            if test_id >= count:
                break

        return tests

    def get_default_config(self) -> Dict[str, Any]:
        """Return default generation configuration."""
        return {
            'rules': [110, 30, 90],
            'width': 16,
            'steps': 1,
            'boundary': 'wrap',
            'tests_per_rule': 10,
        }

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='rules', label='Rule numbers', field_type='multi-select',
                        default=[110, 30, 90], options=[30, 54, 60, 90, 110, 150, 182]),
            ConfigField(name='tests_per_rule', label='Cases per rule', field_type='number',
                        default=10, min_value=1, max_value=200),
            ConfigField(name='width', label='Grid width', field_type='number',
                        default=16, min_value=5, max_value=50),
            ConfigField(name='steps', label='Steps', field_type='number',
                        default=1, min_value=1, max_value=20),
            ConfigField(name='boundary', label='Boundary condition', field_type='select',
                        default='wrap', options=['wrap', 'dead', 'alive'], group='advanced'),
        ]
