# Measure Comparison

> **Task type:** `measure_comparison` | **Answer type:** Measurement / "equal" / "incomparable" / decimal framing

Tests ability to compare two quantities with units, including conversion traps (cm vs inches), equal-value tricks (1 kg vs 1000 g), incomparable pairs (temperature vs weight), and adversarial decimal framing (where version-number or date-based ordering differs from numeric ordering).

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Quantity pair generation with unit conversion, equal tricks, and decimal adversarial framing |
| `prompts.py` | User prompt templates (6 languages x 3 styles) |
| `parser.py` | Response parsing (11+ strategies) with smart quote normalization |
| `evaluator.py` | Unit-normalized comparison with temperature conversion |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `number_format` | select | mixed | `integer`, `decimal`, `fraction`, `mixed` |
| `comparison_type` | select | all | `same_unit`, `mixed_unit`, `equal`, `incomparable`, `decimal`, `all` |
| `question_direction` | select | mixed | `bigger`, `smaller`, `mixed` |
| `unit_categories` | multi-select | all | length, mass, temperature, volume, speed, time |
| `decimal_trap_ratio` | number | 0.3 | Fraction of decimals with adversarial digit traps |
| `close_value_ratio` | number | 0.2 | Fraction of same-unit with very close values |
| `value_order` | select | random | `random`, `bigger_first`, `smaller_first` |
| `fraction_max_denominator` | number | 16 | Max fraction denominator |
| `max_decimal_places` | number | 3 | Max decimal places |
| `type_weights` | weight_map | equal | Custom weights for "all" mode |
| `decimal_framings` | multi-select | all | `neutral`, `decimal`, `version`, `date` |
| `decimal_adversarial_ratio` | number | 0.5 | Fraction where framings disagree on answer |

## Parsing Strategies

1. **boxed** — `{value}` or `\boxed{value}`
2. **bold** — `**value**` (keyword bolds prioritized over value bolds; headers skipped)
3. **label_line** — "The answer is X", "The larger is..."
4. **value_unit_comparative** — "X Y" where Y is a unit
5. **keyword_incomparable** — "cannot compare", "incomparable", "different kinds/types of"
6. **keyword_equal** — "are the same", "same value", "equivalent" (tightened from bare `\bsame\b`)
7. **value_unit_match** — standalone value + unit patterns (not end-first — both options mentioned)
8. **position_match** — compare extracted values by position order
9. **last_value_unit** — fallback to last value+unit found
10. **bare_value_match** — raw numeric extraction for unit-less answers
11. **reverse_comparative** — "the lighter one is X oz"

Smart quote normalization (`_normalize_quotes`) applied before all regex matching. Pipeline reordered: incomparable keywords above value_unit_match, equal keywords below.

See [end-first exceptions](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention) for value_unit_match.

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `correct` | Identified the right quantity (or correctly said equal/incomparable) |
| `wrong` | Picked the wrong quantity or wrong classification |
| `parse_error` | Could not extract an answer |

**Scoring:** 1.0 for correct, 0.0 otherwise. Evaluation handles unit-normalized base value comparison and temperature conversions (C/F/K). Decimal sub-type uses a separate 5-strategy parser.

## Languages

EN, ES, FR, DE, ZH, UA — each with `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
