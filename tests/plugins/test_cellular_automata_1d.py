"""
Unit tests for Cellular Automata 1D plugin.
"""

import pytest
from src.plugins.cellular_automata_1d.generator import C14TestCaseGenerator
from src.plugins.cellular_automata_1d.parser import C14ResponseParser
from src.plugins.cellular_automata_1d.evaluator import C14ResultEvaluator
from src.plugins.base import TestCase, ParsedAnswer


class TestC14Generator:
    """Test C14 test case generation."""

    def test_generate_batch_basic(self):
        """Test basic batch generation."""
        generator = C14TestCaseGenerator()

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
        assert all(tc.task_type == 'c14' for tc in test_cases)

    def test_generate_with_rule(self):
        """Test generation with specific rule."""
        generator = C14TestCaseGenerator()

        config = generator.get_default_config()
        config['rules'] = [110]  # Specific rule
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 3, seed=42)

        assert all(tc.task_params['rule'] == 110 for tc in test_cases)

    def test_generate_reproducibility(self):
        """Test that same seed produces same states."""
        generator = C14TestCaseGenerator()

        config = generator.get_default_config()
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        tests1 = generator.generate_batch(config, prompt_config, 3, seed=42)
        tests2 = generator.generate_batch(config, prompt_config, 3, seed=42)

        # Should generate same initial states
        assert tests1[0].task_params['initial_state'] == tests2[0].task_params['initial_state']


class TestC14Parser:
    """Test C14 response parsing."""

    def test_parse_binary_string(self):
        """Test parsing binary string."""
        parser = C14ResponseParser()

        response = "The next state is: 01101010"

        task_params = {
            'width': 8,
            'expected_state': [0, 1, 1, 0, 1, 0, 1, 0]
        }

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == [0, 1, 1, 0, 1, 0, 1, 0]

    def test_parse_spaced_format(self):
        """Test parsing spaced format."""
        parser = C14ResponseParser()

        response = "Next: 0 1 1 0 1 0 1 0"

        task_params = {
            'width': 8,
            'expected_state': [0, 1, 1, 0, 1, 0, 1, 0]
        }

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == [0, 1, 1, 0, 1, 0, 1, 0]

    def test_parse_list_format(self):
        """Test parsing list format."""
        parser = C14ResponseParser()

        response = "The state is [0, 1, 1, 0, 1, 0, 1, 0]"

        task_params = {
            'width': 8,
            'expected_state': [0, 1, 1, 0, 1, 0, 1, 0]
        }

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == [0, 1, 1, 0, 1, 0, 1, 0]

    def test_parse_invalid(self):
        """Test parsing invalid response."""
        parser = C14ResponseParser()

        response = "I don't know the answer."

        task_params = {
            'width': 8,
            'expected_state': [0, 1, 1, 0, 1, 0, 1, 0]
        }

        result = parser.parse(response, task_params)

        assert not result.success
        assert result.value is None


class TestC14Evaluator:
    """Test C14 result evaluation."""

    def test_evaluate_exact_match(self):
        """Test exact state match."""
        evaluator = C14ResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=[0, 1, 1, 0, 1, 0, 1, 0],
            raw_response='',
            parse_strategy='test'
        )

        expected_answer = [0, 1, 1, 0, 1, 0, 1, 0]
        task_params = {
            'rule': 110,
            'expected_state': expected_answer
        }

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert result.correct
        assert result.match_type == 'exact'
        assert result.accuracy == 1.0
        assert result.details['correct_cells'] == 8
        assert result.details['total_cells'] == 8

    def test_evaluate_partial_match(self):
        """Test partial state match."""
        evaluator = C14ResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=[0, 1, 1, 0, 0, 0, 1, 0],  # 6/8 correct
            raw_response='',
            parse_strategy='test'
        )

        expected_answer = [0, 1, 1, 0, 1, 0, 1, 0]
        task_params = {
            'rule': 110,
            'expected_state': expected_answer
        }

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert not result.correct
        assert result.match_type == 'partial'
        assert result.details['correct_cells'] == 6
        assert result.details['total_cells'] == 8
        # Normalized accuracy: 2 * (0.75 - 0.5) = 0.5
        assert result.accuracy == 0.5

    def test_evaluate_complete_mismatch(self):
        """Test complete mismatch."""
        evaluator = C14ResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=[1, 0, 0, 1, 0, 1, 0, 1],  # All flipped
            raw_response='',
            parse_strategy='test'
        )

        expected_answer = [0, 1, 1, 0, 1, 0, 1, 0]
        task_params = {
            'rule': 110,
            'expected_state': expected_answer
        }

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert not result.correct
        assert result.match_type == 'mismatch'
        assert result.details['correct_cells'] == 0

    def test_evaluate_parse_error(self):
        """Test evaluation with parse error."""
        evaluator = C14ResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=None,
            raw_response='',
            parse_strategy='failed',
            error='Could not parse state'
        )

        expected_answer = [0, 1, 1, 0, 1, 0, 1, 0]
        task_params = {
            'rule': 110,
            'expected_state': expected_answer
        }

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert not result.correct
        assert result.match_type == 'parse_error'
        assert result.accuracy == 0.0

    def test_aggregate_results(self):
        """Test aggregation of multiple results."""
        evaluator = C14ResultEvaluator()

        results = [
            evaluator.evaluate(
                ParsedAnswer([0, 1, 1, 0, 1, 0, 1, 0], '', 'test'),
                [0, 1, 1, 0, 1, 0, 1, 0],
                {'rule': 110, 'expected_state': [0, 1, 1, 0, 1, 0, 1, 0]}
            ),
            evaluator.evaluate(
                ParsedAnswer([0, 1, 1, 0, 0, 0, 1, 0], '', 'test'),
                [0, 1, 1, 0, 1, 0, 1, 0],
                {'rule': 110, 'expected_state': [0, 1, 1, 0, 1, 0, 1, 0]}
            ),
        ]

        aggregated = evaluator.aggregate_results(results)

        assert aggregated['total'] == 2
        assert aggregated['correct'] == 1
        assert aggregated['success_rate'] == 0.5
        assert 'cell_accuracy' in aggregated


class TestC14Roundtrip:
    """Test full roundtrip: generate -> parse -> evaluate."""

    def test_roundtrip_basic(self):
        """Test complete pipeline."""
        generator = C14TestCaseGenerator()
        parser = C14ResponseParser()
        evaluator = C14ResultEvaluator()

        # Generate test case
        config = generator.get_default_config()
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 1, seed=42)
        test_case = test_cases[0]

        # Simulate correct model response
        expected_state = test_case.task_params['expected_state']
        simulated_response = ''.join(str(x) for x in expected_state)

        # Parse response
        parsed = parser.parse(simulated_response, test_case.task_params)
        assert parsed.success

        # Evaluate
        result = evaluator.evaluate(
            parsed,
            expected_state,
            test_case.task_params
        )

        assert result.correct
        assert result.match_type == 'exact'
        assert result.accuracy == 1.0
