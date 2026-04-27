# `src/plugins/` Local Agent Notes

> **Pilot file** for testing whether Claude Code's subdirectory CLAUDE.md lazy-loading works reliably in this project. Verify with `/context`. If this file ends up loaded on every turn (eager-load), delete it and move content to `docs/PLUGIN_GUIDE.md`.
> **Note for the Coding Agent**: if you notice this file being loaded on unrelated tasks or requests – flag it to the user.  

This file scopes **plugin-specific** rules that don't matter outside `src/plugins/`. The root [CLAUDE.md](../../.claude/CLAUDE.md) carries cross-cutting invariants; this file carries plugin-internal ones.

For full plugin documentation see [docs/PLUGIN_GUIDE.md](../../docs/PLUGIN_GUIDE.md).

---

## Plugin layout reminder

Each plugin is a self-contained directory. The minimum scaffold:

```
src/plugins/<task>/
├── __init__.py     # plugin = <Task>Plugin()  ← module-level instance, auto-discovered
├── prompts.py      # USER_PROMPT_TEMPLATES (nested dict: lang → style → template)
├── generator.py    # generate_batch() → List[TestCase]; get_config_schema() → ConfigField[]
├── parser.py       # parse(response, task_params) → ParsedAnswer  (END-FIRST)
└── evaluator.py    # evaluate(parsed, expected, task_params) → EvaluationResult
```

Auto-discovery is in [`__init__.py`](__init__.py) (`PluginRegistry`). Drop the directory in and it loads — no central registration step.

---

## End-first parsing — the rule

**Every parser searches from the END of the response toward the start.** LLMs reason first, answer last; using `re.search()` (which returns the FIRST match) systematically extracts intermediate values.

Use the helpers in [`parse_utils.py`](parse_utils.py):

```python
from src.plugins.parse_utils import (
    safe_enum,                  # str → enum with default fallback (used by all 21 generators)
    re_search_last,             # drop-in re.search returning LAST match
    re_findall_last,            # last N matches
    last_sentences,             # last N sentences
    last_keyword_position,      # position of last keyword hit
    strip_verification_tail,    # remove trailing "Verification:" sections
    normalize_unicode,          # smart-quote + prime fold (apply at parse() entry)
    merge_keywords, merge_patterns,
    get_language,               # extract language from task_params, default "en"
    build_word_to_int,          # multilingual number-word → int map
    build_answer_label_re,      # multilingual "answer|result|respuesta|..." regex
    WORD_TO_INT, ANSWER_LABELS, YES_WORDS, NO_WORDS,
)
```

**Strategy ordering rule:**

1. Empty-response guard — `parse_strategy="empty"`
2. High-confidence strategies on RAW text (boxed, bold, JSON, code blocks) — keep these on the raw response so `**Answer:**` trailers etc. work
3. Lower-confidence strategies on `strip_verification_tail(text)` — pattern-scan, last-number, last-alpha
4. End-of-pipeline fallback — `parse_strategy="fallback"`

`parse_strategy` reserved names: only `"empty"` and `"fallback"` for terminal states. All others are plugin-specific. Do not reintroduce legacy names like `"failed"` / `"none"` / `"parse_error"` — the improvement-report aggregator groups failure modes by these labels.

---

## Multilingual / grammar — the rule

Plugins generate test content in 6 languages (EN, FR, ES, DE, ZH, UA). Each plugin has:

- **`prompts.py`** — user prompt templates per `(language, user_style)`
- **`i18n.py`** or **`<task>_i18n.py`** — localized vocabulary, question templates, narratives
- **`data/`** — per-language word lists, dataset shards

For gendered languages (UA, ES, FR, DE), use [`grammar_utils.py`](grammar_utils.py):

```python
from src.plugins.grammar_utils import (
    article,          # article(lang, gender, definite, case) → "el"/"la"/"der"/...
    resolve_vocab,    # case-inflected form lookup (UA nom/acc/loc)
    pick_templates,   # m/f template variant by subject_gender
    vocab_gender,     # grammatical gender of a noun
)
```

Subject gender is randomly assigned per test case and stored in `task_params["subject_gender"]`. Templates that conjugate verbs / decline nouns must read this.

