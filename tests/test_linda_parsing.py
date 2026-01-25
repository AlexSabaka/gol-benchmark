#!/usr/bin/env python3
"""
Test suite for Linda fallacy parsing edge cases.
Tests for response parsing, deduplication, and explanation stripping.
"""

import sys
sys.path.insert(0, '/Volumes/2TB/repos/gol_eval')

from src.stages.run_testset import parse_linda_response


def test_duplicate_with_explanations():
    """Test: Model outputs duplicate items with different explanations."""
    response = """
Let me analyze this carefully.

RANKING:
1. Alex works for an environmental consulting firm: Least Likely
2. Alex is active in the environmental movement: Likely
3. Alex is a fitness instructor: Unlikely
4. Alex works in marketing: Unlikely
5. Alex is a high school teacher: Possible
6. Alex works for an environmental consulting firm and Alex is active in the environmental movement: Most Likely
7. Alex is a nurse: Unlikely
8. Alex is a bank teller: Least Likely

Final Ranking:
1. Alex works for an environmental consulting firm and Alex is active in the environmental movement
2. Alex is active in the environmental movement
3. Alex is a fitness instructor
4. Alex is a high school teacher
5. Alex is a nurse
6. Alex is a bank teller
"""
    
    result = parse_linda_response(response)
    rankings = result['rankings']
    
    print("Test 1: Duplicate with Explanations")
    print(f"  Parsed {len(rankings)} items (expected ≤10)")
    
    # Check for duplicates
    normalized_items = [r.replace(':', '').replace('-', '').strip().lower() for r in rankings]
    unique_count = len(set(normalized_items))
    
    print(f"  Unique items: {unique_count}/{len(rankings)}")
    assert unique_count == len(rankings), f"Found duplicates! {len(rankings) - unique_count} duplicate(s)"
    assert len(rankings) <= 10, f"Too many items: {len(rankings)}"
    print("  ✅ PASSED")
    return True


def test_likelihood_markers():
    """Test: Strip various likelihood markers."""
    response = """
RANKING:
1. Marie Dubois works as a graphic designer (Most Likely)
2. Marie Dubois is involved in local arts advocacy: Very Likely
3. Marie Dubois works in customer service - Unlikely
4. Marie Dubois works in accounting – Least Likely
5. Marie Dubois is a nurse (Highly Unlikely)
6. Marie Dubois works in insurance sales: Possible
7. Marie Dubois is a librarian (Least Probable)
8. Marie Dubois works as a graphic designer and Marie Dubois is involved in local arts advocacy
"""
    
    result = parse_linda_response(response)
    rankings = result['rankings']
    
    print("\nTest 2: Likelihood Markers Stripping")
    print(f"  Parsed {len(rankings)} items")
    
    # Check that likelihood markers are stripped
    for r in rankings:
        assert ' likely' not in r.lower() or 'least likely' in r.lower(), f"Failed to strip likelihood from: {r}"
        assert ' probable' not in r.lower(), f"Failed to strip probable from: {r}"
        assert ' possible' not in r.lower(), f"Failed to strip possible from: {r}"
    
    print("  ✅ PASSED - All likelihood markers stripped")
    return True


def test_fuzzy_deduplication():
    """Test: Fuzzy matching catches near-duplicates."""
    response = """
RANKING:
1. Jordan is a software engineer
2. Jordan is a software engineer and Jordan contributes to AI safety research
3. Jordan contributes to AI safety research
4. Jordan works in marketing
5. Jordan is a software engineer  
6. Jordan works as a chef
7. Jordan is a nurse
8. Jordan works in insurance
"""
    
    result = parse_linda_response(response)
    rankings = result['rankings']
    
    print("\nTest 3: Fuzzy Deduplication")
    print(f"  Parsed {len(rankings)} items")
    
    # Count exact "Jordan is a software engineer" occurrences
    engineer_count = sum(1 for r in rankings if 'software engineer' in r and ' and ' not in r)
    
    print(f"  'software engineer' standalone occurrences: {engineer_count}")
    assert engineer_count == 1, f"Fuzzy dedup failed: found {engineer_count} instances of 'software engineer'"
    print("  ✅ PASSED - Fuzzy deduplication working")
    return True


