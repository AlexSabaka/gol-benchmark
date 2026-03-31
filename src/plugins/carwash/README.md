# Carwash Paradox

> **Task type:** `carwash` | **Answer type:** Always "drive"

Tests whether the model understands that you must *drive* to a carwash — the car needs to physically be there, regardless of how close it is. The proximity framing ("it's only 50 meters away") is the trap: models frequently recommend walking, forgetting the goal requires the car. Correct answer is always "drive".

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Combinatorial scenario generation from distances, framings, weather, urgency, transport details |
| `prompts.py` | User prompt templates (6 languages x 3 styles) |
| `parser.py` | Response parsing (7 strategies) with conditional/dismissive walk filtering |
| `evaluator.py` | Binary drive/walk classification |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `distances` | multi-select | all | Distance descriptions: 50m, 100m, 200m, corner, 2min_walk |

## Generation

Combinatorial from 5 dimensions:
- **Distances** (5) — proximity framings
- **Framings** (6) — car-dirty setups
- **Weather** (4) — nil, nice, sunny, cold
- **Urgency** (4) — nil, not rushing, free time, urgent
- **Transport details** (3) — nil, parked outside, in driveway
- **Question variants** (6) — walk or drive phrasing

## Parsing Strategies

1. **boxed** — LaTeX `\boxed{drive|walk}`
2. **bold** — bold text (filters conditional walk in surrounding context)
3. **first_sentence** — unambiguous signal in opening line (< 120 chars)
4. **label_line** — "Answer:", "Recommendation:", "Decision:" (last match)
5. **strong_intro** — "you should", "definitely", "the best option is" (last match)
6. **full_text** — score entire response for drive/walk keywords
7. **last_sentences** — score last 5 sentences

**Conditional walk filtering** (v2.10.3-v2.10.4): Excludes mentions like "if walk", "only walk if", "walking won't", "walking back", "walk for exercise", concession patterns, and dismissive statements. First-sentence strategy and contextual bold filtering added in v2.10.4.

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `correct` | Model answered "drive" |
| `naive_trap` | Model answered "walk" (fell for proximity) |
| `parse_error` | Could not classify response |
| `wrong` | Other answer |

**Scoring:** 1.0 for "drive", 0.0 for anything else.

## Languages

EN, ES, FR, DE, ZH, UA — each with `linguistic`, `casual`, and `minimal` prompt styles. Distances, framings, weather, urgency, and questions are localized.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
