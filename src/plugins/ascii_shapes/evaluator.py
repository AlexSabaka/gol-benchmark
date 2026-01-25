"""
ASCII Shapes Result Evaluator

Evaluates parsed answers against expected values
for dimensions, counts, and position questions.
"""

from typing import Any, Dict, List

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator


class AsciiShapesResultEvaluator(ResultEvaluator):
    """
    Evaluator for ASCII Shapes predictions.

    Handles three question types:
    - Dimensions: exact match of "WxH" format
    - Count: exact numeric match
    - Position: boolean match
    """

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate a parsed answer against expected.

        Args:
            parsed_answer: ParsedAnswer containing predicted value
            expected_answer: Expected answer (or None to use task_params)
            task_params: Task parameters containing expected_answer

        Returns:
            EvaluationResult with correctness details
        """
        # Get expected answer from task_params if not provided
        if expected_answer is None:
            expected_answer = task_params.get('expected_answer')

        question_type = task_params.get('question_type', 'dimensions')

        # Handle parse errors
        if not parsed_answer.success:
            return EvaluationResult(
                correct=False,
                match_type='parse_error',
                accuracy=0.0,
                details={
                    'error': parsed_answer.error,
                    'parse_strategy': parsed_answer.parse_strategy,
                    'question_type': question_type,
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

        # Evaluate based on question type
        if question_type == 'dimensions':
            return self._evaluate_dimensions(predicted, expected_answer, parsed_answer, task_params)
        elif question_type == 'count':
            return self._evaluate_count(predicted, expected_answer, parsed_answer, task_params)
        elif question_type == 'position':
            return self._evaluate_position(predicted, expected_answer, parsed_answer, task_params)
        else:
            # Try to infer type from expected answer
            if isinstance(expected_answer, bool):
                return self._evaluate_position(predicted, expected_answer, parsed_answer, task_params)
            elif isinstance(expected_answer, int):
                return self._evaluate_count(predicted, expected_answer, parsed_answer, task_params)
            else:
                return self._evaluate_dimensions(predicted, expected_answer, parsed_answer, task_params)

    def _evaluate_dimensions(
        self,
        predicted: Any,
        expected: Any,
        parsed_answer: ParsedAnswer,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate dimensions answer."""
        # Normalize to WxH format
        pred_str = str(predicted).lower().replace(' ', '')
        exp_str = str(expected).lower().replace(' ', '')

        is_correct = pred_str == exp_str

        # Check if dimensions are swapped
        is_swapped = False
        if not is_correct and 'x' in pred_str and 'x' in exp_str:
            pred_parts = pred_str.split('x')
            exp_parts = exp_str.split('x')
            if len(pred_parts) == 2 and len(exp_parts) == 2:
                if pred_parts[0] == exp_parts[1] and pred_parts[1] == exp_parts[0]:
                    is_swapped = True

        match_type = 'exact' if is_correct else ('swapped' if is_swapped else 'mismatch')

        return EvaluationResult(
            correct=is_correct,
            match_type=match_type,
            accuracy=1.0 if is_correct else 0.0,
            details={
                'predicted': str(predicted),
                'expected': str(expected),
                'is_swapped': is_swapped,
                'question_type': 'dimensions',
                'parse_strategy': parsed_answer.parse_strategy,
            }
        )

    def _evaluate_count(
        self,
        predicted: Any,
        expected: Any,
        parsed_answer: ParsedAnswer,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate count answer."""
        try:
            pred_int = int(predicted)
            exp_int = int(expected)
        except (ValueError, TypeError):
            return EvaluationResult(
                correct=False,
                match_type='type_error',
                accuracy=0.0,
                details={
                    'error': 'Could not convert to integers',
                    'predicted': predicted,
                    'expected': expected,
                },
                error='Type conversion error'
            )

        is_correct = pred_int == exp_int

        return EvaluationResult(
            correct=is_correct,
            match_type='exact' if is_correct else 'mismatch',
            accuracy=1.0 if is_correct else 0.0,
            details={
                'predicted': pred_int,
                'expected': exp_int,
                'difference': abs(pred_int - exp_int),
                'question_type': 'count',
                'parse_strategy': parsed_answer.parse_strategy,
            }
        )

    def _evaluate_position(
        self,
        predicted: Any,
        expected: Any,
        parsed_answer: ParsedAnswer,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate position answer."""
        try:
            pred_bool = bool(predicted)
            exp_bool = bool(expected)
        except (ValueError, TypeError):
            return EvaluationResult(
                correct=False,
                match_type='type_error',
                accuracy=0.0,
                details={
                    'error': 'Could not convert to booleans',
                    'predicted': predicted,
                    'expected': expected,
                },
                error='Type conversion error'
            )

        is_correct = pred_bool == exp_bool

        return EvaluationResult(
            correct=is_correct,
            match_type='exact' if is_correct else 'mismatch',
            accuracy=1.0 if is_correct else 0.0,
            details={
                'predicted': pred_bool,
                'expected': exp_bool,
                'question_type': 'position',
                'parse_strategy': parsed_answer.parse_strategy,
            }
        )

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Aggregate multiple ASCII Shapes results.

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
        success_rate = correct / len(results) if results else 0.0

        match_types = self._count_match_types(results)

        # Question type breakdown
        question_type_stats = {}
        for r in results:
            q_type = r.details.get('question_type', 'unknown')
            if q_type not in question_type_stats:
                question_type_stats[q_type] = {'correct': 0, 'total': 0}
            question_type_stats[q_type]['total'] += 1
            if r.correct:
                question_type_stats[q_type]['correct'] += 1

        return {
            'accuracy': success_rate,
            'success_rate': success_rate,
            'correct': correct,
            'total': len(results),
            'error_count': errors,
            'parse_errors': match_types.get('parse_error', 0),
            'match_types': match_types,
            'question_type_breakdown': question_type_stats,
        }
