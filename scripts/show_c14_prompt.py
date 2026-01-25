#!/usr/bin/env python3
"""Display example C14 prompt"""

import sys
import gzip
import json
from pathlib import Path

# Find the most recent C14 testset
testsets_dir = Path('testsets')
c14_files = list(testsets_dir.glob('testset_c14_tui_validation_test_*.json.gz'))

if not c14_files:
    print('No C14 test sets found')
    sys.exit(0)

testset_path = max(c14_files, key=lambda p: p.stat().st_mtime)

# Load and display first test case
with gzip.open(testset_path, 'rt') as f:
    data = json.load(f)

case = data['test_cases'][0]

print('=' * 70)
print('C14 Generated Prompt Example (Rule 90 - Easy)')
print('=' * 70)
print()
print('SYSTEM PROMPT:')
print('-' * 70)
print(case['prompts']['system'])
print()
print('USER PROMPT:')
print('-' * 70)
print(case['prompts']['user'])
print()
print('=' * 70)
print('TASK PARAMETERS:')
print('-' * 70)
for key, value in case['task_params'].items():
    print(f"  {key}: {value}")
print('=' * 70)