`prompt_metadata` in `TestCase` is critical — it MUST be populated by `generate_batch`, otherwise `run_testset.py` and reanalyze cannot merge it into `task_params` for the parser/evaluator. (See root CLAUDE.md invariant #3.)

---

## Multilingual evaluators — `expected_answer_localized`

For tasks where the answer is a noun (Object Tracking, Sally-Anne), the evaluator must check BOTH `expected_answer` (English) and `expected_answer_localized` (target language) against the parsed response. A Ukrainian "тумбочці" matches localized "тумбочці" via `match_type = "localized_match"` — even though the expected English value is "nightstand".

If you add a new noun-valued task, follow the Object Tracking / Sally-Anne pattern; do not invent a new mechanism.

---

## Phase 1–8 cross-plugin alignment status

The shared-helper adoption tables live in [docs/PLUGIN_GUIDE.md § End-First Parsing Convention](../../docs/PLUGIN_GUIDE.md#end-first-parsing-convention). Quick status:

- **Phase 1** — five helpers extracted from per-plugin code into `parse_utils` (`normalize_unicode`, `normalize_for_label_matching`, `try_parse_number`, `detect_sentinel_keyword`, `has_contextual_marker`).
- **Phase 2** — `parse_strategy` naming normalized: `"empty"` / `"fallback"` reserved.
- **Phase 3** — `strip_verification_tail` adopted in 14 of 21 keyword-driven parsers. Phase 3b grid plugins (`game_of_life`, `cellular_automata_1d`, `picross`) pending annotation evidence — see TECHDEBT.
- **Phase 4** — `build_answer_label_re` + plugin-local `_EXTRA_LABELS` adopted in 9 plugins. Consolidation candidate: TD-109.
- **Phase 5** — `normalize_unicode` adopted at `parse()` entry in all 21 parsers.
- **Phase 8** — annotation-driven refactors. `object_tracking` was the first; template generalised. See `parser-refactor-from-annotations` skill.

When adding a new plugin: assume all five helpers above are required from day one. The "adopted in N of 21" framing is for legacy plugins still being migrated; new plugins start at full adoption.

---

## Common gotchas (plugin-internal)

| Symptom | Cause | Fix |
|---|---|---|
| Plugin doesn't appear in `PluginRegistry.list_task_types()` | `__init__.py` missing module-level `plugin = ...` instance, OR import error during discovery | Run `python3 -c "from src.plugins import PluginRegistry; PluginRegistry.list_task_types(); print(PluginRegistry._discovery_errors)"` to see import errors |
| Parser returns English keywords for a UA response | `language` not in `task_params` | Generator forgot `prompt_metadata=prompt_config`, OR an entry point skipped the `prompt_metadata` → `task_params` merge |
| `strip_verification_tail` deletes a legitimate `**Answer:**` trailer | Helper applied to a high-confidence strategy | Only apply to weaker pattern-scan / last-number strategies |
| Smart-quoted regex (`'`, `"`) doesn't match | Missing `normalize_unicode(response.strip())` at `parse()` entry | Add at entry; placement varies (see PLUGIN_GUIDE Phase 5) |
| Tests pass but live results regress on UA/ES/FR | Multilingual extrapolation in dicts is unvalidated | Track in TECHDEBT with a TD number; await per-language annotation |

---

## When to update this file

Update this file when:

- A new shared helper lands in `parse_utils.py` or `grammar_utils.py` and should be on the agent's hot list
- A new parser-internal convention emerges (e.g. Phase 9 if/when it happens)
- A common gotcha keeps recurring across plugin work

Do NOT update this file with:

- Per-plugin specifics (those go in PLUGIN_GUIDE per-plugin reference sections, or per-plugin README.md)
- Parser-refactor narratives (PLUGIN_GUIDE § End-First Parsing Convention)
- Release notes ([CHANGELOG.md](../../CHANGELOG.md))
- Incomplete refactors ([TECHDEBT.md](../../TECHDEBT.md))

---

*See also: [docs/PLUGIN_GUIDE.md](../../docs/PLUGIN_GUIDE.md), [.claude/CLAUDE.md](../../.claude/CLAUDE.md), [.claude/skills/add-plugin/SKILL.md](../../.claude/skills/add-plugin/SKILL.md), [.claude/skills/parser-refactor-from-annotations/SKILL.md](../../.claude/skills/parser-refactor-from-annotations/SKILL.md).*
