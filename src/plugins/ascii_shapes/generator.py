"""
ASCII Shapes Test Case Generator

Generates test cases for ASCII shape spatial reasoning
with questions about dimensions, counts, and positions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.plugins.base import TestCase, TestCaseGenerator, ConfigField
from src.plugins.i18n.loader import compose_user_prompt


class AsciiShapesTestCaseGenerator(TestCaseGenerator):
    """
    Test case generator for ASCII Shapes benchmark.

    Uses the AsciiShapesGenerator from existing implementation
    to create shape-based spatial reasoning tests.
    """

    def __init__(self):
        self._shapes_generator = None

    def _get_shapes_generator(self, seed: Optional[int] = None):
        """Lazy-load AsciiShapesGenerator."""
        from src.engine.AsciiShapesEngine import AsciiShapesGenerator
        return AsciiShapesGenerator(seed=seed)

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None
    ) -> List[TestCase]:
        """
        Generate a batch of ASCII shapes test cases.

        Args:
            config: Generation configuration with keys:
                - width_range: (min, max) width
                - height_range: (min, max) height
                - symbols: List of symbols to use
                - spacing: List of spacing options
                - question_types: List of question types
                - coordinate_labels: Whether to add coordinate labels
            prompt_config: Prompt configuration
            count: Total number of test cases to generate
            seed: Random seed for reproducibility

        Returns:
            List of TestCase objects
        """
        shapes_generator = self._get_shapes_generator(seed)
        tests = []
        test_id = 0

        # Extract configuration
        width_range = config.get('width_range', (3, 10))
        height_range = config.get('height_range', (3, 8))
        symbols = config.get('symbols', ['*', '#', 'X'])
        spacing_options = config.get('spacing', [' '])
        question_types = config.get('question_types', ['dimensions', 'count', 'position'])
        coordinate_labels = config.get('coordinate_labels', False)
        filled_ratio = config.get('filled_ratio', 0.7)

        # Parse prompt configuration
        language_str = prompt_config.get('language', 'en')
        user_style_str = prompt_config.get('user_style', 'linguistic')
        system_style_str = prompt_config.get('system_style', 'analytical')
        config_name = prompt_config.get('name', f"{user_style_str}_{system_style_str}")

        # Generate tests
        rng = shapes_generator.rng

        for _ in range(count):
            if test_id >= count:
                break

            # Generate random parameters
            width = rng.randint(width_range[0], width_range[1])
            height = rng.randint(height_range[0], height_range[1])
            symbol = rng.choice(symbols)
            spacing = rng.choice(spacing_options)
            filled = rng.random() < filled_ratio
            question_type = rng.choice(question_types)

            # Generate shape
            try:
                shape = shapes_generator.generate_test_case(
                    width=width,
                    height=height,
                    symbol=symbol,
                    spacing=spacing,
                    filled=filled,
                    coordinate_labels=coordinate_labels,
                    question_type=question_type
                )
            except Exception:
                # Fallback to manual shape generation
                rendered = shapes_generator.render_shape(
                    width=width,
                    height=height,
                    symbol=symbol,
                    spacing=spacing,
                    filled=filled,
                    coordinate_labels=coordinate_labels
                )

                # Calculate expected answer
                if question_type == 'dimensions':
                    expected_answer = f"{width}x{height}"
                elif question_type == 'count':
                    if filled:
                        expected_answer = width * height
                    else:
                        if height == 1:
                            expected_answer = width
                        elif width == 1:
                            expected_answer = height
                        else:
                            expected_answer = 2 * (width + height) - 4
                else:  # position
                    x = rng.randint(1, width)
                    y = rng.randint(1, height)
                    if filled:
                        expected_answer = True
                    else:
                        is_border = (y == 1 or y == height or x == 1 or x == width)
                        expected_answer = is_border

                shape = {
                    'rendered': rendered,
                    'width': width,
                    'height': height,
                    'symbol': symbol,
                    'spacing': spacing,
                    'filled': filled,
                    'question_type': question_type,
                    'expected_answer': expected_answer,
                    'question': self._generate_question(question_type, x if question_type == 'position' else None, y if question_type == 'position' else None, language=language_str),
                }

            # Generate prompts
            # Engine returns nested dict {shape: {rendered: ...}, question_key: ...}
            # Fallback path returns flat dict {rendered: ..., question: ...}
            if 'shape' in shape and isinstance(shape['shape'], dict):
                rendered = shape['shape'].get('rendered', '')
                question = self._generate_question(
                    shape.get('question_type', shape.get('question_key', question_type)),
                    language=language_str,
                )
            else:
                rendered = shape.get('rendered', '')
                question = shape.get('question', '')
            user_prompt = compose_user_prompt(
                "ascii_shapes", language_str, user_style_str,
                shape=rendered,
                question=question,
            )
            system_prompt = self._get_system_prompt(system_style_str, language_str)
            full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt

            # Create test case
            test_case = TestCase(
                test_id=f"shapes_{test_id:04d}",
                task_type='ascii_shapes',
                config_name=config_name,
                prompts={
                    'system': system_prompt,
                    'user': user_prompt,
                    'full': full_prompt,
                },
                task_params={
                    'width': width,
                    'height': height,
                    'symbol': symbol,
                    'spacing': spacing,
                    'filled': filled,
                    'coordinate_labels': coordinate_labels,
                    'question_type': question_type,
                    'expected_answer': shape.get('expected_answer'),
                    'rendered_shape': shape.get('rendered', ''),
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

        return tests

    _QUESTIONS: Dict[str, Dict[str, str]] = {
        "en": {
            "dimensions": "What are the dimensions (width x height) of this shape?",
            "count": "How many symbols are in this shape?",
            "position": "Is there a symbol at position ({x}, {y})?",
            "default": "What can you tell me about this shape?",
        },
        "es": {
            "dimensions": "¿Cuáles son las dimensiones (ancho x alto) de esta forma?",
            "count": "¿Cuántos símbolos hay en esta forma?",
            "position": "¿Hay un símbolo en la posición ({x}, {y})?",
            "default": "¿Qué puedes decirme sobre esta forma?",
        },
        "fr": {
            "dimensions": "Quelles sont les dimensions (largeur x hauteur) de cette forme ?",
            "count": "Combien de symboles contient cette forme ?",
            "position": "Y a-t-il un symbole à la position ({x}, {y}) ?",
            "default": "Que pouvez-vous me dire sur cette forme ?",
        },
        "de": {
            "dimensions": "Was sind die Abmessungen (Breite x Höhe) dieser Form?",
            "count": "Wie viele Symbole enthält diese Form?",
            "position": "Gibt es ein Symbol an Position ({x}, {y})?",
            "default": "Was können Sie mir über diese Form sagen?",
        },
        "zh": {
            "dimensions": "这个形状的尺寸（宽 × 高）是多少？",
            "count": "这个形状中有多少个符号？",
            "position": "在位置 ({x}, {y}) 是否有符号？",
            "default": "关于这个形状你能告诉我什么？",
        },
        "ua": {
            "dimensions": "Які розміри (ширина × висота) цієї форми?",
            "count": "Скільки символів у цій формі?",
            "position": "Чи є символ на позиції ({x}, {y})?",
            "default": "Що ви можете сказати про цю форму?",
        },
    }

    def _generate_question(self, question_type: str, x: Optional[int] = None,
                           y: Optional[int] = None, language: str = "en") -> str:
        """Generate question based on type and language."""
        lang_q = self._QUESTIONS.get(language, self._QUESTIONS["en"])
        template = lang_q.get(question_type, lang_q["default"])
        if question_type == "position" and x is not None and y is not None:
            return template.format(x=x, y=y)
        return template

    def get_default_config(self) -> Dict[str, Any]:
        """Return default generation configuration."""
        return {
            'width_range': (3, 10),
            'height_range': (3, 8),
            'symbols': ['*', '#', 'X'],
            'spacing': [' '],
            'question_types': ['dimensions', 'count', 'position'],
            'coordinate_labels': False,
            'filled_ratio': 0.7,
        }

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='count', label='Number of cases', field_type='number',
                        default=50, min_value=1, max_value=500,
                        help='Cases to generate per prompt configuration'),
            ConfigField(name='question_types', label='Question types', field_type='multi-select',
                        default=['dimensions', 'count', 'position'],
                        options=['dimensions', 'count', 'position']),
            ConfigField(name='width_range', label='Width range', field_type='range',
                        default=[3, 10], range_min_default=3, range_max_default=10,
                        min_value=1, max_value=50, help='Min and max width of generated shapes'),
            ConfigField(name='height_range', label='Height range', field_type='range',
                        default=[3, 8], range_min_default=3, range_max_default=8,
                        min_value=1, max_value=50, help='Min and max height of generated shapes'),
            ConfigField(name='symbols', label='Symbols', field_type='multi-select',
                        default=['*', '#', 'X'], options=['*', '#', 'X', 'O', '+', '@'],
                        group='advanced'),
            ConfigField(name='coordinate_labels', label='Coordinate labels', field_type='boolean',
                        default=False, group='advanced',
                        help='Add coordinate labels to the shape grid'),
            ConfigField(name='filled_ratio', label='Filled ratio', field_type='number',
                        default=0.7, min_value=0.0, max_value=1.0, step=0.1, group='advanced',
                        help='Probability shapes are filled vs outline'),
        ]
