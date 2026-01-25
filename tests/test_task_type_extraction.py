#!/usr/bin/env python3
"""
Test task type extraction for ascii_shapes and cellular_automata_1d.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_task_type_extraction():
    """Verify task types are correctly extracted from test_ids."""
    from src.stages.analyze_results import extract_task_breakdown
    
    # Mock results with different task types
    mock_results = [
        {'test_id': 'multi_0000_ascii_shapes', 'evaluation': {'correct': True}},
        {'test_id': 'multi_0001_ascii_shapes', 'evaluation': {'correct': False}},
        {'test_id': 'multi_0002_cellular_automata_1d', 'evaluation': {'correct': True}},
        {'test_id': 'multi_0003_c14', 'evaluation': {'correct': False}},
        {'test_id': 'multi_0004_arithmetic', 'evaluation': {'correct': True}},
        {'test_id': 'multi_0005_game_of_life', 'evaluation': {'correct': True}},
    ]
    
    breakdown = extract_task_breakdown(mock_results)
    
    # Check ascii_shapes is recognized
    assert 'ascii_shapes' in breakdown, "ascii_shapes task type not extracted!"
    assert breakdown['ascii_shapes']['total'] == 2, f"Expected 2 ascii_shapes, got {breakdown['ascii_shapes']['total']}"
    print(f"✓ ascii_shapes: {breakdown['ascii_shapes']['total']} tests recognized")
    
    # Check cellular_automata_1d is recognized
    assert 'cellular_automata_1d' in breakdown, "cellular_automata_1d task type not extracted!"
    assert breakdown['cellular_automata_1d']['total'] == 2, f"Expected 2 cellular_automata_1d, got {breakdown['cellular_automata_1d']['total']}"
    print(f"✓ cellular_automata_1d: {breakdown['cellular_automata_1d']['total']} tests recognized")
    
    # Check other task types still work
    assert 'arithmetic' in breakdown, "arithmetic task type not extracted!"
    assert 'game_of_life' in breakdown, "game_of_life task type not extracted!"
    print(f"✓ arithmetic: {breakdown['arithmetic']['total']} tests recognized")
    print(f"✓ game_of_life: {breakdown['game_of_life']['total']} tests recognized")
    
    # Check no unknown tasks
    assert breakdown.get('unknown', {}).get('total', 0) == 0, "Found unexpected 'unknown' tasks!"
    print("✓ No 'unknown' tasks found")
    
    print("\n✅ ALL TESTS PASSED!")
    print("Task type extraction working correctly for ascii_shapes and cellular_automata_1d.")

if __name__ == '__main__':
    test_task_type_extraction()
