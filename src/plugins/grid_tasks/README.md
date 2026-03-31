# Grid Tasks (Table Reasoning)

> **Task type:** `grid_tasks` | **Answer type:** Varies by question

Tests LLM ability to read and reason about formatted text tables. Questions include cell lookups, row sums, column counts, filtered counts, and min/max identification. Tables are generated with realistic data types (sales, HR, grades, inventory) and rendered in multiple table styles.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Table generation with 4 data types and 5 question types |
| `prompts.py` | User prompt templates (EN, 3 styles) |
| `parser.py` | Response parsing (5 strategies) with JSON extraction |
| `evaluator.py` | Multi-mode evaluation (exact, case-insensitive, numeric tolerance, partial) |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cases_per_config` | number | 10 | Cases per prompt configuration |
| `min_rows` / `max_rows` | number | 2 / 20 | Table row count range |
| `min_cols` / `max_cols` | number | 2 / 10 | Table column count range |
| `data_types` | multi-select | all | `sales`, `hr`, `grades`, `inventory` |
| `question_types` | multi-select | all | `cell_lookup`, `row_sum`, `column_count`, `filter_count`, `max_min` |
| `table_style` | select | unicode | `unicode`, `mysql`, `gfm`, `reddit`, `plain`, `html` |

## Data Types

| Type | Columns |
|------|---------|
| `sales` | Product, Salesperson, Region, Month, Quantity, Revenue, Commission, Quarter |
| `hr` | Employee, Department, Salary, Title, Hire Date |
| `grades` | Student, Subject, Score, Date |
| `inventory` | Product ID, Description, Quantity, Location, Price |

## Parsing Strategies

1. **json_extraction** — extract `{"answer": "X"}` from response
2. **structured_parsing** — structured format detection
3. **regex_patterns** — common answer format patterns
4. **last_line** — extract from final line of response
5. **fallback** — low-confidence extraction

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `exact` | Case-sensitive text match |
| `case_insensitive` | Matched after lowering case |
| `numeric_tolerance` | Numeric match within tolerance (default 0.1) |
| `numeric_mismatch` | Both are numbers but don't match |
| `partial_contains` | Expected value found within response |
| `partial_subset` | Subset match |
| `mismatch` | Answer extracted but wrong |
| `parse_error` | Could not extract answer |
| `no_answer` | Empty response |

**Scoring:** 1.0 for exact, case_insensitive, or numeric_tolerance matches; 0.0 otherwise.

## Languages

EN only — `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
