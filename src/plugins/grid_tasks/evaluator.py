"""
Grid Tasks Result Evaluator

Evaluates model responses against expected answers with support for:
- Exact text matching (case-insensitive)
- Numeric comparison with configurable tolerance
- Partial matching for complex answers
"""

from typing import Any, Dict, List, Optional

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator


class GridTasksResultEvaluator(ResultEvaluator):
    """Evaluate grid task responses."""
    
    def __init__(self, numeric_tolerance: float = 0.1):
        """
        Initialize evaluator.
        
        Args:
            numeric_tolerance: Tolerance for numeric comparisons (default: 0.1)
        """
        self.numeric_tolerance = numeric_tolerance
    
    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate a parsed answer against expected answer.
        
        Args:
            parsed_answer: Parsed model response
            expected_answer: Expected correct answer
            task_params: Task parameters for context
        
        Returns:
            EvaluationResult with correctness, match type, and details
        """
        # Extract value from ParsedAnswer
        if hasattr(parsed_answer, 'value'):
            if not parsed_answer.success:
                return EvaluationResult(
                    correct=False,
                    match_type="parse_error",
                    accuracy=0.0,
                    details={
                        'error': parsed_answer.error,
                        'strategy': parsed_answer.parse_strategy,
                    },
                    error=parsed_answer.error
                )
            model_answer = parsed_answer.value
        else:
            # Backward compatibility with raw strings
            model_answer = parsed_answer
        
        # Handle None values
        if model_answer is None:
            return EvaluationResult(
                correct=False,
                match_type="no_answer",
                accuracy=0.0,
                details={'expected': expected_answer},
                error="Model did not provide an answer"
            )
        
        # Convert to strings for comparison
        model_str = str(model_answer).strip()
        expected_str = str(expected_answer).strip()
        
        # Try different matching strategies
        
        # 1. Exact match (case-sensitive)
        if model_str == expected_str:
            return EvaluationResult(
                correct=True,
                match_type="exact",
                accuracy=1.0,
                details={
                    'expected': expected_str,
                    'parsed': model_str,
                    'strategy': getattr(parsed_answer, 'parse_strategy', 'unknown'),
                }
            )
        
        # 2. Case-insensitive match
        if model_str.lower() == expected_str.lower():
            return EvaluationResult(
                correct=True,
                match_type="case_insensitive",
                accuracy=1.0,
                details={
                    'expected': expected_str,
                    'parsed': model_str,
                    'strategy': getattr(parsed_answer, 'parse_strategy', 'unknown'),
                }
            )
        
        # 3. Numeric comparison with tolerance
        is_numeric, numeric_result = self._compare_numeric(
            model_str, expected_str, self.numeric_tolerance
        )
        if is_numeric:
            if numeric_result['match']:
                return EvaluationResult(
                    correct=True,
                    match_type="numeric_tolerance",
                    accuracy=1.0,
                    details={
                        'expected': expected_str,
                        'parsed': model_str,
                        'difference': numeric_result['difference'],
                        'tolerance': self.numeric_tolerance,
                        'strategy': getattr(parsed_answer, 'parse_strategy', 'unknown'),
                    }
                )
            else:
                return EvaluationResult(
                    correct=False,
                    match_type="numeric_mismatch",
                    accuracy=0.0,
                    details={
                        'expected': expected_str,
                        'parsed': model_str,
                        'difference': numeric_result['difference'],
                        'tolerance': self.numeric_tolerance,
                        'strategy': getattr(parsed_answer, 'parse_strategy', 'unknown'),
                    }
                )
        
        # 4. Partial match (model answer contains expected or vice versa)
        if expected_str.lower() in model_str.lower():
            return EvaluationResult(
                correct=True,
                match_type="partial_contains",
                accuracy=0.8,
                details={
                    'expected': expected_str,
                    'parsed': model_str,
                    'note': 'Model answer contains expected answer',
                    'strategy': getattr(parsed_answer, 'parse_strategy', 'unknown'),
                }
            )
        
        if model_str.lower() in expected_str.lower():
            return EvaluationResult(
                correct=True,
                match_type="partial_subset",
                accuracy=0.6,
                details={
                    'expected': expected_str,
                    'parsed': model_str,
                    'note': 'Model answer is subset of expected answer',
                    'strategy': getattr(parsed_answer, 'parse_strategy', 'unknown'),
                }
            )
        
        # 5. No match
        return EvaluationResult(
            correct=False,
            match_type="mismatch",
            accuracy=0.0,
            details={
                'expected': expected_str,
                'parsed': model_str,
                'strategy': getattr(parsed_answer, 'parse_strategy', 'unknown'),
            }
        )
    
    def _compare_numeric(
        self, value1: str, value2: str, tolerance: float
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Compare two values as numbers with tolerance.
        
        Returns:
            Tuple of (is_numeric, result_dict)
            - is_numeric: True if both values are numeric
            - result_dict: {'match': bool, 'difference': float} if numeric
        """
        try:
            num1 = float(value1)
            num2 = float(value2)
            diff = abs(num1 - num2)
            match = diff <= tolerance
            return True, {'match': match, 'difference': diff}
        except (ValueError, TypeError):
            return False, None
    
    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Aggregate multiple evaluation results.
        
        Args:
            results: List of evaluation results
        
        Returns:
            Dict with aggregate statistics
        """
        if not results:
            return {
                'total': 0,
                'correct': 0,
                'accuracy': 0.0,
                'match_types': {},
                'parse_strategies': {},
            }
        
        total = len(results)
        correct = sum(1 for r in results if r.correct)
        accuracy = correct / total if total > 0 else 0.0
        
        # Count match types
        match_types = {}
        for result in results:
            match_type = result.match_type
            match_types[match_type] = match_types.get(match_type, 0) + 1
        
        # Count parse strategies
        parse_strategies = {}
        for result in results:
            strategy = result.details.get('strategy', 'unknown')
            parse_strategies[strategy] = parse_strategies.get(strategy, 0) + 1
        
        # Calculate average accuracy (considering partial matches)
        avg_accuracy = sum(r.accuracy for r in results) / total if total > 0 else 0.0
        
        return {
            'total': total,
            'correct': correct,
            'accuracy': accuracy,
            'average_accuracy': avg_accuracy,
            'match_types': match_types,
            'parse_strategies': parse_strategies,
            'numeric_tolerance': self.numeric_tolerance,
        }
