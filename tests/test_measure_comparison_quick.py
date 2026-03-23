#!/usr/bin/env python
"""Quick validation of the measure_comparison plugin."""
import sys
sys.path.insert(0, ".")

from src.plugins import PluginRegistry
from src.plugins.measure_comparison.generator import to_base
from src.plugins.base import ParsedAnswer

p = PluginRegistry.get("measure_comparison")
gen = p.get_generator()
parser = p.get_parser()
evaluator = p.get_evaluator()

errors = []

# =====================================================================
# 1. Temperature conversions
# =====================================================================
checks = [
    (to_base(0, "C"), 273.15, "0°C -> K"),
    (to_base(32, "F"), 273.15, "32°F -> K"),
    (to_base(212, "F"), 373.15, "212°F -> K"),
    (to_base(100, "C"), 373.15, "100°C -> K"),
    (to_base(273.15, "K"), 273.15, "273.15K -> K"),
]
for actual, expected, label in checks:
    if abs(actual - expected) > 0.01:
        errors.append(f"TEMP FAIL: {label}: got {actual}, expected {expected}")
print(f"Temperature conversions: {len(checks)} checked, {len(errors)} errors")

# =====================================================================
# 2. Unit conversions
# =====================================================================
unit_checks = [
    (to_base(1, "km"), 1000.0, "1km->m"),
    (to_base(1, "inch"), 0.0254, "1inch->m"),
    (to_base(1, "lb"), 453.592, "1lb->g"),
    (to_base(1, "gallon"), 3785.41, "1gallon->mL"),
    (to_base(1, "L"), 1000.0, "1L->mL"),
    (to_base(3.6, "km/h"), 1.0, "3.6km/h->m/s"),
]
for actual, expected, label in unit_checks:
    if abs(actual - expected) > 0.1:
        errors.append(f"UNIT FAIL: {label}: got {actual}, expected {expected}")
print(f"Unit conversions: {len(unit_checks)} checked")

# =====================================================================
# 3. Generator correctness (same_unit integer)
# =====================================================================
cases = gen.generate_batch(
    config={"comparison_type": "same_unit", "number_format": "integer", "count": 30},
    prompt_config={"user_style": "minimal", "system_style": "analytical"},
    count=30, seed=99,
)
for tc in cases:
    tp = tc.task_params
    v1b = tp["value1_base"]
    v2b = tp["value2_base"]
    d = tp["question_direction"]
    if d == "bigger":
        winner_base = max(v1b, v2b)
    else:
        winner_base = min(v1b, v2b)
    if v1b == winner_base:
        exp_pos = "first"
    else:
        exp_pos = "second"
    if tp["correct_position"] != exp_pos:
        errors.append(f"GEN FAIL: {tc.test_id} expected pos={exp_pos}, got {tp['correct_position']}")
print(f"Generator same_unit correctness: {len(cases)} cases checked")

# =====================================================================
# 4. Generator equal
# =====================================================================
eq_cases = gen.generate_batch(
    config={"comparison_type": "equal", "count": 10},
    prompt_config={"user_style": "casual", "system_style": "analytical"},
    count=10, seed=42,
)
for tc in eq_cases:
    tp = tc.task_params
    if tp["expected_answer"] != "equal":
        errors.append(f"EQUAL FAIL: {tc.test_id} expected='equal', got {tp['expected_answer']}")
    if tp["correct_position"] != "equal":
        errors.append(f"EQUAL POS FAIL: {tc.test_id}")
    # Check base values are very close
    if abs(tp["value1_base"] - tp["value2_base"]) > 0.01:
        errors.append(f"EQUAL BASE FAIL: {tc.test_id}: {tp['value1_base']} vs {tp['value2_base']}")
print(f"Generator equal cases: {len(eq_cases)} checked")

# =====================================================================
# 5. Generator incomparable
# =====================================================================
ic_cases = gen.generate_batch(
    config={"comparison_type": "incomparable", "count": 10},
    prompt_config={"user_style": "casual", "system_style": "analytical"},
    count=10, seed=42,
)
for tc in ic_cases:
    tp = tc.task_params
    if tp["expected_answer"] != "incomparable":
        errors.append(f"INCOMPAT FAIL: {tc.test_id}")
    if "+" not in tp["category"]:
        errors.append(f"INCOMPAT CAT FAIL: {tc.test_id}: {tp['category']}")
print(f"Generator incomparable cases: {len(ic_cases)} checked")

