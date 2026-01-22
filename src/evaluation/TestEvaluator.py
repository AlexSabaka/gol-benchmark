from src.utils.logger import logger
from src.core.types import TestResult

from typing import Dict, List, Optional

import numpy as np

class TestEvaluator:
    """Evaluates model performance"""

    @staticmethod
    def compare_grids(predicted: Optional[List[List[int]]], actual: List[List[int]]) -> TestResult:
        """Compare predicted vs actual grid with detailed error tracking"""
        result: TestResult = {
            "accuracy": 0.0,
            "correct_cells": 0,
            "total_cells": len(actual) * len(actual[0]),
            "parse_error": predicted is None,
            "cell_by_cell": [],
            "raw_response": "",
            "error_details": None
        }

        if predicted is None:
            result["error_details"] = "Failed to parse model response"
            return result

        if len(predicted) != len(actual):
            result["error_details"] = f"Grid height mismatch: expected {len(actual)}, got {len(predicted)}"
            result["parse_error"] = True
            return result

        if any(len(p_row) != len(a_row) for p_row, a_row in zip(predicted, actual)):
            result["error_details"] = "Grid width mismatch between rows"
            result["parse_error"] = True
            return result

        total_cells = len(actual) * len(actual[0])
        correct_cells = 0

        for i in range(len(actual)):
            for j in range(len(actual[0])):
                predicted_val = predicted[i][j]
                actual_val = actual[i][j]
                is_correct = predicted_val == actual_val

                if is_correct:
                    correct_cells += 1

                result["cell_by_cell"].append({
                    'pos': (i, j),
                    'predicted': predicted_val,
                    'actual': actual_val,
                    'correct': is_correct
                })

        result.update({
            "accuracy": 2 * (correct_cells / total_cells - 0.5),
            "correct_cells": correct_cells,
            "total_cells": total_cells,
            "parse_error": False
        })

        return result

    @staticmethod
    def evaluate_batch(results: List[TestResult]) -> Dict:
        """Evaluate a batch of test results with enhanced metrics"""
        if not results:
            return {"error": "No results to evaluate"}

        valid_results = [r for r in results if not r.get("parse_error", False)]
        parse_errors = [r for r in results if r.get("parse_error", False)]

        if not valid_results:
            error_details = "\n".join(
                f"Test {i}: {r.get('error_details', 'Unknown error')}"
                for i, r in enumerate(parse_errors)
            )
            logger.error(f"All tests failed to parse:\n{error_details}")
            return {
                "average_accuracy": 0.0,
                "normalized_accuracy": 0.0,
                "valid_tests": 0,
                "parse_errors": len(parse_errors),
                "total_tests": len(results),
                "success_rate": 0.0,
                "error_details": error_details
            }

        accuracies = [r["accuracy"] for r in valid_results]
        total_accuracy = sum(accuracies)
        normalized_accuracy = total_accuracy / len(results)

        # Calculate error patterns
        error_patterns = {}
        for r in parse_errors:
            error = r.get("error_details", "Unknown error")
            error_patterns[error] = error_patterns.get(error, 0) + 1

        return {
            "average_accuracy": sum(accuracies) / len(accuracies),
            "std_accuracy": float(np.nanstd(accuracies)) if len(accuracies) > 1 else 0.0,
            "normalized_accuracy": normalized_accuracy,
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
            "valid_tests": len(valid_results),
            "parse_errors": len(parse_errors),
            "total_tests": len(results),
            "success_rate": len(valid_results) / len(results),
            "accuracy_distribution": accuracies,
            "perfect_scores": len([a for a in accuracies if a == 1.0]),
            "error_patterns": error_patterns,
            "most_common_errors": sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:3]
        }