def test_sequential_strategy_stopping():
    """Test: Strategy 1 succeeds, strategies 2-4 should not add more items."""
    response = """
Let me rank these options.

RANKING:
1. Linda teaches philosophy at a community college
2. Linda writes for an online magazine on social issues
3. Linda is a bank teller
4. Linda works in customer service
5. Linda is a nurse
6. Linda teaches philosophy at a community college and Linda writes for an online magazine on social issues
7. Linda works in retail
8. Linda works in accounting

Some additional analysis follows...
Linda is clearly well-suited for teaching. Linda would also excel at writing.
"""
    
    result = parse_linda_response(response)
    rankings = result['rankings']
    
    print("\nTest 4: Sequential Strategy Stopping")
    print(f"  Parsed {len(rankings)} items (expected 8)")
    print(f"  Strategy used: {result['parse_strategy']}")
    
    assert result['parse_strategy'] == 'explicit_ranking_section', "Should use Strategy 1"
    assert len(rankings) == 8, f"Expected exactly 8 items, got {len(rankings)}"
    print("  ✅ PASSED - Strategy 1 succeeded and stopped")
    return True


def test_multiple_ranking_sections():
    """Test: Model outputs multiple numbered lists."""
    response = """
Let me analyze each option:

1. Jordan is a software engineer (Likelihood: 7/10)
2. Jordan works in insurance (Likelihood: 2/10)
3. Jordan contributes to AI safety research (Likelihood: 2/10)
4. Jordan is a software engineer and Jordan contributes to AI safety research (Likelihood: 6/10)

After careful consideration, my final ranking is:

RANKING:
1. Jordan is a software engineer
2. AI safety research
3. Jordan works in insurance
4. Jordan is a nurse
5. Jordan works as a chef
6. Jordan works in marketing
"""
    
    result = parse_linda_response(response)
    rankings = result['rankings']
    
    print("\nTest 5: Multiple Ranking Sections")
    print(f"  Parsed {len(rankings)} items")
    print(f"  Strategy used: {result['parse_strategy']}")
    
    # Should prioritize the explicit RANKING section
    assert result['parse_strategy'] == 'explicit_ranking_section', "Should use explicit RANKING section"
    assert len(rankings) <= 10, f"Too many items: {len(rankings)}"
    print("  ✅ PASSED - Prioritized explicit RANKING section")
    return True


def test_parenthetical_explanations():
    """Test: Remove parenthetical explanations."""
    response = """
RANKING:
1. Elena Vasquez works in a bookstore (This aligns with her interests)
2. Elena Vasquez attends social justice workshops (Moderate likelihood)
3. Elena Vasquez works as a teacher (Given her background)
4. Elena Vasquez is a nurse (Less likely fit)
5. Elena Vasquez works in insurance (Unlikely match)
6. Elena Vasquez works in a bookstore and Elena Vasquez attends social justice workshops (Strong fit)
7. Elena Vasquez works in marketing (Doesn't match profile)
8. Elena Vasquez is a bank teller (Least likely)
"""
    
    result = parse_linda_response(response)
    rankings = result['rankings']
    
    print("\nTest 6: Parenthetical Explanations")
    print(f"  Parsed {len(rankings)} items")
    
    # Check that parenthetical content is removed
    for r in rankings:
        assert '(' not in r or 'score' in r.lower(), f"Failed to remove parenthetical: {r}"
    
    print("  ✅ PASSED - Parenthetical explanations stripped")
    return True


def test_only_four_items_parsed():
    """Test: Model only provides 4 items instead of 8 (low ranking quality)."""
    response = """
Based on the profile, here are my assessments:

1. Marie Dubois works as a graphic designer (High likelihood)
2. Marie Dubois is involved in local arts advocacy and Marie Dubois works as a graphic designer (Very high likelihood)

Actually, let me reconsider:

RANKING:
1. Graphic designer and arts advocate
2. Graphic designer
3. Bank teller
4. Real estate agent
"""
    
    result = parse_linda_response(response)
    rankings = result['rankings']
    
    print("\nTest 7: Partial Ranking (4 items)")
    print(f"  Parsed {len(rankings)} items")
    assert len(rankings) >= 3, "Should parse at least 3 items"
    assert len(rankings) <= 6, "Should not fabricate extra items"
    print("  ✅ PASSED - Handled partial ranking gracefully")
    return True


def run_all_tests():
    """Run all Linda parsing tests."""
    tests = [
        test_duplicate_with_explanations,
        test_likelihood_markers,
        test_fuzzy_deduplication,
        test_sequential_strategy_stopping,
        test_multiple_ranking_sections,
        test_parenthetical_explanations,
        test_only_four_items_parsed
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 70)
    print("Linda Fallacy Parsing Test Suite")
    print("=" * 70)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
