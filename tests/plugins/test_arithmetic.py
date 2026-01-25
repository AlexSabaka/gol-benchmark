"""
Unit tests for the Arithmetic plugin.
"""

import pytest
from src.plugins import PluginRegistry
from src.plugins.base import TestCase, ParsedAnswer, EvaluationResult


class TestArithmeticPlugin:
    """Test the Arithmetic plugin."""

    @pytest.fixture
    def plugin(self):
        """Get the Arithmetic plugin."""
        return PluginRegistry.get('arithmetic')

    def test_generator(self, plugin):
        """Test the generator creates valid test cases."""
        generator = plugin.get_generator()

        config = {
            'complexity': [2],
            'target_values': [5],
            'expressions_per_target': 2,
            'mode': 'expression'
        }

        prompt_config = {
            'user_style': 'minimal',
            'system_style': 'analytical',
            'name': 'test_config',
            'language': 'en'
        }

        test_cases = generator.generate_batch(
            config=config,
            prompt_config=prompt_config,
            count=2,
            seed=42
        )

        # Should generate 2 test cases
        assert len(test_cases) == 2

        # Check first test case
        tc = test_cases[0]
        assert isinstance(tc, TestCase)
        assert tc.task_type == 'arithmetic'
        assert 'expression' in tc.task_params
        assert 'expected_answer' in tc.task_params
        assert tc.task_params['expected_answer'] == 5

    def test_parser_latex_boxed(self, plugin):
        """Test parser with LaTeX boxed format."""
        parser = plugin.get_parser()

        response = r"The answer is \boxed{42}"

        parsed = parser.parse(response, {})

        assert isinstance(parsed, ParsedAnswer)
        assert parsed.success
        assert parsed.value == 42.0
        assert parsed.parse_strategy in ['latex_boxed', 'json_unescape_latex']

    def test_parser_equals_pattern(self, plugin):
        """Test parser with equals pattern."""
        parser = plugin.get_parser()

        response = "The calculation gives us = 15"

        parsed = parser.parse(response, {})

        assert isinstance(parsed, ParsedAnswer)
        assert parsed.success
        assert parsed.value == 15.0

    def test_parser_keyword_search(self, plugin):
        """Test parser with keyword search."""
        parser = plugin.get_parser()

        response = "The final answer is 23"

        parsed = parser.parse(response, {})

        assert isinstance(parsed, ParsedAnswer)
        assert parsed.success
        assert parsed.value == 23.0

    def test_evaluator_exact_match(self, plugin):
        """Test evaluator with exact match."""
        evaluator = plugin.get_evaluator()

        parsed = ParsedAnswer(
            value=42.0,
            raw_response="42",
            parse_strategy="test"
        )

        task_params = {'expected_answer': 42}

        result = evaluator.evaluate(parsed, 42, task_params)

        assert isinstance(result, EvaluationResult)
        assert result.correct is True
        assert result.match_type == 'exact'
        assert result.accuracy == 1.0

    def test_evaluator_mismatch(self, plugin):
        """Test evaluator with mismatch."""
        evaluator = plugin.get_evaluator()

        parsed = ParsedAnswer(
            value=10.0,
            raw_response="10",
            parse_strategy="test"
        )

        task_params = {'expected_answer': 42}

        result = evaluator.evaluate(parsed, 42, task_params)

        assert isinstance(result, EvaluationResult)
        assert result.correct is False
        assert result.match_type == 'mismatch'
        assert result.accuracy == 0.0

    def test_evaluator_approximate_match(self, plugin):
        """Test evaluator with approximate match."""
        evaluator = plugin.get_evaluator()

        # Very close but not exact (within tolerance)
        parsed = ParsedAnswer(
            value=42.0000000001,
            raw_response="42.0000000001",
            parse_strategy="test"
        )

        task_params = {'expected_answer': 42}

        result = evaluator.evaluate(parsed, 42, task_params)

        assert isinstance(result, EvaluationResult)
        assert result.correct is True
        assert result.match_type in ['exact', 'approximate']

    def test_roundtrip(self, plugin):
        """Test full roundtrip: generate -> parse -> evaluate."""
        generator = plugin.get_generator()
        parser = plugin.get_parser()
        evaluator = plugin.get_evaluator()

        # Generate a test case
        config = {'complexity': [1], 'target_values': [10], 'expressions_per_target': 1}
        prompt_config = {'user_style': 'minimal', 'system_style': 'analytical', 'name': 'test', 'language': 'en'}

        test_cases = generator.generate_batch(config, prompt_config, count=1, seed=42)
        tc = test_cases[0]

        # Create a mock perfect response
        expected_answer = tc.task_params['expected_answer']
        mock_response = f"The answer is {expected_answer}"

        # Parse the response
        parsed = parser.parse(mock_response, tc.task_params)

        # Evaluate
        result = evaluator.evaluate(parsed, expected_answer, tc.task_params)

        # Should be correct
        assert result.correct is True
        assert result.accuracy == 1.0
