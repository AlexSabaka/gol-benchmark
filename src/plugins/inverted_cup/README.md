# Inverted Cup

> **Task type:** `inverted_cup` | **Answer type:** "flip"

Tests spatial reasoning and object orientation. A cup is described with its top sealed and bottom open — the model must realize the solution is to flip/turn/invert it. Common failure modes include suggesting to drill a hole, cut the seal, or discard the cup entirely.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Combinatorial scenario generation from sources, descriptions, actions, extra contexts |
| `prompts.py` | User prompt templates (EN, 3 styles) |
| `parser.py` | Response parsing (6 strategies) with flip/wrong pattern matching |
| `evaluator.py` | Binary flip/wrong classification |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `description_styles` | multi-select | all 7 | Cup description styles (sealed_top_open_bottom, lid_top_hole_bottom, upside_down_explicit, rim_at_bottom, inverted_normal, mouth_down, closed_on_top) |

## Generation

Combinatorial from 4 dimensions:
- **Sources** (7) — gift, bought, found, joke, birthday, souvenir, competition
- **Description styles** (7) — different ways to describe the inverted cup
- **Action questions** (7) — use to drink, correct way, how to drink, etc.
- **Extra contexts** (5) — nil, transparent, plastic, permanent seal, identical

## Parsing Strategies

1. **boxed** — LaTeX `\boxed{flip|turn|...}`
2. **bold** — bold text (last match)
3. **label_line** — "Answer:", "Action:", "Solution:" (last match)
4. **strong_recommendation** — "you should", "simply", "just", "the solution is" (last match)
5. **full_text** — scan entire response for flip/wrong patterns
6. **last_sentences** — score last 5 sentences

**Flip patterns:** flip, turn (over/upside-down), invert, rotate 180, upend, upright, right-side-up, tilt, tip, mouth-facing-up.
**Wrong patterns:** drill, cut hole, power tool, saw, poke, return to shop, throw away, useless.

**Note:** If "flip" is mentioned anywhere, the model understood the key insight — "wrong" keywords alongside flip are just creative alternatives. See [end-first exceptions](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention).

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `correct` | Model suggested flipping/turning the cup |
| `wrong` | Model suggested a destructive or irrelevant solution |
| `parse_error` | Could not classify the response |

**Scoring:** 1.0 for flip, 0.0 otherwise.

## Languages

EN only — `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
