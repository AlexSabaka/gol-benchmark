# Strawberry (Character Reasoning)

> **Task type:** `strawberry` | **Answer type:** Integer / String / Boolean

Tests character-level reasoning across six sub-types: letter counting (the classic "how many R's in strawberry?"), word reversal, nth-letter extraction, anagram detection, pangram checking, and lipogram verification. These tasks probe whether models can reason about individual characters rather than relying on tokenization-level patterns.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Word selection with repeated-letter preference, sub-type routing |
| `prompts.py` | User prompt templates (6 languages x 3 styles) with per-sub-type templates |
| `parser.py` | Response parsing (8 strategies) with sub-type-specific extraction |
| `evaluator.py` | Type-specific evaluation (integer, string, boolean) |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `sub_types` | multi-select | [count] | Sub-types: `count`, `reverse`, `nth_letter`, `anagram`, `pangram`, `lipogram` |
| `sub_type_weights` | weight_map | equal | Relative selection weights per sub-type |
| `mode` | select | mixed | Count mode: `real`, `absent_letter`, `random`, `mixed` |
| `word_lengths` | multi-select | all | Word length tiers: `short`, `medium`, `long`, `extra_long` |
| `favor_repeated` | boolean | true | Prefer letters that appear multiple times (count mode) |
| `random_word_min` | number | 5 | Min length for random words |
| `random_word_max` | number | 12 | Max length for random words |
| `mixed_weights` | weight_map | equal | Probability weights for count mixed mode |

## Parsing Strategies

1. **boxed** — `{answer}` or `\boxed{answer}`
2. **bold** — `**answer**`
3. **label_line** — "The answer is X" patterns
4. **is_n_tail** — "is X" or "is X." at end of response
5. **last_number** — last integer in response (count sub-type only)
6. **first_number** — first integer in response (count sub-type only)
7. **spelled_out** — spelled-out number conversion ("three" -> 3)
8. **fallback** — low-confidence extraction

For boolean sub-types (anagram, pangram, lipogram): extracts yes/no. For reverse: extracts reversed word. For nth_letter: extracts single character.

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `correct` | Answer matches expected value |
| `wrong` | Answer extracted but incorrect |
| `parse_error` | Could not extract answer |

**Scoring:** 1.0 for correct, 0.0 otherwise. Evaluation is type-specific: integer exact match (count), case-insensitive string match (reverse, nth_letter), boolean match (anagram, pangram, lipogram).

## Languages

EN, ES, FR, DE, ZH, UA — each with `linguistic`, `casual`, and `minimal` prompt styles. Templates are per-sub-type with localized intro text and answer cues.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
