#!/usr/bin/env python3
"""Diagnose test set file to show what's inside."""

import sys
import gzip
import json
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python scripts/diagnose_testset.py <testset.json.gz>")
    sys.exit(1)

testset_path = Path(sys.argv[1])

if not testset_path.exists():
    print(f"❌ File not found: {testset_path}")
    sys.exit(1)

print(f"📦 Analyzing: {testset_path.name}")
print("=" * 80)

try:
    with gzip.open(testset_path, 'rt') as f:
        data = json.load(f)
except Exception as e:
    print(f"❌ Error reading file: {e}")
    sys.exit(1)

# Metadata
print("\n📋 METADATA:")
print("-" * 80)
for key, value in data.get('metadata', {}).items():
    print(f"  {key}: {value}")

# Test cases summary
test_cases = data.get('test_cases', [])
print(f"\n📊 TEST CASES: {len(test_cases)} total")
print("-" * 80)

for i, case in enumerate(test_cases, 1):
    print(f"\n{i}. {case['test_id']} ({case['task_type']})")
    print(f"   Config: {case.get('config_name', 'N/A')}")
    
    # Check prompts
    prompts = case.get('prompts', {})
    system = prompts.get('system', '')
    user = prompts.get('user', '')
    
    print(f"   System Prompt: {'✓ ' + str(len(system)) + ' chars' if system else '❌ EMPTY'}")
    print(f"   User Prompt: {'✓ ' + str(len(user)) + ' chars' if user else '❌ EMPTY'}")
    
    # Task params
    params = case.get('task_params', {})
    print(f"   Parameters: {', '.join(params.keys())}")
    
    # Show a snippet of the user prompt
    if user:
        snippet = user[:100].replace('\n', ' ')
        print(f"   Preview: \"{snippet}...\"")

print("\n" + "=" * 80)
print(f"✅ File is valid and contains {len(test_cases)} test cases")
print("\n💡 Key findings:")

# Check for empty system prompts
empty_system = sum(1 for c in test_cases if not c.get('prompts', {}).get('system', ''))
if empty_system:
    print(f"  - {empty_system}/{len(test_cases)} test cases have EMPTY system prompts")
    print(f"    This is intentional if system_style='none' was selected")

# Check for empty user prompts
empty_user = sum(1 for c in test_cases if not c.get('prompts', {}).get('user', ''))
if empty_user:
    print(f"  ⚠️  {empty_user}/{len(test_cases)} test cases have EMPTY user prompts (BUG!)")

# Task distribution
from collections import Counter
task_counts = Counter(c['task_type'] for c in test_cases)
print(f"  - Task distribution: {dict(task_counts)}")

print()
