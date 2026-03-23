#!/usr/bin/env python
"""Quick validation of the strawberry plugin."""
import sys
sys.path.insert(0, '.')

from src.plugins import PluginRegistry
from src.plugins.base import ParsedAnswer

p = PluginRegistry.get('strawberry')
parser = p.get_parser()
evaluator = p.get_evaluator()

# --- Parser tests ---
tests = [
    ('3', 3),
    (r'\boxed{2}', 2),
    ('**4**', 4),
    ('The answer is 3.', 3),
    ('There are three Rs.', 3),
    ('Answer: 0', 0),
    ('', None),
    ('I think it is five.', 5),
    ('Let me count: s-t-r-a-w-b-e-r-r-y. The letter r appears 3 times.', 3),
    ('zero', 0),
    ('none', 0),
]

print("=== PARSER TESTS ===")
all_ok = True
for resp, exp in tests:
    pa = parser.parse(resp, {'word_length': 15})
    ok = pa.value == exp
    if not ok:
        all_ok = False
    status = 'OK' if ok else 'FAIL'
    print(f"  {status:4s}  value={pa.value!r:6s}  strategy={pa.parse_strategy:15s}  input={resp!r}")

# --- Evaluator tests ---
print("\n=== EVALUATOR TESTS ===")
pa_ok = ParsedAnswer(value=3, raw_response='3', parse_strategy='boxed', confidence=0.95)
pa_wrong = ParsedAnswer(value=5, raw_response='5', parse_strategy='boxed', confidence=0.95)
pa_err = ParsedAnswer(value=None, raw_response='dunno', parse_strategy='fallback', confidence=0.1, error='no int')

tp = {'word': 'strawberry', 'letter': 'r', 'mode': 'real', 'word_length': 10}
for pa, exp, exp_match in [(pa_ok, 3, 'correct'), (pa_wrong, 3, 'wrong'), (pa_err, 3, 'parse_error')]:
    ev = evaluator.evaluate(pa, exp, tp)
    ok = ev.match_type == exp_match
    if not ok:
        all_ok = False
    status = 'OK' if ok else 'FAIL'
    print(f"  {status:4s}  pred={pa.value!r:6s}  match_type={ev.match_type:12s}  off_by={ev.details.get('off_by')}")

# --- Multilingual generator test ---
print("\n=== MULTILINGUAL GENERATOR ===")
gen = p.get_generator()
for lang in ['en', 'es', 'fr', 'de', 'zh', 'ua']:
    cases = gen.generate_batch(
        config={'mode': 'real', 'language': lang},
        prompt_config={'user_style': 'minimal', 'system_style': 'analytical'},
        count=1, seed=42,
    )
    tc = cases[0]
    print(f"  {lang}: {tc.prompts['user'][:80]}...")

print(f"\n{'ALL PASSED' if all_ok else 'SOME TESTS FAILED'}")
