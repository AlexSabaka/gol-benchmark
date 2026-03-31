# Time Arithmetic

> **Task type:** `time_arithmetic` | **Answer type:** Time / Day / Duration / "impossible"

Tests temporal reasoning across seven sub-types: interval arithmetic, midnight-crossing durations, noon/midnight AM/PM traps, day-of-week modular math, impossible date detection, leap year edge cases, and DST spring-forward/fall-back holes. Models must handle 12h/24h formats, boundary conditions, and correctly refuse impossible dates.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Time/date scenario generation with sub-type routing and trick questions |
| `prompts.py` | User prompt templates (6 languages x 3 styles) |
| `parser.py` | Response parsing with validity detection, time normalization, and multilingual day names |
| `evaluator.py` | Temporal comparison with correct-refusal/wrong-compliance tracking |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `sub_types` | multi-select | all except dst_trap | `interval`, `crossing_midnight`, `noon_midnight_trap`, `day_of_week`, `impossible_date`, `leap_year`, `dst_trap` |
| `sub_type_weights` | weight_map | equal | Relative frequency per sub-type |
| `include_trick_questions` | boolean | true | Include impossible_date and leap_year |
| `direction` | select | both | `forward`, `backward`, `both` (add vs subtract) |
| `time_format` | select | 12h | `12h` or `24h` |

## Parsing Strategies

**Validity detection** (for impossible/leap year questions):
1. **first_yes_no** — first yes/no in response (first-match, not end-first)
2. **label_yes_no** — "The answer is yes/no"
3. **boxed** / **bold** — boxed or bolded validity keyword
4. **refusal_keyword** — "impossible", "invalid", "doesn't exist"
5. **validity_keyword** — "valid", "possible", "exists"

**Time/day extraction** (for arithmetic questions):
- **final_answer_label** — "Final answer: ..." (highest priority)
- **time_pattern** — 12/24-hour time with AM/PM normalization
- **day_pattern** — multilingual day-name normalization (EN, ES, FR, DE, UA, ZH)
- **`_extract_day_last()`** helper for day-of-week sub-type

Verification-section stripping (`strip_verification_tail`) applied before parsing. First-bold and first-sentence strategies used for validity questions. See [end-first exceptions](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `correct` | Exact match on time/day/duration |
| `wrong` | Incorrect answer to a valid question |
| `correct_refusal` | Correctly identified impossible date/time |
| `wrong_compliance` | Confidently answered an impossible question (hallucination) |
| `wrong_refusal` | Falsely refused a valid question |
| `parse_error` | Could not extract answer |

**Scoring:** 1.0 for `correct` or `correct_refusal`, 0.0 otherwise. Time comparison normalizes to minutes-since-midnight. Day comparison uses canonical multilingual normalization.

## Languages

EN, ES, FR, DE, ZH, UA — each with `linguistic`, `casual`, and `minimal` prompt styles. Day names supported in all 6 languages for evaluation.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
