"""
Unit tests for Linda Fallacy plugin.
"""

import pytest
from src.plugins.linda_fallacy.generator import LindaFallacyTestCaseGenerator
from src.plugins.linda_fallacy.parser import LindaFallacyResponseParser
from src.plugins.linda_fallacy.evaluator import LindaFallacyResultEvaluator
from src.plugins.base import TestCase, ParsedAnswer


class TestLindaFallacyGenerator:
    """Test Linda Fallacy test case generation."""

    def test_generate_batch_basic(self):
        """Test basic batch generation."""
        generator = LindaFallacyTestCaseGenerator()

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
            count=3,
            seed=42
        )

        assert len(test_cases) == 3
        assert all(isinstance(tc, TestCase) for tc in test_cases)
        assert all(tc.task_type == 'linda_fallacy' for tc in test_cases)

    def test_generate_with_seed_reproducibility(self):
        """Test that same seed produces same test cases."""
        generator = LindaFallacyTestCaseGenerator()

        config = generator.get_default_config()
        prompt_config = {
            'language': 'en',
            'user_style': 'linguistic',
            'system_style': 'analytical',
            'name': 'test_config'
        }

        tests1 = generator.generate_batch(config, prompt_config, 5, seed=42)
        tests2 = generator.generate_batch(config, prompt_config, 5, seed=42)

        # Should generate same personas
        assert tests1[0].task_params['persona_name'] == tests2[0].task_params['persona_name']


class TestLindaFallacyParser:
    """Test Linda Fallacy response parsing."""

    def test_parse_numbered_list(self):
        """Test parsing numbered ranking list."""
        parser = LindaFallacyResponseParser()

        response = """
        Based on the description:
        1. Teacher
        2. Teacher and activist
        3. Activist
        """

        task_params = {
            'statements': ['Teacher', 'Teacher and activist', 'Activist'],
            'conjunction_index': 1
        }

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == ['Teacher', 'Teacher and activist', 'Activist']
        assert 'numbered_list' in result.parse_strategy

    def test_parse_keywords(self):
        """Test parsing with keywords like 'most likely'."""
        parser = LindaFallacyResponseParser()

        response = """
        Most likely: Teacher and activist
        Less likely: Teacher
        Least likely: Activist
        """

        task_params = {
            'statements': ['Teacher', 'Teacher and activist', 'Activist'],
            'conjunction_index': 1
        }

        result = parser.parse(response, task_params)

        assert result.success
        assert 'Teacher and activist' in result.value[0]

    def test_parse_ambiguous(self):
        """Test parsing ambiguous response."""
        parser = LindaFallacyResponseParser()

        response = "I'm not sure about the ranking."

        task_params = {
            'statements': ['Teacher', 'Teacher and activist', 'Activist'],
            'conjunction_index': 1
        }

        result = parser.parse(response, task_params)

        # Should still attempt to parse, but may fail
        assert result.raw_response == response


class TestLindaFallacyEvaluator:
    """Test Linda Fallacy result evaluation."""

    def test_evaluate_conjunction_fallacy(self):
        """Test detection of conjunction fallacy."""
        evaluator = LindaFallacyResultEvaluator()

        # Fallacy: conjunction ranked higher than components
        parsed_answer = ParsedAnswer(
            value=['Teacher and activist', 'Teacher', 'Activist'],
            raw_response='',
            parse_strategy='test'
        )

        task_params = {
            'statements': ['Teacher', 'Teacher and activist', 'Activist'],
            'conjunction_index': 1,
            'component_indices': [0, 2]
        }

        result = evaluator.evaluate(parsed_answer, None, task_params)

        assert not result.correct  # Committed fallacy
        assert result.details['fallacy_committed'] is True

    def test_evaluate_correct_ranking(self):
        """Test correct ranking (no fallacy)."""
        evaluator = LindaFallacyResultEvaluator()

        # Correct: components ranked higher than conjunction
        parsed_answer = ParsedAnswer(
            value=['Teacher', 'Activist', 'Teacher and activist'],
            raw_response='',
            parse_strategy='test'
        )

        task_params = {
            'statements': ['Teacher', 'Teacher and activist', 'Activist'],
            'conjunction_index': 1,
            'component_indices': [0, 2]
        }

        result = evaluator.evaluate(parsed_answer, None, task_params)

        assert result.correct  # No fallacy
        assert result.details['fallacy_committed'] is False

    def test_evaluate_parse_error(self):
        """Test evaluation with parse error."""
        evaluator = LindaFallacyResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=None,
            raw_response='',
            parse_strategy='failed',
            error='Could not parse ranking'
        )

        task_params = {
            'statements': ['Teacher', 'Teacher and activist', 'Activist'],
            'conjunction_index': 1
        }

        result = evaluator.evaluate(parsed_answer, None, task_params)

        assert not result.correct
        assert result.match_type == 'parse_error'


class TestLindaFallacyRoundtrip:
    """Test full roundtrip: generate -> parse -> evaluate."""

    def test_roundtrip_basic(self):
        """Test complete pipeline."""
        generator = LindaFallacyTestCaseGenerator()
        parser = LindaFallacyResponseParser()
        evaluator = LindaFallacyResultEvaluator()

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

        # Simulate model response (committing fallacy)
        statements = test_case.task_params['statements']
        simulated_response = '\n'.join([f"{i+1}. {s}" for i, s in enumerate(statements)])

        # Parse response
        parsed = parser.parse(simulated_response, test_case.task_params)
        assert parsed.success

        # Evaluate
        result = evaluator.evaluate(
            parsed,
            None,
            test_case.task_params
        )

        assert result is not None
        assert 'fallacy_committed' in result.details
