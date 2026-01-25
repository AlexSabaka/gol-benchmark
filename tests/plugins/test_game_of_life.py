"""
Unit tests for the Game of Life plugin.
"""

import pytest
from src.plugins import PluginRegistry
from src.plugins.base import TestCase, ParsedAnswer, EvaluationResult


class TestGameOfLifePlugin:
    """Test the Game of Life plugin."""

    @pytest.fixture
    def plugin(self):
        """Get the Game of Life plugin."""
        return PluginRegistry.get('game_of_life')

    def test_generator(self, plugin):
        """Test the generator creates valid test cases."""
        generator = plugin.get_generator()

        config = {
            'difficulty_levels': ['EASY'],
            'density': 0.5,
            'grids_per_difficulty': 2,
            'cell_markers': ['1', '0']
        }

        prompt_config = {
            'user_style': 'linguistic',
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
        assert tc.task_type == 'game_of_life'
        assert 'initial_grid' in tc.task_params
        assert 'expected_next_state' in tc.task_params
        assert len(tc.prompts['user']) > 0
        assert len(tc.prompts['system']) > 0

    def test_parser_valid_response(self, plugin):
        """Test parser with valid response."""
        parser = plugin.get_parser()

        # Mock response with 3x3 grid
        response = """
        The next state is:
        0 1 0
        1 1 1
        0 1 0
        """

        task_params = {
            'expected_next_state': [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
        }

        parsed = parser.parse(response, task_params)

        assert isinstance(parsed, ParsedAnswer)
        assert parsed.success
        assert parsed.value == [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
        assert parsed.parse_strategy in ['line_scan_reverse', 'marker_search', 'digit_extraction', 'last_resort']

    def test_parser_invalid_response(self, plugin):
        """Test parser with invalid response."""
        parser = plugin.get_parser()

        response = "I don't know"

        task_params = {
            'expected_next_state': [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
        }

        parsed = parser.parse(response, task_params)

        assert isinstance(parsed, ParsedAnswer)
        assert not parsed.success
        assert parsed.value is None
        assert parsed.error is not None

    def test_evaluator_exact_match(self, plugin):
        """Test evaluator with exact match."""
        evaluator = plugin.get_evaluator()

        predicted_grid = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
        expected_grid = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]

        parsed = ParsedAnswer(
            value=predicted_grid,
            raw_response="test",
            parse_strategy="test"
        )

        task_params = {'expected_next_state': expected_grid}

        result = evaluator.evaluate(parsed, expected_grid, task_params)

        assert isinstance(result, EvaluationResult)
        assert result.correct is True
        assert result.match_type == 'exact'
        assert result.accuracy == 1.0
        assert result.details['correct_cells'] == 9
        assert result.details['total_cells'] == 9

    def test_evaluator_partial_match(self, plugin):
        """Test evaluator with partial match."""
        evaluator = plugin.get_evaluator()

        predicted_grid = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]  # Changed middle cell
        expected_grid = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]

        parsed = ParsedAnswer(
            value=predicted_grid,
            raw_response="test",
            parse_strategy="test"
        )

        task_params = {'expected_next_state': expected_grid}

        result = evaluator.evaluate(parsed, expected_grid, task_params)

        assert isinstance(result, EvaluationResult)
        assert result.correct is False
        assert result.match_type == 'partial'
        assert result.details['correct_cells'] == 8
        assert result.details['total_cells'] == 9

    def test_evaluator_aggregate(self, plugin):
        """Test evaluator aggregation."""
        evaluator = plugin.get_evaluator()

        # Create some results
        results = [
            EvaluationResult(
                correct=True,
                match_type='exact',
                accuracy=1.0,
                details={'correct_cells': 9, 'total_cells': 9}
            ),
            EvaluationResult(
                correct=False,
                match_type='partial',
                accuracy=0.556,
                details={'correct_cells': 7, 'total_cells': 9}
            ),
            EvaluationResult(
                correct=True,
                match_type='exact',
                accuracy=1.0,
                details={'correct_cells': 9, 'total_cells': 9}
            ),
        ]

        aggregated = evaluator.aggregate_results(results)

        assert aggregated['total'] == 3
        assert aggregated['correct'] == 2
        assert aggregated['success_rate'] == pytest.approx(2/3)
        assert aggregated['exact_matches'] == 2
        assert aggregated['partial_matches'] == 1
        assert aggregated['total_cells_evaluated'] == 27

    def test_roundtrip(self, plugin):
        """Test full roundtrip: generate -> parse -> evaluate."""
        generator = plugin.get_generator()
        parser = plugin.get_parser()
        evaluator = plugin.get_evaluator()

        # Generate a test case
        config = {'difficulty_levels': ['EASY'], 'grids_per_difficulty': 1, 'cell_markers': ['1', '0']}
        prompt_config = {'user_style': 'minimal', 'system_style': 'analytical', 'name': 'test', 'language': 'en'}

        test_cases = generator.generate_batch(config, prompt_config, count=1, seed=42)
        tc = test_cases[0]

        # Create a mock perfect response
        expected_grid = tc.task_params['expected_next_state']
        mock_response = '\n'.join(' '.join(str(cell) for cell in row) for row in expected_grid)

        # Parse the response
        parsed = parser.parse(mock_response, tc.task_params)

        # Evaluate
        result = evaluator.evaluate(parsed, expected_grid, tc.task_params)

        # Should be perfect match
        assert result.correct is True
        assert result.accuracy == 1.0
