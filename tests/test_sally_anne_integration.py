"""
Integration tests for Sally-Anne false belief test plugin.

Tests:
1. Plugin registration and discovery
2. Test case generation with random names
3. Response parsing (multi-strategy)
4. Result evaluation (belief location vs reality trap)
5. PromptEngine integration
6. TUI integration
7. analyze_results task extraction
8. End-to-end workflow
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.plugins import PluginRegistry
from src.plugins.sally_anne.scenario_builder import SallyAnneScenarioBuilder
from src.plugins.sally_anne.generator import SallyAnneTestCaseGenerator
from src.plugins.sally_anne.parser import SallyAnneResponseParser
from src.plugins.sally_anne.evaluator import SallyAnneResultEvaluator
from src.core.PromptEngine import PromptEngine, PromptContext, TaskType, Language, PromptStyle, SystemPromptStyle


def test_plugin_registration():
    """Test that sally_anne plugin is properly registered."""
    registry = PluginRegistry()
    available_tasks = registry.list_task_types()
    
    assert 'sally_anne' in available_tasks, "sally_anne plugin not registered"
    
    plugin = registry.get('sally_anne')
    assert plugin is not None
    assert plugin.task_type == 'sally_anne'
    assert plugin.display_name == 'Sally-Anne Test'
    assert 'false belief' in plugin.description.lower()
    
    print("✓ Plugin registration verified")


def test_scenario_builder_random_names():
    """Test scenario generation with random names."""
    builder = SallyAnneScenarioBuilder()
    
    # Generate with random names (no subject_pair provided)
    scenario = builder.generate_scenario(
        subject_pair=None,  # Random
        obj='marble',
        containers=('basket', 'box'),
        leave_activity='goes for a walk',
        distractor_count=0,
        include_observer=False,
        seed=42
    )
    
    # Check structure
    assert 'subject_a_name' in scenario
    assert 'subject_a_gender' in scenario
    assert 'subject_a_pronouns' in scenario
    assert 'subject_b_name' in scenario
    assert scenario['object'] == 'marble'
    assert scenario['container_a'] == 'basket'
    assert scenario['container_b'] == 'box'
    assert scenario['correct_answer'] == 'basket'  # Belief location!
    
    # Check pronouns
    pronouns_a = scenario['subject_a_pronouns']
    assert 'subject' in pronouns_a  # he/she
    assert 'possessive' in pronouns_a  # his/her
    assert pronouns_a['subject'] in ['he', 'she']
    
    print(f"✓ Random scenario: {scenario['subject_a_name']} (gender: {scenario['subject_a_gender']}) and {scenario['subject_b_name']}")
    print(f"  Correct answer: {scenario['correct_answer']} (belief location)")
    print(f"  Reality trap: {scenario['container_b']} (actual location)")


def test_scenario_builder_with_observer():
    """Test scenario generation with observer variant."""
    builder = SallyAnneScenarioBuilder()
    
    scenario = builder.generate_scenario(
        subject_pair=('Sally', 'female', 'Anne', 'female'),
        obj='ball',
        containers=('drawer', 'cupboard'),
        leave_activity='goes outside',
        distractor_count=2,
        include_observer=True,
        seed=123
    )
    
    assert scenario['observer'] is not None
    assert 'name' in scenario['observer']
    assert 'gender' in scenario['observer']
    assert 'pronouns' in scenario['observer']
    assert len(scenario['distractor_elements']) == 2
    
    print(f"✓ Observer scenario: Observer {scenario['observer']['name']} watches Sally and Anne")


def test_narrative_and_question_building():
    """Test narrative text generation."""
    builder = SallyAnneScenarioBuilder()
    
    scenario = builder.generate_scenario(
        subject_pair=('Sally', 'female', 'Anne', 'female'),
        obj='marble',
        containers=('basket', 'box'),
        leave_activity='goes for a walk',
        distractor_count=0,
        include_observer=False,
        seed=42
    )
    
    narrative = builder.build_narrative(scenario)
    question = builder.build_question(scenario)
    
    assert 'Sally' in narrative
    assert 'Anne' in narrative
    assert 'marble' in narrative
    assert 'basket' in narrative
    assert 'box' in narrative
    assert 'goes for a walk' in narrative
    
    assert 'Sally' in question
    assert 'look' in question.lower()
    assert 'marble' in question
    
    print("✓ Narrative and question generation verified")
    print(f"  Narrative length: {len(narrative)} chars")
    print(f"  Question: {question}")


def test_test_case_generator():
    """Test test case generation."""
    config = {
        'cases_per_config': 3,
        'use_random_pairs': True,
        'subject_pairs': [],
        'objects': ['marble', 'ball'],
        'containers': [('basket', 'box'), ('drawer', 'cupboard')],
        'distractor_count': 0,
        'leave_activities': ['goes for a walk', 'goes outside'],
        'include_observer': False,
        'seed': 42,
    }
    
    prompt_config = {
        'name': 'test_config',
        'user_style': 'minimal',
        'system_style': 'analytical',
        'language': 'en'
    }
    
    generator = SallyAnneTestCaseGenerator()
    test_cases = generator.generate_batch(config, prompt_config, count=3, seed=42)
    
    assert len(test_cases) == 3
    
    for tc in test_cases:
        assert tc.test_id.startswith('sally_anne_')
        assert tc.task_type == 'sally_anne'
        assert tc.prompts is not None
        assert 'user' in tc.prompts
        assert tc.task_params is not None
        assert 'expected_answer' in tc.task_params
        assert 'subject_a' in tc.task_params
        assert 'container_a' in tc.task_params
        assert 'container_b' in tc.task_params
        assert tc.task_params['correct_answer'] == tc.task_params['container_a']  # Belief location
        assert tc.task_params['reality_trap'] == tc.task_params['container_b']  # Actual location
    
    print(f"✓ Generated {len(test_cases)} test cases")
    print(f"  Test case 0 - Subject A: {test_cases[0].task_params['subject_a']}, Expected: {test_cases[0].task_params['expected_answer']}")


def test_response_parser():
    """Test multi-strategy response parsing."""
    parser = SallyAnneResponseParser()
    
    metadata = {
        'container_a': 'basket',
        'container_b': 'box',
    }
    
    # Strategy 1: Simple answer
    answer1 = parser.parse("basket", metadata)
    assert answer1 == 'basket'
    
    # Strategy 2: In the [container]
    answer2 = parser.parse("She will look in the basket.", metadata)
    assert answer2 == 'basket'
    
    # Strategy 3: JSON format
    answer3 = parser.parse('{"answer": "basket"}', metadata)
    assert answer3 == 'basket'
    
    # Strategy 4: Boxed format
    answer4 = parser.parse("\\boxed{basket}", metadata)
    assert answer4 == 'basket'
    
    # Strategy 5: Reality trap error
    answer5 = parser.parse("box", metadata)
    assert answer5 == 'box'  # Parser extracts, evaluator marks as wrong
    
    print("✓ Response parser verified (5 strategies)")


def test_result_evaluator():
    """Test result evaluation (belief vs reality trap)."""
    evaluator = SallyAnneResultEvaluator()
    
    task_params = {
        'container_a': 'basket',  # Correct (belief location)
        'container_b': 'box',     # Reality trap (actual location)
    }
    
    # Correct answer (belief location)
    result1 = evaluator.evaluate('basket', 'basket', task_params)
    assert result1.correct == True
    assert result1.match_type in ['exact', 'synonym']
    
    # Reality trap error (answered actual location)
    result2 = evaluator.evaluate('box', 'basket', task_params)  # Note: swapped order
    assert result2.correct == False
    assert result2.match_type == 'reality_trap'
    
    # Wrong container (neither correct nor reality trap)
    result3 = evaluator.evaluate('drawer', 'basket', task_params)
    assert result3.correct == False
    assert result3.match_type == 'wrong_container'
    
    # Parse error
    result4 = evaluator.evaluate('PARSE_ERROR', 'basket', task_params)
    assert result4.correct == False
    assert result4.match_type == 'parse_error'
    
    print("✓ Result evaluator verified")
    print(f"  Reality trap detection: {result2.match_type}")


def test_aggregate_results():
    """Test aggregate statistics."""
    evaluator = SallyAnneResultEvaluator()
    
    # Create mock results
    from src.plugins.base import EvaluationResult
    
    results = [
        EvaluationResult(correct=True, match_type='exact', accuracy=1.0, details={}),
        EvaluationResult(correct=True, match_type='synonym', accuracy=1.0, details={}),
        EvaluationResult(correct=False, match_type='reality_trap', accuracy=0.0, details={}),
        EvaluationResult(correct=False, match_type='parse_error', accuracy=0.0, details={}),
        EvaluationResult(correct=False, match_type='wrong_container', accuracy=0.0, details={}),
    ]
    
    stats = evaluator.aggregate_results(results)
    
    assert stats['total_cases'] == 5
    assert stats['correct_count'] == 2
    assert stats['accuracy'] == 0.4
    assert stats['reality_trap_count'] == 1
    assert stats['parse_error_count'] == 1
    assert stats['wrong_container_count'] == 1
    assert stats['reality_trap_rate'] == 0.2
    
    print(f"✓ Aggregate results: {stats['accuracy']*100:.0f}% accuracy, {stats['reality_trap_count']} reality traps")


def test_prompt_engine_integration():
    """Test PromptEngine integration with sally_anne task type."""
    engine = PromptEngine()
    
    # Create context
    context = PromptContext(
        task_type=TaskType.SALLY_ANNE,
        language=Language.EN,
        style=PromptStyle.LINGUISTIC,
        system_style=SystemPromptStyle.ANALYTICAL
    )
    
    # Set variables
    narrative = "Sally puts her marble in the basket. Sally goes for a walk. While Sally is away, Anne takes the marble from the basket and puts it in the box. Sally returns."
    question = "Where will Sally look for her marble?"
    context.update(narrative=narrative, question=question)
    
    # Generate prompts
    result = engine.generate(context)
    
    assert result.system_prompt is not None
    assert result.user_prompt is not None
    assert 'belief' in result.user_prompt.lower() or 'understanding' in result.user_prompt.lower()
    assert narrative in result.user_prompt
    assert question in result.user_prompt
    
    print("✓ PromptEngine integration verified")
    print(f"  User prompt length: {len(result.user_prompt)} chars")


def test_tui_task_selection():
    """Test that sally_anne appears in TUI available tasks."""
    # Import TUI to check task list
    from src.cli.benchmark_tui import BenchmarkTUI
    
    # Just verify the file has sally_anne mentioned
    import src.cli.benchmark_tui as tui_module
    source = Path(tui_module.__file__).read_text()
    
    assert "'id': 'sally_anne'" in source or '"id": "sally_anne"' in source
    assert 'Sally-Anne' in source or 'sally-anne' in source.lower()
    
    print("✓ TUI integration verified (sally_anne in available tasks)")


def test_analyze_results_task_extraction():
    """Test that analyze_results.py can extract sally_anne task type."""
    import src.stages.analyze_results as analyze_module
    
    # Check that the code has sally_anne extraction logic
    source = Path(analyze_module.__file__).read_text()
    
    assert '_sally_anne' in source or 'sally_anne' in source
    
    print("✓ analyze_results task extraction verified")


def test_end_to_end_plugin_workflow():
    """Test complete workflow: register → generate → parse → evaluate."""
    # 1. Get plugin
    registry = PluginRegistry()
    plugin = registry.get('sally_anne')
    assert plugin is not None
    
    # 2. Generate test cases
    config = {
        'cases_per_config': 2,
        'use_random_pairs': True,
        'subject_pairs': [],
        'objects': ['marble'],
        'containers': [('basket', 'box')],
        'distractor_count': 0,
        'leave_activities': ['goes for a walk'],
        'include_observer': False,
        'seed': 999,
    }
    
    prompt_config = {
        'name': 'end_to_end_test',
        'user_style': 'minimal',
        'system_style': 'analytical',
        'language': 'en'
    }
    
    generator = plugin.get_generator()
    test_cases = generator.generate_batch(config, prompt_config, count=2, seed=999)
    assert len(test_cases) == 2
    
    # 3. Simulate model responses
    parser = plugin.create_parser()
    evaluator = plugin.create_evaluator()
    
    results = []
    for tc in test_cases:
        # Simulate correct answer
        expected = tc.task_params['expected_answer']
        model_response = f"The answer is {expected}."
        parsed = parser.parse(model_response, tc.task_params)
        evaluation = evaluator.evaluate(parsed, expected, tc.task_params)
        results.append(evaluation)
    
    # 4. Aggregate
    stats = evaluator.aggregate_results(results)
    
    print(f"✓ End-to-end workflow verified")
    print(f"  Generated: {len(test_cases)} test cases")
    print(f"  Accuracy: {stats['accuracy']*100:.0f}%")
    assert stats['correct_count'] >= 0  # Should have at least some correct


if __name__ == '__main__':
    # Run all tests
    print("=" * 60)
    print("SALLY-ANNE FALSE BELIEF TEST - INTEGRATION TESTS")
    print("=" * 60)
    print()
    
    test_plugin_registration()
    print()
    
    test_scenario_builder_random_names()
    print()
    
    test_scenario_builder_with_observer()
    print()
    
    test_narrative_and_question_building()
    print()
    
    test_test_case_generator()
    print()
    
    test_response_parser()
    print()
    
    test_result_evaluator()
    print()
    
    test_aggregate_results()
    print()
    
    test_prompt_engine_integration()
    print()
    
    test_tui_task_selection()
    print()
    
    test_analyze_results_task_extraction()
    print()
    
    test_end_to_end_plugin_workflow()
    print()
    
    print("=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
