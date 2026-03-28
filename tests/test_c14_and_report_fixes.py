"""
Tests for C14 cell markers support and analyze_results report fixes.
"""
import re
import pytest


# ── C14 cell markers ──

class TestC14CellMarkers:
    """Test cell marker support in cellular_automata_1d generator."""

    def test_normalize_emoji_string(self):
        from src.plugins.cellular_automata_1d.generator import _normalize_cell_markers
        assert _normalize_cell_markers("❤️,🖤") == ["❤️", "🖤"]

    def test_normalize_standard_string(self):
        from src.plugins.cellular_automata_1d.generator import _normalize_cell_markers
        assert _normalize_cell_markers("1,0") == ["1", "0"]

    def test_normalize_list_passthrough(self):
        from src.plugins.cellular_automata_1d.generator import _normalize_cell_markers
        assert _normalize_cell_markers(["X", "O"]) == ["X", "O"]

    def test_normalize_default_fallback(self):
        from src.plugins.cellular_automata_1d.generator import _normalize_cell_markers
        assert _normalize_cell_markers(None) == ["1", "0"]
        assert _normalize_cell_markers(42) == ["1", "0"]

    def test_generate_batch_default_markers(self):
        """Default markers produce 0/1 state strings."""
        from src.plugins.cellular_automata_1d.generator import C14TestCaseGenerator
        gen = C14TestCaseGenerator()
        tests = gen.generate_batch(
            config={'rules': [110], 'tests_per_rule': 1, 'width': 8},
            prompt_config={'language': 'en', 'user_style': 'minimal', 'system_style': 'analytical'},
            count=1, seed=42,
        )
        assert len(tests) == 1
        state_line = tests[0].prompts['user'].split('Current:')[1].split('\n')[0].strip()
        assert all(c in '01 ' for c in state_line)

    def test_generate_batch_custom_markers(self):
        """Custom markers appear in state string."""
        from src.plugins.cellular_automata_1d.generator import C14TestCaseGenerator
        gen = C14TestCaseGenerator()
        tests = gen.generate_batch(
            config={'rules': [110], 'tests_per_rule': 1, 'width': 8,
                    'cell_markers': 'X,O'},
            prompt_config={'language': 'en', 'user_style': 'minimal', 'system_style': 'analytical'},
            count=1, seed=42,
        )
        assert len(tests) == 1
        prompt = tests[0].prompts['user']
        state_line = prompt.split('Current:')[1].split('\n')[0].strip()
        # State should contain X and/or O only (plus spaces)
        assert all(c in 'XO ' for c in state_line)
        assert 'X' in state_line or 'O' in state_line

    def test_generate_batch_emoji_markers(self):
        """Emoji markers work in state strings."""
        from src.plugins.cellular_automata_1d.generator import C14TestCaseGenerator
        gen = C14TestCaseGenerator()
        tests = gen.generate_batch(
            config={'rules': [30], 'tests_per_rule': 1, 'width': 8,
                    'cell_markers': '🔴,⚪'},
            prompt_config={'language': 'en', 'user_style': 'minimal', 'system_style': 'analytical'},
            count=1, seed=42,
        )
        assert len(tests) == 1
        prompt = tests[0].prompts['user']
        # State string should contain the emoji markers
        state_section = prompt.split('Current:')[1].split('\n')[0].strip()
        assert '🔴' in state_section or '⚪' in state_section

    def test_task_params_contain_markers(self):
        """task_params should include live_cell and dead_cell."""
        from src.plugins.cellular_automata_1d.generator import C14TestCaseGenerator
        gen = C14TestCaseGenerator()
        tests = gen.generate_batch(
            config={'rules': [110], 'tests_per_rule': 1, 'width': 8,
                    'cell_markers': 'A,B'},
            prompt_config={'language': 'en', 'user_style': 'minimal', 'system_style': 'analytical'},
            count=1, seed=42,
        )
        tp = tests[0].task_params
        assert tp['live_cell'] == 'A'
        assert tp['dead_cell'] == 'B'

    def test_boundary_description_uses_markers(self):
        """Boundary description should reference the actual markers."""
        from src.plugins.cellular_automata_1d.generator import C14TestCaseGenerator
        gen = C14TestCaseGenerator()
        tests = gen.generate_batch(
            config={'rules': [110], 'tests_per_rule': 1, 'width': 8,
                    'boundary': 'dead', 'cell_markers': 'X,O'},
            prompt_config={'language': 'en', 'user_style': 'linguistic', 'system_style': 'analytical'},
            count=1, seed=42,
        )
        prompt = tests[0].prompts['user']
        assert '(O)' in prompt  # dead marker in boundary description

    def test_rule_table_uses_custom_markers(self):
        """Rule table in prompts should use custom cell markers, not hardcoded 0/1."""
        from src.plugins.cellular_automata_1d.generator import C14TestCaseGenerator
        gen = C14TestCaseGenerator()
        tests = gen.generate_batch(
            config={'rules': [110], 'tests_per_rule': 1, 'width': 8,
                    'cell_markers': 'X,O'},
            prompt_config={'language': 'en', 'user_style': 'minimal', 'system_style': 'analytical'},
            count=1, seed=42,
        )
        prompt = tests[0].prompts['user']
        # Rule table header should use X/O, not 1/0
        assert 'XXX' in prompt  # (1,1,1) → XXX
        assert 'OOO' in prompt  # (0,0,0) → OOO
        assert 'XOX' in prompt  # (1,0,1) → XOX
        # The output values should also use X/O
        # Rule 110: 111→0, so OOO→O and XXX→O  (depends on rule)
        # Just check no bare '111' or '000' patterns in the rule table area
        rule_section = prompt.split('Rule 110')[1].split('Current')[0]
        assert '111' not in rule_section
        assert '000' not in rule_section

    def test_config_schema_includes_cell_markers(self):
        """Config schema should include cell_markers field."""
        from src.plugins.cellular_automata_1d.generator import C14TestCaseGenerator
        gen = C14TestCaseGenerator()
        schema = gen.get_config_schema()
        names = [f.name for f in schema]
        assert 'cell_markers' in names


