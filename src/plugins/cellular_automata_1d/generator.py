"""
Cellular Automata 1D Test Case Generator

Generates test cases for the 1D cellular automaton benchmark
using Wolfram rule numbers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.plugins.base import TestCase, TestCaseGenerator
from src.core.PromptEngine import (
    PromptEngine,
    PromptContext,
    Language,
    PromptStyle,
    SystemPromptStyle,
    TaskType,
)


class C14TestCaseGenerator(TestCaseGenerator):
    """
    Test case generator for 1D Cellular Automata benchmark.

    Uses the CellularAutomataTestGenerator from existing implementation
    to generate test cases with various Wolfram rules.
    """

    def __init__(self):
        self._prompt_engine = PromptEngine()
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

        # Map strings to enums
        try:
            language = Language(language_str)
        except ValueError:
            language = Language.EN

        try:
            user_style = PromptStyle(user_style_str)
        except ValueError:
            user_style = PromptStyle.LINGUISTIC

        try:
            system_style = SystemPromptStyle(system_style_str)
        except ValueError:
            system_style = SystemPromptStyle.ANALYTICAL

        # Generate tests for each rule
        for rule in rules:
            for _ in range(tests_per_rule):
                if test_id >= count:
                    break

                # Generate a test case using CA generator
                try:
                    test_data = ca_generator.generate_test_case(
                        rule=rule,
                        width=width,
                        steps=steps,
                        boundary=boundary
                    )
                except Exception:
                    continue

                initial_state = test_data['initial_state']
                expected_state = test_data['expected_state']

                # Format state for prompt
                state_str = ' '.join(str(x) for x in initial_state)

                # Create prompt context
                context = PromptContext(
                    task_type=TaskType.CELLULAR_AUTOMATA_1D,
                    language=language,
                    style=user_style,
                    system_style=system_style
                )

                # Set CA-specific context
                context.set('rule', rule)
                context.set('initial_state', state_str)
                context.set('width', width)
                context.set('steps', steps)
                context.set('boundary', boundary)

                # Generate prompts
                result = self._prompt_engine.generate(context)

                # Create test case
                test_case = TestCase(
                    test_id=f"c14_{test_id:04d}",
                    task_type='cellular_automata_1d',
                    config_name=config_name,
                    prompts={
                        'system': result.system_prompt,
                        'user': result.user_prompt,
                        'full': f"{result.system_prompt}\n\n{result.user_prompt}"
                    },
                    task_params={
                        'rule': rule,
                        'initial_state': initial_state,
                        'expected_state': expected_state,
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
