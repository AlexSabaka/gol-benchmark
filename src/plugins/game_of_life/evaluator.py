"""
Game of Life Result Evaluator

Evaluates parsed grid predictions against expected next states
using cell-by-cell comparison.
"""

from typing import Any, Dict, List

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator


class GoLResultEvaluator(ResultEvaluator):
    """
    Evaluator for Game of Life predictions.

    Compares predicted grids against expected next states using
    cell-by-cell accuracy. Supports various match types:
    - exact: Perfect match of all cells
    - partial: Some cells match
    - mismatch: Grid parsed but no cells match
    - parse_error: Failed to parse response
    """

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate a parsed grid against expected next state.

        Args:
            parsed_answer: ParsedAnswer containing predicted grid
            expected_answer: Expected next state grid (or None to use task_params)
            task_params: Task parameters containing expected_next_state

        Returns:
            EvaluationResult with correctness and cell-by-cell details
        """
        # Get expected grid from task_params if not provided
        if expected_answer is None:
            expected_answer = task_params.get('expected_next_state')

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
                details={'error': 'Predicted grid is None'},
                error='Predicted grid is None'
            )

        if expected_answer is None:
            return EvaluationResult(
                correct=False,
                match_type='error',
                accuracy=0.0,
                details={'error': 'Expected answer is None'},
                error='Expected answer is None'
            )

        # Check dimensions
        expected_rows = len(expected_answer)
        expected_cols = len(expected_answer[0]) if expected_answer else 0
        predicted_rows = len(predicted)
        predicted_cols = len(predicted[0]) if predicted else 0

        if predicted_rows != expected_rows:
            return EvaluationResult(
                correct=False,
                match_type='dimension_mismatch',
                accuracy=0.0,
                details={
                    'error': f'Row count mismatch: expected {expected_rows}, got {predicted_rows}',
                    'expected_shape': (expected_rows, expected_cols),
                    'predicted_shape': (predicted_rows, predicted_cols),
                },
                error=f'Row count mismatch: {expected_rows} vs {predicted_rows}'
            )

        if any(len(p_row) != expected_cols for p_row in predicted):
            return EvaluationResult(
                correct=False,
                match_type='dimension_mismatch',
                accuracy=0.0,
                details={
                    'error': 'Column count mismatch in some rows',
                    'expected_cols': expected_cols,
                },
                error='Column count mismatch'
            )

        # Cell-by-cell comparison
        total_cells = expected_rows * expected_cols
        correct_cells = 0
        cell_details = []

        for i in range(expected_rows):
            for j in range(expected_cols):
                predicted_val = predicted[i][j]
                expected_val = expected_answer[i][j]
                is_correct = predicted_val == expected_val

                if is_correct:
                    correct_cells += 1

                cell_details.append({
                    'pos': (i, j),
                    'predicted': predicted_val,
                    'expected': expected_val,
                    'correct': is_correct
                })

        # Calculate accuracy (normalized to [-1, 1] range where random = 0)
        raw_accuracy = correct_cells / total_cells if total_cells > 0 else 0.0
        # Normalized accuracy: 2 * (raw - 0.5) maps 0.5 -> 0, 1.0 -> 1.0, 0.0 -> -1.0
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
            }
        )

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Aggregate multiple Game of Life results.

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

        # Calculate success rate (exact matches / total)
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
        }
