# Picross (Nonogram)

> **Task type:** `picross` | **Answer type:** 2D binary grid

Tests LLM ability to solve Nonogram (Picross) puzzles — deduce which cells in a grid are filled or empty using only row and column clue numbers. Each clue lists the lengths of consecutive filled-cell groups in order. Puzzles range from 3×3 (trivial) to 15×15 (nightmare), with a constraint-propagation line solver ensuring all generated puzzles are fairly solvable without guessing. Exercises deductive reasoning, constraint satisfaction, and spatial grounding.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `solver.py` | Line solver (constraint propagation) + backtracking solver for uniqueness validation |
| `grid_gen.py` | Random puzzle generation with line-solvability and uniqueness checks |
| `generator.py` | Test case generation with 3 clue formats, partial-solution mode, ConfigField schema |
| `prompts.py` | User prompt templates (6 languages × 3 styles) |
| `parser.py` | Response parsing (4 strategies) with marker normalization |
| `evaluator.py` | Cell-by-cell grid comparison with normalized accuracy |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `difficulty` | multi-select | `["easy"]` | Puzzle size: `trivial` (3×3), `easy` (5×5), `hard` (10×10), `nightmare` (15×15) |
| `puzzles_per_difficulty` | number | 10 | Cases generated per difficulty level |
| `density` | float | 0.5 | Filled-cell density ratio (0.2–0.8) |
| `require_line_solvable` | boolean | true | Only emit puzzles solvable by constraint propagation alone (no guessing) |
| `clue_format` | select | `inline` | How clues are presented: `inline` (numbered list), `grid_header` (visual vertical alignment), `json` (structured object) |
| `require_unique` | boolean | true | Require exactly one solution (validated via backtracking) |
| `cell_markers` | text | `1,0` | Filled/empty cell display markers |
| `partial_solution` | boolean | false | Reveal ~50% of cells as hints (blanked cells marked as unknown) |

## Clue Formats

### `inline` (default)

```
Rows:
  Row 1: 3
  Row 2: 1 1
Columns:
  Col 1: 2
  Col 2: 1 1
```

### `grid_header`

Full vertical alignment with visual separator — helps models ground clues to column positions:

```
     1 2
     2 1
   ─┼────
  3 │. . .
1 1 │. . .
```

### `json`

```json
{"rows": [[3], [1, 1]], "cols": [[2], [1, 1]]}
```

## Solver

The line solver uses constraint propagation: for each row/column, it enumerates all valid placements of clue groups consistent with known cell values, then intersects them to determine forced cells. This repeats until no progress is made. Puzzles that fully resolve via this method are "line-solvable" — they require no backtracking or guessing.

The backtracking solver exhaustively searches for solutions (up to a configurable cap) and is used during generation to verify uniqueness. It is not used during evaluation.

## Parsing Strategies

1. **line_scan_reverse** — scan from end of response, collect lines matching grid row patterns, build grid bottom-up
2. **marker_search** — look for keywords (`solution`, `grid`, `answer`, `result`, `output`, `resolved`) and extract following grid
3. **digit_extraction** — extract rectangular pattern of binary values from response body
4. **last_resort** — collect all binary tokens and arrange into expected grid dimensions

**Marker normalization:** X/., ■/□, #/-, and configured cell markers are all normalized to 1/0 before grid construction.

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `exact` | Every cell matches expected grid |
| `partial` | Some cells correct, some wrong (>50% raw accuracy) |
| `mismatch` | Grid extracted but mostly wrong (≤50% raw accuracy) |
| `dimension_mismatch` | Extracted grid has wrong dimensions |
| `parse_error` | Could not extract a grid from response |

**Scoring:** Cell-by-cell accuracy normalized via `2 * (raw - 0.5)`, mapping chance-level (0.5) to 0 and perfect to 1.0. Parse errors score 0.0.

**Aggregate metrics:** Standard accuracy + `normalized_accuracy` (mean of per-case normalized scores).

## Languages

EN, ES, FR, DE, ZH, UA — each with `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