# ── Report: expected value display ──

class TestExpectedDisplay:
    """Test _get_expected_display helper for various answer types."""

    def test_expected_answer_string(self):
        from src.stages.analyze_results import _get_expected_display
        assert _get_expected_display({'expected_answer': '42'}) == '42'

    def test_expected_answer_number(self):
        from src.stages.analyze_results import _get_expected_display
        assert _get_expected_display({'expected_answer': 42}) == '42'

    def test_expected_state_1d_list(self):
        """C14 expected_state: 1D array → space-separated."""
        from src.stages.analyze_results import _get_expected_display
        result = _get_expected_display({'expected_state': [0, 1, 1, 0, 1]})
        assert result == '0 1 1 0 1'

    def test_expected_next_state_2d_list(self):
        """GoL expected_next_state: 2D grid → rows separated by |."""
        from src.stages.analyze_results import _get_expected_display
        grid = [[1, 0, 1], [0, 1, 0]]
        result = _get_expected_display({'expected_next_state': grid})
        assert result == '1 0 1 | 0 1 0'

    def test_expected_fallacy(self):
        from src.stages.analyze_results import _get_expected_display
        result = _get_expected_display({'expected_fallacy': 'conjunction'})
        assert result == 'conjunction'

    def test_no_expected_key(self):
        from src.stages.analyze_results import _get_expected_display
        assert _get_expected_display({'rule': 110}) == 'N/A'

    def test_priority_order(self):
        """expected_answer takes priority over expected_state."""
        from src.stages.analyze_results import _get_expected_display
        result = _get_expected_display({
            'expected_answer': 'primary',
            'expected_state': [0, 1]
        })
        assert result == 'primary'


# ── Report: thinking block extraction ──

class TestThinkingExtraction:
    """Test _extract_thinking helper."""

    def test_no_thinking(self):
        from src.stages.analyze_results import _extract_thinking
        sample = {'output': {'raw_response': 'Just an answer'}}
        thinking, clean = _extract_thinking(sample)
        assert thinking is None
        assert clean == 'Just an answer'

    def test_reasoning_key(self):
        from src.stages.analyze_results import _extract_thinking
        sample = {
            'output': {
                'raw_response': 'The answer is 42',
                'reasoning': 'Let me think step by step...'
            }
        }
        thinking, clean = _extract_thinking(sample)
        assert thinking == 'Let me think step by step...'
        assert clean == 'The answer is 42'

    def test_think_tags(self):
        from src.stages.analyze_results import _extract_thinking
        raw = '<think>Let me reason about this...</think>\n\nThe answer is 42'
        sample = {'output': {'raw_response': raw}}
        thinking, clean = _extract_thinking(sample)
        assert thinking == 'Let me reason about this...'
        assert clean == 'The answer is 42'

    def test_think_tags_stripped_when_reasoning_present(self):
        """When reasoning key is present AND think tags exist, tags are stripped."""
        from src.stages.analyze_results import _extract_thinking
        sample = {
            'output': {
                'raw_response': '<think>internal</think>\nFinal answer',
                'reasoning': 'API reasoning'
            }
        }
        thinking, clean = _extract_thinking(sample)
        assert thinking == 'API reasoning'
        assert '<think>' not in clean
        assert 'Final answer' in clean

    def test_empty_output(self):
        from src.stages.analyze_results import _extract_thinking
        sample = {'output': {}}
        thinking, clean = _extract_thinking(sample)
        assert thinking is None
        assert clean == ''


# ── Report: parsed answer formatting ──

class TestParsedDisplay:
    """Test _format_parsed_display matches _get_expected_display formatting."""

    def test_2d_list(self):
        from src.stages.analyze_results import _format_parsed_display
        val = [[0, 0, 0], [1, 1, 1]]
        assert _format_parsed_display(val) == '0 0 0 | 1 1 1'

    def test_1d_list(self):
        from src.stages.analyze_results import _format_parsed_display
        assert _format_parsed_display([0, 1, 1, 0]) == '0 1 1 0'

    def test_string(self):
        from src.stages.analyze_results import _format_parsed_display
        assert _format_parsed_display('hello') == 'hello'

    def test_none(self):
        from src.stages.analyze_results import _format_parsed_display
        assert _format_parsed_display(None) == 'N/A'

    def test_number(self):
        from src.stages.analyze_results import _format_parsed_display
        assert _format_parsed_display(42) == '42'