# =====================================================================
# 6. Parser tests
# =====================================================================
parser_tests = [
    # (response, task_params, expected_value)
    (r"\boxed{1 mm}", {"value1": "1", "unit1_symbol": "mm", "value2": "0.1", "unit2_symbol": "mm"}, "1 mm"),
    ("**0.2 kg**", {"value1": "0.2", "unit1_symbol": "kg", "value2": "0.11", "unit2_symbol": "kg"}, "0.2 kg"),
    ("They are equal.", {}, "equal"),
    ("These cannot be compared — different units.", {}, "incomparable"),
    ("Answer: 5 km", {"value1": "5", "unit1_symbol": "km", "value2": "3", "unit2_symbol": "km"}, "5 km"),
    ("The first one.", {"value1": "10", "unit1_symbol": "cm", "value2": "5", "unit2_symbol": "cm"}, "10 cm"),
    ("", {}, None),
    ("I think 3/4 cup is more.", {"value1": "3/4", "unit1_symbol": "cup", "value2": "1/2", "unit2_symbol": "cup"}, "3/4 cup"),
    ("Both values are the same.", {}, "equal"),
    ("You can't compare kilograms to meters!", {}, "incomparable"),
    ("The second option, 100 mph.", {"value1": "50", "unit1_symbol": "km/h", "value2": "100", "unit2_symbol": "mph"}, "100 mph"),
]
for resp, tp, exp in parser_tests:
    pa = parser.parse(resp, tp)
    ok = pa.value == exp
    status = "OK" if ok else "FAIL"
    print(f"  {status}: parse({resp[:50]!r}...) -> {pa.value!r} [{pa.parse_strategy}]")
    if not ok:
        errors.append(f"PARSER FAIL: input={resp!r}, got={pa.value!r}, expected={exp!r}")

# =====================================================================
# 7. Evaluator tests
# =====================================================================
# Normal correct
pa_ok = ParsedAnswer(value="1 mm", raw_response="1 mm", parse_strategy="boxed", confidence=0.95)
er = evaluator.evaluate(pa_ok, "1 mm", {"comparison_type": "same_unit", "correct_position": "first", "value1": "1", "unit1_symbol": "mm"})
if not er.correct:
    errors.append(f"EVAL FAIL: normal correct: {er.match_type}")
else:
    print(f"  OK: evaluator normal correct -> {er.match_type}")

# Normal wrong
pa_wr = ParsedAnswer(value="0.1 mm", raw_response="0.1 mm", parse_strategy="bold", confidence=0.90)
er = evaluator.evaluate(pa_wr, "1 mm", {"comparison_type": "same_unit", "correct_position": "first", "value1": "1", "unit1_symbol": "mm"})
if er.correct:
    errors.append("EVAL FAIL: normal wrong should be wrong")
else:
    print(f"  OK: evaluator normal wrong -> {er.match_type}")

# Equal correct
pa_eq = ParsedAnswer(value="equal", raw_response="they are equal", parse_strategy="keyword_equal", confidence=0.9)
er = evaluator.evaluate(pa_eq, "equal", {"comparison_type": "equal"})
if not er.correct or er.match_type != "correct_equal":
    errors.append(f"EVAL FAIL: equal correct: {er.match_type}")
else:
    print(f"  OK: evaluator equal correct -> {er.match_type}")

# Incomparable correct
pa_ic = ParsedAnswer(value="incomparable", raw_response="cannot compare", parse_strategy="keyword_incomparable", confidence=0.9)
er = evaluator.evaluate(pa_ic, "incomparable", {"comparison_type": "incomparable"})
if not er.correct or er.match_type != "correct_incomparable":
    errors.append(f"EVAL FAIL: incomparable correct: {er.match_type}")
else:
    print(f"  OK: evaluator incomparable correct -> {er.match_type}")

# Parse error
pa_err = ParsedAnswer(value=None, raw_response="dunno", parse_strategy="fallback", confidence=0.1, error="No answer found")
er = evaluator.evaluate(pa_err, "1 mm", {"comparison_type": "same_unit"})
if er.correct:
    errors.append("EVAL FAIL: parse error should be wrong")
else:
    print(f"  OK: evaluator parse error -> {er.match_type}")

# =====================================================================
# 8. Multilingual prompts
# =====================================================================
for lang in ["en", "es", "fr", "de", "zh", "ua"]:
    cases = gen.generate_batch(
        config={"comparison_type": "same_unit", "number_format": "integer", "language": lang, "count": 1},
        prompt_config={"user_style": "casual", "system_style": "analytical"},
        count=1, seed=42,
    )
    tc = cases[0]
    if not tc.prompts["user"]:
        errors.append(f"LANG FAIL: {lang} produced empty user prompt")
    else:
        print(f"  OK: lang={lang} prompt starts with: {tc.prompts['user'][:60]}...")

# =====================================================================
# Summary
# =====================================================================
print()
if errors:
    print(f"FAILURES ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
else:
    print("ALL PASSED")
