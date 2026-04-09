"""
Picross (Nonogram) Result Evaluator

Cell-by-cell grid comparison with normalized accuracy.
Adapted from the Game of Life evaluator.
"""

from typing import Any, Dict, List

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator


class PicrossEvaluator(ResultEvaluator):
    """Evaluator for Picross predictions.

    Compares predicted grids against expected solutions using
    cell-by-cell accuracy with normalization: ``2 * (raw - 0.5)``
    maps chance level (0.5 for a binary grid) to 0.0 and perfect to 1.0.
    """

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any],
    ) -> EvaluationResult:
        if expected_answer is None:
            expected_answer = task_params.get("expected_grid")

        # Handle parse errors
        if not parsed_answer.success:
            return EvaluationResult(
                correct=False,
                match_type="parse_error",
                accuracy=0.0,
                details={
                    "error": parsed_answer.error,
                    "parse_strategy": parsed_answer.parse_strategy,
                },
                error=parsed_answer.error,
            )

        predicted = parsed_answer.value

        if predicted is None:
            return EvaluationResult(
                correct=False, match_type="parse_error", accuracy=0.0,
                details={"error": "Predicted grid is None"},
                error="Predicted grid is None",
            )

        if expected_answer is None:
            return EvaluationResult(
                correct=False, match_type="error", accuracy=0.0,
                details={"error": "Expected answer is None"},
                error="Expected answer is None",
            )

        # Dimension check
        expected_rows = len(expected_answer)
        expected_cols = len(expected_answer[0]) if expected_answer else 0
        predicted_rows = len(predicted)
        predicted_cols = len(predicted[0]) if predicted else 0

        if predicted_rows != expected_rows:
            return EvaluationResult(
                correct=False, match_type="dimension_mismatch", accuracy=0.0,
                details={
                    "error": f"Row count mismatch: expected {expected_rows}, got {predicted_rows}",
                    "expected_shape": (expected_rows, expected_cols),
                    "predicted_shape": (predicted_rows, predicted_cols),
                },
                error=f"Row count mismatch: {expected_rows} vs {predicted_rows}",
            )

        if any(len(row) != expected_cols for row in predicted):
            return EvaluationResult(
                correct=False, match_type="dimension_mismatch", accuracy=0.0,
                details={
                    "error": "Column count mismatch in some rows",
                    "expected_cols": expected_cols,
                },
                error="Column count mismatch",
            )

        # Cell-by-cell comparison
        total_cells = expected_rows * expected_cols
        correct_cells = 0
        cell_details: List[Dict[str, Any]] = []

        for i in range(expected_rows):
            for j in range(expected_cols):
                pred_val = predicted[i][j]
                exp_val = expected_answer[i][j]
                is_correct = pred_val == exp_val
                if is_correct:
                    correct_cells += 1
                cell_details.append({
                    "pos": (i, j),
                    "predicted": pred_val,
                    "expected": exp_val,
                    "correct": is_correct,
                })

        raw_accuracy = correct_cells / total_cells if total_cells > 0 else 0.0
        normalized_accuracy = 2 * (raw_accuracy - 0.5)

        if correct_cells == total_cells:
            match_type = "exact"
            is_correct = True
        elif correct_cells > 0:
            match_type = "partial"
            is_correct = False
        else:
            match_type = "mismatch"
            is_correct = False

        return EvaluationResult(
            correct=is_correct,
            match_type=match_type,
            accuracy=normalized_accuracy,
            details={
                "correct_cells": correct_cells,
                "total_cells": total_cells,
                "raw_accuracy": raw_accuracy,
                "cell_by_cell": cell_details,
                "parse_strategy": parsed_answer.parse_strategy,
            },
        )

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        if not results:
            return {
                "accuracy": 0.0, "normalized_accuracy": 0.0,
                "correct": 0, "total": 0, "error_count": 0, "match_types": {},
            }

        base = super().aggregate_results(results)

        # Add average normalized accuracy
        accuracies = [r.accuracy for r in results if r.accuracy is not None]
        base["normalized_accuracy"] = (
            sum(accuracies) / len(accuracies) if accuracies else 0.0
        )
        return base
