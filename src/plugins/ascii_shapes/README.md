# ASCII Shapes Spatial Reasoning

> **Task type:** `ascii_shapes` | **Answer type:** Dimensions / count / boolean

Tests LLM spatial reasoning on ASCII art shapes with three question types: measuring dimensions (WxH), counting symbol occurrences, and checking whether a symbol exists at a given coordinate. Shapes can be filled or outlined, using configurable symbols.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Shape generation with `AsciiShapesEngine`, random parameters per test |
| `prompts.py` | User prompt templates (6 languages x 3 styles) |
| `parser.py` | Response parsing (3 specialized parsers routed by question type) |
| `evaluator.py` | Type-specific evaluation with swapped-dimensions detection |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `question_types` | multi-select | all | `dimensions`, `count`, `position` |
| `width_range` | range | [3, 10] | Shape width range (1-50) |
| `height_range` | range | [3, 8] | Shape height range (1-50) |
| `symbols` | multi-select | [*, #, X] | Drawing symbols (*, #, X, O, +, @) |
| `coordinate_labels` | boolean | false | Add row/column labels to grid |
| `filled_ratio` | float | 0.7 | Probability of filled vs outlined shapes |

## Parsing Strategies

Routed by `question_type`:

**Dimensions:**
- WxH patterns, "W by H", width/height keywords, natural language ("chars across, lines down")
- Last match; fallback to last two numbers

**Count:**
- "answer:", "there are", "=", standalone numbers
- Last match; fallback to last number in response

**Position:**
- Positive words (yes, true, present, exists) vs negative words (no, false, absent, not present)
- Uses end position of last occurrence for tie-breaking

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `exact` | Answer matches expected value |
| `swapped` | Dimensions are correct but width/height swapped |
| `mismatch` | Answer extracted but incorrect |
| `parse_error` | Could not extract an answer |
| `type_error` | Extracted value has wrong type for question |

**Scoring:** 1.0 for correct, 0.0 otherwise. Aggregates include per-question-type breakdown.

## Languages

EN, ES, FR, DE, ZH, UA — each with `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
