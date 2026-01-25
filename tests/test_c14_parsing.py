#!/usr/bin/env python3
"""Test C14 response parsing with real model outputs."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.stages.run_testset import parse_c14_response

# Real examples from the results file
test_cases = [
    # Case 1: "Final Answer:" format
    {
        "response": """Final Answer: 1 1 1 1 1 1 1 1 0 1 0 0 0 1 1 0""",
        "expected": [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0],
        "name": "Final Answer format"
    },
    
    # Case 2: "Next Row:" format
    {
        "response": """Next Row: 1 1 0 1 1 0 1 1 1 0 1 0 1 0 1 0""",
        "expected": [1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0],
        "name": "Next Row format"
    },
    
    # Case 3: Plain state at end
    {
        "response": """Okay, let's calculate...
        
The next state is:
0 1 0 1 1 0 1 1 0 0 1 0 1 1 1 0""",
        "expected": [0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0],
        "name": "Next state format"
    },
    
    # Case 4: Embedded in explanation (like test #8)
    {
        "response": """**Resulting Next Row:**

0 1 0 1 1 0 1 1 0 0 1 0 1 1 1 0

**Final Answer:**

0 1 0 1 1 0 1 1 0 0 1 0 1 1 1 0""",
        "expected": [0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0],
        "name": "Markdown format"
    },
    
    # Case 5: Continuous format
    {
        "response": """The answer is: 1101101100101110""",
        "expected": [1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0],
        "name": "Continuous format"
    },
    
    # Case 6: Array format
    {
        "response": """Result: [1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0]""",
        "expected": [1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0],
        "name": "Array format"
    },
]

print("🧪 Testing C14 Response Parsing")
print("=" * 70)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['name']}")
    print(f"  Input: {test['response'][:60]}...")
    
    parsed = parse_c14_response(test['response'])
    
    if parsed == test['expected']:
        print(f"  ✅ PASSED - Parsed: {parsed}")
        passed += 1
    else:
        print(f"  ❌ FAILED")
        print(f"     Expected: {test['expected']}")
        print(f"     Got: {parsed}")
        failed += 1

print("\n" + "=" * 70)
print(f"Results: {passed} passed, {failed} failed")

if failed == 0:
    print("✅ All tests passed!")
    sys.exit(0)
else:
    print("❌ Some tests failed")
    sys.exit(1)
