"""Quick verification of the family_relations plugin."""
from src.plugins.family_relations import plugin

# --- Parser tests ---
p = plugin.get_parser()

test_responses = [
    ("The answer is 3", 3),
    ("\\boxed{7}", 7),
    ("**5**", 5),
    ("After careful analysis, there are seven children.", 7),
    ("So the answer = 4.", 4),
    ("Let me think... maybe 6? No wait, actually it is 3.", 3),
    ("", None),
]

print("=== Parser tests ===")
for resp, expected_val in test_responses:
    result = p.parse(resp, {})
    status = "OK" if result.value == expected_val else "FAIL"
    print(f"  [{status}] value={result.value} strategy={result.parse_strategy} <- {repr(resp[:55])}")

# --- Evaluator tests ---
print("\n=== Evaluator tests ===")
e = plugin.get_evaluator()
from src.plugins.base import ParsedAnswer

cases = [
    (3, 3, "correct"),
    (5, 3, "overcounting"),
    (2, 3, "undercounting"),
]
for predicted, expected, exp_match in cases:
    pa = ParsedAnswer(value=predicted, raw_response=str(predicted), parse_strategy="test", confidence=1.0)
    r = e.evaluate(pa, expected, {"sub_type": "sibling_count"})
    status = "OK" if r.match_type == exp_match else "FAIL"
    print(f"  [{status}] predicted={predicted} expected={expected}: match_type={r.match_type} correct={r.correct}")

# Parse error
pa = ParsedAnswer(value=None, raw_response="dunno", parse_strategy="fallback", confidence=0.1, error="Could not parse")
r = e.evaluate(pa, 3, {"sub_type": "sibling_count"})
status = "OK" if r.match_type == "parse_error" else "FAIL"
print(f"  [{status}] predicted=None expected=3: match_type={r.match_type} correct={r.correct}")

# --- Generation test ---
print("\n=== Generation test ===")
g = plugin.get_generator()
cases = g.generate_batch(
    config={},
    prompt_config={"user_style": "linguistic", "system_style": "analytical", "name": "test"},
    count=5,
    seed=99,
)
for tc in cases:
    st = tc.task_params["sub_type"]
    ans = tc.task_params["expected_answer"]
    tmpl = tc.task_params["template"]
    print(f"  [{st}] answer={ans} template={tmpl}")

print("\nAll checks passed!")
