#!/usr/bin/env python3
"""Test report generation with token data"""

import sys
import json
import gzip
from pathlib import Path
from datetime import datetime

sys.path.insert(0, 'src')

# Create a mock result file with token data
mock_result = {
    'metadata': {
        'result_id': 'test_123',
        'created_at': datetime.now().isoformat(),
        'hostname': 'test-machine'
    },
    'model_info': {
        'model_name': 'test-model-with-tokens',
        'provider': 'ollama',
        'quantization': None
    },
    'testset_metadata': {
        'testset_name': 'test_arithmetic',
        'task_type': 'arithmetic'
    },
    'execution_info': {
        'successful_tests': 10,
        'failed_tests': 0,
        'duration_seconds': 25.5,
        'average_time_per_test': 2.55
    },
    'summary_statistics': {
        'accuracy': 0.80,
        'correct_responses': 8,
        'total_input_tokens': 2500,
        'total_output_tokens': 1800,
        'avg_input_tokens_per_test': 250,
        'avg_output_tokens_per_test': 180
    },
    'test_config': {},
    'results': []
}

# Save mock result
output_path = Path('/tmp/test_token_report_result.json.gz')
with gzip.open(output_path, 'wt', encoding='utf-8') as f:
    json.dump(mock_result, f, indent=2)

print(f"✓ Created mock result file: {output_path}")

# Now generate a report from it
from stages.analyze_results import generate_markdown_report

report_path = '/tmp/test_token_report.md'
generate_markdown_report([mock_result], report_path, grouped_by_model=False)

print(f"✓ Generated report: {report_path}")
print("\nReport preview:")
print("=" * 70)

with open(report_path, 'r') as f:
    lines = f.readlines()
    # Find and print the table
    in_table = False
    for line in lines:
        if '| Model |' in line or '|-------|' in line or in_table:
            print(line.rstrip())
            in_table = True
            if in_table and line.strip() == '':
                break
        if 'Token Usage' in line:
            # Print token usage section
            for i, l in enumerate(lines[lines.index(line):lines.index(line)+10]):
                print(l.rstrip())
            break

print("=" * 70)
