"""
Integration tests for grid_tasks plugin.

Tests plugin discovery, generation, parsing, and evaluation.
"""

import json
from pathlib import Path

import pytest

# Test fixtures
SAMPLE_RESPONSES = {
    'boxed': r'The answer is \boxed{42}',
    'bold': 'The answer is **Alice Smith**',
    'answer_pattern': 'Answer: 1500.50',
    'json': '{"answer": "Engineering"}',
    'code_block': '```\n95\n```',
    'quoted': 'The value is "New York"',
    'last_line': 'Based on the table, the result is:\n125.75',
    'first_number': 'Looking at the data, we can see 42 items match the criteria.',
}


def test_plugin_registration():
    """Test that grid_tasks plugin is properly registered."""
    from src.plugins import PluginRegistry
    
    registry = PluginRegistry()
    task_types = registry.list_task_types()
    
    assert 'grid_tasks' in task_types, "grid_tasks not found in registered plugins"
    
    plugin = registry.get('grid_tasks')
    assert plugin is not None
    assert plugin.task_type == 'grid_tasks'
    assert plugin.display_name == 'Grid Tasks (Table Reasoning)'
    assert 'table' in plugin.description.lower()


def test_plugin_components():
    """Test that plugin provides all required components."""
    from src.plugins import PluginRegistry
    
    registry = PluginRegistry()
    plugin = registry.get('grid_tasks')
    
    # Test generator
    generator = plugin.get_generator()
    assert generator is not None
    assert hasattr(generator, 'generate_batch')
    assert hasattr(generator, 'get_default_config')
    
    # Test parser
    parser = plugin.get_parser()
    assert parser is not None
    assert hasattr(parser, 'parse')
    assert hasattr(parser, 'get_strategies')
    
    # Test evaluator
    evaluator = plugin.get_evaluator()
    assert evaluator is not None
    assert hasattr(evaluator, 'evaluate')
    assert hasattr(evaluator, 'aggregate_results')


def test_generator_default_config():
    """Test generator default configuration."""
    from src.plugins.grid_tasks.generator import GridTasksTestCaseGenerator
    
    generator = GridTasksTestCaseGenerator()
    config = generator.get_default_config()
    
    assert 'min_rows' in config
    assert 'max_rows' in config
    assert 'min_cols' in config
    assert 'max_cols' in config
    assert 'data_types' in config
    assert 'question_types' in config
    assert 'table_style' in config
    assert 'cases_per_config' in config
    
    assert config['min_rows'] >= 1
    assert config['max_rows'] >= config['min_rows']
    assert config['min_cols'] >= 1
    assert config['max_cols'] >= config['min_cols']
    assert len(config['data_types']) > 0
    assert len(config['question_types']) > 0


def test_generator_generates_test_cases():
    """Test that generator creates valid test cases."""
    from src.plugins.grid_tasks.generator import GridTasksTestCaseGenerator
    
    generator = GridTasksTestCaseGenerator()
    
    config = {
        'min_rows': 3,
        'max_rows': 5,
        'min_cols': 2,
        'max_cols': 4,
        'data_types': ['sales', 'hr'],
        'question_types': ['cell_lookup', 'row_sum'],
        'table_style': 'unicode',
    }
    
    prompt_config = {
        'name': 'test_config',
        'user_style': 'minimal',
        'system_style': 'analytical',
        'language': 'en',
    }
    
    test_cases = generator.generate_batch(config, prompt_config, count=5, seed=42)
    
    assert len(test_cases) == 5
    
    for tc in test_cases:
        assert tc.task_type == 'grid_tasks'
        assert tc.config_name == 'test_config'
        assert 'system' in tc.prompts
        assert 'user' in tc.prompts
        assert 'expected_answer' in tc.task_params
        assert 'question' in tc.task_params
        assert 'data_type' in tc.task_params
        assert 'question_type' in tc.task_params
        
        # Check that table is in user prompt
        assert '╔' in tc.prompts['user'] or '|' in tc.prompts['user'] or '+' in tc.prompts['user']
        assert 'Question:' in tc.prompts['user']


