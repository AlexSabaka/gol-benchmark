"""
Unit tests for the Object Tracking (Grape Test) plugin.
"""

import pytest
from src.plugins.object_tracking.step_builder import StepBuilder, ScenarioStep, Scenario
from src.plugins.object_tracking.generator import ObjectTrackingTestCaseGenerator
from src.plugins.object_tracking.parser import ObjectTrackingResponseParser
from src.plugins.object_tracking.evaluator import ObjectTrackingResultEvaluator
from src.plugins.base import TestCase, ParsedAnswer


class TestStepBuilder:
    """Test the StepBuilder scenario generator."""

    def test_build_scenario_basic(self):
        """Test basic scenario generation."""
        builder = StepBuilder(seed=42)

        scenario = builder.build_scenario(
            obj='grape',
            container='cup',
            subject='I',
            initial_location='counter',
            pre_inversion_distractors=0,
            post_inversion_distractors=0,
            post_inversion_moves=0
        )

        assert scenario.object == 'grape'
        assert scenario.container == 'cup'
        assert scenario.subject == 'I'
        assert scenario.initial_location == 'counter'
        assert len(scenario.steps) >= 2  # At least placement + inversion
        assert scenario.final_object_location == 'counter'  # Falls to counter

    def test_placement_step_first(self):
        """Verify placement is always first step."""
        builder = StepBuilder(seed=42)

        scenario = builder.build_scenario(
            obj='marble',
            container='bowl',
            subject='you',
            initial_location='table'
        )

        first_step = scenario.steps[0]
        assert first_step.step_number == 1
        assert first_step.action_type == 'place'
        assert 'marble' in first_step.description.lower()
        assert 'bowl' in first_step.description.lower()
        assert 'table' in first_step.description.lower()

    def test_inversion_step_present(self):
        """Verify inversion step is present."""
        builder = StepBuilder(seed=42)

        scenario = builder.build_scenario(
            obj='keys',
            container='mug',
            subject='I',
            initial_location='desk'
        )

        inversion_steps = [s for s in scenario.steps if s.action_type == 'invert']
        assert len(inversion_steps) == 1

        inv_step = inversion_steps[0]
        assert 'mug' in inv_step.description.lower()
        assert any(word in inv_step.description.lower()
                   for word in ['upside down', 'flip', 'invert', 'tip', 'turn'])

    def test_object_location_after_inversion(self):
        """Verify object location tracking after inversion."""
        builder = StepBuilder(seed=42)

        scenario = builder.build_scenario(
            obj='coin',
            container='cup',
            subject='I',
            initial_location='shelf',
            post_inversion_moves=2  # Move container twice after inversion
        )

        # Find inversion step
        inv_index = scenario.inversion_step_index

        # Before inversion, object is in container
        for step in scenario.steps[:inv_index]:
            assert step.object_location_after in ['container', 'shelf']

        # After inversion, object stays at shelf even if container moves
        for step in scenario.steps[inv_index:]:
            assert step.object_location_after == 'shelf'

        # Container moved to new location, but object stays
        assert scenario.post_inversion_container_location != 'shelf'
        assert scenario.final_object_location == 'shelf'

    def test_distractors(self):
        """Verify distractor steps are added."""
        builder = StepBuilder(seed=42)

        scenario = builder.build_scenario(
            obj='grape',
            container='cup',
            subject='I',
            initial_location='counter',
            pre_inversion_distractors=2,
            post_inversion_distractors=2,
            distractor_types=['irrelevant', 'spatial', 'temporal']
        )

        distractor_steps = [s for s in scenario.steps if s.action_type == 'distractor']
        assert len(distractor_steps) == 4

        # Distractors shouldn't affect object location
        for step in distractor_steps:
            assert step.affects_object is False

    def test_sticky_object(self):
        """Test that sticky objects don't fall on inversion."""
        builder = StepBuilder(seed=42)

        scenario = builder.build_scenario(
            obj='honey',
            container='jar',
            subject='I',
            initial_location='counter',
            is_sticky=True
        )

        # Object stays in container even after inversion
        assert scenario.final_object_location == 'container'
        assert scenario.is_sticky is True

    def test_seed_reproducibility(self):
        """Test that same seed produces same scenarios."""
        builder1 = StepBuilder(seed=42)
        builder2 = StepBuilder(seed=42)

        scenario1 = builder1.build_scenario(
            obj='grape',
            container='cup',
            subject='I',
            initial_location='counter',
            pre_inversion_distractors=1,
            post_inversion_moves=1
        )

        scenario2 = builder2.build_scenario(
            obj='grape',
            container='cup',
            subject='I',
            initial_location='counter',
            pre_inversion_distractors=1,
            post_inversion_moves=1
        )

        assert len(scenario1.steps) == len(scenario2.steps)
        for s1, s2 in zip(scenario1.steps, scenario2.steps):
            assert s1.description == s2.description

    def test_format_steps_narrative(self):
        """Test narrative formatting."""
        builder = StepBuilder(seed=42)

        scenario = builder.build_scenario(
            obj='grape',
            container='cup',
            subject='I',
            initial_location='counter'
        )

        narrative = builder.format_steps_narrative(scenario.steps)
        assert isinstance(narrative, str)
        assert 'grape' in narrative.lower()
        assert 'cup' in narrative.lower()

    def test_format_steps_numbered(self):
        """Test numbered list formatting."""
        builder = StepBuilder(seed=42)

        scenario = builder.build_scenario(
            obj='grape',
            container='cup',
            subject='I',
            initial_location='counter'
        )

        numbered = builder.format_steps_numbered(scenario.steps)
        assert '1.' in numbered
        assert '2.' in numbered


