"""
Linda Fallacy Test Case Generator

Generates test cases for the conjunction fallacy benchmark
using persona templates and distractors.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.plugins.base import TestCase, TestCaseGenerator, ConfigField
from src.plugins.linda_fallacy.prompts import USER_PROMPT_TEMPLATES
from src.plugins.linda_fallacy.i18n import (
    PERSONA_TEMPLATES,
    ACTIVITIES_CONNECTORS,
)


# Language to culture mapping
LANGUAGE_CULTURE_MAP = {
    'en': ['western', 'african', 'european'],
    'es': ['latin_american', 'european'],
    'fr': ['european', 'african'],
    'de': ['european'],
    'zh': ['east_asian'],
    'ua': ['european'],
}


class LindaTestCaseGenerator(TestCaseGenerator):
    """
    Test case generator for Linda Conjunction Fallacy benchmark.

    Uses the LindaBenchmark class from the existing implementation
    to generate culturally-aligned persona-based test cases.
    """

    def __init__(self):
        self._linda_benchmark = None

    def _get_linda_benchmark(self, language: str, num_options: int, culture_filter: Optional[str] = None):
        """Lazy-load LindaBenchmark to avoid circular imports."""
        from src.benchmarks.linda_eval import LindaBenchmark
        return LindaBenchmark(
            language=language,
            num_options=num_options,
            culture_filter=culture_filter
        )

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None
    ) -> List[TestCase]:
        """
        Generate a batch of Linda Fallacy test cases.

        Args:
            config: Generation configuration with keys:
                - num_options: Number of ranking options (default 8)
                - culture_filter: Optional culture filter
                - personas_per_config: Number of personas per config
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
        test_id = 0

        # Extract configuration
        num_options = config.get('num_options', 8)
        culture_filter = config.get('culture_filter', None)
        personas_per_config = config.get('personas_per_config', count)

        # Parse prompt configuration
        language_str = prompt_config.get('language', 'en')
        user_style_str = prompt_config.get('user_style', 'linguistic')
        system_style_str = prompt_config.get('system_style', 'analytical')
        config_name = prompt_config.get('name', f"{user_style_str}_{system_style_str}")

        # Validate culture-language alignment
        compatible_cultures = LANGUAGE_CULTURE_MAP.get(language_str, ['western'])
        if culture_filter and culture_filter not in compatible_cultures:
            culture_filter = compatible_cultures[0]

        # Initialize Linda benchmark
        try:
            linda_benchmark = self._get_linda_benchmark(
                language=language_str,
                num_options=num_options,
                culture_filter=culture_filter
            )
        except Exception as e:
            return []

        # Filter personas by language-compatible cultures if no specific filter
        if not culture_filter:
            linda_benchmark.persona_templates = [
                p for p in linda_benchmark.persona_templates
                if p.culture in compatible_cultures
            ]

        if not linda_benchmark.persona_templates:
            return []

        # Generate test cases
        for persona_idx in range(min(personas_per_config, count)):
            if test_id >= count:
                break

            # Cycle through available personas
            persona = linda_benchmark.persona_templates[persona_idx % len(linda_benchmark.persona_templates)]

            # Generate test item using Linda's logic
            try:
                test_item = linda_benchmark.generate_test_item(persona)
            except Exception:
                continue

            # Format persona description using language-aware template
            traits_str = ", ".join(persona.personality_traits)
            background_str = ". ".join(persona.background)
            activities_connector = ACTIVITIES_CONNECTORS.get(language_str, ACTIVITIES_CONNECTORS["en"])
            activities_str = activities_connector.join(persona.activities)
            template = PERSONA_TEMPLATES.get(language_str, PERSONA_TEMPLATES["en"])
            persona_description = template.format(
                name=persona.name, age=persona.age,
                traits=traits_str, background=background_str, activities=activities_str,
            )

            ranked_items = '\n'.join(
                f"{i+1}. {item}" for i, item in enumerate(test_item.all_items)
            )

            # Generate prompts
            user_prompt = self._format_user_prompt(
                USER_PROMPT_TEMPLATES, language_str, user_style_str,
                persona_description=persona_description,
                ranked_items=ranked_items,
                num_options=len(test_item.all_items),
            )
            system_prompt = self._get_system_prompt(system_style_str, language_str)
            full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

            # Create test case
            test_case = TestCase(
                test_id=f"linda_{test_id:04d}",
                task_type='linda_fallacy',
                config_name=config_name,
                prompts={
                    'system': system_prompt,
                    'user': user_prompt,
                    'full': full_prompt,
                },
                task_params={
                    'persona': {
                        'name': persona.name,
                        'age': persona.age,
                        'personality_traits': persona.personality_traits,
                        'background': persona.background,
                        'activities': persona.activities,
                        'culture': persona.culture
                    },
                    'test_item': {
                        'description': test_item.description,
                        'conjunction_item': test_item.conjunction_item,
                        'component_a': test_item.component_a,
                        'component_b': test_item.component_b,
                        'distractors': test_item.distractors,
                        'all_items': test_item.all_items
                    },
                    'expected_fallacy': True,
                    'num_options': len(test_item.all_items)
                },
                prompt_metadata={
                    'user_style': user_style_str,
                    'system_style': system_style_str,
                    'language': language_str,
                    'culture': persona.culture
                },
                generation_metadata={
                    'seed': seed,
                    'generator_version': "1.0.0",
                    'created_at': datetime.now().isoformat(),
                    'culture_filter': culture_filter,
                    'language_culture_aligned': True
                }
            )

            tests.append(test_case)
            test_id += 1

        return tests

    def get_default_config(self) -> Dict[str, Any]:
        """Return default generation configuration."""
        return {
            'num_options': 8,
            'culture_filter': None,
            'personas_per_config': 5,
        }

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='num_options', label='Options per question', field_type='number',
                        default=8, min_value=3, max_value=10),
            ConfigField(name='personas_per_config', label='Personas count', field_type='number',
                        default=5, min_value=1, max_value=50),
            ConfigField(name='culture_filter', label='Culture filter', field_type='select',
                        default='', group='advanced',
                        options=['', 'western', 'east_asian', 'south_asian', 'african',
                                 'middle_eastern', 'latin_american', 'european'],
                        help='Filter personas by cultural context (empty = all)'),
        ]
