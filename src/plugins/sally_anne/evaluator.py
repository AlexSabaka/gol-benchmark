"""
Sally-Anne Result Evaluator

Evaluates model responses against expected answers (belief location).
"""

from typing import Dict, Any, List
from ..base import ResultEvaluator, EvaluationResult


class SallyAnneResultEvaluator(ResultEvaluator):
    """
    Evaluator for Sally-Anne test results.
    
    Checks if the model correctly identifies where Subject A will look
    (the belief location - container_a) vs the reality trap (actual location - container_b).
    """
    
    def __init__(self):
        # Container synonyms for flexible matching
        self.container_synonyms = {
            'basket': ['basket', 'hamper', 'wicker basket', 'the basket'],
            'box': ['box', 'container', 'storage box', 'carton', 'the box'],
            'drawer': ['drawer', 'cabinet drawer', 'the drawer'],
            'cupboard': ['cupboard', 'cabinet', 'closet', 'the cupboard'],
            'bag': ['bag', 'purse', 'sack', 'tote', 'the bag'],
            'pocket': ['pocket', 'coat pocket', 'pants pocket', 'the pocket'],
        }
    
    def evaluate(
        self,
        parsed_answer: Any,
        expected_answer: Any,
        task_params: Dict[str, Any]
    ) -> 'EvaluationResult':
        """
        Evaluate Sally-Anne test result.
        
        Args:
            parsed_answer: Parsed answer object (or string for backward compat)
            expected_answer: Correct answer (belief location - container_a)
            task_params: Test case parameters with container_a, container_b
            
        Returns:
            EvaluationResult with:
            - correct: Boolean
            - accuracy: 1.0 (exact match) or 0.0 (mismatch)
            - match_type: "exact", "synonym", "reality_trap", "parse_error", or "wrong_container"
            - details: Additional evaluation information
        """
        # Handle parse errors and extract value from ParsedAnswer
        if hasattr(parsed_answer, 'value'):
            # ParsedAnswer object
            if not parsed_answer.success:
                return EvaluationResult(
                    correct=False,
                    accuracy=0.0,
                    match_type="parse_error",
                    details={
                        'expected': expected_answer,
                        'received': str(parsed_answer),
                        'reason': parsed_answer.error or 'Failed to parse model response'
                    }
                )
            model_answer = parsed_answer.value
        else:
            # String (backward compat)
            model_answer = parsed_answer
        
        if model_answer in ["PARSE_ERROR", "NO_RESPONSE", None]:
            return EvaluationResult(
                correct=False,
                accuracy=0.0,
                match_type="parse_error",
                details={
                    'expected': expected_answer,
                    'received': str(model_answer),
                    'reason': 'Failed to parse model response'
                }
            )
        
        # Normalize answers
        expected_norm = expected_answer.lower().strip()
        model_norm = model_answer.lower().strip()
        
        # Get container locations from task_params
        container_a = task_params.get('container_a', '').lower()  # Correct (belief location)
        container_b = task_params.get('container_b', '').lower()  # Reality trap (actual location)
        
        # Check for exact match with expected (container_a)
        if model_norm == expected_norm or model_norm == container_a:
            return EvaluationResult(
                correct=True,
                accuracy=1.0,
                match_type='exact',
                details={
                    'expected': expected_answer,
                    'received': model_answer,
                    'belief_location': container_a,
                    'actual_location': container_b,
                }
            )
        
        # Check for synonym match with container_a (correct answer)
        if self._is_synonym_match(container_a, model_norm):
            return EvaluationResult(
                correct=True,
                accuracy=1.0,
                match_type='synonym',
                details={
                    'expected': expected_answer,
                    'received': model_answer,
                    'belief_location': container_a,
                    'actual_location': container_b,
                }
            )
        
        # Check if model fell for reality trap (answered container_b instead of container_a)
        if model_norm == container_b or self._is_synonym_match(container_b, model_norm):
            return EvaluationResult(
                correct=False,
                accuracy=0.0,
                match_type="reality_trap",
                details={
                    'expected': expected_answer,
                    'received': model_answer,
                    'reason': f'Model answered actual location ({container_b}) instead of belief location ({container_a})',
                    'belief_location': container_a,
                    'actual_location': container_b,
                }
            )
        
        # Wrong answer (neither correct nor reality trap)
        return EvaluationResult(
            correct=False,
            accuracy=0.0,
            match_type="wrong_container",
            details={
                'expected': expected_answer,
                'received': model_answer,
                'reason': 'Answered a different container',
                'belief_location': container_a,
                'actual_location': container_b,
            }
        )
    
    def _is_synonym_match(self, canonical: str, answer: str) -> bool:
        """
        Check if answer matches canonical container (with synonyms).
        
        Args:
            canonical: Canonical container name
            answer: Model answer (normalized)
            
        Returns:
            True if answer matches canonical or its synonyms
        """
        canonical_lower = canonical.lower()
        answer_lower = answer.lower()
        
        # Direct match
        if canonical_lower == answer_lower:
            return True
        
        # Check if canonical is in answer or vice versa
        if canonical_lower in answer_lower or answer_lower in canonical_lower:
            return True
        
        # Check synonyms
        for container, synonyms in self.container_synonyms.items():
            if canonical_lower in [s.lower() for s in synonyms]:
                # canonical is a synonym of container
                if answer_lower in [s.lower() for s in synonyms]:
                    return True
        
        return False
    
    def aggregate_results(self, results: List['EvaluationResult']) -> Dict[str, Any]:
        """
        Aggregate multiple evaluation results.
        
        Args:
            results: List of EvaluationResult objects
            
        Returns:
            Dictionary with aggregate statistics:
            - accuracy: Overall accuracy rate
            - total_cases: Number of test cases
            - correct_count: Number of correct answers
            - reality_trap_count: Number of reality trap errors
            - parse_error_count: Number of parse errors
            - wrong_container_count: Number of other wrong answers
        """
        if not results:
            return {
                'accuracy': 0.0,
                'total_cases': 0,
                'correct_count': 0,
                'reality_trap_count': 0,
                'parse_error_count': 0,
                'wrong_container_count': 0,
            }
        
        correct_count = sum(1 for r in results if r.correct)
        reality_trap_count = sum(1 for r in results if r.match_type == 'reality_trap')
        parse_error_count = sum(1 for r in results if r.match_type == 'parse_error')
        wrong_container_count = sum(1 for r in results if r.match_type == 'wrong_container')
        
        return {
            'accuracy': correct_count / len(results),
            'total_cases': len(results),
            'correct_count': correct_count,
            'reality_trap_count': reality_trap_count,
            'parse_error_count': parse_error_count,
            'wrong_container_count': wrong_container_count,
            'reality_trap_rate': reality_trap_count / len(results),
        }
