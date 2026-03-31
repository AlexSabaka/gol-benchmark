# 1D Cellular Automata

> **Task type:** `cellular_automata_1d` | **Answer type:** 1D binary array

Tests LLM ability to apply Wolfram elementary cellular automaton rules (0-255) to predict the next generation of a 1D binary state. Each rule defines 8 neighborhood-to-output mappings that the model must apply correctly across the full width with configurable boundary conditions.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | State generation using `CellularAutomata1DEngine` with boundary modes |
| `prompts.py` | User prompt templates (6 languages x 3 styles) with localized boundary descriptions |
| `parser.py` | Response parsing (4 strategies) |
| `evaluator.py` | Cell-by-cell comparison with length mismatch handling |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `rules` | multi-select | [110, 30, 90] | Wolfram rule numbers to test (30, 54, 60, 90, 110, 150, 182) |
| `tests_per_rule` | number | 10 | Cases generated per rule |
| `width` | number | 16 | Grid width (5-50 cells) |
| `steps` | number | 1 | Evolution steps to predict (1-20) |
| `boundary` | select | `wrap` | Boundary handling: `wrap`, `dead`, `alive` |
| `cell_markers` | text | `1,0` | Alive/dead cell markers (emoji supported since v2.10.2) |

## Parsing Strategies

1. **marker_search** — look for "Final Answer:", "Next state:", etc. (last match)
2. **line_scan** — find lines with space-separated 0s/1s (reverse order)
3. **code_block** — extract from code blocks (last block first)
4. **digit_extraction** — extract 0s and 1s from response body (from end)

Accepts space-separated, comma-separated, and continuous formats. All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `exact` | All cells match expected state |
| `partial` | Some cells correct (overlapping portion if length >= 8) |
| `mismatch` | State extracted but mostly wrong |
| `length_mismatch` | Different number of cells than expected |
| `parse_error` | Could not extract a 1D state from response |

**Scoring:** Cell-by-cell accuracy normalized via `2 * (raw - 0.5)`. Length mismatches compare the overlapping portion when min length >= 8. Aggregates include per-rule breakdown.

## Languages

EN, ES, FR, DE, ZH, UA — each with `linguistic`, `casual`, and `minimal` prompt styles. Boundary descriptions are localized per language.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
