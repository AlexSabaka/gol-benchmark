# Sally-Anne Test

> **Task type:** `sally_anne` | **Answer type:** Container name

Tests Theory of Mind (false belief reasoning). Subject A places an object in container A and leaves. Subject B moves the object to container B. The model must identify where Subject A *believes* the object is (container A) — not where it actually is (container B). The "reality trap" is the most common failure mode.

## Module Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration (auto-discovered) |
| `generator.py` | Scenario generation using `SallyAnneScenarioBuilder` |
| `prompts.py` | User prompt templates (EN, 3 styles) |
| `parser.py` | Response parsing (7 strategies) with reality-trap detection |
| `evaluator.py` | Belief vs reality evaluation with synonym matching |

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cases_per_config` | number | 5 | Test cases per prompt configuration |
| `subject_pairs` | list | [('Sally','female','Anne','female')] | (name_a, gender_a, name_b, gender_b) tuples |
| `objects` | text | marble,ball,toy,book,keys | Comma-separated object pool |
| `containers` | implicit | (basket,box), (drawer,cupboard), (bag,pocket) | Container pairs |
| `distractor_count` | number | 0 | Extra distractor elements (0-5) |
| `leave_activities` | text | goes for a walk, goes outside, ... | Activities for Subject A's absence |
| `include_observer` | boolean | false | Add an observer character |

## Parsing Strategies

1. **boxed** — LaTeX `\boxed{container}`
2. **bold_markdown** — last `**container**` (2-3 word bold text)
3. **answer_pattern** — "Answer: container", "answer is container"
4. **look_pattern** — "will look in the [container]", "will search [container]"
5. **last_sentence** — container mentioned in last sentence with context
6. **json** — JSON fields: answer, location, container
7. **direct_match** — count occurrences with context weighting (look_pattern context gets +2)

All strategies follow the [end-first parsing convention](../../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention). Verification-section stripping (`strip_verification_tail`) applied before parsing.

## Evaluation

| Match Type | Meaning |
|------------|---------|
| `exact` | Answered container_a (correct belief location) |
| `synonym` | Matched via container synonym |
| `reality_trap` | Answered container_b (actual location, not belief) |
| `parse_error` | Could not extract a container name |
| `wrong_container` | Answered a container not in the scenario |

**Scoring:** 1.0 for correct (belief location), 0.0 otherwise. Reality trap rate tracked as a key diagnostic metric.

## Languages

EN only — `linguistic`, `casual`, and `minimal` prompt styles.

## See Also

- [Plugin Guide](../../../docs/PLUGIN_GUIDE.md) — full plugin architecture reference
- [Project Overview](../../../docs/PROJECT_OVERVIEW.md) — benchmark suite context
