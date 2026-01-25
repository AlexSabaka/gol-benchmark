"""
Arithmetic Test Case Generator

Generates mathematical expression test cases with configurable
complexity levels and target values.
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
from src.engine.MathExpressionGenerator import MathExpressionGenerator


class ArithmeticTestCaseGenerator(TestCaseGenerator):
    """
    Test case generator for arithmetic expression benchmark.

    Generates mathematical expressions with configurable complexity
    and target values using tree-based expression generation.
    """

    def __init__(self):
        self._prompt_engine = PromptEngine()
        self._generator = None
        self._current_seed = None

    def _get_generator(self, seed: Optional[int] = None) -> MathExpressionGenerator:
        """Get or create the math expression generator."""
        if self._generator is None or (seed is not None and seed != self._current_seed):
            self._generator = MathExpressionGenerator(seed=seed or 42)
            self._current_seed = seed
        return self._generator

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None
    ) -> List[TestCase]:
        """
        Generate a batch of arithmetic test cases.

        Args:
            config: Generation configuration with keys:
                - complexity: List of complexity levels (1-5) or single int
                - target_values: List of target values to generate expressions for
                - expressions_per_target: Number of expressions per target (default 10)
                - mode: 'expression' or 'equation' mode
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
        generator = self._get_generator(seed)
        tests = []
        test_id = 0

        # Extract configuration
        complexity_levels = config.get('complexity', [2])
        if isinstance(complexity_levels, int):
            complexity_levels = [complexity_levels]

        target_values = config.get('target_values', [1, 2, 3, 4, 5])
        if isinstance(target_values, int):
            target_values = [target_values]

        expressions_per_target = config.get('expressions_per_target', config.get('count', 10))
        mode = config.get('mode', 'expression')

        # Parse prompt configuration
        language_str = prompt_config.get('language', 'en')
        user_style_str = prompt_config.get('user_style', 'minimal')
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
            user_style = PromptStyle.MINIMAL

        try:
            system_style = SystemPromptStyle(system_style_str)
        except ValueError:
            system_style = SystemPromptStyle.ANALYTICAL

        # Generate tests
        for complexity in complexity_levels:
            for target_value in target_values:
                if test_id >= count:
                    break

                # Generate expressions for this target
                expressions = generator.generate_expressions_for_target(
                    target=target_value,
                    complexity=complexity,
                    count=expressions_per_target
                )

                for expression in expressions:
                    if test_id >= count:
                        break

                    # Create prompt context
                    context = PromptContext(
                        task_type=TaskType.MATH_EXPRESSION,
                        language=language,
                        style=user_style,
                        system_style=system_style
                    )

                    # Set expression context
                    context.set('expression', expression)
                    context.set('variables', {})

                    # Generate prompts
                    result = self._prompt_engine.generate(context)

                    # Create test case
                    test_case = TestCase(
                        test_id=f"ari_{test_id:04d}",
                        task_type='arithmetic',
                        config_name=config_name,
                        prompts={
                            'system': result.system_prompt,
                            'user': result.user_prompt,
                            'full': f"{result.system_prompt}\n\n{result.user_prompt}"
                        },
                        task_params={
                            'complexity': complexity,
                            'target_value': target_value,
                            'expression': expression,
                            'expected_answer': target_value,
                            'variables': {},
                            'mode': mode
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
            'complexity': [2],
            'target_values': [1, 2, 3, 4, 5],
            'expressions_per_target': 10,
            'mode': 'expression',
        }