class TestObjectTrackingGenerator:
    """Test the test case generator."""

    def test_generate_batch_basic(self):
        """Test basic batch generation."""
        generator = ObjectTrackingTestCaseGenerator()

        config = {
            'object': ['grape', 'marble'],
            'container': ['cup', 'bowl'],
            'location_initial': ['counter', 'table'],
            'distractor_count': [0, 1],
        }
        prompt_config = {
            'language': 'en',
            'user_style': 'casual',
            'system_style': 'none',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(
            config=config,
            prompt_config=prompt_config,
            count=5,
            seed=42
        )

        assert len(test_cases) == 5
        assert all(isinstance(tc, TestCase) for tc in test_cases)
        assert all(tc.task_type == 'object_tracking' for tc in test_cases)

    def test_generate_with_seed_reproducibility(self):
        """Test that same seed produces same test cases."""
        generator = ObjectTrackingTestCaseGenerator()

        config = generator.get_default_config()
        prompt_config = {
            'language': 'en',
            'user_style': 'casual',
            'system_style': 'none',
            'name': 'test_config'
        }

        tests1 = generator.generate_batch(config, prompt_config, 5, seed=42)
        tests2 = generator.generate_batch(config, prompt_config, 5, seed=42)

        for t1, t2 in zip(tests1, tests2):
            assert t1.task_params['object'] == t2.task_params['object']
            assert t1.task_params['expected_answer'] == t2.task_params['expected_answer']

    def test_task_params_structure(self):
        """Test that task_params has required fields."""
        generator = ObjectTrackingTestCaseGenerator()

        config = generator.get_default_config()
        prompt_config = {
            'language': 'en',
            'user_style': 'casual',
            'system_style': 'none',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 1, seed=42)
        tc = test_cases[0]

        # Check required fields
        assert 'object' in tc.task_params
        assert 'container' in tc.task_params
        assert 'initial_location' in tc.task_params
        assert 'steps' in tc.task_params
        assert 'inversion_step_index' in tc.task_params
        assert 'expected_answer' in tc.task_params
        assert 'difficulty' in tc.task_params

    def test_prompt_styles(self):
        """Test different prompt styles generate different prompts."""
        generator = ObjectTrackingTestCaseGenerator()

        config = generator.get_default_config()

        casual_config = {'user_style': 'casual', 'system_style': 'none', 'name': 'casual'}
        linguistic_config = {'user_style': 'linguistic', 'system_style': 'analytical', 'name': 'linguistic'}

        casual_tests = generator.generate_batch(config, casual_config, 1, seed=42)
        linguistic_tests = generator.generate_batch(config, linguistic_config, 1, seed=42)

        # Prompts should be different
        assert casual_tests[0].prompts['user'] != linguistic_tests[0].prompts['user']


class TestObjectTrackingParser:
    """Test the response parser."""

    def test_parse_single_word(self):
        """Test single word response parsing."""
        parser = ObjectTrackingResponseParser()

        response = "counter"
        task_params = {'expected_answer': 'counter'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == 'counter'
        assert result.parse_strategy == 'single_word'

    def test_parse_single_word_with_punctuation(self):
        """Test single word with punctuation."""
        parser = ObjectTrackingResponseParser()

        response = "Counter."
        task_params = {'expected_answer': 'counter'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == 'counter'

    def test_parse_answer_prefix(self):
        """Test 'Answer: location' pattern."""
        parser = ObjectTrackingResponseParser()

        response = "The answer is counter"
        task_params = {'expected_answer': 'counter'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == 'counter'
        assert result.parse_strategy == 'answer_prefix'

    def test_parse_sentence_pattern(self):
        """Test 'The grape is on the counter' pattern."""
        parser = ObjectTrackingResponseParser()

        response = "The grape is on the counter."
        task_params = {'object': 'grape', 'expected_answer': 'counter'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == 'counter'
        assert result.parse_strategy == 'sentence_pattern'

    def test_parse_location_keyword(self):
        """Test known location extraction."""
        parser = ObjectTrackingResponseParser()

        response = "Based on my analysis, the grape would be on the counter because..."
        task_params = {
            'object': 'grape',
            'expected_answer': 'counter',
            'initial_location': 'counter'
        }

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == 'counter'

    def test_parse_location_normalization(self):
        """Test countertop -> counter normalization."""
        parser = ObjectTrackingResponseParser()

        response = "countertop"
        task_params = {'expected_answer': 'counter'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == 'counter'  # Normalized

    def test_parse_empty_response(self):
        """Test handling of empty response."""
        parser = ObjectTrackingResponseParser()

        response = ""
        task_params = {'expected_answer': 'counter'}

        result = parser.parse(response, task_params)

        assert not result.success
        assert result.value is None
        assert result.error == 'Empty response'

    def test_parse_last_word_fallback(self):
        """Test last word extraction as fallback."""
        parser = ObjectTrackingResponseParser()

        response = "Therefore, the answer must be table"
        task_params = {'expected_answer': 'table'}

        result = parser.parse(response, task_params)

        assert result.success
        assert result.value == 'table'


class TestObjectTrackingEvaluator:
    """Test the result evaluator."""

    def test_evaluate_exact_match(self):
        """Test exact location match."""
        evaluator = ObjectTrackingResultEvaluator()

        parsed_answer = ParsedAnswer(
            value='counter',
            raw_response='counter',
            parse_strategy='single_word'
        )

        expected_answer = 'counter'
        task_params = {
            'expected_answer': 'counter',
            'object': 'grape',
            'difficulty': 'easy'
        }

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert result.correct
        assert result.match_type == 'exact'
        assert result.accuracy == 1.0

    def test_evaluate_synonym_match(self):
        """Test synonym matching (countertop == counter)."""
        evaluator = ObjectTrackingResultEvaluator()

        parsed_answer = ParsedAnswer(
            value='countertop',
            raw_response='countertop',
            parse_strategy='single_word'
        )

        expected_answer = 'counter'
        task_params = {
            'expected_answer': 'counter',
            'object': 'grape',
            'difficulty': 'easy'
        }

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert result.correct
        assert result.match_type == 'synonym_match'
        assert result.accuracy == 1.0

    def test_evaluate_case_insensitive(self):
        """Test case-insensitive comparison."""
        evaluator = ObjectTrackingResultEvaluator()

        parsed_answer = ParsedAnswer(
            value='COUNTER',
            raw_response='COUNTER',
            parse_strategy='single_word'
        )

        expected_answer = 'counter'
        task_params = {'expected_answer': 'counter'}

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert result.correct

    def test_evaluate_mismatch(self):
        """Test incorrect location detection."""
        evaluator = ObjectTrackingResultEvaluator()

        parsed_answer = ParsedAnswer(
            value='microwave',  # Wrong - object is on counter
            raw_response='microwave',
            parse_strategy='single_word'
        )

        expected_answer = 'counter'
        task_params = {
            'expected_answer': 'counter',
            'object': 'grape',
            'difficulty': 'medium'
        }

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert not result.correct
        assert result.match_type == 'mismatch'
        assert result.accuracy == 0.0

    def test_evaluate_parse_error(self):
        """Test evaluation with parse error."""
        evaluator = ObjectTrackingResultEvaluator()

        parsed_answer = ParsedAnswer(
            value=None,
            raw_response='I dont know',
            parse_strategy='failed',
            error='Could not parse location'
        )

        expected_answer = 'counter'
        task_params = {'expected_answer': 'counter'}

        result = evaluator.evaluate(parsed_answer, expected_answer, task_params)

        assert not result.correct
        assert result.match_type == 'parse_error'

    def test_evaluate_aggregation(self):
        """Test result aggregation with difficulty breakdown."""
        evaluator = ObjectTrackingResultEvaluator()

        results = [
            evaluator.evaluate(
                ParsedAnswer('counter', '', 'test'),
                'counter',
                {'expected_answer': 'counter', 'difficulty': 'easy', 'distractor_count': 0, 'object': 'grape'}
            ),
            evaluator.evaluate(
                ParsedAnswer('counter', '', 'test'),
                'counter',
                {'expected_answer': 'counter', 'difficulty': 'medium', 'distractor_count': 1, 'object': 'grape'}
            ),
            evaluator.evaluate(
                ParsedAnswer('microwave', '', 'test'),  # Wrong
                'counter',
                {'expected_answer': 'counter', 'difficulty': 'hard', 'distractor_count': 2, 'object': 'marble'}
            ),
        ]

        aggregated = evaluator.aggregate_results(results)

        assert aggregated['total'] == 3
        assert aggregated['correct'] == 2
        assert aggregated['accuracy'] == pytest.approx(0.667, rel=0.01)
        assert 'difficulty_breakdown' in aggregated
        assert 'distractor_breakdown' in aggregated
        assert 'object_breakdown' in aggregated


class TestObjectTrackingRoundtrip:
    """Test full roundtrip: generate -> parse -> evaluate."""

    def test_roundtrip_correct_answer(self):
        """Test complete pipeline with correct answer."""
        generator = ObjectTrackingTestCaseGenerator()
        parser = ObjectTrackingResponseParser()
        evaluator = ObjectTrackingResultEvaluator()

        # Generate test case
        config = generator.get_default_config()
        prompt_config = {
            'language': 'en',
            'user_style': 'casual',
            'system_style': 'none',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 1, seed=42)
        test_case = test_cases[0]

        # Simulate correct model response
        expected_answer = test_case.task_params['expected_answer']
        simulated_response = expected_answer

        # Parse response
        parsed = parser.parse(simulated_response, test_case.task_params)
        assert parsed.success

        # Evaluate
        result = evaluator.evaluate(
            parsed,
            expected_answer,
            test_case.task_params
        )

        assert result.correct
        assert result.accuracy == 1.0

    def test_roundtrip_wrong_answer(self):
        """Test pipeline with incorrect answer (common mistake)."""
        generator = ObjectTrackingTestCaseGenerator()
        parser = ObjectTrackingResponseParser()
        evaluator = ObjectTrackingResultEvaluator()

        # Generate test case
        config = {
            'object': ['grape'],
            'container': ['cup'],
            'location_initial': ['counter'],
            'post_inversion_moves': [1],  # Container moves after inversion
            'distractor_count': [0],
        }
        prompt_config = {
            'language': 'en',
            'user_style': 'casual',
            'system_style': 'none',
            'name': 'test_config'
        }

        test_cases = generator.generate_batch(config, prompt_config, 1, seed=42)
        test_case = test_cases[0]

        # Simulate wrong answer: model answers where container is, not object
        wrong_answer = test_case.task_params['post_inversion_container_location']
        expected_answer = test_case.task_params['expected_answer']

        # Should be different (container moved, object stayed)
        if wrong_answer != expected_answer:
            simulated_response = wrong_answer

            # Parse response
            parsed = parser.parse(simulated_response, test_case.task_params)
            assert parsed.success

            # Evaluate
            result = evaluator.evaluate(
                parsed,
                expected_answer,
                test_case.task_params
            )

            assert not result.correct
            assert result.match_type == 'mismatch'

    def test_inversion_logic_verification(self):
        """Verify the core object tracking logic is correct."""
        generator = ObjectTrackingTestCaseGenerator()

        config = {
            'object': ['grape'],
            'container': ['cup'],
            'location_initial': ['counter'],
            'post_inversion_moves': [2],  # Move container to 2 different places
            'distractor_count': [1],
        }
        prompt_config = {
            'language': 'en',
            'user_style': 'casual',
            'system_style': 'none',
            'name': 'test'
        }

        test_cases = generator.generate_batch(config, prompt_config, 1, seed=42)
        tc = test_cases[0]

        # Object should be at initial location (counter)
        assert tc.task_params['expected_answer'] == 'counter'

        # Container should have moved elsewhere
        assert tc.task_params['post_inversion_container_location'] != 'counter'

        # Check step-by-step tracking
        steps = tc.task_params['steps']
        inv_idx = tc.task_params['inversion_step_index']

        # Before inversion: object in container
        for i, step in enumerate(steps):
            if i < inv_idx:
                assert step['object_location_after'] == 'container'

        # At and after inversion: object at counter
        for i, step in enumerate(steps):
            if i >= inv_idx:
                assert step['object_location_after'] == 'counter'
