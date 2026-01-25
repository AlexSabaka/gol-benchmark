"""
Arithmetic Result Evaluator

Evaluates parsed numeric answers against expected values
with support for exact and approximate matching.
"""

from typing import Any, Dict, List

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator


class ArithmeticResultEvaluator(ResultEvaluator):
    """
    Evaluator for arithmetic expression predictions.

    Compares predicted numeric values against expected answers.
    Supports exact matching and approximate matching with tolerance.
    """

    def __init__(self, tolerance: float = 1e-9):
        """
        Initialize evaluator.

        Args:
            tolerance: Relative tolerance for approximate matching
        """
        self.tolerance = tolerance

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate a parsed answer against expected value.

        Args:
            parsed_answer: ParsedAnswer containing predicted value
            expected_answer: Expected answer (or None to use task_params)
            task_params: Task parameters containing expected_answer

        Returns:
            EvaluationResult with correctness and match details
        """
        # Get expected value from task_params if not provided
        if expected_answer is None:
            expected_answer = task_params.get('expected_answer')
            if expected_answer is None:
                expected_answer = task_params.get('target_value')

        # Handle parse errors
        if not parsed_answer.success:
            return EvaluationResult(
                correct=False,
                match_type='parse_error',
                accuracy=0.0,
                details={
                    'error': parsed_answer.error,
                    'parse_strategy': parsed_answer.parse_strategy,
                },
                error=parsed_answer.error
            )

        predicted = parsed_answer.value

        # Validate inputs
        if predicted is None:
            return EvaluationResult(
                correct=False,
                match_type='parse_error',
                accuracy=0.0,
                details={'error': 'Predicted value is None'},
                error='Predicted value is None'
            )

        if expected_answer is None:
            return EvaluationResult(
                correct=False,
                match_type='error',
                accuracy=0.0,
                details={'error': 'Expected answer is None'},
                error='Expected answer is None'
            )

        # Convert to float for comparison
        try:
            predicted_float = float(predicted)
            expected_float = float(expected_answer)
        except (ValueError, TypeError) as e:
            return EvaluationResult(
                correct=False,
                match_type='conversion_error',
                accuracy=0.0,
                details={
                    'error': f'Failed to convert values: {e}',
                    'predicted': predicted,
                    'expected': expected_answer,
                },
                error=f'Conversion error: {e}'
            )

        # Compare values
        is_exact = predicted_float == expected_float

        # Check approximate match
        is_approximate = False
        if not is_exact and expected_float != 0:
            relative_error = abs(predicted_float - expected_float) / abs(expected_float)
            is_approximate = relative_error <= self.tolerance
        elif not is_exact and expected_float == 0:
            is_approximate = abs(predicted_float) <= self.tolerance

        is_correct = is_exact or is_approximate

        # Determine match type
        if is_exact:
            match_type = 'exact'
        elif is_approximate:
            match_type = 'approximate'
        else:
            match_type = 'mismatch'

        # Calculate accuracy (1.0 for correct, 0.0 for incorrect)
        accuracy = 1.0 if is_correct else 0.0

        return EvaluationResult(
            correct=is_correct,
            match_type=match_type,
            accuracy=accuracy,
            details={
                'predicted': predicted_float,
                'expected': expected_float,
                'is_exact': is_exact,
                'is_approximate': is_approximate,
                'parse_strategy': parsed_answer.parse_strategy,
                'expression': task_params.get('expression', ''),
                'complexity': task_params.get('complexity', 0),
            }
        )

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Aggregate multiple arithmetic results.

        Args:
            results: List of EvaluationResult objects

        Returns:
            Dictionary with aggregated statistics
        """
        if not results:
            return {
                'accuracy': 0.0,
                'correct': 0,
                'total': 0,
                'error_count': 0,
                'match_types': {},
            }

        correct = sum(1 for r in results if r.correct)
        errors = sum(1 for r in results if r.error is not None)
        parse_errors = sum(1 for r in results if r.match_type == 'parse_error')

        # Calculate accuracy
        success_rate = correct / len(results) if results else 0.0

        # Count match types
        match_types = self._count_match_types(results)

        # Calculate complexity breakdown
        complexity_stats = {}
        for r in results:
            complexity = r.details.get('complexity', 'unknown')
            if complexity not in complexity_stats:
                complexity_stats[complexity] = {'correct': 0, 'total': 0}
            complexity_stats[complexity]['total'] += 1
            if r.correct:
                complexity_stats[complexity]['correct'] += 1

        return {
            'accuracy': success_rate,
            'success_rate': success_rate,
            'correct': correct,
            'total': len(results),
            'error_count': errors,
            'parse_errors': parse_errors,
            'exact_matches': match_types.get('exact', 0),
            'approximate_matches': match_types.get('approximate', 0),
            'mismatches': match_types.get('mismatch', 0),
            'match_types': match_types,
            'complexity_breakdown': complexity_stats,
        }