def test_generator_all_data_types():
    """Test generator with all data types."""
    from src.plugins.grid_tasks.generator import GridTasksTestCaseGenerator
    
    generator = GridTasksTestCaseGenerator()
    data_types = ['sales', 'hr', 'grades', 'inventory']
    
    for data_type in data_types:
        config = {
            'min_rows': 3,
            'max_rows': 3,
            'min_cols': 3,
            'max_cols': 3,
            'data_types': [data_type],
            'question_types': ['cell_lookup'],
            'table_style': 'unicode',
        }
        
        prompt_config = {'name': f'{data_type}_test', 'user_style': 'minimal', 'system_style': 'analytical'}
        
        test_cases = generator.generate_batch(config, prompt_config, count=1, seed=42)
        assert len(test_cases) == 1
        assert test_cases[0].task_params['data_type'] == data_type


def test_generator_all_question_types():
    """Test generator with all question types."""
    from src.plugins.grid_tasks.generator import GridTasksTestCaseGenerator
    
    generator = GridTasksTestCaseGenerator()
    question_types = ['cell_lookup', 'row_sum', 'column_count', 'filter_count', 'max_min']
    
    for question_type in question_types:
        config = {
            'min_rows': 4,
            'max_rows': 4,
            'min_cols': 3,
            'max_cols': 3,
            'data_types': ['sales'],
            'question_types': [question_type],
            'table_style': 'mysql',
        }
        
        prompt_config = {'name': f'{question_type}_test', 'user_style': 'casual', 'system_style': 'analytical'}
        
        test_cases = generator.generate_batch(config, prompt_config, count=1, seed=123)
        assert len(test_cases) == 1
        assert test_cases[0].task_params['question_type'] == question_type


def test_parser_strategies():
    """Test all parser strategies."""
    from src.plugins.grid_tasks.parser import GridTasksResponseParser
    
    parser = GridTasksResponseParser()
    strategies = parser.get_strategies()
    
    assert len(strategies) >= 6  # Should have at least 6 strategies
    assert 'boxed_latex' in strategies
    assert 'bold_markdown' in strategies
    assert 'answer_pattern' in strategies
    
    # Test each sample response
    for strategy_hint, response in SAMPLE_RESPONSES.items():
        parsed = parser.parse(response, {})
        assert parsed.success, f"Failed to parse {strategy_hint}: {response}"
        assert parsed.value is not None
        assert parsed.confidence > 0


def test_parser_boxed_latex():
    """Test LaTeX boxed notation parsing."""
    from src.plugins.grid_tasks.parser import GridTasksResponseParser
    
    parser = GridTasksResponseParser()
    response = r'Based on the table, \boxed{42.50}'
    
    parsed = parser.parse(response, {})
    assert parsed.success
    assert parsed.value == '42.50'
    assert parsed.parse_strategy == 'boxed_latex'
    assert parsed.confidence == 1.0


def test_parser_bold_markdown():
    """Test bold markdown parsing."""
    from src.plugins.grid_tasks.parser import GridTasksResponseParser
    
    parser = GridTasksResponseParser()
    response = 'The employee is **John Doe** with salary **75000**'
    
    parsed = parser.parse(response, {})
    assert parsed.success
    assert '75000' in parsed.value or 'John Doe' in parsed.value  # Last bold wins
    assert parsed.parse_strategy == 'bold_markdown'


def test_parser_answer_patterns():
    """Test answer pattern parsing."""
    from src.plugins.grid_tasks.parser import GridTasksResponseParser
    
    parser = GridTasksResponseParser()
    
    patterns = [
        'Answer: 42',
        'The answer is: 123.45',
        'Final answer: Engineering',
        'Result: 99',
    ]
    
    for pattern in patterns:
        parsed = parser.parse(pattern, {})
        assert parsed.success, f"Failed to parse: {pattern}"
        assert parsed.parse_strategy == 'answer_pattern'


def test_evaluator_exact_match():
    """Test evaluator with exact matches."""
    from src.core.types import ParsedAnswer
    from src.plugins.grid_tasks.evaluator import GridTasksResultEvaluator
    
    evaluator = GridTasksResultEvaluator(numeric_tolerance=0.1)
    
    # Exact text match
    parsed = ParsedAnswer(value='Alice', raw_response='Alice', parse_strategy='direct', confidence=1.0)
    result = evaluator.evaluate(parsed, 'Alice', {})
    assert result.correct
    assert result.match_type == 'exact'
    assert result.accuracy == 1.0


