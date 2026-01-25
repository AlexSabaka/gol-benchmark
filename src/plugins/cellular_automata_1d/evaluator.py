"""
Cellular Automata 1D Result Evaluator

Evaluates parsed 1D states against expected states
using cell-by-cell comparison.
"""

from typing import Any, Dict, List

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator


class C14ResultEvaluator(ResultEvaluator):
    """
    Evaluator for 1D Cellular Automata predictions.

    Compares predicted states against expected next states using
    cell-by-cell accuracy.
    """

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate a parsed state against expected.

        Args:
            parsed_answer: ParsedAnswer containing predicted state
            expected_answer: Expected state (or None to use task_params)
            task_params: Task parameters containing expected_state

        Returns:
            EvaluationResult with correctness and cell details
        """
        # Get expected state from task_params if not provided
        if expected_answer is None:
            expected_answer = task_params.get('expected_state')

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
                details={'error': 'Predicted state is None'},
                error='Predicted state is None'
            )

        if expected_answer is None:
            return EvaluationResult(
                correct=False,
                match_type='error',
                accuracy=0.0,
                details={'error': 'Expected state is None'},
                error='Expected state is None'
            )

        # Ensure both are lists
        predicted = list(predicted)
        expected = list(expected_answer)

        # Check length match
        if len(predicted) != len(expected):
            # Try to handle length mismatch by truncating/padding
            min_len = min(len(predicted), len(expected))
            if min_len < 8:
                return EvaluationResult(
                    correct=False,
                    match_type='length_mismatch',
                    accuracy=0.0,
                    details={
                        'error': f'Length mismatch: predicted {len(predicted)}, expected {len(expected)}',
                        'predicted_length': len(predicted),
                        'expected_length': len(expected),
                    },
                    error=f'Length mismatch: {len(predicted)} vs {len(expected)}'
                )

            # Compare overlapping portion
            predicted = predicted[:min_len]
            expected = expected[:min_len]

        # Cell-by-cell comparison
        total_cells = len(expected)
        correct_cells = 0
        cell_details = []

        for i in range(total_cells):
            predicted_val = predicted[i]
            expected_val = expected[i]
            is_correct = predicted_val == expected_val

            if is_correct:
                correct_cells += 1

            cell_details.append({
                'pos': i,
                'predicted': predicted_val,
                'expected': expected_val,
                'correct': is_correct
            })

        # Calculate accuracy
        raw_accuracy = correct_cells / total_cells if total_cells > 0 else 0.0
        # Normalized accuracy: 2 * (raw - 0.5)
        normalized_accuracy = 2 * (raw_accuracy - 0.5)

        # Determine match type
        if correct_cells == total_cells:
            match_type = 'exact'
            is_correct = True
        elif correct_cells > 0:
            match_type = 'partial'
            is_correct = False
        else:
            match_type = 'mismatch'
            is_correct = False

        return EvaluationResult(
            correct=is_correct,
            match_type=match_type,
            accuracy=normalized_accuracy,
            details={
                'correct_cells': correct_cells,
                'total_cells': total_cells,
                'raw_accuracy': raw_accuracy,
                'cell_by_cell': cell_details,
                'parse_strategy': parsed_answer.parse_strategy,
                'rule': task_params.get('rule', 'unknown'),
            }
        )

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Aggregate multiple C14 results.

        Args:
            results: List of EvaluationResult objects

        Returns:
            Dictionary with aggregated statistics
        """
        if not results:
            return {
                'accuracy': 0.0,
                'normalized_accuracy': 0.0,
                'correct': 0,
                'total': 0,
                'error_count': 0,
                'match_types': {},
            }

        # Count correct (exact matches)
        correct = sum(1 for r in results if r.correct)

        # Count errors
        errors = sum(1 for r in results if r.error is not None)

        # Average accuracy
        valid_accuracies = [r.accuracy for r in results if r.error is None]
        avg_accuracy = sum(valid_accuracies) / len(valid_accuracies) if valid_accuracies else 0.0

        # Success rate
        success_rate = correct / len(results) if results else 0.0

        # Count match types
        match_types = self._count_match_types(results)

        # Calculate cell-level statistics
        total_cells_correct = 0
        total_cells = 0
        for r in results:
            if 'correct_cells' in r.details:
                total_cells_correct += r.details['correct_cells']
                total_cells += r.details['total_cells']

        cell_accuracy = total_cells_correct / total_cells if total_cells > 0 else 0.0

        # Rule breakdown
        rule_stats = {}
        for r in results:
            rule = r.details.get('rule', 'unknown')
            if rule not in rule_stats:
                rule_stats[rule] = {'correct': 0, 'total': 0}
            rule_stats[rule]['total'] += 1
            if r.correct:
                rule_stats[rule]['correct'] += 1

        return {
            'accuracy': avg_accuracy,
            'normalized_accuracy': avg_accuracy,
            'success_rate': success_rate,
            'correct': correct,
            'total': len(results),
            'error_count': errors,
            'parse_errors': match_types.get('parse_error', 0),
            'exact_matches': match_types.get('exact', 0),
            'partial_matches': match_types.get('partial', 0),
            'match_types': match_types,
            'cell_accuracy': cell_accuracy,
            'total_cells_evaluated': total_cells,
            'rule_breakdown': rule_stats,
        }
