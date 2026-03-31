# Family Relations

> **Task type:** `family_relations` | **Answer type:** Integer (person count)

Tests perspective-aware reasoning on family counting puzzles. The classic trap: "Sally has 3 brothers. Each brother has 2 sisters. How many sisters does Sally have?" (answer: 1, not 2 — Sally herself is one of the sisters). Models must avoid counting the subject as their own sibling.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Procedural puzzle generation with 4 sub-types |
| `prompts.py` | User prompt templates (EN, 3 styles) |
| `parser.py` | Integer extraction (7 strategies) |
| `evaluator.py` | Exact integer match with overcounting/undercounting diagnostics |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `sub_types` | multi-select | all | `sibling_count`, `shared_children`, `generational`, `perspective_shift` |
| `count` | number | 20 | Total puzzles to generate |

## Sub-Types

| Sub-Type | What It Tests | Classic Trap |
|----------|---------------|-------------|
| `sibling_count` | Self-reference avoidance | Counting yourself as your own sibling |
| `shared_children` | Shared-node deduction | "Each daughter has one brother" = 1 brother total, not 1 each |
| `generational` | Grandparent/cousin counting | Shared ancestors across branches |
| `perspective_shift` | Multi-perspective constraints | Same family viewed from different members |

## Parsing Strategies

1. **boxed** — `{answer}` or `\boxed{answer}`
2. **bold** — `**answer**`
3. **label_line** — "The answer is X"
4. **is_n_tail** — "is N" or "is N." at end
5. **last_number** — last integer in response
6. **spelled_out** — spelled-out number conversion ("three" -> 3)
7. **fallback** — low-confidence extraction

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `correct` | Predicted count equals expected |
| `overcounting` | Predicted > expected (classic trap: counted self as sibling) |
| `undercounting` | Predicted < expected (missed a family member) |
| `parse_error` | Could not extract an integer |

**Scoring:** 1.0 for correct, 0.0 otherwise. Diagnostics track predicted value, expected value, template used, trap type, and difficulty.

## Languages

EN only — `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
