"""
Unit tests for ASCII Shapes plugin.
"""

import pytest
from src.plugins.ascii_shapes.generator import AsciiShapesTestCaseGenerator
from src.plugins.ascii_shapes.parser import AsciiShapesResponseParser
from src.plugins.ascii_shapes.evaluator import AsciiShapesResultEvaluator
from src.plugins.base import TestCase, ParsedAnswer


class TestAsciiShapesGenerator:
    """Test ASCII Shapes test case generation."""

    def test_generate_batch_basic(self):
        """Test basic batch generation."""
        generator = AsciiShapesTestCaseGenerator()

        config = generator.get_default_config()
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(
            config=config,
            prompt_config=prompt_config,
            count=5,
            seed=42
        )

        assert len(test_cases) == 5
        assert all(isinstance(tc, TestCase) for tc in test_cases)
        assert all(tc.task_type == 'ascii_shapes' for tc in test_cases)

    def test_generate_dimensions_question(self):
        """Test generation with dimensions question."""
        generator = AsciiShapesTestCaseGenerator()

        config = generator.get_default_config()
        config['question_types'] = ['dimensions']
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 3, seed=42)

        assert all(tc.task_params['question_type'] == 'dimensions' for tc in test_cases)
        assert all(isinstance(tc.task_params['expected_answer'], str) for tc in test_cases)
        assert all('x' in tc.task_params['expected_answer'] for tc in test_cases)

    def test_generate_count_question(self):
        """Test generation with count question."""
        generator = AsciiShapesTestCaseGenerator()

        config = generator.get_default_config()
        config['question_types'] = ['count']
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 3, seed=42)

        assert all(tc.task_params['question_type'] == 'count' for tc in test_cases)
        assert all(isinstance(tc.task_params['expected_answer'], int) for tc in test_cases)

    def test_generate_position_question(self):
        """Test generation with position question."""
        generator = AsciiShapesTestCaseGenerator()

        config = generator.get_default_config()
        config['question_types'] = ['position']
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 3, seed=42)

        assert all(tc.task_params['question_type'] == 'position' for tc in test_cases)
        assert all(isinstance(tc.task_params['expected_answer'], bool) for tc in test_cases)


