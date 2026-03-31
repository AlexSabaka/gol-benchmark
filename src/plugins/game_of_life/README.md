# Conway's Game of Life

> **Task type:** `game_of_life` | **Answer type:** 2D grid of 0s/1s

Tests LLM ability to apply Conway's cellular automaton rules (birth/survival) to predict the next generation of a grid. Grids range from 3x3 (easy) to 10x10 (nightmare), with configurable density and a mix of known Life patterns and random states. Exercises rule-based grid transformation and spatial reasoning.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Grid generation using `GameOfLifeEngine` with known patterns and random states |
| `prompts.py` | User prompt templates (6 languages x 3 styles) |
| `parser.py` | Response parsing (4 strategies) |
| `evaluator.py` | Cell-by-cell grid comparison with normalized accuracy |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `difficulty_levels` | multi-select | all | Grid complexity: EASY (3x3), MEDIUM (5x5), HARD (7x7), NIGHTMARE (10x10) |
| `grids_per_difficulty` | number | 10 | Cases generated per difficulty level |
| `density` | float | 0.5 | Live-cell density ratio (0.1-0.9) |
| `known_patterns_ratio` | float | 0.3 | Fraction of grids using known Life patterns vs random |
| `cell_markers` | text | `1,0` | Live/dead cell display markers (emoji supported since v2.10.1) |
| `exclude_empty` | boolean | false | Regenerate if initial grid is all dead cells |

## Parsing Strategies

1. **line_scan_reverse** — scan from end of response looking for grid-shaped line patterns
2. **marker_search** — look for keywords (`next:`, `result:`, `grid:`, `state:`) and extract following grid
3. **digit_extraction** — extract rectangular pattern of 0s and 1s from response body
4. **last_resort** — collect all digits and arrange into expected grid dimensions

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `exact` | Every cell matches expected grid |
| `partial` | Some cells correct, some wrong |
| `mismatch` | Grid extracted but mostly wrong |
| `parse_error` | Could not extract a grid from response |
| `dimension_mismatch` | Extracted grid has wrong dimensions |

**Scoring:** Cell-by-cell accuracy normalized via `2 * (raw - 0.5)`, mapping chance-level (0.5) to 0 and perfect to 1.0.

## Languages

EN, ES, FR, DE, ZH, UA — each with `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