def test_evaluator_case_insensitive():
    """Test case-insensitive matching."""
    from src.core.types import ParsedAnswer
    from src.plugins.grid_tasks.evaluator import GridTasksResultEvaluator
    
    evaluator = GridTasksResultEvaluator()
    
    parsed = ParsedAnswer(value='alice', raw_response='alice', parse_strategy='direct', confidence=1.0)
    result = evaluator.evaluate(parsed, 'Alice', {})
    assert result.correct
    assert result.match_type == 'case_insensitive'


def test_evaluator_numeric_tolerance():
    """Test numeric comparison with tolerance."""
    from src.core.types import ParsedAnswer
    from src.plugins.grid_tasks.evaluator import GridTasksResultEvaluator
    
    evaluator = GridTasksResultEvaluator(numeric_tolerance=0.1)
    
    # Within tolerance
    parsed = ParsedAnswer(value='42.05', raw_response='42.05', parse_strategy='direct', confidence=1.0)
    result = evaluator.evaluate(parsed, '42.00', {})
    assert result.correct
    assert result.match_type == 'numeric_tolerance'
    assert result.details['difference'] == 0.05
    
    # Outside tolerance
    parsed2 = ParsedAnswer(value='42.50', raw_response='42.50', parse_strategy='direct', confidence=1.0)
    result2 = evaluator.evaluate(parsed2, '42.00', {})
    assert not result2.correct
    assert result2.match_type == 'numeric_mismatch'


def test_evaluator_partial_match():
    """Test partial matching."""
    from src.core.types import ParsedAnswer
    from src.plugins.grid_tasks.evaluator import GridTasksResultEvaluator
    
    evaluator = GridTasksResultEvaluator()
    
    # Model answer contains expected
    parsed = ParsedAnswer(value='The answer is Engineering', raw_response='...', parse_strategy='direct', confidence=1.0)
    result = evaluator.evaluate(parsed, 'Engineering', {})
    assert result.correct
    assert result.match_type == 'partial_contains'
    assert result.accuracy == 0.8


def test_evaluator_aggregate_results():
    """Test result aggregation."""
    from src.core.types import ParsedAnswer, EvaluationResult
    from src.plugins.grid_tasks.evaluator import GridTasksResultEvaluator
    
    evaluator = GridTasksResultEvaluator()
    
    results = [
        EvaluationResult(correct=True, match_type='exact', accuracy=1.0, details={'strategy': 'boxed'}),
        EvaluationResult(correct=True, match_type='case_insensitive', accuracy=1.0, details={'strategy': 'bold'}),
        EvaluationResult(correct=False, match_type='mismatch', accuracy=0.0, details={'strategy': 'answer_pattern'}),
        EvaluationResult(correct=True, match_type='numeric_tolerance', accuracy=1.0, details={'strategy': 'last_line'}),
    ]
    
    agg = evaluator.aggregate_results(results)
    
    assert agg['total'] == 4
    assert agg['correct'] == 3
    assert agg['accuracy'] == 0.75
    assert 'match_types' in agg
    assert 'parse_strategies' in agg


def test_table_formatting_styles():
    """Test table generation with different styles."""
    from src.plugins.grid_tasks.generator import GridTasksTestCaseGenerator
    
    generator = GridTasksTestCaseGenerator()
    
    styles = ['unicode', 'mysql', 'gfm', 'plain']
    
    for style in styles:
        config = {
            'min_rows': 2,
            'max_rows': 2,
            'min_cols': 2,
            'max_cols': 2,
            'data_types': ['sales'],
            'question_types': ['cell_lookup'],
            'table_style': style,
        }
        
        prompt_config = {'name': f'style_{style}', 'user_style': 'minimal', 'system_style': 'analytical'}
        
        test_cases = generator.generate_batch(config, prompt_config, count=1, seed=999)
        assert len(test_cases) == 1
        
        table_str = test_cases[0].prompts['user']
        
        # Check style-specific characters
        if style == 'unicode':
            assert '╔' in table_str or '║' in table_str
        elif style == 'mysql':
            assert '+' in table_str and '-' in table_str
        elif style == 'gfm':
            assert '|' in table_str


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
