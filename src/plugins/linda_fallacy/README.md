# Linda Conjunction Fallacy

> **Task type:** `linda_fallacy` | **Answer type:** Probability ranking

Tests LLM susceptibility to the conjunction fallacy — the cognitive bias where people judge P(A and B) > P(A). Given a persona description, models rank statements by probability. The fallacy is detected when a conjunction item (A and B) is ranked higher than either component (A or B) alone.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Persona and statement generation using `LindaBenchmark` with culture alignment |
| `prompts.py` | User prompt templates (language-dependent, 3 styles) |
| `parser.py` | Response parsing (4 strategies) with ranking extraction and deduplication |
| `evaluator.py` | Conjunction fallacy detection via fuzzy matching |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `num_options` | number | 8 | Number of statements to rank (3-10) |
| `personas_per_config` | number | 5 | Personas generated per config |
| `culture_filter` | select | (all) | Culture alignment: western, east_asian, south_asian, african, middle_eastern, latin_american, european |

## Parsing Strategies

1. **explicit_ranking_section** — look for RANKING/CLASIFICACION headers
2. **numbered_list_fallback** — find numbered lists anywhere in response
3. **probability_keyword** — extract lines with probability mentions (most/least probable)
4. **sentence_extraction** — find statements about persona using keywords

Post-parsing deduplication via word-level Jaccard similarity (> 0.85 = duplicate).

**Note:** This plugin extracts ordered rankings, not positional single answers — end-first does not apply in the usual sense. See [end-first exceptions](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `exact` | Correct ranking extracted |
| `fallacy_detected` | Conjunction ranked above component(s) — model fell for the bias |
| `no_fallacy` | Model avoided the conjunction trap |
| `conjunction_not_found` | Could not locate the conjunction item in ranking |
| `components_not_found` | Could not locate component items in ranking |

**Scoring:** 1.0 if the model avoided the fallacy, 0.0 if it fell for it. Fuzzy matching (substring, normalized, character overlap > 0.8) used for statement identification.

## Languages

Language-dependent via `LindaBenchmark` — EN, ES, FR with culture-aligned personas. Each with `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
