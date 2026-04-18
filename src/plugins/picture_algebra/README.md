# Picture Algebra

> **Task type:** `picture_algebra` | **Answer type:** Dict of variable → integer (or sentinel for trick cases)

Tests how much a model's ability to solve small linear systems (2–3 variables, 2–4 equations, integer solutions) degrades when variables are rendered as emoji instead of letters. The underlying algebra is identical across surface forms; the measurable delta is the **semantic interference score** — the GSM-Symbolic experiment reproduced locally on any model.

## Surface forms

Run the same seed three times with different `surface_form` values to get the interference score:

| Surface form | Rendering | Example |
|---|---|---|
| `alpha` | Single letters `x`, `y`, `z` | `2·x + y = 11` |
| `emoji` | Emoji drawn from a category pool | `2·🍎 + 🍌 = 11` |
| `nonsense` | Made-up uppercase words | `2·FOO + BAR = 11` |

## Trick cases (optional)

`trick_rate > 0` mixes in underdetermined or inconsistent systems whose correct answer is a refusal sentinel (`CANNOT_BE_DETERMINED` / `NO_SOLUTION`). Models that confidently invent a numeric answer are flagged as `system_error_missed`.

## Match types

| Type | Meaning |
|------|---------|
| `correct` | Every requested variable's value is right |
| `wrong_value` | Model solved for the right variables but at least one value is wrong |
| `wrong_variable` | Model solved for different variables than asked |
| `partial` | Some variables right, some wrong (`question_scope=all` only) |
| `system_error` | Correctly refused an impossible / underdetermined system |
| `system_error_missed` | Gave a confident numeric answer to an impossible system |
| `system_error_false_positive` | Refused a solvable system — hallucinated impossibility |
| `parse_error` | Parser could not extract an answer |

## Aggregation

`aggregate_results` includes breakdowns by `surface_form`, `emoji_category`, `operations`, `num_variables`, `determinacy`, and `question_scope`. When a batch contains both `alpha` and `emoji` cases, a top-level `semantic_interference_delta` appears — the accuracy gap between those surface forms.
