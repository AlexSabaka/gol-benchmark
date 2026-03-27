"""Tests for GoL plugin changes: cell markers, sorted patterns, exclude_empty."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.plugins.game_of_life.generator import format_grid, _normalize_cell_markers, GoLTestCaseGenerator
from src.core.TestGenerator import TestGenerator


def test_normalize_cell_markers_emoji_string():
    assert _normalize_cell_markers('❤️,🖤') == ['❤️', '🖤']


def test_normalize_cell_markers_standard_string():
    assert _normalize_cell_markers('1,0') == ['1', '0']


def test_normalize_cell_markers_list_passthrough():
    assert _normalize_cell_markers(['X', '.']) == ['X', '.']


def test_normalize_cell_markers_single_value():
    assert _normalize_cell_markers('AB') == ['AB', '0']


def test_format_grid_emoji():
    grid = [[1, 0], [0, 1]]
    result = format_grid(grid, '❤️', '🖤')
    assert '❤️' in result and '🖤' in result
    assert '1' not in result and '0' not in result


def test_format_grid_collision_safe():
    """Markers that contain '0' or '1' characters should not cause corruption."""
    grid = [[1, 0], [0, 1]]
    result = format_grid(grid, '10', '01')
    lines = result.split('\n')
    assert lines[0] == '10 01'
    assert lines[1] == '01 10'


def test_generate_batch_emoji_markers():
    gen = GoLTestCaseGenerator()
    cases = gen.generate_batch(
        config={'difficulty_levels': ['EASY'], 'grids_per_difficulty': 2,
                'cell_markers': '❤️,🖤', 'density': 0.5},
        prompt_config={'user_style': 'minimal', 'system_style': 'analytical', 'language': 'en'},
        count=2, seed=42
    )
    assert len(cases) == 2
    user_prompt = cases[0].prompts['user']
    assert '❤️' in user_prompt, f'Emoji not in prompt: {user_prompt[:200]}'


def test_sorted_patterns_loading():
    pats = TestGenerator._load_sorted_patterns(5, 5)
    assert len(pats) > 5, f'Expected many patterns, got {len(pats)}'
    # Verify all patterns fit within 5x5
    for pat in pats:
        assert len(pat) <= 5, f'Pattern height {len(pat)} exceeds 5'
        assert all(len(row) <= 5 for row in pat), f'Pattern width exceeds 5'


def test_sorted_patterns_content():
    """Verify patterns are parsed correctly (only 0s and 1s)."""
    pats = TestGenerator._load_sorted_patterns(3, 3)
    for pat in pats:
        for row in pat:
            for cell in row:
                assert cell in (0, 1), f'Invalid cell value: {cell}'


def test_sorted_patterns_caching():
    """Second call should return same object (cached)."""
    pats1 = TestGenerator._load_sorted_patterns(5, 5)
    pats2 = TestGenerator._load_sorted_patterns(5, 5)
    assert pats1 is pats2


def test_generate_known_pattern_uses_sorted():
    """With dimensions, should return patterns from sorted_patterns."""
    from src.core.types import BaseTestConfig
    from dataclasses import dataclass, field
    from typing import List

    @dataclass
    class Cfg(BaseTestConfig):
        models: List[str] = field(default_factory=lambda: ["dummy"])
        seed: int = 42
        def __post_init__(self):
            super().__post_init__()

    tg = TestGenerator(Cfg())
    pat = tg.generate_known_pattern(5, 5)
    assert len(pat) <= 5
    assert all(len(row) <= 5 for row in pat)


def test_exclude_empty():
    gen = GoLTestCaseGenerator()
    cases = gen.generate_batch(
        config={'difficulty_levels': ['EASY'], 'grids_per_difficulty': 10,
                'density': 0.5, 'exclude_empty': True},
        prompt_config={'user_style': 'minimal', 'system_style': 'analytical', 'language': 'en'},
        count=10, seed=42
    )
    for c in cases:
        grid = c.task_params['initial_grid']
        has_live = any(cell for row in grid for cell in row)
        assert has_live, 'Empty grid found with exclude_empty=True!'


def test_task_params_contain_markers():
    """Verify cell markers propagate to task_params."""
    gen = GoLTestCaseGenerator()
    cases = gen.generate_batch(
        config={'difficulty_levels': ['EASY'], 'grids_per_difficulty': 1,
                'cell_markers': '❤️,🖤', 'density': 0.5},
        prompt_config={'user_style': 'minimal', 'system_style': 'analytical', 'language': 'en'},
        count=1, seed=42
    )
    assert cases[0].task_params['live_cell'] == '❤️'
    assert cases[0].task_params['dead_cell'] == '🖤'
