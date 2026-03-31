# Arithmetic Expression Evaluation

> **Task type:** `arithmetic` | **Answer type:** Numeric value

Tests LLM ability to evaluate mathematical expressions with varying complexity levels and operator mixes. Expressions are generated via tree-based construction targeting specific numeric results, ensuring solvability and controlled difficulty.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Expression generation using `MathExpressionGenerator` with target values |
| `prompts.py` | User prompt templates (EN, 3 styles) |
| `parser.py` | Response parsing (6 strategies including LaTeX support) |
| `evaluator.py` | Numeric comparison with tolerance |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `complexity` | multi-select | [2, 3] | Expression complexity levels (1-5) |
| `expressions_per_target` | number | 10 | Expressions generated per target value |
| `target_values` | text | `1,2,3,4,5` | Comma-separated target result values |
| `mode` | select | `expression` | `expression` or `equation` mode |

## Parsing Strategies

1. **json_unescape_latex** — handle escaped LaTeX in JSON responses
2. **latex_boxed** — extract from `\boxed{number}` patterns
3. **keyword_search** — look for keywords (`answer`, `result`, `final answer`, etc.)
4. **equals_pattern** — find `= number` patterns
5. **last_number** — extract the last number in response (skips percentages)
6. **answer_patterns** — regex for common answer formats (`answer:`, `result:`, `solution:`)

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `exact` | Predicted value equals expected exactly |
| `approximate` | Within relative error <= 1e-9 |
| `mismatch` | Numeric answer extracted but incorrect |
| `conversion_error` | Could not convert parsed string to number |
| `parse_error` | No numeric answer found in response |

**Scoring:** 1.0 for correct (exact or approximate), 0.0 otherwise. Aggregates include per-complexity breakdown.

## Languages

EN only — `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
