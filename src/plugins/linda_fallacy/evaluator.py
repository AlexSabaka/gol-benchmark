"""
Linda Fallacy Result Evaluator

Evaluates whether the model fell for the conjunction fallacy
by checking if the conjunction item was ranked higher than its components.
"""

import re
from typing import Any, Dict, List

from src.plugins.base import EvaluationResult, ParsedAnswer, ResultEvaluator


class LindaResultEvaluator(ResultEvaluator):
    """
    Evaluator for Linda Conjunction Fallacy predictions.

    Determines whether the model exhibited the conjunction fallacy
    by ranking the conjunction (A and B) higher than at least one
    of its component statements (A or B alone).
    """

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate if the model exhibited the conjunction fallacy.

        Args:
            parsed_answer: ParsedAnswer containing rankings dict
            expected_answer: Not used (we check for fallacy presence)
            task_params: Task parameters containing test_item details

        Returns:
            EvaluationResult with fallacy detection details
        """
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

        rankings_data = parsed_answer.value
        if not rankings_data or not isinstance(rankings_data, dict):
            return EvaluationResult(
                correct=False,
                match_type='invalid_format',
                accuracy=0.0,
                details={'error': 'Invalid rankings format'},
                error='Invalid rankings format'
            )

        rankings = rankings_data.get('rankings', [])
        if not rankings:
            return EvaluationResult(
                correct=False,
                match_type='no_rankings',
                accuracy=0.0,
                details={'error': 'No rankings found in response'},
                error='No rankings found'
            )

        # Get test item details
        test_item = task_params.get('test_item', {})
        conjunction_item = test_item.get('conjunction_item', '')
        component_a = test_item.get('component_a', '')
        component_b = test_item.get('component_b', '')

        # Find positions of key items in rankings
        def find_position(item: str, rankings: List[str]) -> int:
            """Find position of item in rankings using fuzzy matching."""
            item_lower = item.lower()
            item_norm = re.sub(r'[^a-zA-Z0-9]', '', item_lower)

            for i, ranking in enumerate(rankings):
                ranking_lower = ranking.lower()
                ranking_norm = re.sub(r'[^a-zA-Z0-9]', '', ranking_lower)

                # Exact substring match
                if item_lower in ranking_lower or ranking_lower in item_lower:
                    return i

                # Normalized match
                if item_norm in ranking_norm or ranking_norm in item_norm:
                    return i

                # High similarity match
                if len(item_norm) > 5 and len(ranking_norm) > 5:
                    overlap = len(set(item_norm) & set(ranking_norm))
                    union = len(set(item_norm) | set(ranking_norm))
                    if overlap / union > 0.8:
                        return i

            return -1

        conj_pos = find_position(conjunction_item, rankings)
        comp_a_pos = find_position(component_a, rankings)
        comp_b_pos = find_position(component_b, rankings)

        # Determine if fallacy occurred
        # Fallacy = conjunction ranked higher (lower position number) than at least one component
        fallacy_detected = False
        fallacy_details = {}

        if conj_pos >= 0:
            if comp_a_pos >= 0 and conj_pos < comp_a_pos:
                fallacy_detected = True
                fallacy_details['conj_vs_a'] = f"Conjunction ({conj_pos+1}) ranked higher than component A ({comp_a_pos+1})"

            if comp_b_pos >= 0 and conj_pos < comp_b_pos:
                fallacy_detected = True
                fallacy_details['conj_vs_b'] = f"Conjunction ({conj_pos+1}) ranked higher than component B ({comp_b_pos+1})"

        # For Linda tests, detecting the fallacy means the model "failed" (fell for the trap)
        # So correct = True means model did NOT fall for the fallacy
        model_avoided_fallacy = not fallacy_detected

        if conj_pos < 0:
            match_type = 'conjunction_not_found'
        elif comp_a_pos < 0 and comp_b_pos < 0:
            match_type = 'components_not_found'
        elif fallacy_detected:
            match_type = 'fallacy_detected'
        else:
            match_type = 'no_fallacy'

        # Accuracy: 1.0 if avoided fallacy, 0.0 if fell for it
        accuracy = 1.0 if model_avoided_fallacy else 0.0

        return EvaluationResult(
            correct=model_avoided_fallacy,
            match_type=match_type,
            accuracy=accuracy,
            details={
                'fallacy_detected': fallacy_detected,
                'conjunction_position': conj_pos + 1 if conj_pos >= 0 else None,
                'component_a_position': comp_a_pos + 1 if comp_a_pos >= 0 else None,
                'component_b_position': comp_b_pos + 1 if comp_b_pos >= 0 else None,
                'num_rankings': len(rankings),
                'fallacy_details': fallacy_details,
                'parse_strategy': rankings_data.get('parse_strategy', 'unknown'),
            }
        )

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Aggregate multiple Linda Fallacy results.

        Args:
            results: List of EvaluationResult objects

        Returns:
            Dictionary with aggregated statistics
        """
        if not results:
            return {
                'accuracy': 0.0,
                'fallacy_rate': 0.0,
                'correct': 0,
                'total': 0,
                'error_count': 0,
                'match_types': {},
            }

        # Count results
        avoided_fallacy = sum(1 for r in results if r.correct)
        fell_for_fallacy = sum(1 for r in results if r.match_type == 'fallacy_detected')
        errors = sum(1 for r in results if r.error is not None)
        parse_errors = sum(1 for r in results if r.match_type == 'parse_error')

        # Fallacy rate (how often model falls for the trap)
        valid_results = [r for r in results if r.error is None and r.match_type not in ['parse_error', 'conjunction_not_found', 'components_not_found']]
        fallacy_rate = fell_for_fallacy / len(valid_results) if valid_results else 0.0

        # Success rate (avoiding fallacy)
        success_rate = avoided_fallacy / len(results) if results else 0.0

        match_types = self._count_match_types(results)

        return {
            'accuracy': success_rate,
            'success_rate': success_rate,
            'fallacy_rate': fallacy_rate,
            'correct': avoided_fallacy,
            'fell_for_fallacy': fell_for_fallacy,
            'total': len(results),
            'valid_results': len(valid_results),
            'error_count': errors,
            'parse_errors': parse_errors,
            'match_types': match_types,
        }
