"""
Object Tracking Result Evaluator

Evaluates object tracking predictions with support for:
- Case-insensitive comparison
- Location synonym matching
- Difficulty-based aggregation
"""

from typing import Any, Dict, List, Optional

from src.plugins.base import ResultEvaluator, EvaluationResult, ParsedAnswer


class ObjectTrackingResultEvaluator(ResultEvaluator):
    """
    Evaluator for object tracking predictions.

    Handles:
    - Case-insensitive comparison
    - Location synonym matching (countertop == counter)
    - Partial match detection
    - Aggregation with difficulty breakdown
    """

    def __init__(self):
        # Location equivalence groups
        self.equivalences = {
            'counter': ['counter', 'countertop', 'kitchen counter', 'worktop', 'benchtop', 'work surface'],
            'table': ['table', 'tabletop', 'dining table', 'kitchen table', 'coffee table'],
            'shelf': ['shelf', 'bookshelf', 'shelving', 'cupboard shelf'],
            'desk': ['desk', 'desktop', 'writing desk', 'work desk'],
            'microwave': ['microwave', 'microwave oven'],
            'refrigerator': ['refrigerator', 'fridge', 'icebox'],
            'oven': ['oven', 'stove'],
            'floor': ['floor', 'ground', 'flooring'],
            'sink': ['sink', 'basin'],
            'drawer': ['drawer'],
            'cabinet': ['cabinet', 'cupboard'],
            'dresser': ['dresser', 'bureau', 'chest of drawers'],
            'nightstand': ['nightstand', 'bedside table', 'night table'],
        }

        # Build reverse lookup: variant -> canonical
        self.canonical = {}
        for canonical_name, variants in self.equivalences.items():
            for variant in variants:
                self.canonical[variant.lower()] = canonical_name

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate parsed location against expected.

        Args:
            parsed_answer: ParsedAnswer from parser
            expected_answer: Expected location (can be None, will use task_params)
            task_params: Task parameters for context

        Returns:
            EvaluationResult with correctness and details
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
                    'object': task_params.get('object'),
                    'difficulty': task_params.get('difficulty'),
                },
                error=parsed_answer.error
            )

        predicted = parsed_answer.value
        expected = expected_answer or task_params.get('expected_answer')

        # Handle missing values
        if predicted is None:
            return EvaluationResult(
                correct=False,
                match_type='no_answer',
                accuracy=0.0,
                details={
                    'error': 'No location extracted',
                    'expected': expected,
                    'object': task_params.get('object'),
                    'difficulty': task_params.get('difficulty'),
                },
                error='No location extracted'
            )

        if expected is None:
            return EvaluationResult(
                correct=False,
                match_type='error',
                accuracy=0.0,
                details={'error': 'No expected answer provided'},
                error='No expected answer provided'
            )

        # Handle special case where expected is "container" (sticky object)
        if expected == 'container':
            # For sticky objects, the object stays in container
            # This shouldn't happen in normal tests, but handle it
            expected = task_params.get('initial_location', expected)

        # Normalize both answers
        predicted_str = str(predicted).lower().strip()
        expected_str = str(expected).lower().strip()

        predicted_canonical = self._canonicalize(predicted_str)
        expected_canonical = self._canonicalize(expected_str)

        # Check for matches (English canonical)
        is_exact = predicted_canonical == expected_canonical
        is_raw_match = predicted_str == expected_str

        # Check localized expected answer (multilingual support)
        expected_localized = task_params.get('expected_answer_localized', '')
        is_localized_match = False
        if expected_localized:
            exp_loc_str = str(expected_localized).lower().strip()
            is_localized_match = (
                predicted_str == exp_loc_str
                or predicted_str in exp_loc_str
                or exp_loc_str in predicted_str
            )

        is_correct = is_exact or is_raw_match or is_localized_match

        # Determine match type
        if is_localized_match and not is_exact and not is_raw_match:
            match_type = 'localized_match'
        elif is_exact and is_raw_match:
            match_type = 'exact'
        elif is_exact:
            match_type = 'synonym_match'
        elif is_raw_match:
            match_type = 'raw_match'
        elif self._is_partial_match(predicted_str, expected_str):
            match_type = 'partial'
            is_correct = False  # Partial matches are not correct
        else:
            match_type = 'mismatch'

        # Build details
        details = {
            'predicted': predicted,
            'predicted_canonical': predicted_canonical,
            'expected': expected,
            'expected_canonical': expected_canonical,
            'parse_strategy': parsed_answer.parse_strategy,
            'confidence': parsed_answer.confidence,
            'object': task_params.get('object'),
            'container': task_params.get('container'),
            'initial_location': task_params.get('initial_location'),
            'inversion_step_index': task_params.get('inversion_step_index'),
            'post_inversion_container_location': task_params.get('post_inversion_container_location'),
            'distractor_count': task_params.get('distractor_count', 0),
            'difficulty': task_params.get('difficulty'),
            'sticky_object': task_params.get('sticky_object', False),
        }

        return EvaluationResult(
            correct=is_correct,
            match_type=match_type,
            accuracy=1.0 if is_correct else 0.0,
            details=details
        )

    def _canonicalize(self, location: str) -> str:
        """Convert location to canonical form."""
        location = location.lower().strip()
        return self.canonical.get(location, location)

    def _is_partial_match(self, predicted: str, expected: str) -> bool:
        """Check for partial/substring match."""
        return predicted in expected or expected in predicted

    def _count_match_types(self, results: List[EvaluationResult]) -> Dict[str, int]:
        """Count occurrences of each match type."""
        counts = {}
        for r in results:
            match_type = r.match_type
            counts[match_type] = counts.get(match_type, 0) + 1
        return counts

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Aggregate object tracking results with breakdowns.

        Returns:
            Dictionary with:
            - accuracy: Overall accuracy
            - correct: Number correct
            - total: Total count
            - error_count: Number of errors
            - parse_errors: Number of parse errors
            - match_types: Breakdown by match type
            - difficulty_breakdown: Accuracy by difficulty level
            - distractor_breakdown: Accuracy by distractor count
        """
        if not results:
            return {
                'accuracy': 0.0,
                'correct': 0,
                'total': 0,
                'error_count': 0,
                'parse_errors': 0,
                'match_types': {},
                'difficulty_breakdown': {},
                'distractor_breakdown': {},
            }

        correct = sum(1 for r in results if r.correct)
        errors = sum(1 for r in results if r.error is not None)
        parse_errors = sum(1 for r in results if r.match_type == 'parse_error')

        # Breakdown by difficulty
        difficulty_stats = {}
        for r in results:
            diff = r.details.get('difficulty', 'unknown')
            if diff not in difficulty_stats:
                difficulty_stats[diff] = {'correct': 0, 'total': 0}
            difficulty_stats[diff]['total'] += 1
            if r.correct:
                difficulty_stats[diff]['correct'] += 1

        # Calculate accuracy per difficulty
        for diff, stats in difficulty_stats.items():
            if stats['total'] > 0:
                stats['accuracy'] = stats['correct'] / stats['total']
            else:
                stats['accuracy'] = 0.0

        # Breakdown by distractor count
        distractor_stats = {}
        for r in results:
            count = r.details.get('distractor_count', 0)
            if count not in distractor_stats:
                distractor_stats[count] = {'correct': 0, 'total': 0}
            distractor_stats[count]['total'] += 1
            if r.correct:
                distractor_stats[count]['correct'] += 1

        # Calculate accuracy per distractor count
        for count, stats in distractor_stats.items():
            if stats['total'] > 0:
                stats['accuracy'] = stats['correct'] / stats['total']
            else:
                stats['accuracy'] = 0.0

        # Breakdown by object type
        object_stats = {}
        for r in results:
            obj = r.details.get('object', 'unknown')
            if obj not in object_stats:
                object_stats[obj] = {'correct': 0, 'total': 0}
            object_stats[obj]['total'] += 1
            if r.correct:
                object_stats[obj]['correct'] += 1

        # Average accuracy per object
        for obj, stats in object_stats.items():
            if stats['total'] > 0:
                stats['accuracy'] = stats['correct'] / stats['total']
            else:
                stats['accuracy'] = 0.0

        return {
            'accuracy': correct / len(results),
            'success_rate': correct / len(results),
            'correct': correct,
            'total': len(results),
            'error_count': errors,
            'parse_errors': parse_errors,
            'match_types': self._count_match_types(results),
            'difficulty_breakdown': difficulty_stats,
            'distractor_breakdown': distractor_stats,
            'object_breakdown': object_stats,
        }