class TestAsciiShapesParser:
    """Test ASCII Shapes response parsing."""

    def test_parse_dimensions_wxh(self):
        """Test parsing WxH format."""
        parser = AsciiShapesResponseParser()

        response = "The dimensions are 8x5"

        task_params = {'question_type': 'dimensions'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == "8x5"
        assert 'dimensions' in result.parse_strategy

    def test_parse_dimensions_by(self):
        """Test parsing 'by' format."""
        parser = AsciiShapesResponseParser()

        response = "It is 8 by 5 in size"

        task_params = {'question_type': 'dimensions'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == "8x5"

    def test_parse_dimensions_keywords(self):
        """Test parsing with keywords."""
        parser = AsciiShapesResponseParser()

        response = "The width is 8 and the height is 5"

        task_params = {'question_type': 'dimensions'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == "8x5"

    def test_parse_count_keyword(self):
        """Test parsing count with keyword."""
        parser = AsciiShapesResponseParser()

        response = "The total number of symbols is 24"

        task_params = {'question_type': 'count'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == 24

    def test_parse_count_number_only(self):
        """Test parsing count with just number."""
        parser = AsciiShapesResponseParser()

        response = "42"

        task_params = {'question_type': 'count'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == 42

    def test_parse_position_yes(self):
        """Test parsing positive position."""
        parser = AsciiShapesResponseParser()

        response = "Yes, there is a symbol at that position"

        task_params = {'question_type': 'position'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value is True

    def test_parse_position_no(self):
        """Test parsing negative position."""
        parser = AsciiShapesResponseParser()

        response = "No, there isn't a symbol at that position"

        task_params = {'question_type': 'position'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value is False

    def test_parse_invalid(self):
        """Test parsing invalid response."""
        parser = AsciiShapesResponseParser()

        response = "I cannot determine this."

        task_params = {'question_type': 'dimensions'}

        result = parser.parse(response, task_params)

        assert not result.success
        assert result.value is None


class TestAsciiShapesEvaluator:
    """Test ASCII Shapes result evaluation."""

    def test_evaluate_dimensions_exact(self):
        """Test exact dimension match."""
        evaluator = AsciiShapesResultEvaluator()

        parsed_answer = ParsedAnswer(
            value="8x5",
            raw_response='',
            parse_strategy='test'
        )

        expected_answer = "8x5"
        task_params = {'question_type': 'dimensions'}

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert result.correct
        assert result.match_type == 'exact'
        assert result.accuracy == 1.0

    def test_evaluate_dimensions_mismatch(self):
        """Test dimension mismatch."""
        evaluator = AsciiShapesResultEvaluator()

        parsed_answer = ParsedAnswer(
            value="8x5",
            raw_response='',
            parse_strategy='test'
        )

        expected_answer = "5x8"
        task_params = {'question_type': 'dimensions'}

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert not result.correct
        assert result.match_type == 'mismatch'
        assert result.accuracy == 0.0

    def test_evaluate_count_exact(self):
        """Test exact count match."""
        evaluator = AsciiShapesResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=24,
            raw_response='',
            parse_strategy='test'
        )

        expected_answer = 24
        task_params = {'question_type': 'count'}

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert result.correct
        assert result.match_type == 'exact'
        assert result.accuracy == 1.0

    def test_evaluate_count_close(self):
        """Test close count (within tolerance)."""
        evaluator = AsciiShapesResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=23,
            raw_response='',
            parse_strategy='test'
        )

        expected_answer = 24
        task_params = {'question_type': 'count'}

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        # Within 10% tolerance should be considered correct
        assert result.correct
        assert result.match_type == 'approximate'

    def test_evaluate_count_far(self):
        """Test far count (outside tolerance)."""
        evaluator = AsciiShapesResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=30,
            raw_response='',
            parse_strategy='test'
        )

        expected_answer = 24
        task_params = {'question_type': 'count'}

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        # Outside tolerance
        assert not result.correct
        assert result.match_type == 'mismatch'

    def test_evaluate_position_correct(self):
        """Test correct position answer."""
        evaluator = AsciiShapesResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=True,
            raw_response='',
            parse_strategy='test'
        )

        expected_answer = True
        task_params = {'question_type': 'position'}

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert result.correct
        assert result.match_type == 'exact'
        assert result.accuracy == 1.0

    def test_evaluate_position_incorrect(self):
        """Test incorrect position answer."""
        evaluator = AsciiShapesResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=True,
            raw_response='',
            parse_strategy='test'
        )

        expected_answer = False
        task_params = {'question_type': 'position'}

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert not result.correct
        assert result.match_type == 'mismatch'
        assert result.accuracy == 0.0

    def test_evaluate_parse_error(self):
        """Test evaluation with parse error."""
        evaluator = AsciiShapesResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=None,
            raw_response='',
            parse_strategy='failed',
            error='Could not parse'
        )

        expected_answer = "8x5"
        task_params = {'question_type': 'dimensions'}

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert not result.correct
        assert result.match_type == 'parse_error'

    def test_aggregate_results(self):
        """Test aggregation of multiple results."""
        evaluator = AsciiShapesResultEvaluator()

        results = [
            evaluator.evaluate(
                ParsedAnswer("8x5", '', 'test'),
                "8x5",
                {'question_type': 'dimensions'}
            ),
            evaluator.evaluate(
                ParsedAnswer(24, '', 'test'),
                24,
                {'question_type': 'count'}
            ),
            evaluator.evaluate(
                ParsedAnswer(True, '', 'test'),
                False,
                {'question_type': 'position'}
            ),
        ]

        aggregated = evaluator.aggregate_results(results)

        assert aggregated['total'] == 3
        assert aggregated['correct'] == 2
        assert aggregated['success_rate'] == pytest.approx(0.667, rel=0.01)


class TestAsciiShapesRoundtrip:
    """Test full roundtrip: generate -> parse -> evaluate."""

    def test_roundtrip_dimensions(self):
        """Test complete pipeline for dimensions."""
        generator = AsciiShapesTestCaseGenerator()
        parser = AsciiShapesResponseParser()
        evaluator = AsciiShapesResultEvaluator()

        # Generate test case
        config = generator.get_default_config()
        config['question_types'] = ['dimensions']
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 1, seed=42)
        test_case = test_cases[0]

        # Simulate correct model response
        expected_answer = test_case.task_params['expected_answer']
        simulated_response = f"The dimensions are {expected_answer}"

        # Parse response
        parsed = parser.parse(simulated_response, test_case.task_params)
        assert parsed.success

        # Evaluate
        result = evaluator.evaluate(
            parsed,
            expected_answer,
            test_case.task_params
        )

        assert result.correct
        assert result.match_type == 'exact'

    def test_roundtrip_count(self):
        """Test complete pipeline for count."""
        generator = AsciiShapesTestCaseGenerator()
        parser = AsciiShapesResponseParser()
        evaluator = AsciiShapesResultEvaluator()

        # Generate test case
        config = generator.get_default_config()
        config['question_types'] = ['count']
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 1, seed=42)
        test_case = test_cases[0]

        # Simulate correct model response
        expected_answer = test_case.task_params['expected_answer']
        simulated_response = f"The answer is {expected_answer}"

        # Parse response
        parsed = parser.parse(simulated_response, test_case.task_params)
        assert parsed.success

        # Evaluate
        result = evaluator.evaluate(
            parsed,
            expected_answer,
            test_case.task_params
        )

        assert result.correct

    def test_roundtrip_position(self):
        """Test complete pipeline for position."""
        generator = AsciiShapesTestCaseGenerator()
        parser = AsciiShapesResponseParser()
        evaluator = AsciiShapesResultEvaluator()

        # Generate test case
        config = generator.get_default_config()
        config['question_types'] = ['position']
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 1, seed=42)
        test_case = test_cases[0]

        # Simulate correct model response
        expected_answer = test_case.task_params['expected_answer']
        simulated_response = "Yes" if expected_answer else "No"

        # Parse response
        parsed = parser.parse(simulated_response, test_case.task_params)
        assert parsed.success

        # Evaluate
        result = evaluator.evaluate(
            parsed,
            expected_answer,
            test_case.task_params
        )

        assert result.correct
        assert result.match_type == 'exact'
