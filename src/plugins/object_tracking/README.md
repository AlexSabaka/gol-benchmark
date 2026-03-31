# Object Tracking (Grape Test)

> **Task type:** `object_tracking` | **Answer type:** Location name

Tests LLM ability to track an object's location through a sequence of physical steps, especially when a container is inverted — causing the object to fall out and remain at the drop location even if the container moves afterward. Distractors (irrelevant, spatial, temporal) add difficulty.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Scenario generation using `StepBuilder` with inversion and post-move logic |
| `prompts.py` | User prompt templates (EN, 3 styles) |
| `parser.py` | Response parsing (7 strategies) with location normalization |
| `evaluator.py` | Location matching with synonym equivalence groups |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `object` | multi-select | grape, marble, keys, coin, ring, pill, button, pebble | Tracked objects |
| `container` | multi-select | cup, bowl, bucket, mug, box, jar, glass | Container types |
| `location_initial` | multi-select | counter, table, shelf, desk, dresser, nightstand | Starting locations |
| `subject` | multi-select | [I] | Narration subject |
| `distractor_count` | multi-select | [0, 1, 2] | Number of distractor steps (0-4) |
| `post_inversion_moves` | multi-select | [0, 1, 2] | Container moves after inversion (0-3) |
| `distractor_types` | multi-select | all | `irrelevant`, `spatial`, `temporal` |
| `sticky_objects` | multi-select | [] | Objects that don't fall when inverted |

## Parsing Strategies

1. **single_word** — response is a single meaningful word
2. **answer_prefix** — "Answer: X", "The answer is X", "Location: X"
3. **bold_keyword** — first bold text matching a known location (first-match, not end-first)
4. **first_sentence_location** — known location in first sentence (first-match, not end-first)
5. **sentence_pattern** — "[object] is on/in the [location]" (last match)
6. **location_keyword** — known locations from task params (last match)
7. **last_word** — last meaningful word as fallback

**Note:** Strategies 3-4 use first-match because models bold the answer upfront then mention distractor locations in explanations. See [end-first exceptions](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

Post-parsing: location normalization with synonym groups (countertop -> counter, etc.).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `exact` | Location matches expected (case-insensitive) |
| `synonym_match` | Matched via location equivalence group |
| `raw_match` | Matched raw parsed value |
| `partial` | Partial string overlap (not counted as correct) |
| `mismatch` | Wrong location extracted |
| `parse_error` | Could not extract a location |
| `no_answer` | Empty response |

**Scoring:** 1.0 for correct (exact or synonym), 0.0 otherwise. Difficulty auto-computed from distractor count (weight 1), post-inversion moves (weight 2), and late inversion (weight 1). Aggregates include difficulty, distractor, and object breakdowns.

## Languages

EN only — `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
