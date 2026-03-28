import os
import re
import gzip
import json
import pathlib
from typing import Counter

DIR = pathlib.Path('./results')
OUT = pathlib.Path('./incorrect_results.jsonl')
# Read all .json.gz files, decompress, then filter only those that are incorrect

count_total = Counter()
with open(OUT, 'w', encoding='utf-8') as out_f:
    for filename in os.listdir(DIR):
        if not filename.endswith('.json.gz'):
            continue
        file_path = DIR / filename
        with open(file_path, 'rb') as f, gzip.open(f, 'rt', encoding='utf-8') as gz:
            json_text = gz.read()
            data = json.loads(json_text)
            model = data.get('model_info', {}).get('model_name', 'unknown_model')
            results = data.get('results', [])
            for r in results:
                raw_response = r.get('output', {}).get('raw_response', '')
                if raw_response is None or raw_response.strip() == "":
                    continue  # Skip if no raw_response
                test_id = r.get('test_id', 'unknown')
                test_id = re.sub(r'^multi_\d+_', '', test_id)
                test_id = re.sub(r'(_\d+)+$', '', test_id)
                if not r.get('evaluation', {}).get('correct', False):
                    res = {
                        'test_id': test_id,
                        'model': model,
                        'user_prompt': r.get('input', {}).get('user_prompt', ''),
                        'raw_response': raw_response,
                        'parsed_answer': r.get('output', {}).get('parsed_answer', {}),
                        'expected_answer': r.get('input', {}).get('task_params', {}).get('expected_answer', ''),
                    }
                    out_f.write(json.dumps(res) + '\n')
                    count_total[test_id] += 1

print("Incorrect counts by test_id:")
for test_id, count in count_total.most_common():
    print(f"{test_id}: {count}")