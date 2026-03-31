# Symbol Arithmetic

> **Task type:** `symbol_arithmetic` | **Answer type:** Symbol from operation table

Tests pure rule-following on arbitrary binary operation tables over abstract symbol sets. No mathematical semantics — the model must look up results from a provided table without importing unwarranted algebraic assumptions (commutativity, associativity) from training. Detects when models silently assume these properties.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Operation table and expression tree generation with configurable algebraic properties |
| `prompts.py` | User prompt templates (EN, 3 styles) |
| `parser.py` | Symbol extraction (7 strategies) with undefined detection |
| `evaluator.py` | 8-type match taxonomy revealing algebraic assumption patterns |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `difficulty` | select | medium | `easy` (3 sym, commutative, depth 1), `medium` (4 sym, non-commutative, depth 2), `hard` (5 sym, non-associative, depth 3), `nightmare` (6 sym, arbitrary, depth 4, partial table) |
| `count` | number | 10 | Test cases |
| `set_size` | number | 4 | Symbol set size (3-6) |
| `expression_depth` | number | 2 | Nested operation depth (1-5) |
| `operation_class` | select | non_commutative | `commutative`, `non_commutative`, `non_associative`, `arbitrary` |
| `table_completeness` | select | full | `full` or `partial` (some cells undefined) |

## Symbol Pools

| Pool | Symbols |
|------|---------|
| ALPHA | A-Z (26 uppercase letters) |
| EMOJI | Colored circles, squares (18 symbols) |
| NONSENSE | FOO, BAR, BAZ, QUX, ZAP, MIX |

## Parsing Strategies

1. **undefined_detection** — detects "UNDEFINED", "undefined", "unknown"
2. **boxed_symbol** — `{symbol}` or `\boxed{symbol}`
3. **labelled_answer** — "The answer is X"
4. **equals_pattern** — "X =" pattern
5. **bold_symbol** — `**symbol**`
6. **last_symbol** — last word/symbol in response
7. **fallback** — low-confidence extraction

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `correct` | Right symbol |
| `wrong_assumed_commutative` | Wrong, but matches a commuted variant (swapped operand order) |
| `wrong_assumed_associative` | Wrong, but matches a regrouped variant (changed parenthesization) |
| `wrong_arbitrary` | Wrong, no classifiable assumption |
| `undefined_correct` | Correctly flagged an undefined lookup |
| `undefined_wrong` | Invented an answer for an undefined operation |
| `undefined_missed` | Falsely claimed a defined operation is undefined |
| `parse_error` | Could not extract an answer |

**Scoring:** 1.0 for `correct` or `undefined_correct`, 0.0 otherwise.

**Diagnostic metrics:**
- Commutativity assumption rate: `n_commuted_wrong / total_wrong`
- Associativity assumption rate: `n_associated_wrong / total_wrong`
- Undefined detection rate
- Per-dimension breakdowns: operation_class, expression_depth, table_format, symbol_type

## Languages

EN only — `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
