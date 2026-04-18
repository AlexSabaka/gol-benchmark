# TECHDEBT

Living register of postponed decisions, incomplete refactors, workarounds, and known limitations in GoL Benchmark. Companion to [CHANGELOG.md](CHANGELOG.md): the changelog records what shipped, this file records what was intentionally left undone or what shipped with caveats.

> **Last audited:** 2026-04-18 (against v2.25.0)
> **Maintenance:** When closing a debt item, move its row into the `## Resolved` section at the bottom with a version + date stamp. When opening a new item, use the next free `TD-NNN` ID.

## Conventions

- **Severity** — `high` (impairs correctness, security, or significant maintenance), `medium` (slows future work, fragile), `low` (cosmetic, organizational)
- **Effort** — `S` (~1h), `M` (~half day), `L` (~1+ day), `XL` (multi-day refactor)
- IDs are stable (`TD-001`, `TD-002`, …); never renumber. Use the next free ID for new entries.

---

## 1. Postponed / Deferred Work

Features and implementations that were explicitly punted to a later iteration, with the placeholder still in the tree.

| ID | Item | Where | Severity | Effort | Notes |
|----|------|-------|----------|--------|-------|
| TD-001 | `HuggingFaceProvider.list_models()` returns `[]` with `# TODO: Implement HF model listing` | [src/utils/model_providers.py:302-305](src/utils/model_providers.py#L302) | medium | M | Provider is registered and used by the web UI dropdown — empty list silently degrades the UX. Either implement against the HF Hub API or remove the provider from the registry. |
| TD-002 | `_generate_radar_comparison()` is a `pass` placeholder | [src/stages/analyze_results.py:2810-2811](src/stages/analyze_results.py#L2810) | low | M | Comment says "Skip for now if too complex". Caller still invokes it; the function silently no-ops, so radar charts are missing from generated reports. |
| TD-003 | Decimal-framing measure comparison: English-only templates | `src/plugins/measure_comparison/` | medium | M | v2.8.1 CHANGELOG: "English-only framing templates for now (multilingual deferred)". Other 5 languages fall back to EN, so the test isn't really multilingual for this sub-type. |
| TD-004 | Encoding & Cipher: English-only framing templates | `src/plugins/encoding_cipher/` | medium | M | v2.9.0 / v2.13.0 CHANGELOG entries: "English-only prompts for v1 (multilingual deferred)". Same pattern as TD-003 — partial multilingual coverage. |
| TD-005 | Translation provider chain depends on `deep-translator` upstream | [src/web/translation.py](src/web/translation.py) | low | S | v2.20.0: ships with Google as default (no API key) but no rate-limit handling. `mymemory` fallback exists but provider switching is env-only — no admin UI. |

---

## 2. Incomplete Refactors

Migrations that landed the new system but left the old code in place for compatibility. The shipped state works; cleanup is what's owed.

| ID | Item | Where | Severity | Effort | Notes |
|----|------|-------|----------|--------|-------|
| TD-010 | **PromptEngine legacy template body still in tree (~1500 lines)** | [src/core/PromptEngine.py](src/core/PromptEngine.py) (lines ~272–1582) | high | L | v2.8.0 migrated all user-prompt templates to plugin-local `prompts.py` files; v2.19.0 relabeled the old code from "Deprecated" to "Legacy (still used by `generate_testset.py` — not removed yet)". Until `generate_testset.py` is updated to call only the plugin path, the legacy templates can't be deleted. PROBE: confirm what `generate_testset.py` still pulls from PromptEngine, then remove sections incrementally per task type. |
| TD-011 | `src/benchmarks/linda_eval.py` — entire deprecated module retained | [src/benchmarks/linda_eval.py](src/benchmarks/linda_eval.py) | medium | S | Emits a runtime `DeprecationWarning` on import; superseded by `src/plugins/linda_fallacy/`. Confirm no callers, then delete the module + the `src/benchmarks/` directory if it becomes empty. |
| TD-012 | Abandoned plugin directory: `crossword_puzzle/` | [src/plugins/crossword_puzzle/](src/plugins/crossword_puzzle/) | low | S | Folder contains only `open_dictionary_processed.csv` — no `__init__.py`, generator, parser, or evaluator. Either complete the plugin or remove the folder + dictionary. |
| TD-014 | 8 plugin generators carry an empty `__init__(self): pass` | `src/plugins/{carwash,false_premise,misquote,measure_comparison,strawberry,inverted_cup,grid_tasks,family_relations}/generator.py` | low | S | Boilerplate left over from a refactor where state moved to the base class. A no-op `__init__` is harmless but confusing — prefer removing the override entirely. |
| TD-015 | Plugin "Legacy"-vs-"Deprecated" labelling is inconsistent | [src/core/PromptEngine.py](src/core/PromptEngine.py) header + per-section comments | low | S | Some sections say "DEPRECATED", others "Legacy", and the module docstring uses both. Pick one term and align — currently grep'ing for either misses the other. |

---

## 3. Workarounds & Architectural Smells

Patterns that work but are fragile or violate the codebase's own conventions. Each one is something a future developer will trip over.

| ID | Item | Where | Severity | Effort | Notes |
|----|------|-------|----------|--------|-------|
| TD-020 | **Bare `except: pass` cluster in numeric/dimension parsing** | [src/stages/run_testset.py:280-281, 340-341, 554-555, 561-562](src/stages/run_testset.py#L280) | high | M | Four bare-except blocks silently swallow `ValueError`, `IndexError`, `AttributeError`, etc. Real parsing failures surface as "wrong answer" instead of being logged. Replace with typed exceptions and at least a `logger.debug()`. |
| TD-021 | FastAPI route ordering is order-dependent (load-bearing comments) | [src/web/api/human_review.py](src/web/api/human_review.py) (header comment), [src/web/api/analysis.py](src/web/api/analysis.py) | medium | M | Comments explicitly warn "specific routes must come before `{filename}` catch-all". Listed in `.claude/CLAUDE.md` as Known Issue #6. Move catch-all `/{filename}` routes to a separate router mounted last, or use explicit path prefixes (`/files/{filename}`). |
| TD-022 | Circular import: `src/web/jobs.py` ↔ `src/web/judge.py` | [src/web/jobs.py](src/web/jobs.py), [src/web/judge.py](src/web/judge.py) | medium | M | v2.19.0 CHANGELOG documents this: "progress-tracking closures mirror the module-level helpers" exists specifically to break the cycle. Extract progress-tracking primitives into a third module (e.g. `src/web/job_progress.py`) so neither imports the other. |
| TD-023 | `noqa: E402` import ordering bypass | [src/stages/run_testset.py:52](src/stages/run_testset.py#L52) | low | S | A late-bound import sidesteps PEP 8 to defer model-interface loading. Likely related to optional deps (torch/transformers). Review whether the late import is still required or can move to module top. |
| TD-024 | Silent `except Exception: pass` in YAML system-prompt loader | [src/core/PROMPT_STYLES.py:160-165](src/core/PROMPT_STYLES.py#L160) | medium | S | Falls back to hardcoded `SYSTEM_PROMPTS` if the YAML loader throws — but the failure is invisible. Add `logger.warning()` so a malformed YAML file doesn't silently change behavior. |
| TD-025 | `JobManager` is a process-global singleton with mutable state | [src/web/jobs.py](src/web/jobs.py) (727 lines, instantiated at module level) | medium | L | Routes import the singleton and mutate it directly. Breaks ergonomic testability and makes lifecycle non-explicit. Move to FastAPI `Depends()` with an app-state-bound instance. |
| TD-026 | `_stash_prompt_config()` smuggles state via instance attribute | [src/plugins/base.py:258](src/plugins/base.py#L258) | low | M | A `self._custom_system_prompt` is set/cleared around `generate_batch()` so the call signature doesn't have to change. Works, but invisible coupling between caller and method. Pass via the existing `prompt_config` dict instead. |
| TD-027 | Object-tracking parser uses **first-match** instead of project-standard end-first | [src/plugins/object_tracking/parser.py](src/plugins/object_tracking/parser.py) | low | — | **Intentional** (see CLAUDE.md "End-First Parsing Convention") — models bold the answer first then enumerate distractors. Documented exception, not actual debt. Listed here so future readers don't try to "fix" it. |
| TD-028 | Time-arithmetic validity uses **first-bold/first-sentence** detection | [src/plugins/time_arithmetic/parser.py](src/plugins/time_arithmetic/parser.py) | low | — | Same shape as TD-027 — yes/no validity questions get the answer upfront. Intentional exception, documented for future readers. |
| TD-029 | Carwash parser fragility around `\bno\b` boundary | [src/plugins/carwash/parser.py](src/plugins/carwash/parser.py) | low | M | v2.2.0 CHANGELOG flags this as a recurring false-positive vector ("no" inside "not", "nothing", "know"). Currently passes via word-boundary regex but assumes English. v2.23.1 added 6-language negation patterns (`WALK_NEGATION` / `DRIVE_NEGATION`) and dual-keyword filtering (`_is_conditional_drive` / `_is_conditional_walk`) that mitigate many false positives — but the `\bno\b` boundary issue in particular remains unaddressed. |
| TD-030 | `parse_utils.py` `re_search_last()` consumes iterator with `for last in it: pass` | [src/plugins/parse_utils.py:40-45](src/plugins/parse_utils.py#L40) | low | S | Idiomatic but opaque. `more_itertools.last()` or `deque(it, maxlen=1)` reads more clearly. |
| TD-093 | **`_PRE_WALK_CONDITIONAL` trailing-anchor dead code** — 4 patterns include the walk keyword inside the alternation group, then the trailing `.{0,80}?\b(?:walk\|walking)\b` requires a SECOND walk mention that rarely exists | [src/plugins/carwash/parser.py](src/plugins/carwash/parser.py) `_PRE_WALK_CONDITIONAL` | low | S | Affected patterns: `(?:walk\|walking)\s+or\s+(?:driv\w+)`, `(?:walk\|walking)\s+(?:vs\.?\|versus)\s+(?:driv\w+)`, `\bwhether\s+to\s+(?:walk\|walking)`, `\b(?:determine\|decide\|choose)\s+(?:\w+\s+){0,4}(?:walk\|walking)`. These all consume "walk" inside the alternation, so the trailing anchor requires a second "walk" that isn't there. The same patterns in `_WALK_CONDITIONAL` (which has no trailing anchor) DO work. Fix: either remove the dead patterns from `_PRE_WALK_CONDITIONAL` or restructure the regex so the alternation captures only the conditional keyword (not walk). Low priority — `_WALK_CONDITIONAL` covers the same cases. |
| TD-094 | **`_is_conditional_walk` uses window-proximity matching; `_is_conditional_drive` uses positional matching** — design asymmetry | [src/plugins/carwash/parser.py](src/plugins/carwash/parser.py) | low | M | v2.23.1 added `_is_conditional_drive` with positional matching (`finditer` + span-containment check) because window proximity was too aggressive for drive filtering — a listing phrase 50 chars before the drive position would false-filter it. `_is_conditional_walk` still uses the older window approach (120 chars back + 80 forward). This asymmetry is acceptable because over-filtering walk rarely hurts (walk = wrong answer in carwash), but for consistency and correctness the walk function should also adopt positional matching. Blocked by TD-093 — the dead-code `_PRE_WALK_CONDITIONAL` patterns would need cleanup first since they can't be converted to positional matching (they include the keyword itself). |
| TD-080 | `text_pattern` regex candidate kind is near-redundant post-v2.4 | [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py) `_context_anchored_regex` + `_auto_regex_with_meta` | low | S | The legacy span-text-LCP fallback is only meaningful for synthetic test data with empty `before` context. Every real annotated case has a 120-char window + either a `context_anchor` or `format_only` / `merged_label_disjunction` lead. Existing tests depend on it (`test_v2_span_group_confidence_levels`, `test_v2_1_regex_test_harness_match_rate`) so removal isn't zero-effort. PROBE: run a week of real annotations, confirm `text_pattern` never leads the sort in practice, then remove + update those two tests to use a `context_anchor`-shaped setup. |
| TD-081 | `_model_answer_distribution` is a backwards-compat shim | [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py) | low | S | v2.4 refactored the primary helper to `_model_answer_stats` returning `(distribution, variants)`. The old `_model_answer_distribution` is now just `return _model_answer_stats(...)[0]`. Kept to avoid churning v2.2-era tests. Remove the shim once `test_v2_2_model_answer_distribution_strips_markdown` (and any external callers) is migrated to call `_model_answer_stats` directly. |
| TD-082 | No stemming — `walk` and `walking` live in separate model-answer buckets | [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py) `_strip_markdown` / `_is_aligned` | low | — | **Intentional** per v2.3 alignment semantics ("different stems count as misaligned — surfacing those differences is the whole point"). Listed here so future "helpful" PorterStemmer additions don't silently over-merge buckets the agent needs to see as distinct. Re-evaluate only when the agent asks for a `by_lemma_group` field explicitly. |
| TD-083 | `label` format's capture shape is greedy-to-terminator | [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py) `_format_capture` | medium | M | The `label` format emits a non-greedy capture up to the next `.` or newline (see `_format_capture`). On real responses this captures entire sentences like `Definitively walk to the carwash` when the agent wanted `walk`. The capture-quality metrics surface this (high `match_rate`, lower `capture_exact_rate`) but the generator itself doesn't attempt a "tighten" pass. Fix: emit a second `label` candidate that caps capture at 3 words or the first content word after a filler adverb. |
| TD-084 | Legacy `_auto_regex` / `_auto_regex_with_meta` retained but no longer primary | [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py) | low | S | v2.2 moved regex generation to `_context_anchored_regex`; the v1 span-text LCP helpers (`_auto_regex`, `_auto_regex_with_meta`) are now only invoked via the `text_pattern` fallback path (see TD-080). Resolving TD-080 would also unblock deletion of these. |
| TD-085 | `api_key` / `api_base` stored in plaintext `jobs.json` | [src/web/job_store.py](src/web/job_store.py), [src/web/jobs.py](src/web/jobs.py) | medium | M | v2.21.0: `Job.to_storable_dict()` serialises all execution params including `api_key` and `api_base` to `jobs.json`. Anyone with read access to the file sees API credentials. Fix: encrypt the credential fields at rest (e.g. `cryptography.fernet`), or store only a credential reference (key name in a secrets store) rather than the raw value. Short-term: document that `jobs.json` must be in `.gitignore` and on a mode-600 path (CLAUDE.md Known Issue #11). |
| TD-086 | Resume creates a new job ID — paused row stays visible as "Cancelled (superseded)" | [src/web/jobs.py](src/web/jobs.py) `resume()`, [src/web/api/execution.py](src/web/api/execution.py) | low | M | v2.21.0 design: `resume()` marks the paused job CANCELLED with `error="Superseded by resumed job"` and returns a fresh job ID. The Jobs page therefore shows two rows for what is conceptually one run. Fix options: (a) reuse the original job ID on resume and update it in-place; (b) add a `parent_job_id` foreign key so the UI can group them; (c) hide "Superseded" rows in the default table filter. |
| TD-087 | `partial_<job_id>.json.gz` orphaned on server crash mid-pause | [src/web/jobs.py](src/web/jobs.py) `_save_partial_results()` | low | S | v2.21.0: the partial file is written by the worker, then deleted on successful resume + completion. If the server crashes between pause signal and final deletion the partial file lives indefinitely in `results/`. Fix: on server startup, scan `results/` for `partial_*.json.gz` files whose `job_id` appears in the store with state CANCELLED/COMPLETED and delete stale ones. |
| TD-089 | **`_BOLD_HEADER_RE` exclusion list in encoding_cipher parser is a hardcoded set** | [src/plugins/encoding_cipher/parser.py](src/plugins/encoding_cipher/parser.py) `_BOLD_HEADER_RE` | low | S | Added in v2.22.1 to prevent `_try_bold_plaintext` from returning section headers (`Step N:`, `Final Answer:`, etc.) as decoded plaintext. The list covers observed patterns from 12 result files but is not exhaustive — new models with different header phrasing will require manual additions. Fix: derive exclusion heuristics from the improvement-report `label_taxonomy` field (spans where `answer_label_match = 0` but `label_colon = 1`) rather than a static list. |
| TD-090 | **encoding_cipher parser ignores `parse_strategy` (encoding type) in task_params** | [src/plugins/encoding_cipher/parser.py](src/plugins/encoding_cipher/parser.py) | low | M | v2.22.1 made the generator emit `parse_strategy = enc_type` (`"base64"` / `"caesar"` / `"morse"`) into `task_params`, but the parser doesn't yet branch on it. Each encoding type has distinct output characteristics (base64 → alphanumeric-only output; caesar/ROT-N → decoded text with recognizable English words; morse → dash/dot input, decoded English text). Specialised per-type label patterns (e.g. `rot13` in label for caesar) and output-format validators (e.g. reject base64-encoded string as plaintext) could sharply reduce `wrong_decode` for adversarial responses. |
| TD-091 | **No unit tests for the 4 new decode_only strategies added in v2.22.1** | [tests/plugins/](tests/plugins/) | medium | M | `_try_context_anchored_bold`, `_try_blockquote_after_label`, `_try_italic_phrase`, `_try_bold_plaintext` are covered only by integration-level tests (59 existing tests pass). Each strategy should have its own unit test asserting the correct span is extracted for the canonical example from each annotation group (Groups A–E), and that it returns `None` on non-matching input. Without these, a future regex tweak can silently regress a group. |
| TD-092 | **`"fancy_unicode"` still listed in `_LEGACY_TASK_TYPES` after plugin restoration** | [src/stages/analyze_results.py](src/stages/analyze_results.py) `_LEGACY_TASK_TYPES`, [src/web/reanalyze.py](src/web/reanalyze.py) `_TASK_TYPE_SUFFIXES` | medium | S | v2.19.0 added `"fancy_unicode"` to `_LEGACY_TASK_TYPES` when the skeleton was removed. Now that the plugin is fully implemented and auto-discovered by `PluginRegistry.list_task_types()` (v2.23.0), the entry is redundant — `fancy_unicode` will appear in both the registry list and the legacy list, potentially causing duplicate task-type inference in filename parsing. Fix: remove `"fancy_unicode"` from `_LEGACY_TASK_TYPES` and confirm `_TASK_TYPE_SUFFIXES` in `reanalyze.py` picks it up from the registry. Also track as language debt: `fancy_unicode` is EN-only (like `encoding_cipher`, TD-004) — multilingual extension deferred due to partial coverage in non-Latin scripts. |
| TD-088 | **Improvement Report v2.7 — agent-facing structural additions** (v2.6 data additions landed) | [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py), [frontend/src/components/review/improvement-report-dialog.tsx](frontend/src/components/review/improvement-report-dialog.tsx) | medium | L | v2.6 landed `negative_span_groups`, `context_anchor_groups`, `manual_keyword_distribution`, auto-inferred `parser_was_correct` — see CHANGELOG v2.24.0. Remaining structural additions deferred to v2.7: `priority_actions[]` (ranked refactor actions computed from `regex_test[]` × `count` × `capture_contains_rate`); `parser_fingerprint` (plugin / source hash / emitted `parse_strategy` literals / timestamp); per-group `count_aligned` / `count_misaligned`; per-group `closest_existing_strategy` + `strategy_gap`; `conflicts[]` (surprising class combos); `avoid_patterns[]` (high-fire-low-capture); frontend "Priority actions" tab. Related to TD-043 — v2.7 work naturally forces that split. |
| TD-095 | **Per-case annotation delete endpoint missing** | [src/web/api/human_review.py](src/web/api/human_review.py) | medium | M | The existing `DELETE /annotations/{result_file_id}` wipes the entire sidecar for a file. There's no way to delete a single case's annotation (e.g. to clear a contaminated entry). The current workaround is response-hash validation that silently drops contaminated entries on load — but if a `response_class` is wrong without a span (the hash match passes but the class is stale), there's no UI affordance to clear it. Add `DELETE /annotations/{result_file_id}/{case_id}` or a `POST /annotations/{result_file_id}/{case_id}/clear` endpoint. Frontend would need a "Clear annotation" button in the review workspace footer. |
| TD-096 | **`_response_hash` uses MD5 of first 128 chars — theoretical collision risk** | [src/web/api/human_review.py](src/web/api/human_review.py) `_response_hash()` | low | S | MD5(first 128 chars) → 8 hex chars = 4,294,967,296 buckets. For a single result file with at most a few thousand entries, collision probability is negligible in practice. However, if two different responses happen to share identical first-128-char prefixes (possible with templated or short responses), their sidecar entries would collide. Consider: (a) extending the prefix to 256 chars, (b) hashing the full response, or (c) using a stronger hash. The current implementation is safe for all observed real-world testsets but the assumption should be revisited if templated/short-response plugins are annotated at scale. |
| TD-097 | **`picture_algebra` split-RNG invariant is load-bearing and invisible** | [src/plugins/picture_algebra/generator.py](src/plugins/picture_algebra/generator.py) `generate_batch()` — `token_rng_seed = seed ^ 0xA1B2C3D4` | medium | S | v2.25.0 — the plugin exists to measure the GSM-Symbolic accuracy delta between surface forms, which only works if the **same seed + different `surface_form` → identical underlying math**. Emoji pool sampling consumes RNG state that alpha/nonsense slicing doesn't, so a single shared RNG silently drifts after the first emoji case. Fix shipped via a second `token_rng` seeded from `seed ^ 0xA1B2C3D4`. One cross-surface-form reproducibility test guards it ([tests/plugins/test_picture_algebra.py](tests/plugins/test_picture_algebra.py) `test_same_seed_same_math_across_surface_forms`), but nothing in the file structure telegraphs the invariant — a future refactor that "cleans up" by unifying RNGs would silently break the experimental design. Fix options: (a) inline a doctest in `generate_batch()` that asserts structures match, (b) extract a `_TokenPicker` class that owns its own RNG and makes the separation obvious, (c) document the XOR constant with a named `_TOKEN_RNG_OFFSET`. |
| TD-098 | **`picture_algebra.foreign_labels` strategy is ASCII-only by design** | [src/plugins/picture_algebra/parser.py](src/plugins/picture_algebra/parser.py) `_strategy_foreign_labels` | low | M | v2.25.0 — the strategy detects `<word> = <int>` assignments using a label that isn't one of our tokens, surfaces them as-is so the evaluator returns `wrong_variable`. The regex is intentionally restricted to `[A-Za-z][A-Za-z_0-9]{0,5}` so a stray `n = 3` in reasoning text doesn't masquerade as an answer. **Consequence**: when an `emoji`-surface-form problem is answered with *different* emoji (model picked 🍇/🍊 when asked about 🍎/🍌), the strategy won't fire and `last_numbers` positional fallback will silently return a `correct`-looking match against our tokens. Currently unobserved in smoke tests but a real hole in the `wrong_variable` metric for emoji-vs-emoji confusion. Fix: extend the foreign-label alphabet to include Unicode symbol ranges when `surface_form == "emoji"`. |
| TD-099 | **`picture_algebra.operations='all'` rendering path untested** | [src/plugins/picture_algebra/generator.py](src/plugins/picture_algebra/generator.py) `_render_term` | low | S | v2.25.0 — tests exercise `add_only` (via `easy` preset) and `add_subtract` (default), but `add_multiply` and `all` — the two modes with mixed numeric prefixes and subtraction signs — have no coverage. `_render_term` carries conditional branches for all four modes; a regression there (e.g. wrong sign placement for `all` with coef=-1) would ship silently. Add one test per operations mode asserting a fixed seed produces a stable equation string. |
| TD-100 | **`picture_algebra._verify_unique` swallows sympy exceptions** | [src/plugins/picture_algebra/generator.py](src/plugins/picture_algebra/generator.py) `_verify_unique`, `_is_consistent` | low | S | v2.25.0 — both helpers wrap `linsolve` in `try/except Exception: return False`. A genuine sympy bug or malformed input would cause silent rejection followed by up to 30 resamples, then a `RuntimeError("Unable to generate…")`. No log line ever surfaces why. Replace the broad except with specific `(ValueError, NotImplementedError, TypeError)` and log at `DEBUG` so pathological inputs are diagnosable. |
| TD-101 | **13 pre-existing plugin test failures not tracked** | [tests/plugins/test_ascii_shapes.py](tests/plugins/test_ascii_shapes.py) (4), [tests/plugins/test_cellular_automata_1d.py](tests/plugins/test_cellular_automata_1d.py) (3), [tests/plugins/test_linda_fallacy.py](tests/plugins/test_linda_fallacy.py) (6) | medium | M | Discovered during v2.25.0 picture_algebra integration — `pytest tests/plugins/` reports 13 failures across 3 plugins that exist on `dev` / `feat/improvements` branches and are unrelated to any recent change. Failures include `test_generate_count_question` (ascii_shapes), `test_generate_batch_basic` (C14), `test_parse_numbered_list` (linda_fallacy), among others. These already-red tests mask future regressions: a new failure in one of these plugins will blend into the existing redness. Fix: either repair the tests (update fixtures to current plugin behavior) or skip-with-reason while the underlying plugin is reworked, so CI gives a meaningful signal again. |

---

## 4. God Modules (Refactor Candidates)

Files that have outgrown a single responsibility and would benefit from splitting. Severity reflects how often they're touched and how hard they are to navigate.

| ID | File | Lines | Severity | Effort | Suggested split |
|----|------|-------|----------|--------|-----------------|
| TD-040 | [src/stages/analyze_results.py](src/stages/analyze_results.py) | **3,439** | high | XL | `result_loader.py` (file IO + reanalyze hooks) · `metrics.py` (aggregation) · `report_generator.py` (HTML/markdown) · `visualizations/` (per-chart files). Already imported as `_re`, `_random` aliases — name-mangling smells. |
| TD-041 | [src/core/PromptEngine.py](src/core/PromptEngine.py) | **1,787** | high | L | Resolves with TD-010. Once legacy templates are removed, the active surface (`Language`, `PromptStyle`, `SystemPromptStyle`) is small enough to live in `src/core/prompts/` with one file per concern. |
| TD-042 | [src/plugins/measure_comparison/generator.py](src/plugins/measure_comparison/generator.py) | **1,319** | medium | L | Extract `units.py` (unit table + i18n) + `conversions.py` (unit-system math). Generator-proper would shrink ~70%. |
| TD-043 | [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py) | **~2,100** (v2.6) | high | L | Grew from 1,057 (v2.20.0) through v2.1/2.2/2.3/2.4/2.5/2.6 iterations. v2.6 added `_collect_negative_records`, `_negative_span_analysis`, `_answer_keyword_distribution`, `_context_anchor_groups` (+~150 lines). Now contains per-axis breakdowns, data quality auto-diagnostics, parser-span alignment, anchor classification, merged-disjunction synthesis, capture-quality harness, model-answer distribution + variants, strategy ranking, n-gram extraction, long-tail group collapse, negative mark aggregation — all in one module. Suggested split: `alignment.py` (normalize/align helpers + parser_span_alignment), `span_groups.py` (_span_analysis + _split_long_tail + helpers), `regex_gen.py` (_context_anchored_regex, _merged_label_disjunction, _filter_candidates, _regex_test_harness), `negative_marks.py` (v2.6 negative span/keyword pipeline), `breakdowns.py` (axis + strategy), `data_quality.py`, `model_answers.py`. Severity remains `high` — most-edited file in the project. |
| TD-044 | [src/plugins/false_premise/parser.py](src/plugins/false_premise/parser.py) | **967** | medium | M | Five domains share a parser; extract `refusal_detection.py` and per-domain heuristics. |
| TD-045 | [src/web/jobs.py](src/web/jobs.py) | **~430** (post-v2.21.0 split — `job_store.py` extracted) | medium | M | Resolves partially with TD-025 and the v2.21.0 `JobStore` extraction. Remaining candidates: job state machine, queue logic, worker orchestration, pause/resume each ~100–150 lines. |
| TD-046 | [frontend/src/pages/execute/matrix-wizard.tsx](frontend/src/pages/execute/matrix-wizard.tsx) | **1,383** | low | M | Step components inline. Extract one file per step (Setup/Axes/Models/Settings/Review) — pattern already used elsewhere via `components/wizard/`. |
| TD-047 | [frontend/src/pages/configure.tsx](frontend/src/pages/configure.tsx) | **1,123** | low | M | Same wizard pattern — Setup/Plugins/Prompts/Review. Plugin-config row rendering should move to a dedicated `components/plugin-config/` file. |
| TD-048 | [frontend/src/components/review/improvement-report-dialog.tsx](frontend/src/components/review/improvement-report-dialog.tsx) | ~1,380 (v2.6) | medium | M | Grew from ~520 lines at v2.20.0 to ~1,380 across six iterations (v2.6 added `NegativesTab` + `NegativeMarkGroup`/`ContextAnchorGroup` types). Now 10 tabs + 11+ sub-components all in one file. Suggested split: one file per tab under `components/review/improvement-report/` with a thin dialog wrapper. Keeps bundle chunking manageable and makes iterating on a single tab less risky. |

---

## 5. Type & Lint Suppressions

Bypasses that hide a real type/lint problem under a comment. Each `type: ignore` and `eslint-disable` is a deferred fix.

| ID | Item | Where | Severity |
|----|------|-------|----------|
| TD-050 | Two consecutive `# type: ignore[union-attr]` on `re.search().group()` | [src/plugins/time_arithmetic/evaluator.py:176-177](src/plugins/time_arithmetic/evaluator.py#L176) | low |
| TD-051 | `# type: ignore[assignment]` on operation-table dict | [src/plugins/symbol_arithmetic/generator.py:350](src/plugins/symbol_arithmetic/generator.py#L350) | low |
| TD-052 | `// eslint-disable-next-line @typescript-eslint/no-explicit-any` on Recharts `shape` prop | [frontend/src/components/charts/scaling-scatter.tsx:169](frontend/src/components/charts/scaling-scatter.tsx#L169) | low |

Frontend overall has very low TypeScript debt — only one `any` in the active tree.

---

## 6. Test Coverage Gaps

Plugins that exist and ship in production but have **no** dedicated test file. The plugin system has 21 registered plugins; tests cover 13 fully and 2 partially.

| ID | Plugin | Status |
|----|--------|--------|
| TD-069 | `fancy_unicode` | No test file — parser has 10 strategies + refusal/runaway sentinels; evaluator has 7-type taxonomy + plaintext-evidence heuristic; all untested |
| ~~TD-060~~ | ~~`carwash`~~ | **Resolved v2.23.1** — 93 tests across 17 classes; see Resolved section |
| TD-061 | `family_relations` | No test file |
| TD-062 | `grid_tasks` | No test file |
| TD-063 | `measure_comparison` | No test file (despite being one of the largest plugins — TD-042) |
| TD-064 | `misquote` | No test file |
| TD-065 | `sally_anne` | No test file (parser had a v2.4.1 contract violation — TD-073 — that better tests would have caught) |
| TD-066 | `symbol_arithmetic` | No test file |
| TD-067 | `false_premise` | Parser tests only ([test_false_premise_parser.py](tests/plugins/test_false_premise_parser.py)); generator + evaluator untested |
| TD-068 | `inverted_cup` | Parser tests only ([test_inverted_cup_parser.py](tests/plugins/test_inverted_cup_parser.py)); generator + evaluator untested |

**Severity:** medium overall. High for `measure_comparison` and `false_premise` because they have the most parsing logic.

---

## 7. Repo Hygiene & Documentation Drift

| ID | Item | Where | Severity |
|----|------|-------|----------|
| TD-070 | Untracked PRD lives at repo root | [PRD_Human_Review_Feature.md](PRD_Human_Review_Feature.md) | low — should move under `docs/research/` or be deleted now that v2.20.0 has shipped the feature |
| TD-071 | `jobs.json` (persistent job-manager state) lives at repo root and is not in `.gitignore` | `jobs.json` | low — path is now configurable via `GOL_JOBS_FILE` env var (v2.21.0); still needs a `.gitignore` entry, and the default path should arguably move to a dedicated `data/` or `run/` dir rather than the repo root |
| TD-072 | Plugin folder count (22) ≠ registered plugin count (21) | `src/plugins/` | low — resolves with TD-012 (crossword_puzzle is the only remaining undeclared folder; TD-013 closed v2.23.0, picture_algebra added v2.25.0) |
| TD-073 | `.claude/CLAUDE.md` Known Issue list is the de-facto debt register | [.claude/CLAUDE.md](.claude/CLAUDE.md) "Known Issues & Gotchas" | low — items 6, 7, 8, 9, 10 in that list are debt items, not gotchas. Once this file matures, link from CLAUDE.md to here for the maintenance perspective. |

---

## 8. Acknowledged Limitations (NOT debt — listed for context)

These are documented constraints that are unlikely to be "fixed" — included so future readers understand they were considered intentional rather than overlooked.

- **False Premise — 9 inherently ambiguous cases** (4 food_safety, 5 medicine) per v2.10.7. Genuine grey-area judgement calls; further parser tuning would over-fit.
- **Symbol Arithmetic — associativity trace guarded at 7 leaves** (Catalan-number explosion). Larger expression trees would blow the trace budget.
- **Empty-grid retry capped at 10 attempts** for GoL pattern generation (v2.10.1) — prevents pathological infinite loops at the cost of occasionally rejecting valid configs.
- **Object Tracking + Time Arithmetic parsers use first-match** (TD-027, TD-028) — documented exceptions to the project-wide end-first convention.

---

## Resolved

When a debt item is fixed, move its row here with the version + date that closed it. Keep the original ID — never reuse.

| ID | Item | Resolved In | Date |
| --- | --- | --- | --- |
| TD-013 | Abandoned plugin directory `fancy_unicode/` — fully implemented as the 20th plugin; `_LEGACY_TASK_TYPES` entry cleanup tracked separately as TD-092. | v2.23.0 | 2026-04-16 |
| TD-060 | `carwash` — no test file. Now has 93 tests across 17 classes covering all 11 strategies, multilingual keywords, bold/label/newline extraction, negative patterns, vs/comparison filtering, drive conditional filtering, new labels, "therefore" connectors, strategy emission, parsed-answer shape. | v2.23.1 | 2026-04-17 |
| TD-088 (v2.5 portion) | Improvement Report v2.5 tactical cut — delete `confusion_matrix` / top-level `anchor_frequency` / top-level `response_classes`, suppress `strategy_breakdown` + `answer_when_missed.by_expected`, add `long_tail_groups`, empty-omit `ordering_hints` / `annotator_notes`. TD-088 remains open for the v2.7 structural additions. | v2.22.0 | 2026-04-16 |
| TD-088 (v2.6 portion) | Improvement Report v2.6 data additions — `negative_span_groups[]`, `context_anchor_groups[]`, `manual_keyword_distribution`, auto-inferred `parser_was_correct` from span-parser alignment (replaces manual `parser_ok`), Negatives tab in dialog. TD-088 remains open for v2.7 structural additions (`priority_actions[]`, `parser_fingerprint`, etc.). | v2.24.0 | 2026-04-17 |

---

## Adding to This Register

When you discover or introduce tech debt:

1. Pick the next free `TD-NNN` ID (don't renumber existing entries).
2. Slot it into the matching section. If none fits, create a new section with a `## N. Title` header.
3. Always include: file:line link (use markdown link format for VSCode), severity, effort estimate.
4. If the debt is **intentional** (architectural exception), include it but mark severity `—` and explain why it's not actionable. This prevents future "helpful" reverts.
5. Cross-reference the CHANGELOG version where the debt was introduced if known.

When you fix something:

1. Move the row to `## Resolved` — don't delete it.
2. Note the version that shipped the fix.
3. If the fix introduced new debt, open a new TD entry and reference the closed one.
