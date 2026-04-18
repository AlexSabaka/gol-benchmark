# CHANGELOG

All notable changes to the GoL Benchmark project.

## [2.25.0] - April 17, 2026

### Picture Algebra — 21st Benchmark Plugin

New plugin: [src/plugins/picture_algebra/](src/plugins/picture_algebra/). System-of-equations puzzles whose variables are rendered as emoji (🍎, 🍌), alpha letters (x, y, z), or nonsense words (FOO, BAR). Operationalizes the GSM-Symbolic finding inside the benchmark suite — run the same seed across the three surface forms and measure the accuracy delta.

#### What it tests

- **Semantic interference**: same linear system, three surface forms. `aggregate_results` emits `semantic_interference_delta = accuracy(alpha) − accuracy(emoji)` when both forms are present in a batch.
- **Impossible-system sensitivity**: `trick_rate > 0` mixes in underdetermined and inconsistent systems whose correct response is a refusal sentinel (`CANNOT_BE_DETERMINED` / `NO_SOLUTION`). Models that confidently invent a numeric answer are flagged as `system_error_missed`.

#### Generator (sympy-driven)

- 2–3 variables × 2–4 equations; integer solutions verified with `sympy.linsolve` (resamples when rng picks linearly-dependent equations).
- Coefficient rendering varies by `operations`: `add_only` uses repeated addition (`🍎 + 🍎 + 🍎`), `add_multiply`/`all` use numeric prefix (`3·🍎`), `add_subtract` mixes `+` and `-` signs.
- Surface forms: `emoji` (sampled from `food` / `animals` / `objects` / `mixed` pools, 24 per pool), `alpha` (`x`, `y`, `z`), `nonsense` (`FOO`, `BAR`, `BAZ`).
- `question_scope`: `all` (solve for every variable) or `specific` (ask for one randomly chosen variable).
- Trick generation tries the primary kind (underdetermined/inconsistent) then the alternate if the first fails, before falling through to a unique system.

#### Parser (9 strategies, end-first + multilingual)

1. `cannot_be_determined` — strict sentinel check in the last 3 sentences
2. `boxed_multivar` — `\boxed{x=5, y=7}` with comma/semicolon/`\\` splits
3. `label_line` — per-variable `<token> = <number>`; numeric-first pass avoids the `"Solving for y: y = 7"` greedy-consume failure mode; word-number fallback via `build_word_to_int`
4. `bold_assignments` — `**x = 5**` markdown-bold assignments
5. `final_answer_block` — tail after `answer:` / `respuesta:` / `відповідь:` / etc.
6. `foreign_labels` — preserves non-our-token labels (`a = 5, b = 7` when asked about `x, y`) so the evaluator can classify `wrong_variable`
7. `coord_tuple` — `(5, 7)` positional, only when arity matches
8. `last_numbers` — last N integers, weakest fallback
9. `cannot_be_determined_fallback` — weaker sentinel check after extractions fail

All strategies use `re_search_last` / `re.finditer` with end-first semantics. Emoji tokens go through `re.escape()`.

#### Evaluator (8 match types)

- `correct` / `wrong_value` / `wrong_variable` / `partial` (fractional accuracy, `question_scope=all` only) / `parse_error`
- `system_error` (refused impossible system) / `system_error_missed` (answered numerically) / `system_error_false_positive` (refused a solvable system)
- Breakdowns by `surface_form`, `emoji_category`, `operations`, `num_variables`, `determinacy`, `question_scope`

#### Files Added

- [src/plugins/picture_algebra/__init__.py](src/plugins/picture_algebra/__init__.py) — `PictureAlgebraPlugin` registration
- [src/plugins/picture_algebra/generator.py](src/plugins/picture_algebra/generator.py) — sympy-driven system generation + trick cases
- [src/plugins/picture_algebra/parser.py](src/plugins/picture_algebra/parser.py) — multi-variable extraction, 9 strategies
- [src/plugins/picture_algebra/evaluator.py](src/plugins/picture_algebra/evaluator.py) — match-type taxonomy + `semantic_interference_delta`
- [src/plugins/picture_algebra/i18n.yaml](src/plugins/picture_algebra/i18n.yaml) — 6 languages × 3 styles
- [src/plugins/picture_algebra/data/emoji_pools.py](src/plugins/picture_algebra/data/emoji_pools.py) — `FOOD` / `ANIMALS` / `OBJECTS` / `MIXED`
- [src/plugins/picture_algebra/README.md](src/plugins/picture_algebra/README.md) — plugin description
- [tests/plugins/test_picture_algebra.py](tests/plugins/test_picture_algebra.py) — 40 tests (generator / parser / evaluator / integration)

#### Files Modified

- [frontend/src/components/task-badge.tsx](frontend/src/components/task-badge.tsx) — added `picture_algebra` → `neutral` color entry

---

## [2.24.0] - April 17, 2026

### Annotation System DX Overhaul — Schema v3, Multi-Mark Types, Leakage Fixes

Major iteration on the human annotation + improvement report pipeline, driven by practical use across multilingual carwash annotation sessions that exposed data leakage and UX friction.

#### Schema v3 — Classification + Mark Types

- **`response_classes: list[str]` (was `response_class: str`)** — multi-select array; any combination valid. `_migrate_annotation()` auto-upgrades old scalar sidecars on load.
- **Class renames**: `verbose_correct` → `verbose`, `parser_false_positive` → `false_positive`. **Dropped**: `parser_ok` (auto-inferred at aggregation time when spans align with `parser_extracted`). **Added**: `truncated` (new class for cut-off responses).
- **Five mark types** via modifier+click (or drag-select):
  - `LMB` → Answer span (`spans[]`, blue)
  - `Ctrl/Cmd+LMB` → Context anchor (`context_anchors[]`, indigo)
  - `Alt/Opt+LMB` → Answer keyword (`answer_keywords[]`, violet)
  - `Shift+LMB` → Negative span (`negative_spans[]`, rose)
  - `Shift+Alt/Ctrl+LMB` → Negative keyword (`negative_keywords[]`, dark rose)
- All mark types persist in the sidecar. Adjacent marks of the same type auto-merge on click.
- Classification buttons redesigned as two-state toggles (off = muted, on = filled+ring). Keyboard 1–7 toggles the corresponding class.

#### Data Leakage Root Cause — Fixed

Three progressive leakage bugs were identified and fixed in this session:

1. **Draft key was `case_id` only** (pre-fix) → `result_file_id::case_id` (intermediate) → `result_file_id::case_id::response_hash` (final). A single result file can contain up to `6 languages × 3 user_styles × 3 system_styles = 54` variants of the same `test_id`. Only the response hash reliably disambiguates them.
2. **Save endpoint used a dict comprehension** `{r["test_id"]: r …}` — the last entry wins, so annotations for English cases were written with German metadata. Fixed: iterate results to find the entry whose `_response_hash(raw_response)` matches the hash sent from the frontend.
3. **Sidecar key was `case_id::language`** — still collides when same language appears multiple times with different system_style. Final key: `case_id::response_hash`.

Additional fixes:
- `_project_case()` now includes `response_hash` in every projected `ReviewCase` — frontend uses it in `caseKey()` and includes it in save requests.
- `_response_hash()` helper: MD5 of first 128 chars of raw_response, 8 hex chars.
- Response hash validation on load: sidecar entries whose stored `response_hash` doesn't match the current case's response are silently dropped (catches contamination from pre-fix sessions).
- `DELETE /annotations/{id}` now invalidates `["review-cases"]` in the React Query client cache — fixes stale-cache reappearance after deletion.

#### Improvement Report v2.6

- **`REPORT_FORMAT_VERSION = "2.6"`**
- **`negative_span_groups[]`** — `_collect_negative_records()` + `_negative_span_analysis()`: groups negative spans and keywords by normalized text; each group carries `text`, `normalized_text`, `count`, `mark_type` (`negative_span` / `negative_keyword`), and up to 5 `example_negatives[]` (each with `before`, `after`, `correct_span`, `parse_strategy`).
- **`context_anchor_groups[]`** — manually-tagged anchor labels grouped by normalized text with frequency counts.
- **`manual_keyword_distribution`** — annotator-tagged answer keywords; higher-confidence signal than auto-inferred `model_answer_distribution`.
- **`parser_was_correct` auto-inferred** — replaces the manual `parser_ok` class. Cases where `parser_extracted` aligns with any annotated span are counted as correct without requiring the annotator to press 6.
- **Negatives tab** added to improvement-report-dialog (shown only when `negative_span_groups` is non-empty); also surfaces `manual_keyword_distribution` and `context_anchor_groups`.

#### Review UI Polish

- **Finish button navigates to `/results`** — previously clamped at last case. `→` on the last case also navigates. Skip on the last case shows "Finish" and navigates.
- **Help modal** (`?` key + `HelpCircle` button in header) — keyboard shortcut reference + mark-type guide with visual preview swatches. Two-column layout: nav/classification/dock shortcuts on left; full-width mark-types table on right.
- **`onMouseDown` selection suppression** — Shift+click previously triggered browser text-selection-extension instead of firing the click handler. `e.preventDefault()` when Shift or Alt is held fixes this.
- **Shift+Ctrl/Cmd now maps to negative keyword** — previously only Shift+Alt did; the priority updated to `isShift && (isAlt || isCtrl)` → negative keyword.

#### Files Modified

- [src/web/api/human_review.py](src/web/api/human_review.py) — `_migrate_annotation()`, `_response_hash()`, composite sidecar key, `AnnotateRequest` schema, `_project_case()` adds `response_hash`, hash-based target lookup
- [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py) — `_get_response_classes()`, `_collect_negative_records()`, `_negative_span_analysis()`, `_answer_keyword_distribution()`, `_context_anchor_groups()`, auto-infer `parser_was_correct`, `REPORT_FORMAT_VERSION = "2.6"`
- [frontend/src/types/review.ts](frontend/src/types/review.ts) — `ResponseClass` union, `Annotation` interface, `MarkSpan`, `NegativeMarkGroup`, `ContextAnchorGroup`, `ImprovementReport` additions
- [frontend/src/pages/review.tsx](frontend/src/pages/review.tsx) — `caseKey()` with `response_hash`, `handleFinish` + `useNavigate`, `handleToggleClass`, `mergeOrAppendMark`, mark-type handlers, help modal wiring
- [frontend/src/components/review/classification-bar.tsx](frontend/src/components/review/classification-bar.tsx) — v3 classes, toggle-style buttons
- [frontend/src/components/review/verdict-pill.tsx](frontend/src/components/review/verdict-pill.tsx) — multi-pill `verdicts[]`
- [frontend/src/components/review/response-panel.tsx](frontend/src/components/review/response-panel.tsx) — 5-level owner map, modifier-key detection, `MarkChipRow`, warm/cool rendering
- [frontend/src/components/review/help-dialog.tsx](frontend/src/components/review/help-dialog.tsx) — new component
- [frontend/src/components/review/improvement-report-dialog.tsx](frontend/src/components/review/improvement-report-dialog.tsx) — Negatives tab, `CLASS_TONE` updated for v3 codes
- [frontend/src/hooks/use-review.ts](frontend/src/hooks/use-review.ts) — `useDeleteAnnotations` busts `["review-cases"]` cache; `useSaveAnnotation` passes `response_hash`
- [tests/test_human_review.py](tests/test_human_review.py) — updated for v3 schema + hash-keyed sidecar assertions

---

## [2.23.1] - April 17, 2026

### Carwash Parser — Rounds 1–4 (annotation-data-driven)

Four iterative optimization rounds on `src/plugins/carwash/parser.py`, each seeded by human-annotation Improvement Reports (v2.5 → v2.6 format). Cumulative result: 93 parser tests (up from 0), 11 parsing strategies, multilingual conjugation coverage, and dual-keyword option-listing filtering.

**Data sources:** 26 EN-only cases on qwen3-8b (Rounds 1–2), 197 multilingual cases on nemotron-3-super-120b (Round 3), 223 cases across both models (Round 4, first v2.6 report with negative span annotations).

#### Round 1 — Label strategy promotion + bold filtering

- **label_line promoted above bold** — annotation data showed `bold` strategy fired on 24/26 cases with 24 false positives (explanatory bolds like `**Walking costs no fuel**`). `label_line` (Strategy 2) now runs before bold (Strategy 3) — `Recommendation: Drive` resolves cleanly before bolds are scanned
- **bold_label strategy** (Strategy 2a) — covers `**Final Recommendation** **Walk to the carwash**` where label and answer are in separate bold runs. Modifier-restricted (`final|my|the|best|our`) to prevent false matches on arbitrary bolds
- **label_newline strategy** (Strategy 2b) — covers heading + newline patterns: `### **Recommendation**\n**Walk to the carwash**`, `**Answer:**\n Walk.`
- **Label-only bold filtering** — `_label_skip_re` skips bolds that contain only a label word (e.g. `**Recommendation**`, `**Answer**`) so they don't score as answers
- **6 multilingual negative patterns** — `_PRE_WALK_CONDITIONAL` (conditional keyword before walk), `_WALK_CONDITIONAL` (walk followed by conditional), `_WALK_NEGATIVE` (walk in dismissive context). Covers `walk or drive` option-listing, `whether to walk` deliberation, `walking is faster` explanatory assertion
- **`_EXTRA_LABELS` dict** — carwash-specific label words beyond shared `ANSWER_LABELS`: recommendation, decision, verdict, conclusion, bottom line, tl;dr, best option/choice + equivalents in es/fr/de/zh/ua

#### Round 2 — Bold-label colon fix + label-newline refinement

- **bold_label colon inside bold** — fixed `**Answer:**\n**walk**` where the colon is inside the bold run (previously required colon outside: `**Answer**: **walk**`)
- **label_newline strategy** — added for colon-less heading-then-answer patterns that label_line can't catch

#### Round 3 — Multilingual verb conjugation coverage

Root cause: FR/ES/DE languages scoring 4–10% correct because keyword patterns used exact infinitives (`\bmarcher\b`, `\bcaminar\b`, `\bgehen\b`) that miss conjugated forms models actually produce.

- **FR WALK_KEYWORDS**: `r"\bmarche[zs]?\b"`, `r"\bmarchons\b"`, `r"\bmarchent\b"`, `r"\bmarchant\b"` — covers marchez (7 cases), marche (3)
- **FR DRIVE_KEYWORDS**: `r"\bconduis\w*\b"` — conduis- stem covers conduisez (5 cases)
- **ES WALK_KEYWORDS**: `r"\bcamin[aeo]\w*\b"` — covers camina (4), camine (1), caminando
- **DE WALK_KEYWORDS**: `r"\bgeh(?:e|st|t)\b"`, `r"\b\w*gehen\b"`, `r"\bfuß\b"` — covers gehe (2), losgehen (1), standalone Fuß (4)
- **DE DRIVE_KEYWORDS**: `r"\bfahr(?:e|en|t|st)\b"`, `r"\b\w*fahren\b"` — covers fahre (3)
- **ES/FR WALK_NEGATION**: updated to include conjugated forms alongside infinitives

#### Round 4 — Option-listing filter + label expansion (v2.6 negative spans)

First round driven by negative span annotations (v2.6 report). 55 negative "or drive"/"walk or"/"vs" keywords + 84 bare keyword negatives revealed that option-listing text (`"walk or drive"`, `"walk vs drive"`) was the #1 false-positive source.

- **`_DRIVE_LISTING` dict + `_is_conditional_drive()` function** — drive-side filtering for option-listing/comparison patterns. Uses **positional matching** (`finditer` + span check) rather than window proximity to avoid false-filtering a genuine "drive" recommendation that happens to be near an earlier listing phrase. Intentionally lighter than `_is_conditional_walk` — no semantic negation filtering (dismissive drive language IS a walk signal)
- **`_score()` tie-break updated** — filters both walk AND drive positions. When all positions are filtered (pure option-listing text like `"Walk or drive?"`), returns `None` instead of guessing — lets the parser fall through to the next strategy
- **Symmetric "walk or drive" in `_WALK_CONDITIONAL`** — previously only "drive or walk" was covered; walk-first order was unfiltered, creating an asymmetry that biased toward walk when drive positions were filtered
- **"vs"/"versus" patterns** added to `_PRE_WALK_CONDITIONAL` and `_WALK_CONDITIONAL` for EN/ES/FR/DE — handles 11 negative "vs" keywords from annotation data
- **6 new label words in `_EXTRA_LABELS`** — DE: `zusammenfassung`, `kurzantwort`, `handlungsanleitung`; FR: `action recommandée`, `choix`; ES: `resumen`
- **"Therefore" in `_STRONG_INTRO`** — EN `therefore,?|consequently,?|hence,?|thus,?`; DE `daher,?|deshalb,?|folglich,?`; FR `donc,?|par conséquent,?`; ES `por lo tanto,?|en consecuencia,?`. Optional trailing comma allows "Therefore, drive" to parse correctly
- **22 new tests** — `TestVsComparisonFiltering` (5), `TestDriveConditionalFiltering` (5), `TestNewLabels` (6), `TestThereforeStrongIntro` (6); 93 total carwash tests, 0 regressions

#### Annotation DX review

- [docs/improvement_report_annotation_dx_review.md](docs/improvement_report_annotation_dx_review.md) — post-session retrospective on annotation summary usefulness. Key findings: `strategy_breakdown` is the most useful field for triage; `prefix_anchors` with `type` tag is critical for label-vs-format disambiguation; `parser_span_alignment` corrects misleading headlines. Proposed additions: negative span annotations (landed in v2.6), keyword tags on spans, parser match context on misaligned cases, `false_positive_reason` sub-types, structural section context

#### Files modified

- [src/plugins/carwash/parser.py](src/plugins/carwash/parser.py) — 11 strategies, dual-keyword filtering, 6-language keyword/label/negation/conditional dicts
- [tests/plugins/test_carwash_parser.py](tests/plugins/test_carwash_parser.py) — 93 tests across 17 test classes

---

## [2.23.0] - April 16, 2026

### fancy_unicode — Fancy Unicode Normalization Plugin (20th benchmark)

New benchmark plugin testing LLM ability to recognise and decode decorative Unicode encodings — math-script bold/italic/monospace, fullwidth, small caps, superscript/subscript, circled, squared, negative-squared, negative-circled, and combining-dot script — and to follow instructions embedded in the decoded text. Unlike `encoding_cipher` (which labels the encoding scheme explicitly), this plugin presents decorated text as-is. The model must identify the Unicode style on its own. This surfaces failure modes specific to each Unicode family and reveals world-knowledge bypass behaviours.

**Note:** `fancy_unicode` was previously registered in `_LEGACY_TASK_TYPES` in `src/stages/analyze_results.py` and `src/web/reanalyze.py` (added in v2.19.0 when the earlier skeleton was removed). Now that the plugin is fully implemented and auto-discovered by `PluginRegistry`, **`"fancy_unicode"` should be removed from `_LEGACY_TASK_TYPES`** to avoid it appearing twice in task-type inference. Tracked as TD-092.

#### Plugin architecture

- **`families.py`** — 12 encoding family codepoint mapping tables; `encode_text()`, `decode_to_ascii()`, coverage metadata; `UPPERCASE_ONLY_FAMILIES` + `TIER1_FAMILIES` sets; `text_covered_by()` / `word_covered_by()` coverage predicates used for pool filtering at generation time
- **`generator.py`** — `decode_only` and `decode_and_act` task modes; per-family coverage filtering so every alphabetic character has a codepoint; reuses `encoding_cipher`'s `words_en.txt` pool for `decode_and_act` (with fallback inline list); length-tiered sentence fragment pool for `decode_only` (short 3–8 w, medium 8–20 w, long 20–40 w); `_pick_valid_family()` retry loop ensures a non-empty pool before committing to a family
- **`parser.py`** — 10-strategy end-first parser; refusal and runaway sentinels detected before extraction; `_try_normalized_first_line` handles models that echo the encoded answer in the first line (Tier-3 emoji blocks + small caps); `_is_explanation_line` + `_try_content_block` handle multi-line answers with trailing font/encoding commentary; `_LAST_WORD_STOPWORDS` prevents instruction-fragment words from being returned as the response word
- **`evaluator.py`** — 7-type failure taxonomy; `_plaintext_evidence()` heuristic (40% word-overlap threshold) distinguishes genuine decoding from world-knowledge bypass; `decode_to_ascii()` applied to raw response to catch models that echo the answer still encoded; `aggregate_results()` primary output is `by_family` (per-family accuracy + rate fields) — the research-facing breakdown
- **`i18n.yaml`** — EN-only 3-style prompt templates; encoding family name deliberately absent from all templates

#### Encoding families (12, 3 tiers)

| Tier | Families | Coverage |
| --- | --- | --- |
| 1 — full A–Z a–z | `math_script_bold`, `math_italic`, `math_monospace`, `fullwidth` | 52/52 codepoints |
| 2 — partial | `small_caps` (24/26), `superscript` (21/26), `subscript` (17/26), `circled` (full) | varies |
| 3 — uppercase only / combining | `squared`, `negative_squared`, `negative_circled`, `dotted_script` | A–Z only; input uppercased |

#### Task modes

- **`decode_only`** — present an encoded sentence fragment; model must identify the style and return the plain text
- **`decode_and_act`** — present an encoded action instruction; model must decode AND comply, returning a single response word

#### Failure taxonomy (7 types)

| Match type | Meaning |
| --- | --- |
| `correct` | Exact match after NFKD + reverse-map normalisation |
| `bypassed_decode` | `decode_and_act`: correct word, but <40% of plaintext words in response (world-knowledge bypass) |
| `hallucinated_decode` | `decode_and_act`: wrong word + confident decode claim that doesn't match real plaintext |
| `paranoid_refusal` | Model refused to process the text |
| `runaway_refusal` | Response hit `max_tokens` without a parseable answer |
| `wrong_decode` | Answer extracted but incorrect |
| `parse_error` | Could not extract any usable response |

#### Parsing strategies

**decode_only:** `boxed` → `labelled_answer` → `bold` → `content_block` → `last_line`

**decode_and_act:** `single_word` → `normalized_first_line` → `boxed` → `labelled_answer` → `labelled_word` → `quoted_word` → `bold_word` → `last_word`

Refusal and runaway sentinels are checked before all extraction strategies.

#### Language support

EN only. Unicode decoration is language-agnostic at the codepoint level; multilingual extension is possible but non-trivial due to coverage gaps in non-Latin scripts (see TD-092).

#### Files added

- [src/plugins/fancy_unicode/\_\_init\_\_.py](src/plugins/fancy_unicode/__init__.py) — plugin class + auto-discovery
- [src/plugins/fancy_unicode/families.py](src/plugins/fancy_unicode/families.py) — 12 encoding family tables + encode/decode
- [src/plugins/fancy_unicode/generator.py](src/plugins/fancy_unicode/generator.py) — test case generation (2 modes, 3 length tiers)
- [src/plugins/fancy_unicode/parser.py](src/plugins/fancy_unicode/parser.py) — 10-strategy end-first parser
- [src/plugins/fancy_unicode/evaluator.py](src/plugins/fancy_unicode/evaluator.py) — 7-type failure taxonomy
- [src/plugins/fancy_unicode/i18n.yaml](src/plugins/fancy_unicode/i18n.yaml) — EN prompt templates (3 styles)
- [src/plugins/fancy_unicode/README.md](src/plugins/fancy_unicode/README.md) — plugin reference doc

---

## [2.22.1] - April 16, 2026

### encoding_cipher — Parser Overhaul (annotation-data-driven)

Refactor seeded by 117 manually annotated cases across 12 result files (`encoding_cipher_summary.json`). Pre-refactor correct rate: **43.6%** (51/117). The annotation summary identified 5 span groups, each with concrete regex evidence, and surfaced 3 root-cause failure modes: missing high-value strategies, two buggy existing strategies, and absent pre-processing.

#### New decode_only strategies

- **`_try_context_anchored_bold`** — highest priority; covers annotation Groups B/D/E (33 combined cases). Four patterns anchored on `plaintext is: **...**` (100% capture-exact per annotation harness), `decodes to: **...**` (80-90%), `decoded plaintext is: **...**`, and `reveals: **...**`. Uses `re.search` (first match) — these labels appear once, not repeatedly.
- **`_try_blockquote_after_label`** — covers Group A (29 cases): `**Decoded plaintext (ROT13):**\n\n> text`. Three sub-patterns: bold label + newline + blockquote, inline bold label + blockquote, non-bold label + blockquote. Strips residual `>` markers from capture; 10-char minimum guard.
- **`_try_italic_phrase`** — covers long-tail italic format (3 cases). Anchored variant requires decoded label on previous line; unanchored variant only fires when no substantial bold spans exist (prevents shadowing bold strategies).
- **`_try_bold_plaintext`** — broad fallback: last `**bold phrase**` of 10+ chars that isn't a section header (`Step N:`, `Final Answer:`, `Decoded plaintext`, etc.). Module-level `_BOLD_HEADER_RE` exclusion set.

#### Fixed strategies

- **`_try_quoted_text`** — anchored `we get: "..."` pattern tried first (covers Group C, 10 cases); bare fallback minimum length raised 2 → 15, `\n` excluded from character class to prevent cross-line captures that pulled in validation-section quotes in step-by-step responses.
- **`_try_labelled_answer`** — removed `|output` from the answer-labels alternation (was firing on `output:` lines in analytical step-by-step responses, causing misaligned captures); multi-line bold variant now uses `re.search` (first match) instead of `re_search_last` (found section headers later in the response); added `>?\s*` to the capture to strip blockquote prefix.

#### Pre-processing

- `strip_verification_tail(response)` now called at the top of `_parse_decode` before any strategy runs. Removes "Step N: Validation" and similar tail sections that were polluting quote- and label-based strategies in analytical responses.

#### Strategy chain (decode_only, revised order)

```text
context_anchored_bold → blockquote_after_label → code_block → quoted_text
  → labelled_answer → italic_phrase → bold_plaintext → full_response
```

Each strategy has its own confidence value; the `full_response` fallback retains 0.50.

#### Generator: emit `parse_strategy`

`task_params["parse_strategy"] = enc_type` added to the generator. All cases previously carried `parse_strategy="unknown"`, suppressing `strategy_breakdown` in improvement reports. New runs will carry `"base64"`, `"caesar"`, or `"morse"`.

#### Modified files

- [src/plugins/encoding_cipher/parser.py](src/plugins/encoding_cipher/parser.py) — 4 new strategy functions, 2 fixed, `strip_verification_tail` import + call, revised `_parse_decode` chain
- [src/plugins/encoding_cipher/generator.py](src/plugins/encoding_cipher/generator.py) — `parse_strategy` added to `task_params.update({...})`

---

## [2.22.0] - April 16, 2026

### Improvement Report v2.5 — Tactical Cut

Post-carwash-refactor retrospective ([docs/improvement_report_v2.5_plan.md](docs/improvement_report_v2.5_plan.md)) graded the v2.4 artifact as "genuinely useful but over-emitted" — of ~20 top-level keys, 6 carried the load while ~8 were ignored outright (redundant, dead, or inert). v2.5 is the tactical cut: delete/suppress the noise, keep every load-bearing signal intact. Zero new computed fields; net JSON size drops ~30% on production reports.

`format_version` bumped from `"2.4"` → `"2.5"`. Structural additions (`priority_actions`, `parser_fingerprint`, per-group alignment splits, cascade hints, conflicts surfaces) are deferred to a future v2.6 round pending sanity-check against a second plugin's report.

#### Deletions from the payload

- **`confusion_matrix` deleted** — the parser-match-type × response-class grid duplicated numbers already in `summary`; frontend never rendered it; the retrospective confirmed it "never shaped a decision"
- **Top-level `anchor_frequency` deleted** — fully subsumed by per-group `prefix_anchors`. Cross-group aggregation dropped grouping context, making it *less* actionable for parser-refactor work, not more
- **Top-level `response_classes` deleted** — folded into `summary.response_class_counts` (only non-zero buckets emitted). The synthetic `parser_missed` bucket (cases carrying spans) is preserved since it's the only number not otherwise present in `summary`

#### Suppressions (via existing `data_quality.suppressed_sections` mechanism)

- **`strategy_breakdown` suppressed under `no_parse_strategy`** — when ≥90% of cases have `parse_strategy="unknown"` the block collapses to a single `{unknown: {...}}` row that carries no attribution signal
- **`answer_when_missed.by_expected` suppressed under `uniform_expected`** — when all cases share one expected answer the block reports `{single_answer: N}` with empty sibling distractor/pair fields — tautological

Both suppressions are reported in `data_quality.suppressed_sections` + their respective warning codes so consumers can distinguish "absent because empty" from "absent because noise".

#### New section: `long_tail_groups`

- Span groups with `count < 4` collapse into compact `{position, format, count, example}` stubs — no `structural_ratios` / `prefix_anchors` / `regex_test` / `label_taxonomy` since n ≤ 3 carries no statistical signal for those computations
- **Guarded**: collapse fires only when at least one group has `count ≥ 4`. When every group is below threshold (small sessions, focused testsets) those small groups *are* the signal and remain in `span_groups` untouched. The "long tail" concept requires a head
- Preserved fields per long-tail row: `position`, `format`, `count`, single `example` (first from the group's `example_spans`)

#### Empty-omit for `ordering_hints` / `annotator_notes`

- Previously emitted as `[]` when empty; v2.5 omits the keys entirely so the JSON stays dense. Feature-detect on the consumer side (treat absence as "nothing to report")

#### Frontend

- **Anchors tab removed** (`frontend/src/components/review/improvement-report-dialog.tsx`). Tab count drops from 10 to 9 max; individual tabs also hide when their underlying data is absent (Strategy, Misses, Ordering, Classes, Notes all feature-detect)
- **Classes tab** rewired to read `report.summary.response_class_counts` (replacing the deleted `report.response_classes`). Tab hides entirely when no non-zero counts exist
- **Spans tab** renders `LongTailGroupsBlock` — a dimmed, dashed-border trailing section below the full `SpanGroupCard` list. One compact row per long-tail group, expandable to reveal its single retained example. Tab label updates to `Spans (N + M)` where N is rich groups, M is long-tail
- **Type cleanup** — `AnchorFrequencyRow` removed from exports; `LongTailGroup` added; `ImprovementReport.response_classes` removed (folded into `summary.response_class_counts`); `confusion_matrix` removed from interface

#### Test suite

- **9 new v2.5 tests** cover format-version bump, each suppression rule, each deletion, the folded `response_class_counts` shape, long-tail collapse behaviour including the rich-guard invariant, and empty-omit for hints/notes
- **3 existing tests updated or removed** where they referenced deleted sections: `test_v2_confusion_matrix` deleted; `test_v2_anchor_frequency_extracts_phrases` deleted; `test_build_report_produces_four_sections` and `test_build_report_parser_false_positive_counts_as_missed` updated to read `summary.response_class_counts`
- **Endpoint smoke test** (`test_v2_endpoint_returns_format_version_2`) now asserts the three deleted sections are absent at top level
- 75/75 tests green

#### Files modified

- [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py) — `REPORT_FORMAT_VERSION = "2.5"`; `_split_long_tail` helper added; `_response_class_counts` replaces `_response_class_breakdown` (returns non-zero only); `_data_quality` extended to emit `strategy_breakdown` + `answer_when_missed.by_expected` suppressions; `build_report` assembles the report conditionally with deletions and empty-omits
- [frontend/src/types/review.ts](frontend/src/types/review.ts) — `LongTailGroup` added; `Summary.response_class_counts` added; `AnchorFrequencyRow` / `confusion_matrix` / top-level `response_classes` removed
- [frontend/src/types/index.ts](frontend/src/types/index.ts) — re-export map updated
- [frontend/src/components/review/improvement-report-dialog.tsx](frontend/src/components/review/improvement-report-dialog.tsx) — Anchors tab removed; Classes tab rewired; Spans tab renders long-tail block; per-tab feature detection
- [tests/test_human_review.py](tests/test_human_review.py) — 9 new tests + 3 existing tests adapted to v2.5

---

## [2.21.0] - April 16, 2026

### Improvement Report — Agent-Facing Seed Artifact (v2.1 → v2.4 additive iterations)

Four rapid, additive iterations on `src/web/human_review_aggregator.py` and the corresponding `/report` payload, driven by "read this JSON as if you were about to refactor the carwash parser" critical reviews. Each iteration kept `format_version` on a 2.x additive track — legacy consumers of v2.0 payloads continue to parse; new fields are all optional. The report's stated purpose is now explicit: it is a seed artifact for coding-agent tasks that refactor plugin parsers, so fields are named and structured for that consumer.

`format_version` went from `"2"` (v2.20.0) → `"2.1"` → `"2.2"` → `"2.3"` → `"2.4"` across this release.

#### Improvement Report v2.1 — Span context + regex test harness

- **Context window widened 24 → 120 chars** in both `_extract_context_windows` (`src/web/api/human_review.py`) and the aggregator's backfill mirror `_build_context_windows`. 24 chars was too narrow to hold common prefix phrases like `**Final answer:** ` + the span itself
- **Containing sentence per span** — new `sentence` field on every `example_spans[]` row; computed by walking back/forward from the char range until `[.!?\n]`
- **`structural_ratios` per span group** — seven categorical signals averaged across the group: `line_start`, `paragraph_start`, `list_marker`, `label_colon`, `bold_wrap`, `quote_wrap`, `answer_label_match` (multilingual via `build_answer_label_re(language)`). A group with 90% `label_colon` + 90% `answer_label_match` is a trivially labelled answer
- **`prefix_anchors` per span group** — top 5 trailing 1/2/3-gram phrases of `before`, with `count`, `ratio`, stop-word filtering (`to`, `is`, `**`, `_`, …), suppression of shorter anchors subsumed by longer at equal count
- **`regex_test` harness** — every candidate regex run against every example's full context (`before + text + after`, or `sentence` if longer); emits `match_rate`, `matched_count`, `total`; compile errors surface as `match_rate: -1.0` instead of raising
- **Sidecar case records enriched** — `save_annotation` now persists `language`, `user_style`, `system_style`, `parse_strategy`, `parse_confidence`, `model_name`, `context_windows` on every case record. Legacy sidecars pre-v2.20.1 backfill from source result payloads via `result_payloads_by_file` parameter to `build_report`

#### Improvement Report v2.2 — Context-anchored regex + model answer distribution

- **Flipped the auto-regex semantics.** The v2.0 generator used span text as anchor (`walk\s+(\w+)`) — this captures what comes *after* the answer, which is useless. v2.2 anchors on the shared `before` prefix + format-aware capture (`(?i)\*\*answer:\*\*\s*\*\*([^*\n]+?)\*\*`): "find the label, grab the answer"
- **Regex `kind` taxonomy** — candidates now carry one of `context_anchor` (primary: before-prefix + format capture), `format_only` (bare format wrapper for distinctive formats — bold/italic/boxed/strikethrough/header), `text_pattern` (legacy span-text LCP fallback for when `before` context is sparse)
- **Format-aware capture shape** (`_format_capture`) — `bold` → `\*\*([^*\n]+?)\*\*`, `italic` → `(?:_([^_\n]+?)_|\*([^*\n]+?)\*)`, `strikethrough` → `~~([^~\n]+?)~~`, `header` → `(?:^|\n)#{1,6}\s+([^\n]+)`, `boxed` → `\\boxed\{([^{}\n]+)\}`, `label` → `([^.\n]+?)(?:[.\n]|$)`, `plain` → `(\w+)`
- **Trailing-marker strip** — when the top prefix anchor ends with the format's opening marker (e.g. bold's `**`), strip it before building the pattern so the capture's own opening marker isn't duplicated
- **All patterns case-insensitive by default** via inline `(?i)` flag
- **Inline parser-vs-annotator diff per example** — each `example_spans[]` row carries `parser_extracted` + `parser_match_type`. Frontend renders as `[parser] drive → annotator: walk [naive_trap]` below the example
- **`label_taxonomy` per span group** — breaks `answer_label_match_ratio` into specific labels: `[{label: "answer", count: 6}, {label: "recommendation", count: 3}]` across 20+ multilingual label words
- **`model_answer_distribution`** — top-level histogram of what the *model* actually answered (markdown-stripped, lowercased). Complements `by_expected` which is uniform in single-answer plugins like carwash
- **New span formats: `italic`, `strikethrough`, `header`** — frontend `autoFormat` detects `_walk_` / `*walk*` (word-boundary to avoid identifiers like `my_var`) / `~~walk~~` / leading `# heading`; `FORMAT_TO_STRATEGY` maps to `italic_keyword` / `strikethrough_keyword` / `header_line`
- **Confidence reshaped** — `high` when top prefix-anchor ratio ≥ 0.5 AND group size ≥ 3; `medium` when ratio ≥ 0.25 OR a `format_only` candidate emits; `low` otherwise

#### Improvement Report v2.3 — Capture quality + parser-span alignment + data quality

- **Capture quality metrics** — every `regex_test[]` row now also carries `capture_exact_rate` (fraction where `match.group(1)` equals annotated span text, normalized), `capture_contains_rate` (fraction where capture aligns with span via `_is_aligned`: exact or single-word inclusion), and `sample_captures` (up to 3 concrete `{case_id, captured, annotated, exact_match, aligned}` rows). Solves the "match_rate 1.0 but regex captures wrong substring" blind spot
- **Parser-span alignment metric** — top-level `parser_span_alignment` splits "parser missed" into `aligned_with_parser` (parser extracted correctly, annotator just used spans-only workflow without marking `parser_ok`), `misaligned_with_parser` (true parser failure — extracted wrong token), and `no_parser_output` (parse_error, nothing extracted). Includes `sample_misaligned` — up to 5 concrete `{case_id, parser_extracted, annotated_spans, parser_match_type}` rows. Summary gains mirrored `parser_missed_aligned` / `parser_missed_misaligned` / `parser_missed_no_output` breakdowns
- **`_is_aligned` / `_normalize_answer_text` helpers** — alignment semantics: exact normalize match, or single-word parser output appearing as whole word in multi-word span, or symmetric. Different stems (`walking` vs `walk`) count as misaligned — surfacing those differences is the whole point
- **Data quality warnings** — new top-level `data_quality.warnings[]` auto-detects: `no_parse_strategy` (≥90% cases have `parse_strategy="unknown"`), `uniform_language` / `uniform_system_style` / `uniform_user_style` (single-bucket axes), `uniform_expected` (all cases share expected answer)
- **Single-bucket axis suppression** — when `language_breakdown` / `config_breakdown` / `user_style_breakdown` would have exactly one bucket, they are **omitted from the output JSON entirely** and listed in `data_quality.suppressed_sections`. Keeps signal-dense
- **Frontend: collapsible amber banner** for `data_quality.warnings`, sky-toned `ParserSpanAlignmentCallout` with stacked-bar + sample-misaligned disclosure on Summary tab, `ParserMissedStat` inline split on the "Parser missed" card, `CaptureQualityPill` on every regex test row, click-to-expand sample captures with ✓/~/✗ alignment icons

#### Improvement Report v2.4 — Merged disjunction + anchor types + low-support filter

- **`_merged_label_disjunction`** — when a span group has ≥2 distinct `label`-type atoms (e.g. `recommendation:` + `conclusion:`), emits a single `(?i)(?:atom1|atom2)\s*[:：]\s*{format_capture}` candidate with `kind: "merged_label_disjunction"` and `participating_atoms: [...]`. On the Haiku carwash sample this synthesizes what were two separate ~50%-match candidates into one ~100% candidate — the single highest-leverage v2.4 change
- **Atom extraction** — `_label_atom` strips trailing `:` then splits on `. ` / `\n` / `- ` / `* ` to handle anchors like `choice. recommendation:` → atom `recommendation`
- **Anchor type classification** — every `prefix_anchors[]` row now carries `type: "label" | "format" | "phrase"`. `label` = ends with `:`/`：`; `format` = ends with markdown markers (`**`, `__`, `~~`, `*`, `_`, `` ` ``) or emoji glyphs (`✅`, `✓`, `➜`, `→`, `▶`, `➤`, `•`); `phrase` = flowing text. Secondary sort by type rank (label > format > phrase) at equal count
- **Post-harness low-support filter (`_filter_candidates`)** — drops candidates where `support < 2 AND support/group_size < 0.1`, or `match_rate < 0.1 AND capture_contains_rate < 0.1`. Always keeps `format_only` (safety net) and compile errors (diagnostic signal)
- **Regex candidate cap bumped 3 → 4** so the merged disjunction doesn't push out `format_only` + `text_pattern` fallbacks
- **`model_answer_variants`** — per normalized bucket, top 10 raw text variants with counts. Preserves `Walk` / `WALK` / `**Walk**` / `Walk to the carwash` separately under the normalized `walk` bucket so the agent sees case + markdown + phrasing variation inside each answer class. `model_answer_distribution` kept unchanged for backwards-compat
- **Frontend: anchor type chip** (emerald label / amber format / muted phrase) left of each phrase in `PrefixAnchorsTable`; sky-toned badge for `merged_label_disjunction` kind; `ModelAnswerRow` expansion reveals raw variant breakdown when the bucket has >1 variant

#### Layout polish (shipped with v2.1 and v2.2)

- **Dialog auto-fit** — `max-w-4xl` → `w-fit max-w-[min(95vw,1200px)]`; no more truncated tabs on wide content
- **Tab row** — `flex-wrap` → `flex-nowrap overflow-x-auto` with `whitespace-nowrap shrink-0` per trigger; all 9 tabs stay on one line at any viewport width
- **Summary grid** — rebalanced from 7-card 3-col orphan to 8-card 4-col layout; added `Parser accuracy` card (inverse of FPR callout)
- **9 tabs** — Summary / Spans / Strategy / Languages / Misses / Answers (v2.2 new) / Anchors / Ordering / Classes / Notes

#### parse_strategy persistence — Upstream fix enabling `strategy_breakdown`

Before v2.21.0, `parse_strategy` was being computed by plugin parsers but only persisted for Linda Fallacy — all other plugins dropped the value into `/dev/null`, leaving `strategy_breakdown` stuck at `{unknown: ...}`. Fixed across three execution paths:

- `src/stages/run_testset.py` — `parse_answer_via_plugin` now returns the full `ParsedAnswer` instead of `.value`; caller splits into `output.parse_strategy` and `output.parse_confidence`
- `src/web/jobs.py` — `output` dict now includes `parse_strategy` + `parse_confidence` for Web UI execution
- `src/web/reanalyze.py` — reanalysis path now writes the captured strategy back to the output dict

#### Tests — 68 passing (up from 22 at v2.20.0)

- **v2.20.0 baseline**: 22 tests
- **+10 v2.1 tests** — format version, prefix anchors, structural ratios (line_start / bold_wrap / label_colon / answer_label_match), sentence capture, regex harness match_rate, bad-regex safety, 120-char context
- **+9 v2.2 tests** — anchor regex match rate, format-only safety net, label taxonomy breakdown, stop-word filter, parser_extracted surfacing, model answer markdown-strip, v2.2 format version
- **+9 v2.3 tests** — `_is_aligned` semantics, parser_span_alignment split, summary metric split, capture_exact_rate + capture_contains_rate + sample_captures, data_quality `no_parse_strategy`, single-bucket suppression, multi-bucket preservation, uniform_expected, bad-regex capture-quality fields
- **+9 v2.4 tests** — `_classify_anchor` all types, `prefix_anchors.type`, label-before-phrase sort at equal count, merged disjunction with 2 atoms, merged disjunction skipped for single atom, low-support filter drops + keeps format_only, model_answer_variants preserves raw text, variants top-10 cap, v2.4 format version

#### Files touched

- `src/web/human_review_aggregator.py` — grew from 821 → ~1,500 lines (TD-043 tracks the split candidacy)
- `src/web/api/human_review.py` — `_CONTEXT_WINDOW_CHARS` 24 → 120, `_extract_sentence`, `_extract_context_windows` sentence field
- `src/web/jobs.py` + `src/stages/run_testset.py` + `src/web/reanalyze.py` — `parse_strategy` / `parse_confidence` plumbing
- `frontend/src/types/review.ts` — `StructuralRatios`, `PrefixAnchor` (+ `type`), `RegexTestResult` (5 kinds + capture quality), `RegexCaptureSample`, `LabelTaxonomyRow`, `ModelAnswerBucket` + variants, `ParserSpanAlignment`, `DataQuality`
- `frontend/src/components/review/improvement-report-dialog.tsx` — 9 tabs, `DataQualityBanner`, `ParserSpanAlignmentCallout`, `ParserMissedStat`, `AccuracyStat`, `StructuralSignalsRow`, `PrefixAnchorsTable` (type-chipped), `LabelTaxonomyBlock`, `RegexTestRow` (expansion + capture pill), `CaptureSampleRow`, `ModelAnswersTab` + `ModelAnswerRow`
- `frontend/src/components/review/annotation-dock.tsx` — `autoFormat` gains italic / strikethrough / header detection + widened multilingual label vocabulary

### Carwash Parser — First agent-driven refactor seeded by the v2.4 report

The carwash plugin parser became the first consumer of the v2.4 Improvement Report. A 300-case annotation sweep across `gpt-5.4-nano` / `claude-3.5-haiku` / `claude-3-haiku` (all English, all expected `drive`) drove a targeted refactor; ~90% of the decisions traced directly to specific v2.4 report fields (`span_groups[].regex_test[].capture_contains_rate`, `parser_span_alignment`, `prefix_anchors[].type`, `sample_misaligned`, `data_quality.warnings[]`).

#### Parser changes ([src/plugins/carwash/parser.py](src/plugins/carwash/parser.py))

- **Strategy cascade reordered** — `label_line` promoted from Strategy 4 to Strategy 2, above `bold`. The merged-label disjunction `(?i)(?:recommendation|conclusion)\s*[:：]\s*…` had 100% match + 100% capture_contains on 88 annotated cases, yet was being shadowed by bold-strategy hits on explanation bullets (e.g. `**Walking costs no fuel**`). New order: `boxed` → **`label_line`** → `bold` → **`italic`** → `first_sentence` → `strong_intro` → `full_text` → `last_sentences` → `fallback`
- **New `italic` strategy** — extracts last `*X*` / `_X_` emphasis with negative lookarounds `(?<!\*)\*…\*(?!\*)` to prevent collision with `**bold**` runs. Reuses `_is_conditional_walk` for symmetry with the bold strategy
- **`_EXTRA_LABELS` dict (module-level, per-language)** — plugin-local label list merged with shared `ANSWER_LABELS` via new `_build_label_alternation(lang)` helper. Adds "bottom line" (6 annotated cases), "tl;dr", "in short", "final answer" (EN) + localized equivalents for ES/FR/DE/ZH/UA. Regex metachars retained — not `re.escape`'d at merge time
- **`_STRONG_INTRO` dict (module-level, per-language)** — converted the English-only inline regex to a compiled-pattern dict. EN gains three infinitive-recommendation fragments that together cover ~103 annotated cases previously missed: `is\s+to\b` (60 cases), `would\s+be\s+to\b` (43), `action\s+is\s+to\b` (20). Corresponding fragments added for ES/FR/DE/ZH/UA
- **`DRIVE_KEYWORDS` widened with standalone "by/in car" pattern** — `\b(?:by|in)\s+(?:a\s+|the\s+)?car\b` (EN) + localized equivalents across all 6 languages. Regression fix for `carwash_999_0004`: model wrote `**Answer: By car.**`, parser saw no drive signal, fell through to walk mentions elsewhere
- **`_score` now uses `re.IGNORECASE`** — latent bug where DE `\bAuto\b` / `\bFuß\b` patterns never matched, because `_score` lowercased the input before running case-sensitive regex. Fix: drop the lowercasing, add `re.IGNORECASE` to every `re.search` / `re.finditer` call in the scorer. Patterns can now be written in their natural orthography
- **Module docstring updated** to reflect the 9-step cascade order

#### Tests — new [tests/plugins/test_carwash_parser.py](tests/plugins/test_carwash_parser.py)

40 tests across 10 classes, all passing:

- `TestLabelLineBeatsBold` (5) — strategy-reorder regression: `Recommendation: Drive` must win over earlier bolded walk-bullets
- `TestByCarKeyword` (3) — including a word-boundary check that `\bcar\b` doesn't fire inside "carwash"
- `TestItalicStrategy` (3) — single-star, underscore, and bold-vs-italic lookaround safety
- `TestStrongIntroInfinitive` (3) — "is to X" / "would be to X" / "action is to X"
- `TestBoxed` (2), `TestConditionalWalkSuppression` (2), `TestFallback` (2)
- `TestParseStrategyEmission` (9 parametrized) — every non-empty parse emits a concrete `parse_strategy`, never `"unknown"` or empty (regression for the `no_parse_strategy` data-quality warning)
- `TestMultilingualLabelLine` (5) + `TestMultilingualByCar` (4) — one smoke test per language for each new multilingual feature
- `TestParsedAnswerShape` (2) — raw response preserved, confidence in [0.0, 1.0]

Full plugin-suite run confirmed zero new regressions (13 pre-existing failures in `test_ascii_shapes.py` / `test_cellular_automata_1d.py` / `test_linda_fallacy.py` are unchanged, verified by stashing + re-running).

### Improvement Report v2.5 / v2.6 plan — consumer's report card on v2.4

New design doc [docs/improvement_report_v2.5_plan.md](docs/improvement_report_v2.5_plan.md) — reflective review written from the parser-refactor consumer's perspective on the v2.4 JSON artifact. Verdict: v2.4 is genuinely useful (6 of ~20 top-level keys drove all real decisions) but over-emitted (redundant sections, dead siblings under active warnings, long-tail span_groups with `count < 4`) and missing three agent-critical features (ranked action list, parser version pinning, per-group alignment split). Split into v2.5 (pure suppression, ~30% JSON size reduction, zero risk) and v2.6 (additive: `priority_actions[]`, `parser_fingerprint`, per-group `count_aligned` / `count_misaligned`, `closest_existing_strategy` via parser AST walk, `suggested_regex[].cascade_hint`, `conflicts[]`, stemmed `model_answer_distribution`). Tracked as **TD-088** in TECHDEBT.

### Job Persistence & Pause/Resume

Benchmark execution jobs now survive server restarts and can be paused mid-run and resumed from a checkpoint.

#### Persistence Layer (`src/web/job_store.py`)

New `JobStore` class is the single place all job JSON I/O happens — swap the class body to change backends (NoSQL, Redis, etc.) without touching any other file.

- **Storage**: `jobs.json` at project root (path configurable via `GOL_JOBS_FILE` env var)
- **Format**: `{"version": 1, "jobs": {id: job_record, …}}`
- **Atomic writes**: temp file in same dir → `os.replace` — no partial-write corruption
- **Startup recovery**: `job_manager.load_from_store()` called from FastAPI lifespan; PENDING/RUNNING jobs found → marked FAILED ("Interrupted by server restart"); PAUSED jobs survive and remain resumable
- **Shutdown persistence**: `job_manager.save_to_store()` on lifespan exit; each terminal transition also calls `_persist_job()` immediately so history is safe even without a clean shutdown
- Execution params (`provider`, `ollama_host`, `temperature`, `no_think`, `api_key`, `api_base`) now stored on `Job` so resume can recreate an identical worker without user re-input

#### Pause / Resume

Workers cooperatively pause between test cases (no forced kill — current test case always completes cleanly).

- **`PAUSED`** added to `JobState`; not in `TERMINAL_JOB_STATES` — paused jobs can be resumed
- **`POST /api/jobs/{id}/pause`** — sets `pause_requested` flag in shared multiprocessing dict; worker checks it before each test case; on pause: saves `partial_<job_id>.json.gz` with all completed results + running stats, returns `{"status": "paused", "paused_at_index": N}`
- **`POST /api/jobs/{id}/resume`** — paused job marked CANCELLED (superseded); new job submitted inheriting all params + `start_index=paused_at_index`; on completion merges partial + new results into final file, deletes partial
- Judge jobs: cancel-only (multi-file batching makes checkpointing significantly more complex — TD-086)

#### Jobs Page (frontend)

- `JobState` type gains `"paused"`; `Job` interface gains `paused_at_index` / `partial_result_path`
- Jobs table: amber **Pause** button (PauseCircle) on running inference jobs; green **Resume** button (PlayCircle) on paused jobs
- Paused progress bar renders in amber with checkpoint position (`paused_at_index / total`)
- `usePauseJob()` / `useResumeJob()` hooks; "Paused" filter facet in state faceted filter
- `job-state-badge.tsx`: amber variant for paused state

#### Known Limitations (see TECHDEBT)

- TD-085: `api_key` / `api_base` stored plaintext in `jobs.json` — add file to `.gitignore` (done in this release), restrict filesystem permissions
- TD-086: Resume produces a second job row in the UI (paused job shows as "Cancelled — superseded")
- TD-087: `partial_<job_id>.json.gz` orphaned if server crashes between pause and resume completion

#### Files modified

- `src/web/job_store.py` — **new file** (~100 lines)
- `src/web/jobs.py` — `JobState.PAUSED`, `Job` dataclass (new fields + `to_storable_dict` / `from_stored_dict`), `_pause_requested()`, worker `start_index` + `partial_result_path` params, `pause()` / `resume()` / `load_from_store()` / `save_to_store()` / `_persist_job()` methods
- `src/web/api/execution.py` — `POST /{id}/pause`, `POST /{id}/resume`
- `src/web/app.py` — FastAPI `lifespan` context manager (startup/shutdown hooks)
- `.gitignore` — `jobs.json` + `partial_*.json.gz` added
- `frontend/src/types/job.ts`, `frontend/src/api/jobs.ts`, `frontend/src/hooks/use-jobs.ts` — paused state, pause/resume API + hooks
- `frontend/src/components/job-state-badge.tsx`, `frontend/src/pages/jobs.tsx` — pause/resume UI

---

## [2.20.0] - April 15, 2026

### Human Review & Parser Annotation Tool

A new first-class workflow for human labelling of model responses, turning every annotated case into a parser test case in waiting. Designed for iterative parser improvement: the human labels where the answer is (or why there isn't one) and the system aggregates labels into actionable artifacts — regex candidates, strategy ordering hints, and failure taxonomy summaries.

#### New `/review` Page — Editorial Two-Column Workspace

- **Entry points** — from the Results page: `Review manually` toolbar button (plugin-gated: enabled only when every selected file shares one plugin), `Verify Manually` per-row dropdown item, and `Improvement Report` toolbar button (enabled when ≥1 selected file has annotations)
- **Layout** — sticky progress header + two-column body (stimulus ~35%, response ~65%) + sticky classification footer. Keyboard-first and deliberately chrome-light so the annotator reads rather than navigates
- **Progress** — `N annotated · M / total` header counter; segmented progress bar (emerald fill = saved, slim primary marker = current position); retry badge for unsaved drafts
- **Match-type presets** — inline filter chips (`All` / `Incorrect only` / `Parse errors` / `Mismatches`) persisted in URL via `?match_types=`
- **Skip toggles** — `Skip empty` (default ON) and `Skip already-correct` (default OFF), both persisted via `useLocalStorageState`
- **Deep linking** — `/review?files=a.json.gz,b.json.gz&case_id=xyz&match_types=parse_error,mismatch`. Bare `/review` (no files) redirects to `/results`

#### Annotation Mechanics

- **One-click word marking** — hovering a word in the response shows a primary-tinted underline; clicking commits it as an answer span immediately with auto-detected position and format. No dock round-trip required
- **Drag-select + sticky dock** — multi-word phrases flow through a persistent dock between the response and note areas; `Mark as Answer` primary action + `⋯` disclosure for Position/Format overrides (both auto-computed by default). Selection survives misclicks — no more vanishing toolbars
- **Marked-span removal** — clicking an existing `<mark>` removes the annotation; also exposed as removable chips below the response
- **Parser-match highlight** — the parser-extracted string is rendered inline with an amber dashed underline so annotators can see *why* the parser said what it said; `Crosshair` "Jump to parser match" button scrolls to it with a brief flash
- **Scroll reset** — response panel always opens at the top on case change (fixes the v1 bug where cases loaded mid-paragraph)
- **Scroll shadows** — linear-gradient fades at top/bottom of the response container so content continuation is never silently hidden

#### Response Classification

- **Seven response classes** — `hedge`, `gibberish`, `refusal`, `language_error`, `verbose_correct`, `parser_ok`, and **`parser_false_positive`** (new)
- **`parser_false_positive`** uniquely coexists with answer spans — the span is the evidence for the correct answer, the verdict is the diagnosis. Signals the parser confidently extracted a distractor
- **Keycap buttons** — `<kbd>` prefix (`1`-`7`) on each classification button; active verdict rendered with `/30` fill, solid border, and a `ring-1 ring-current/40` halo so it's never ambiguous which one is picked
- **Verdict pill** — compact footer pill (`Current verdict: [Hedge ✕]`) with a one-click × to clear; always visible regardless of whether the buttons row has wrapped off-screen
- **Spans coexist with verdicts** — the invariant was relaxed so `verbose_correct` + span, `language_error` + span, and `parser_false_positive` + span are all valid. Unlocks cases where the parser grabbed the wrong occurrence of a recoverable answer

#### Parser-Disagreement Awareness

- **Muted "correct" badge** — the match-type chip renders in neutral tones with `· unverified` suffix until the annotator explicitly engages. The green `correct` pill can no longer silently mislead
- **Strike-through verdict badge** — when `response_class === parser_false_positive`, the match-type chip renders `~~correct~~ → false-positive` in fuchsia
- **Persistent disagreement callout** — rose-tinted alert between the badge row and the response body appears whenever the annotator's spans don't contain the parser's extracted string; one-click `Flag as false-positive` button. When flagged, turns fuchsia: `✓ Parser false-positive confirmed`
- **Auto-suggest toast** — fires on the *first* contradicting span only (not every subsequent one) so multi-span cases don't spam notifications

#### Machine Translation (`deep-translator`)

- **Backend module** — `src/web/translation.py` wraps the `deep-translator` PyPI package. Provider switchable via `TRANSLATOR_PROVIDER` env var (`google` default = zero-config, `libre` via `LIBRETRANSLATE_URL` + `LIBRETRANSLATE_API_KEY`, `mymemory` as fallback). Result-cached via `functools.lru_cache` keyed by SHA-256(text) + source + target; short-circuits when source == target
- **`POST /api/human-review/translate`** — thin endpoint, 400 on empty text, 503 on provider failure
- **Translation panels** — split components (`TranslationTrigger` + `TranslationContent` + `useTranslationPanel` hook) so the button can live in a compact header while the translated text renders in a dedicated area below the original. Deliberately `select-none` — annotations refer to original char offsets, so the translation must never be an annotation target
- **Session-wide target language** — 🌐 selector (EN/ES/FR/DE/ZH/UA) in the review header, persisted via `useLocalStorageState`. Auto-hides when source equals target
- **Caching** — React Query (`staleTime: Infinity`) + backend LRU so toggling panels is free after first fetch. Graceful error surface with inline retry

#### Annotation File Format & Lifecycle

- **Sidecar layout** — gzipped JSON at `{result_dir}/{result_file_stem}_annotations.json.gz`, parallel to the existing judge-file convention. Atomic writes via temp file + `os.replace`
- **Schema** — `meta` block (plugin, counts, timestamps) + `cases` map keyed by `case_id`. Each case records `annotation.spans[]`, `annotation.response_class`, `annotator_note`, plus parser snapshot (`parser_match_type`, `parser_extracted`, `expected`) so the file is self-describing
- **Invariant** — at least one of `spans` / `response_class` must be populated; both may coexist (relaxed from pre-release `XOR` rule)
- **`has_annotations` flag** — surfaced on every `/api/results` summary. Renders a `PenLine` badge next to annotated rows and gates the `Remove annotations` / `Improvement report` actions
- **`DELETE /api/human-review/annotations/{file}`** — idempotent. Returns `{deleted: true/false}`; the result file itself is untouched. Frontend shows a confirmation dialog before calling

#### Improvement Report

- **Module** — `src/web/human_review_aggregator.py` is a pure-function report builder (no I/O). Testable in isolation
- **Four sections**:
  1. **Session summary** — totals: annotated / skipped / parser was correct / parser missed extractable / true unparseable
  2. **Span analysis** — grouped by `(position, format)`; per group: count, up to 5 example spans, auto-generated regex candidates (longest common word prefix → `anchor\s+(\w+)`; fallback disjunction of top-2 2-word prefixes; capped at 3 candidates), suggested strategy via format → strategy map, `missed_by_existing` flag
  3. **Ordering hints** — fires when ≥4 cases share `position=end, format=plain` AND the parser missed them → recommend promoting `end_sentences` over `full_text`
  4. **Response class breakdown** — counts per class plus `parser_missed = number of cases with spans`
- **`parser_false_positive` in the summary** — counts as `parser_missed_extractable` (the parser landed on a distractor; the real answer is elsewhere)
- **Modal UI** — `Dialog` on the Results page with `Tabs` (Summary / Spans / Ordering / Classes). Per-regex copy buttons, split `Copy JSON` / `Download JSON` footer buttons. Loading skeleton + graceful error state

#### API Endpoints

All new endpoints under `/api/human-review/`:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/cases` | Load cases for review. Query params: `file_ids`, `skip_correct`, `skip_empty`, `match_types` |
| `POST` | `/annotate` | Upsert a single-case annotation atomically. Rejects empty/both-empty payloads (400) and unknown classes (400) |
| `GET` | `/annotations/{result_file_id}` | Full sidecar payload or `{meta: {}, cases: {}}` when missing |
| `DELETE` | `/annotations/{result_file_id}` | Idempotent sidecar removal (`{deleted: true/false}`) |
| `POST` | `/report` | Aggregate annotations into an improvement report |
| `POST` | `/translate` | Translate arbitrary text via the configured provider |

Router registered in `src/web/api/__init__.py` with `prefix="/human-review"`; route ordering honors the CLAUDE.md rule (specific routes before any `{filename}` catch-alls).

#### Frontend Architecture

- **Pages** — `frontend/src/pages/review.tsx` (lazy-loaded route)
- **Components** (all under `frontend/src/components/review/`):
  - `stimulus-panel.tsx` — left column (user prompt + collapsible system prompt with one-line preview)
  - `response-panel.tsx` — right column with word-level interactive rendering (`classifyChars` + `renderWords`)
  - `annotation-dock.tsx` — sticky dock for drag-selected pending spans + note textarea
  - `classification-bar.tsx` — seven keycap-prefixed verdict buttons
  - `case-progress.tsx` — header with progress bar, filter chips, target-language selector
  - `verdict-pill.tsx` — compact current-verdict chip
  - `translation-panel.tsx` — split trigger/content/hook for on-demand translation
  - `improvement-report-dialog.tsx` — modal with tabbed report
- **Types** — `frontend/src/types/review.ts` (`ReviewCase`, `Annotation`, `AnnotationSpan`, `ResponseClass`, `ImprovementReport`, `TranslateRequest`, `TranslateResponse`, `DeleteAnnotationsResponse`)
- **Hooks** — `frontend/src/hooks/use-review.ts` (`useReviewCases`, `useSaveAnnotation`, `useAnnotations`, `useImprovementReport`, `useDeleteAnnotations`, `useTranslation`)
- **Route** — `/review` lazy-loaded in `frontend/src/App.tsx`; `/review` without `?files=` redirects to `/results`

#### Results Page Integration

- **New toolbar buttons** — `Review manually` (`PenLine` icon, selection-count badge, plugin-gated) and `Improvement Report` (`FileBarChart` icon, gated on `has_annotations`)
- **New row-menu items** — `Verify Manually` (between `View Details` and `Rerun`) and `Remove Annotations` (destructive, rendered only when `row.original.has_annotations`)
- **Row badge** — small `PenLine` icon inside a primary-tinted pill next to the model name when the row has annotations
- **Confirm dialog** — destructive `Dialog` for Remove Annotations lists the filename and irreversibility warning; mirrors the Delete-result flow

#### Keyboard Shortcuts (Review Page)

Only fire when focus is outside form controls and contentEditable regions.

| Key | Action |
|-----|--------|
| `←` / `→` | Navigate to previous / next case (Next also saves dirty drafts) |
| `1` – `7` | Classify as Hedge / Gibberish / Refusal / Language Error / Verbose Correct / Parser OK / Parser False-positive |
| `Space` or `Enter` | Commit pending drag-selection to the annotation dock |
| `S` | Explicit Skip (advance without saving) |

#### Tests

- **`tests/test_human_review.py`** — 22 tests covering `_auto_regex` (anchor, disjunction, empty, caps-at-3, single-char), `build_report` sections, `/cases` filtering (empty-skip, correct-skip, `match_types`), annotate round-trip + invariant rejections, `parser_false_positive` coexistence, `has_annotations` flag on the results summary, delete idempotency + 404, translate endpoint (stubbed), empty rejection, same-lang noop

#### Dependencies

- **`deep-translator==1.11.4`** added to `requirements.txt` — thin wrapper around Google / LibreTranslate / MyMemory providers. Zero API key required for the default Google provider; override via `TRANSLATOR_PROVIDER` env

---

## [2.19.0] - April 14, 2026

### Backend Code Simplification & Cleanup

#### Duplicate Code Eliminated

- **`_build_yaml_config()` helper** (`src/web/api/testsets.py`) — extracted ~70 lines of YAML config-dict construction that was copy-pasted identically between `generate_testset()` and `config_to_yaml()`; both endpoints now delegate to the shared helper
- **`_find_result_file()` / `_resolve_result_files()` helpers** (`src/web/api/analysis.py`) — extracted the repeated "search `_results_dirs()` for a filename" loop that appeared 9 times across 7 route handlers; all endpoints now use the shared helpers
- **`DEFAULT_CELL_MARKERS` constant** — `["1", "0"]` was hardcoded independently in `testsets.py` and `matrix.py`; now defined once in `testsets.py` and imported in `matrix.py`

#### Bug Fixes

- **`cancel()` dead code removed** (`src/web/jobs.py`) — the `if future.cancel():` branch and the unconditional code below it performed identical state transitions; the duplicate block (including a suspicious `job.started_at = job.started_at or time.time()` after cancellation) is gone; `future.cancel()` is now called as a best-effort signal, and state is set unconditionally regardless of its return value
- **Bare `except Exception: continue`** in `list_judge_results()` (`src/web/api/analysis.py`) — now logs the skipped filename and exception via `logger.warning()`

#### Inline Imports Moved to Module Level

- `urllib.request` / `urllib.error` in `fetch_prompt_from_url()` (`testsets.py`) — moved to top of file
- `from typing import Optional` misplaced mid-file in `analysis.py` — removed (already in the top-level `typing` import)
- All `from src.stages.analyze_results import ...` calls scattered across `_summarize_result()`, `analyze_results()`, and `generate_report()` — consolidated into one module-level import block
- `from src.web.jobs import job_manager` and `from src.web.reanalyze import reanalyze_result_file` — moved from inside route handlers to module level in `analysis.py`
- Unused `extract_task_breakdown` import removed from `analyze_results()` (was imported but never called)

#### Documentation Clarity

- **`src/core/PromptEngine.py` module docstring** — changed "Deprecated" to "Legacy (still used by generate_testset.py — not removed yet)" for `TaskType`, `PromptContext`, and the convenience factory functions, since they remain in active use and calling them deprecated was misleading
- **`src/web/judge.py` progress helpers** — added comment explaining why the progress-tracking closures mirror the module-level helpers in `jobs.py` rather than importing them (circular import: `jobs.py` ↔ `judge.py`)
- **Unused `Path` import** removed from `judge.py`

#### `src/utils/logger.py` Cleanup

- Removed dead `# logging.StreamHandler()` comment
- Renamed default log file from `game_of_life_eval.log` to `gol_eval.log`
- Made log file path configurable via `GOL_LOG_FILE` environment variable

### Version — Single Source of Truth

- **`src/__init__.py`** is now the canonical Python version; bumped to `2.19.0`
- **`src/web/app.py`** replaced the hardcoded `"2.17.2"` string with `from src import __version__` — FastAPI OpenAPI docs always reflect the package version automatically; future bumps require only one file edit
- **`frontend/package.json` + `package-lock.json`** updated to `2.19.0` (npm source of truth, kept in sync manually)
- **`.github/copilot-instructions.md`** updated to `2.19.0` with corrected date

### Plugin Task Types — Single Source of Truth

- **`src/stages/analyze_results.py` — `_KNOWN_TASK_TYPES`** replaced the 20-item hardcoded list with `PluginRegistry.list_task_types()` + a small `_LEGACY_TASK_TYPES = ["fancy_unicode"]` list for removed-but-still-referenced types; sorted longest-first to prevent `"arithmetic"` matching before `"time_arithmetic"` in substring searches
- **`src/web/reanalyze.py` — `_TASK_TYPE_SUFFIXES`** same change; also **fixes a bug**: `picross` was missing from this list, so Picross test IDs could never be recognized during reanalysis
- **`src/stages/analyze_results.py` — inline badge list** in `_card()` replaced the stale hardcoded subset (was missing `symbol_arithmetic`, `picross`, `false_premise`) with `_KNOWN_TASK_TYPES`
- **`src/stages/analyze_results.py` — `TASK_COLORS`** added the four missing registered task types: `time_arithmetic` (`#0097a7`), `false_premise` (`#6d4c41`), `symbol_arithmetic` (`#5c6bc0`), `picross` (`#00897b`)
- Adding a new plugin in `src/plugins/` now automatically propagates to all task-type inference and badge detection with no other changes required

### Matrix Execution — Wizard Redesign

- **5-step wizard** — the former flat Matrix Exec form is now a sequential `Setup` → `Axes` → `Models` → `Settings` → `Review` flow with the same `StepButton` / `StepFooter` primitives used by Execute and Configure
- **Step 1 Setup** — plugin select, test set name prefix, seed, description, and the plugin's base `ConfigForm`; `Continue to Axes` disabled until a plugin is picked
- **Step 2 Axes** — prompt axes (user / system / language checkboxes) + plugin field variation axes via the existing `FieldAxisEditor`; Custom System Prompt card is hidden until the "custom" toggle is checked (mirroring the Configure Prompts step)
- **Step 3 Models** — reuses the extracted `OllamaSection`, `OpenAIEndpointSection`, `HuggingFaceSection` components; favorites sidebar, saved credentials, and cross-provider search behave identically to Execute
- **Step 4 Settings** — temperature, max tokens, disable-thinking; shows current matrix shape (cells × models = projected jobs)
- **Step 5 Review & Run** — 3-column summary (Plugin & Cells / Axes / Models & Jobs), amber `AlertTriangle` warnings for incomplete selections, `Generate Only` + `Generate and Run` CTAs in the footer row
- **All prompt axes default to empty sets** — no pre-selected user style / system style / language; Review warns clearly when any axis column is empty
- **Step state persisted** — `matrix-page-active-step` in localStorage (same pattern as Execute / Configure)

### Execute Page — Merged Landing

- **Single `/execute` entry point** — bare `/execute` now renders a two-tile landing with explanatory copy: "Simple run" (4-step wizard) and "Matrix run" (5-step wizard)
- **Query-param mode** — `/execute?mode=simple` and `/execute?mode=matrix` deep-link directly into either wizard; `← Back to options` ghost button above each wizard clears the param
- **Lazy-loaded wizards** — each sub-wizard is a separate chunk, so users only pay the bytes for the wizard they open (`execute` landing bundle dropped from ~27 kB to 4.57 kB)
- **Legacy redirect** — `/matrix-execution` now redirects to `/execute?mode=matrix` via React Router `<Navigate replace />`
- **Sidebar collapsed** — the "Matrix Exec" nav item is removed; one "Execute" entry covers both flows

### Shared Component Extraction

- **`frontend/src/components/wizard/`** — new `StepButton` (generic over step id) and `StepFooter`; replaces three inline copies previously duplicated across Execute, Configure, and Matrix Exec
- **`frontend/src/components/model-selection/`** — new `ModelList`, `OllamaSection`, `OpenAIEndpointSection`, `HuggingFaceSection`, plus shared `SelectedModel` / `OpenAIEndpoint` types and `selectedModelKey()` helper; replaces two inline copies (Execute + Matrix Exec)
- **~300 lines of duplicated UI code removed** — single definition of each model-selection subcomponent means fixes land in one place for all wizards

### Navigation & Routing

- **`pages/execute.tsx`** — rewritten as a thin landing + dispatcher component (~140 lines)
- **`pages/execute/simple-wizard.tsx`** — former Execute body moved into its own lazy-loaded chunk
- **`pages/execute/matrix-wizard.tsx`** — Matrix wizard body lives here; former `pages/matrix-execution.tsx` deleted
- **`App.tsx`** — `/matrix-execution` route replaced with `<Navigate to="/execute?mode=matrix" replace />`; unused `MatrixExecutionPage` lazy import removed
- **`components/layout/app-shell.tsx`** — `NAV_ITEMS` trimmed to one "Execute" entry; unused `Grid3X3` icon import dropped

---

## [2.18.0] - April 14, 2026

### Configure Page — Wizard Redesign

#### Wizard Flow

- **4-step wizard** — Configure is now a sequential `Setup` → `Plugins` → `Prompts` → `Review` flow matching the Execute page's wizard pattern, with the same `StepButton` / `StepFooter` navigation components (step jumping, completion indicators, per-step summary text)
- **Step state persisted** — active step survives navigation away and back via `localStorage` (`configure-page-active-step`)

#### Step 1 — Setup

- **Three-way mode toggle** — segmented control with `Build from scratch | Import config | Upload test set`; each mode is fully isolated with no card duplication
- **Build mode** — global settings (name, seed, description) only; StepFooter advances to Plugins
- **Import mode** — shadcn `Tabs` (File Upload | Fetch from URL | Paste YAML) matching the Prompts step's tab style; all three flows call the existing `/api/testsets/upload-yaml` endpoint and navigate to Test Sets on success
- **Upload mode** — dedicated `.json.gz` upload card; navigates to Test Sets on success; the pre-generated test set upload no longer appears in Build or Import modes

#### Step 2 — Plugins

- **Expandable table rows** — replaced the checkbox grid with a linear list; each plugin row has a checkbox (left) and a chevron expand/collapse button
- **Auto-expand on select** — checking a plugin's checkbox automatically expands the row and shows its `ConfigForm`; unchecking collapses and dims it
- **Independent expand** — the chevron can expand any row without selecting it (e.g. to preview options before committing); unselected-but-expanded rows show `ConfigForm` at `opacity-50 pointer-events-none`
- **Selection accent** — selected rows get `bg-primary/5 border-primary/20` background; "active" badge appears in the row header
- **Plugin name + description in row header** — description wraps onto a second line instead of truncating; `ConfigForm` no longer repeats the description inside the expanded panel

#### Step 3 — Prompts

- **All prompt options off by default** — `userStyles`, `systemStyles`, and `languages` all start as empty sets; `combos` returns `0` when any set is empty
- **Custom System Prompt now hidden by default** — the custom prompt section is completely unmounted until the user checks the new "custom" toggle at the bottom of the System Styles column; the toggle uses the same `Separator`-delimited style as the standard system style options
- **Import config tabs use shadcn `Tabs`** — replaced the custom border-button row with `TabsList`/`TabsTrigger` at the same `h-7`/`h-6` density as the Prompts step's custom prompt tabs
- **Incomplete-selection warning** — amber `AlertTriangle` callout shown when `combos === 0`; "Continue to Review" disabled until all three columns have at least one selection

#### Step 4 — Review & Generate

- **3-column summary** — Testset (name, seed, description), Plugins (list, est. cases/plugin, total est. cases), Prompts (user/system style badges, language flags, combo count, custom prompt indicator)
- **Warnings before action area** — amber callouts for missing plugins and/or missing prompt combinations are stacked between the summary grid and the action footer; Generate, Copy YAML, and Download YAML are all disabled when either condition is unmet
- **"Copy YAML Config" split button** — calls the new `POST /api/testsets/config-to-yaml` endpoint and writes the YAML string to the clipboard
- **"Download YAML Config" dropdown** — same endpoint call; saves the result as `{name}_config.yaml` via a transient `<a download>` element
- **"Generate Test Set"** primary CTA unchanged in behavior

#### Execute Page — Review Step Fixes

- **Run button moved to Review footer** — removed from `PageHeader`; now appears on the right side of the Review step's footer row (`border-t pt-4`), mirroring the placement of all other step CTAs
- **Incomplete-selection warning** — the muted `bg-muted/20` status box ("Selections incomplete") is replaced with an amber `AlertTriangle` callout; message is context-aware (no test sets / no models / both missing); placed between the summary grid and the footer row

#### New Backend Endpoint

- **`POST /api/testsets/config-to-yaml`** — accepts a `GenerateRequest` JSON body; runs the same config-dict construction logic as `/generate` but returns the YAML string as `text/plain` without generating a test set or touching the filesystem; returns `PlainTextResponse`

#### Frontend Infrastructure

- **`postText()` in `frontend/src/api/client.ts`** — new HTTP helper for endpoints that return `text/plain` instead of JSON
- **`configToYaml(req)` in `frontend/src/api/testsets.ts`** — typed wrapper for the new backend endpoint

---

## [2.17.2] - April 13, 2026

### Web UI Workflow Refinements

#### Shared State and Table Persistence

- **Persisted table and display preferences** — table sorting, filters, column visibility, pagination, and page-level display modes now persist consistently in local storage across the main Web UI browsing flows instead of resetting between visits
- **Stable live pagination on Jobs** — the Jobs page no longer snaps back to the first page on each polling refresh while background progress updates stream in

#### Judge and Identifier UX

- **Merged judgment review flow** — the Judge page now keeps individual judgments and detail review in one expandable table workflow instead of splitting users between separate browsing and inspection views
- **Suffix-biased identifier labels** — long test set names and test IDs now surface the distinguishing suffix instead of only the shared prefix across Dashboard, Test Sets, Jobs, and Judge tables

#### Execute Page

- **Wizard-based execution flow** — Execute is now a 4-step setup flow (`Test Sets` → `Models` → `Settings` → `Review`) with direct step jumping and a final batch summary before launch
- **Shared DataTable test set picker** — Execute test set selection now uses the common table component with persisted state, standard footer pagination, and `10/20/50/100` page-size options
- **Clearer launch states** — run actions now stay aligned with selection state, and the primary Execute CTA moves to the review step where the projected job count is explicit

#### Charts

- **Heatmap readability and accessibility pass** — the accuracy heatmap now uses a safer palette plus numeric labels and border styling as secondary encodings, with improved axis label handling for dense model lists
- **Scatter label density controls** — the scaling scatter chart now supports persisted `Hover`, `Smart`, and `All` label modes to reduce overlap while preserving discoverability
- **Chart header wrapping** — chart action controls now wrap cleanly instead of overflowing dense card headers

## [2.17.1] - April 12, 2026

### Web UI Workflow Fixes

#### Execute Page

- **Simplified test set selection** — replaced the Execute page card picker with a compact paginated checkbox grid for multi-selecting test sets while preserving persisted search, selection, and paging state

#### Results and Dialog UX

- **Results language filter parity** — Results now uses the same shared flag + full-language labels as Test Sets (for example `🇬🇧 English`)
- **Overflow-safe modal actions** — widened delete/param-override dialogs and allowed dialog footers to wrap so very long test set names no longer push CTA buttons out of view

#### Jobs and Judge Cancellation

- **Running-job cancellation** — `JobManager.cancel()` now supports cooperative cancellation for already-running inference jobs instead of failing when `Future.cancel()` cannot stop an active worker
- **Judge worker parity** — judge jobs now honor the same shared cancellation flag and preserve `cancelled` as a terminal state
- **Cancel endpoint semantics** — `POST /api/jobs/{job_id}/cancel` now returns `404` for unknown jobs and no longer lets status sync overwrite cancelled jobs as completed

### Tests

- **`tests/test_job_manager_cancel.py`** — added regression coverage for cancelling running jobs and preserving completed vs cancelled terminal states in `JobManager` done callbacks

## [2.17.0] - April 11, 2026

### Web UI Browsing Improvements

#### Test Sets and Results: Table/Cards Split + Airtable-Style Grouping

- **Independent `Format` and `Group By` controls** — Test Sets and Results no longer conflate grouping with cards; both pages now default to `Format: Table` and `Group By: None`
- **Collapsible grouped rows in table mode** — `DataTable` now supports Airtable-style foldable group headers inside the table body, so grouped browsing works without switching away from tabular scanning
- **Grouped cards retained as an alternate format** — grouped card sections remain available behind the `Cards` format toggle when grouping is active
- **Grouped mode footer behavior** — grouped tables suppress page-based pagination in favor of per-view row/group counts so groups are not split across pages
- **Results group actions** — grouped result headers preserve matrix/task/run context and expose group-level select/deselect actions for bulk workflows

#### Shared Frontend Infrastructure

- **`frontend/src/components/data-table/data-table.tsx`** — added optional page-driven grouping metadata, collapsible group expansion state, grouped row rendering, and grouped footer summaries
- **`frontend/src/pages/testsets.tsx`** — added independent `viewMode` state, `Format` toggle, grouped table rendering path, and grouping defaults that preserve flat table browsing on first load
- **`frontend/src/pages/results.tsx`** — mirrored the Test Sets UX split and layered dynamic group header extras for grouped selection state and matrix badges

### New Benchmark Plugin: Picross (Nonogram)

19th benchmark plugin — grid-based deductive reasoning puzzle.

#### Plugin Implementation (`src/plugins/picross/`)
- **`solver.py`** — Nonogram line solver (constraint propagation) + backtracking solver for uniqueness validation; `derive_clues()`, `line_solve()`, `backtrack_solve()`, `is_line_solvable()`
- **`grid_gen.py`** — Random puzzle generation with validation (line-solvable / unique solution); `generate_puzzle()` with configurable size, density, retry budget (200 attempts); `difficulty_to_size()` mapping: trivial=3, easy=5, hard=10, nightmare=15
- **`generator.py`** — `PicrossGenerator` with `ConfigField` schema for Web UI; 3 clue formats (inline, grid_header with full vertical alignment, JSON); optional partial-solution mode (~50% cells blanked randomly); 6 languages × 3 styles prompt matrix
- **`parser.py`** — `PicrossParser` with 4-strategy end-first grid extraction (line_scan_reverse, marker_search, digit_extraction, last_resort); normalizes X/., ■/□, #/- markers to 1/0
- **`evaluator.py`** — `PicrossEvaluator` with cell-by-cell comparison; normalized accuracy formula `2*(raw - 0.5)`; match types: exact, partial, mismatch, dimension_mismatch, parse_error
- **`prompts.py`** — User prompt templates for all 6 languages (EN/ES/FR/DE/ZH/UA) × 3 styles (linguistic/casual/minimal)

#### Integration
- `src/stages/analyze_results.py` — added `"picross"` to `_KNOWN_TASK_TYPES` + `"nono"` / `"nonogram"` aliases in `_TASK_ALIASES`
- `reanalyze_results.py` — added `"picross"` to `_TASK_TYPE_SUFFIXES`

#### Tests
- `tests/plugins/test_picross.py` — 38 tests covering solver, grid generation, plugin discovery, generator (all formats + partial solution + multilingual), parser (edge cases: code blocks, unicode markers, end-first, wrong dims), evaluator (exact/partial/dimension_mismatch/parse_error/aggregation)

## [2.16.1] - April 8, 2026

### Frontend UX Improvements

#### Results Page Toolbar Redesign
- **Icon-only action buttons with tooltips** — Reanalyze, Analyze, Charts, LLM Judge, and Delete buttons are now compact icon buttons with selection-count badges and tooltip labels; "Generate Report" keeps its text label as the primary action
- **Per-row dropdown actions** — each result row now has a `⋯` menu with View Details, Rerun with Params, and Delete (replaces the old eye icon)
- **Filter-aware select-all** — "Select All" now selects only the currently filtered/visible rows, not the entire dataset
- **Test Set grouping** — new "Test Set" option in the Group By toolbar alongside None/Model/Task

#### DataTable Enhancement
- **`onFilteredRowsChange` callback** — `DataTable` component now exposes filtered rows to parent via a new optional prop, enabling filter-aware bulk operations

#### Jobs Page
- **Job type badge** — jobs now display a "judge" or "inference" badge; judge model names strip the `judge:` prefix for cleaner display
- **Smart navigation** — "View" button on completed jobs routes to `/judge` page for judge jobs, `/results` for inference jobs

#### Judge Page
- **Delete judge results** — new destructive "Delete" button in the judge result detail view with confirmation toast
- **Tooltip on notes** — long judgment notes now display full text on hover via tooltip

#### TestSets Page
- **Language filter labels** — language filter chips now show flag emoji + full language name (e.g. "🇬🇧 English") instead of raw codes
- **Controlled detail tabs** — detail sheet tab state is now controlled (preserves selection on re-open)

#### New Components
- **`language-filter-chip.tsx`** — `languageLabel()` and `languageFilterOptions()` utilities mapping language codes to flag + name
- **`prompt-style-badge.tsx`** — compact badge component showing prompt style with user/system icon

### Multilingual Measure Comparison Enhancements
- **Localized unit display names** — imperial/customary units now display localized names in CJK and Slavic languages (e.g. "英尺" for foot in Chinese, "фут" in Ukrainian, "Fuß" in German); metric abbreviations remain international
- **Decimal framing templates** — all 4 framing types (neutral, decimal, version, date) now available in all 6 languages (ES, FR, DE, ZH, UA added)
- **New `_unit_display()` helper** with `UNIT_DISPLAY_NAMES` lookup table

### Bug Fix: prompt_metadata Propagation to Parsers
- **`run_testset.py`** — merges `prompt_metadata` fields (language, user_style, system_style) into `task_params` before calling plugin parsers and evaluators, so multilingual parsers receive the correct language context during CLI execution
- **`src/web/jobs.py`** — same prompt_metadata → task_params merge applied in the web worker execution path, fixing multilingual parsing in the Web UI

### Quality of Life
- **Filename truncation** (`path_manager.py`) — testset filenames with many task types are now truncated: task list capped at 120 chars (replaced with `N_tasks`), total filename capped at 240 chars to avoid filesystem errors
- **Standalone `reanalyze_results.py`** — CLI script for bulk re-analysis of result files using current plugin parsers; detects false negatives from falsy expected_answer bugs and boolean parser issues; supports `--fix` and `--reparse-all` modes

## [2.16.0] - April 4, 2026

### LLM-as-a-Judge Feature

New feature for auditing incorrect model responses using a judge LLM to classify them as true incorrect, false negative, or parser failure.

#### Backend
- **New module** `src/web/judge.py` — `run_judge_worker()` subprocess function with default system/user prompts; loads result files, filters to incorrect results, queries judge LLM for each, parses JSON verdicts with regex fallback, saves `judge_*.json.gz` output with summary statistics; atomic writes via tempfile
- **New `submit_judge()` method** on `JobManager` (`src/web/jobs.py`) — creates judge background jobs reusing the ProcessPoolExecutor with progress tracking
- **3 new API endpoints** (`src/web/api/analysis.py`):
  - `POST /api/results/judge` — submit a judge job (model, provider, prompts, sampling params, result files, only_incorrect toggle)
  - `GET /api/results/judge-results` — list all judge output files with summary stats (verdict counts, parser issue breakdown)
  - `GET /api/results/judge-results/{filename}` — get full judge result with all individual judgments
- **Judge output format**: JSON.gz with metadata (judge model, duration), summary (total_judged, true_incorrect, false_negative, parser_failure counts + parser_issues breakdown), and per-result judgments (verdict, parser_issue type, confidence, notes)

#### Frontend
- **"LLM Judge" button** on Results page toolbar — opens a setup Sheet for configuring the judge
- **Judge Setup Sheet** (`components/judge-setup-sheet.tsx`) — 4 sections:
  - Scope: "Only incorrect results" toggle + file count
  - Model selection: Ollama / OpenAI-Compatible tabs with model discovery + saved credentials
  - Prompts: collapsible system prompt and user prompt template editors (pre-filled with defaults, editable, with reset-to-default)
  - Sampling: temperature + max tokens
- **Toolbar reorganized** — buttons grouped into Analysis (Reanalyze, Analyze, Charts) | Actions (Rerun, Report, LLM Judge) | Destructive (Delete), separated by vertical dividers
- **New types**: `JudgeRequest`, `JudgeSubmitResponse`, `JudgeSummary`, `JudgmentEntry`, `JudgeResult`
- **New API/hooks**: `submitJudge()`, `fetchJudgeResults()`, `fetchJudgeResult()`; `useSubmitJudge()`, `useJudgeResults()`

### Multilingual Evaluator Fix
- **Object Tracking evaluator** — now checks `expected_answer_localized` from task_params alongside English `expected_answer`; new `localized_match` match type for non-English correct answers (e.g. Ukrainian "тумбочці" matching localized "тумбочці" when expected is English "nightstand")
- **Object Tracking parser** — `_get_known_locations()` now includes `expected_answer_localized` in the known locations set
- **Sally-Anne evaluator** — checks `expected_answer_localized`, `container_a_display`, `container_b_display` from task_params; reality trap detection also recognizes localized container names

## [2.15.0] - April 4, 2026

### Deep Multilingual Content Localization (all 18 plugins)

All 18 benchmark plugins now generate test content (scenarios, questions, data, narratives) in the requested language — not just prompt wrappers. Previously, only the outer instruction text was translated while generated content remained English.

#### Batch 1: ASCII Shapes, Grid Tasks, Object Tracking
- **ASCII Shapes** — questions ("What are the dimensions...?") now generated in all 6 languages via `_QUESTIONS` dict
- **Grid Tasks** — column headers, data values (products, regions, months, departments, cities, etc.), and question templates all localized; new `data/grid_i18n.py` with translation tables for 4 data generators × 6 languages
- **Object Tracking** — scenario narratives (placement, inversion, movement, distractors, questions) fully localized via `step_i18n.py`; vocabulary (objects, containers, locations, rooms, appliances) translated; subject pronouns/possessives per language; fixed accent errors in Spanish, French, German prompts

#### Batch 2: Encoding Cipher, Family Relations, Sally-Anne
- **Encoding Cipher** — encoding display names localized ("cifrado César", "凯撒密码"); sentence fragments for decode_only mode translated (10 per language); act instructions translated; new word lists: `words_es.txt`, `words_fr.txt`, `words_de.txt`, `words_zh.txt`
- **Family Relations** — relationship labels (brother/hermano/frère/Bruder/兄弟/брат), plural forms, pronouns, names, question templates, and narrative templates all localized via `i18n.py`; all 10 template functions accept `language`; fixed accent errors in Spanish, French, German prompts
- **Sally-Anne** — narrative templates (place/leave/move/witness/return), question templates, objects, containers, pronouns, and names all localized via `scenario_i18n.py`; `ScenarioBuilder` accepts `language`; `expected_answer_localized` added to task_params; fixed accent errors in Spanish, French, German prompts

#### Batch 3: False Premise, Inverted Cup, Strawberry
- **Inverted Cup** — all 4 constant arrays (`DESCRIPTION_STYLES`, `SOURCES`, `ACTION_QUESTIONS`, `EXTRA_CONTEXTS`) converted to per-language dicts with 7 entries × 6 languages
- **Strawberry** — `_ordinal()` expanded for 6 languages (Spanish `.º`, French `er/e`, German `.`, Chinese `第`, Ukrainian `-й`); pangram templates fixed ("English alphabet" → "Latin alphabet"); new Chinese data files: `words_zh.txt`, `anagram_pairs_zh.txt`, `pangrams_zh.txt`, `lipograms_zh.txt`
- **False Premise** — question templates for all 5 domains (chemistry, medicine, food, physics, logic) translated via `i18n.py`; urgency/authority framings localized; chemical/drug names intentionally kept universal; all scenario builder methods accept `language`

#### Batch 4: Linda Fallacy, Misquote Attribution
- **Misquote** — `FRAMING_TEMPLATES` converted to per-language dict (4 styles × 6 languages) with culturally appropriate quote marks (French « », German „"); `_QUESTIONS_BLOCK` localized for all 6 languages
- **Linda Fallacy** — persona description templates, conjunction connectors, component statement templates (9 backgrounds × 6 languages), and distractor pools (12 items × 6 languages) all localized via `i18n.py`; legacy `linda_eval.py` refactored to delegate to i18n module

#### Grammatical Gender Fix (UA, ES, FR, DE)

Eliminated all slash patterns ("кинув/кинула", "un/una", "le/la", "der/die") in gendered languages and fixed Ukrainian noun case endings.

- **New shared module** `src/plugins/grammar_utils.py` — `article()` (ES/FR/DE article by gender+case), `pick_templates()` (gender-aware template selection), `resolve_vocab()` (case-form lookup), `vocab_gender()`
- **Object Tracking** — full rewrite of `step_i18n.py`: Ukrainian vocabulary expanded with nom/acc/loc case forms for all nouns; templates split into m/f variants for UA and FR; ES/FR/DE articles resolved by noun gender; Spanish contracted articles (al, del); German case-aware articles (der/den/dem × m/f/n). Random `subject_gender` per test case stored in `task_params`.
- **Sally-Anne** — full rewrite of `scenario_i18n.py`: Ukrainian case forms + gender-split templates; French possessives by object gender (son/sa); German possessives with case+gender (seinen/seine/ihr/ihre); ES contracted articles (del); object/subject pronouns per language. Random `subject_gender` per test case.
- **Family Relations** — article slashes removed from ES/FR/DE question and narrative templates; callers prepend articles via `label_with_article()` helper; Spanish "only child" split into m/f; French verb agreement via pronoun placeholder; German relative pronouns resolved.
- **Grid Tasks** — ES/FR/DE question templates rephrased to avoid article ambiguity (e.g. "¿Cuál es el valor de {column}?" instead of "¿Cuál es el/la {column}?").
- **Inverted Cup** — Ukrainian SOURCES split into m/f variants with correct past-tense verbs; random gender per test case.

#### Other fixes in this release
- **Testset generation count fix** — `generate_testset.py` no longer divides count by number of prompt configs; `count` now means "per prompt config" (e.g. count=100 × 72 configs = 7,200 cases); linda_fallacy pre-multiplication removed
- **Count ConfigField added** to 7 plugins that lacked it: ascii_shapes, carwash, inverted_cup, measure_comparison, object_tracking, strawberry, time_arithmetic

## [2.14.0] - April 4, 2026

### UI & Workflow Improvements

Major enhancements to the React SPA frontend and FastAPI backend, implementing the PRD for Charts, Results, Test Sets, Configure, and Execute pages.

#### Charts Page
- **Heatmap legend fix** — gradient direction corrected from horizontal to vertical (bottom=red, top=green)
- **Chart filters** — new `ChartFilters` component with multi-select popover dropdowns for task type and language filtering; applied to all 4 tabs (heatmap, comparison, scaling, dimensions)
- **Log scale toggle** — scaling scatter tab has a button to switch X-axis between log and linear scale
- **Task filter on scaling** — scatter plot recalculates per-model accuracy from only the filtered tasks when task filter is active
- **"By Dimension" tab** — new tab with bar charts showing accuracy breakdown by Language, User Prompt Style, or System Prompt Style; backend `/api/results/analyze` returns `dimension_breakdowns` computed from `prompt_metadata`
- **Language-aware filtering** — backend extracts `languages` from result test cases; frontend filters results by language at file-selection level

#### Results Page
- **Reanalyze button** — re-parse and re-evaluate existing model outputs using current plugin parsers without re-running inference; shows per-file accuracy change toasts
- **Rerun with params** — opens shared Param Override Modal, finds matching testset by metadata name, navigates to Execute page
- **Grouping toggle** — sort results by None / Model / Task Type via segmented buttons in toolbar
- **Select all / deselect all** — checkbox in the table header column toggles all; visual states: filled, half-opacity, dim
- **Delete button** — red destructive button in header actions, confirmation dialog, new `DELETE /api/results/{filename}` endpoint
- **Language column** — shows language flags (e.g. flag emojis), with faceted filter
- **User Style / System Style columns** — shows style name or "multi" when several; with faceted filters

#### Test Sets Page
- **View Details column** — moved from dropdown menu to its own dedicated table column with Eye icon
- **Tabbed detail sheet** — Overview (metadata/params) + Cases (paginated with Previous/Next controls)
- **Paginated cases** — backend `GET /api/testsets/{filename}` now supports `page` and `page_size` query params; returns all cases paginated instead of first 5
- **Regenerate with params** — opens shared Param Override Modal, generates new testset variant with overridden prompt params
- **Grouping toggle** — sort testsets by None / Task Type
- **Language column** — shows language flags, with faceted filter
- **User Style / System Style columns** — shows style name or "multi"; with faceted filters

#### Configure Page
- **Count field first** — plugin config forms now sort count-like fields (count, grids_per_difficulty, expressions_per_target, etc.) to appear first; implemented at both API level (`src/web/api/plugins.py`) and client side (`config-form.tsx`)
- **Custom system prompt** — new card with 3 input modes: Text (textarea), File Upload (.txt/.md), and URL Fetch (via `POST /api/testsets/fetch-prompt-url`); character count display with >4000 char warning; included in `GenerateRequest`

#### Execute Page
- **Multi-provider model selection** — all providers (Ollama, OpenAI-compatible, HuggingFace) are now collapsible cards visible simultaneously; select models from any combination of providers in a single run
- **Multiple OpenAI-compatible endpoints** — "Add Another Endpoint" button for configuring Groq, OpenRouter, vLLM, etc. side by side, each with independent model discovery
- **HuggingFace model search** — search HuggingFace Hub by name (2+ chars), optional API key for gated models
- **Global model search** — single search box filters across all provider sections
- **Favorite models** — star toggle per model; localStorage-backed; favorites sorted to top
- **Favorites sidebar** — sticky side panel showing all favorited models grouped by provider; one-click selection with auto provider-switch
- **Encrypted credential storage** — Save/Load API credentials for OpenAI-compatible endpoints via Web Crypto API (AES-GCM)
- **Multi-provider run** — on Run, models are grouped by provider+endpoint and one `/api/jobs/run` request is fired per group; summary badges show count per provider

#### Shared Components & UI Fixes
- **Param Override Modal** (`param-override-modal.tsx`) — reusable Dialog for overriding user style, system style (including custom prompt), and language; used by both Results (rerun → Execute) and Test Sets (regenerate → new testset)
- **Textarea component** (`ui/textarea.tsx`) — new shadcn-style textarea primitive
- **Dialog overflow fix** — `DialogContent` now uses `overflow-hidden overflow-y-auto` with `max-h-[calc(100vh-2rem)]`; prevents horizontal scrollbar and buttons being pushed off-screen by long filenames
- **Language flags utility** (`lib/language-flags.ts`) — maps language codes to flag emojis
- **Dimension bar chart** (`charts/dimension-bar-chart.tsx`) — horizontal bar chart for language/style breakdowns

#### Backend — Reanalysis
- **New module** `src/web/reanalyze.py` — extracted from root `reanalyze_results.py`; provides `reanalyze_result_file()` with atomic file writes (tempfile + `os.replace`)
- **New endpoint** `POST /api/results/{filename}/reanalyze` — re-parses all test results using current plugin parsers, recalculates summary statistics, returns `{old_accuracy, new_accuracy, changes}`

#### Backend — Custom System Prompts
- **Plugin base class** (`src/plugins/base.py`) — `_get_system_prompt()` now accepts `custom_system_prompt` param; `_build_prompts()` forwards it; new `_stash_prompt_config()` method stores custom prompt before `generate_batch()` so all generators automatically pick it up without modification
- **Pipeline** (`src/stages/generate_testset.py`) — propagates `custom_system_prompt` from config through to `prompt_conf` dict; calls `_stash_prompt_config()` before batch generation
- **API** (`src/web/api/testsets.py`) — `GenerateRequest` gains `custom_system_prompt` field; new `POST /api/testsets/fetch-prompt-url` endpoint fetches prompt text from URL (capped at 50KB)

#### Backend — Task Type Inference Fix
- **`_infer_task_type_from_id()`** (`src/stages/analyze_results.py`) — replaced fragile 30-line if/elif chain with a clean function checking 18 canonical task types (longest-first) + 6 aliases (`tracking`→`object_tracking`, `ari`→`arithmetic`, `gol`→`game_of_life`, `c14`→`cellular_automata_1d`, `linda`→`linda_fallacy`, `false_belief`→`sally_anne`); prefers explicit `task_params.task_type` when available
- **Fixed object_tracking "unknown"** — `tracking_0000` test IDs were not matched because the old code only checked `_tracking` (with leading underscore); now also checks `startswith("tracking_")`
- **Fixed `ari_` test IDs** — old arithmetic abbreviation now recognized via alias
- **Shared inference** — `_summarize_result()` in `analysis.py` now imports and uses the same `_infer_task_type_from_id()` instead of naive `test_id.split("_")[0]`

#### Backend — Prompt Metadata in Results
- **`jobs.py`** now stores `prompt_metadata` (user_style, system_style, language) and `config_name` in each result entry, enabling dimension breakdowns and filtering
- **Testset summaries** (`_peek_testset()`) now extract `languages`, `user_styles`, `system_styles` from test case prompt_metadata
- **Result summaries** (`_summarize_result()`) now extract `user_styles`, `system_styles` alongside existing `languages`
- **Analyze endpoint** returns `dimension_breakdowns` with per-bucket accuracy for language, user_style, system_style

#### Frontend Types & API Layer
- New types: `ParamOverrides`, `ReanalyzeResponse`, `DimensionBucket`, `TestsetDetail.total_cases/page/page_size`
- Updated types: `ResultSummary.{languages,user_styles,system_styles}`, `TestsetSummary.{languages,user_styles,system_styles}`, `AnalyzeResponse.dimension_breakdowns`
- New API functions: `reanalyzeResult()`, `fetchPromptFromUrl()`, `deleteResult()`
- New hooks: `useReanalyzeResult()`, `useDeleteResult()`
- New libs: `credential-store.ts`, `favorite-models.ts`, `language-flags.ts`

## [2.13.0] - April 1, 2026

### Full Multilingual Support (all 18 plugins)

All benchmark plugins now support 6 languages (EN, ES, FR, DE, ZH, UA) across prompts, data, and response parsing.

#### Phase 1: Multilingual Prompt Templates
- **11 plugins upgraded** from English-only to 6-language prompt support: symbol_arithmetic, arithmetic, family_relations, grid_tasks, inverted_cup, object_tracking, misquote, false_premise, encoding_cipher, sally_anne (new prompts.py + generator refactored to `_build_prompts()`), linda_fallacy (added DE/ZH/UA to existing EN/ES/FR)
- Encoding cipher: ROT/Morse subtasks restricted to EN+UA only (other languages forced to Base64)

#### Phase 2: Data Relocation + Multilingual Data
- **Moved data to plugins** — relocated `data/` subdirectories into respective plugin source dirs (`src/plugins/*/data/`); updated all `_DATA_DIR` path references in 4 plugins (encoding_cipher, strawberry, false_premise, game_of_life) + `generate_testset.py` + `TestGenerator.py`
- **Encoding cipher** — language-aware word loading (`words_en.txt` + `words_ua.txt`); generator updated with `_load_words(language)` fallback
- **Strawberry** — 20 new multilingual data files: `words_{lang}.txt` (ES/FR/DE/UA), `anagram_pairs_{lang}.txt`, `pangrams_{lang}.txt`, `lipograms_{lang}.txt`; all 4 loaders accept language parameter with English fallback
- false_premise and game_of_life data is language-agnostic (scientific/mathematical) — no multilingual variants needed

#### Phase 3: Multilingual Parser Refactoring + Confidence Scoring
- **Shared utilities** (`parse_utils.py`) — added `merge_keywords()`, `merge_patterns()`, `get_language()`, `build_word_to_int()`, `build_answer_label_re()`, plus shared `WORD_TO_INT`, `ANSWER_LABELS`, `YES_WORDS`, `NO_WORDS` dicts for all 6 languages
- **13 parsers refactored** for multilingual response parsing:
  - family_relations — multilingual number words via shared `build_word_to_int()`
  - grid_tasks — multilingual answer labels
  - ascii_shapes — **added confidence scores** (was returning 0.0) + multilingual boolean/dimension words
  - linda_fallacy — **added confidence scores** + DE/ZH/UA ranking headers and probability keywords
  - encoding_cipher — multilingual refusal patterns + answer labels
  - strawberry — shared multilingual number words + yes/no words from parse_utils
  - misquote — multilingual Q1/Q2 attribution + agreement/disagreement keywords (6 languages)
  - inverted_cup — multilingual flip/wrong patterns (6 languages)
  - sally_anne — multilingual look/search patterns + context keywords
  - object_tracking — multilingual stop words + location verb patterns
  - carwash — multilingual drive/walk keywords + conditional/negation/dismissive patterns (6 languages)
  - false_premise — multilingual refusal/compliance/impossibility/danger/negation patterns (530→967 lines, 6 languages)
  - measure_comparison — completed multilingual unit names, comparative adjectives, equal/incomparable keywords
- **All parsers** now extract language from `task_params` via `get_language()` and use `merge_keywords()` to combine English (always included as fallback) with target language keywords
- **Confidence scoring standardized** — all parsers follow consistent scale: boxed=0.95, bold=0.90, label=0.85, pattern=0.80, keyword=0.70, fallback=0.50, error=0.1
- **Zero regressions** — 299 tests passed throughout all 3 phases (14 pre-existing failures unchanged)

## [2.12.0] - March 31, 2026

### Web UI Improvements

- **Jobs page** — new dedicated page (`/jobs`) with DataTable showing all jobs, state badges with spinner for running, progress bars, cancel/view actions, and faceted state filter
- **Faceted filters** — new reusable `DataTableFacetedFilter` component (popover with checkbox list and counts); applied to Results (model + task) and TestSets (task) pages
- **Plugin descriptions** — `BenchmarkPlugin.description` auto-reads from each plugin's `README.md`; shown on Configure page when a task is selected
- **Configure page cleanup** — sampling parameters (temperature, max tokens, disable thinking) moved to Execute page only
- **Execute page simplified** — single-column layout, navigates to `/jobs` after submission
- **Navigation** — added "Jobs" nav item between Execute and Results

### Removed: TUI and HTMX+Jinja2 interfaces

- **Deleted `src/cli/`** — Terminal UI (questionary + rich) removed entirely (~3,000 lines)
- **Deleted HTMX+Jinja2 web UI** — templates, static assets, and partials router removed
- **React SPA promoted to root** — now served at `/` instead of `/app/`
- **Removed dependencies** — `rich`, `questionary`, `prompt_toolkit` dropped from requirements.txt
- **Archived outdated docs** — TUI-centric architecture docs moved to `docs/_archive/`

## [2.11.0] - March 31, 2026

### React SPA Frontend (replaces HTMX + Jinja2 web UI)

Replaced the server-rendered HTMX + Jinja2 web interface with a modern single-page application built on **Vite 6 + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui**.

#### Stack

- **Vite 6.4** — dev server with HMR, proxies `/api` to FastAPI at `:8000`
- **React 19** — with React Router 7 (client-side routing)
- **TypeScript** — strict mode, full type coverage across API layer
- **Tailwind CSS v4** — via `@tailwindcss/vite` plugin
- **shadcn/ui** — 18 components (Button, Card, Dialog, DataTable, Command, etc.)
- **TanStack React Query** — data fetching with auto-refresh hooks
- **TanStack React Table** — sortable/filterable data tables
- **Lucide React** — icons throughout

#### Frontend Structure (`frontend/`)

```
frontend/
├── src/
│   ├── api/            # Typed API client (client.ts, plugins.ts, models.ts, testsets.ts, jobs.ts, results.ts)
│   ├── hooks/          # React Query hooks (use-plugins.ts, use-models.ts, use-testsets.ts, use-jobs.ts, use-results.ts)
│   ├── types/          # TypeScript interfaces (plugin.ts, model.ts, testset.ts, job.ts, result.ts, index.ts)
│   ├── pages/          # 6 pages: Dashboard, Configure, TestSets, Execute, Results, Reports
│   ├── components/
│   │   ├── ui/         # shadcn/ui primitives (18 components)
│   │   ├── layout/     # AppLayout, Sidebar, Header
│   │   ├── plugin-config/  # Dynamic config field renderer
│   │   └── data-table/ # Generic sortable/filterable DataTable
│   ├── App.tsx         # Router + QueryClientProvider
│   └── main.tsx        # Entry point
├── vite.config.ts      # base: "/app/", proxy /api → :8000
└── package.json
```

#### Pages

| Route | Page | Description |
|-------|------|-------------|
| `/app/` | Dashboard | Plugin count, model status, recent test sets & jobs |
| `/app/configure` | Configure | Dynamic plugin selection, multi-language checkboxes with flags, prompt style matrix, plugin-specific config fields |
| `/app/testsets` | Test Sets | List/inspect generated test sets |
| `/app/execute` | Execute | Job submission with model & test set selection, real-time progress |
| `/app/results` | Results | Browse results with DataTable, accuracy breakdowns |
| `/app/reports` | Reports | View generated HTML reports in iframe |

#### Key Features

- **Dynamic plugin config forms** — `ConfigField` schemas from backend rendered as typed form controls (number, select, multi-select, boolean, range, weight_map)
- **Multi-language selection** — checkboxes with flag emojis (🇬🇧🇪🇸🇫🇷🇩🇪🇨🇳🇺🇦), generates prompt configs per language × user style × system style
- **Dark/light theme** — via next-themes + Tailwind CSS
- **Auto-refreshing job status** — React Query polling with configurable intervals
- **Responsive layout** — collapsible sidebar, mobile-friendly

#### Backend Changes

- **Route reordering in `analysis.py`**: Specific routes (`/reports`, `/report/{filename}`, `/charts/{filename}`) moved before catch-all `/{filename}` to fix 404 errors
- FastAPI continues to serve the REST API at `/api/`; built frontend served from `/app/`

---

## [2.10.7] - March 30, 2026

### False Premise Parser — False-Negative Fixes (70 cases analyzed, 61 fixes)

Fixed 61 confirmed false negatives from LLM-judge review across all 5 false_premise domains (medicine: 37/42, chemistry: 12/14, logic: 7/7, physics: 3/3, food_safety: 2/4). In all 70 cases the model correctly refused or identified the false premise but the parser misclassified the response.

#### 7 Root Causes Identified & Fixed

1. **Smart/curly quote mismatch** (RC1, 11 cases): Unicode curly apostrophes (`'` U+2019) broke every regex using straight `'`. All gpt-oss terse refusals ("I'm sorry, but I can't help with that.") fell through to fallback → None.

2. **False compliance signals in refusal text** (RC2, ~25 cases): INSTRUCTION_PATTERNS matched "mix bleach and ammonia" even in negated/warning context ("Do NOT mix bleach and ammonia"). MEASUREMENT_PATTERN matched "1 ppm" in danger explanations and "1 tablespoon per gallon" in safe-alternative sections.

3. **Overly broad HEDGE_QUALIFIERS** (RC3, ~20 cases): Bare `however|but|that said|nevertheless` matched generic transition words in virtually all explanatory refusal text, feeding into hedge classification.

4. **Hedge position comparison with warning context** (RC4, ~15 cases): Models saying "Never combine X — it produces chloramine gas" triggered both refusal AND compliance signals, with safe-alternative measurements appearing after refusal → hedge.

5. **Logic domain zero/null answers** (RC5, 7 cases): Models correctly answering "probability is 0" or "trick question" didn't match impossibility or refusal patterns.

6. **Strategy ordering** (RC6, 3+ cases): Impossibility check ran after hedge detection, so physics/logic responses with transition words were caught by hedge first.

7. **Missing refusal phrasings** (RC7, 6+ cases): "I can't help with that", "you can't make", "isn't a safe dose" — common refusal verbs (help, assist, make) weren't in REFUSAL_PATTERNS.

#### Parser Changes (`src/plugins/false_premise/parser.py`)

- **Smart/curly quote normalization**: `'` `'` `"` `"` → ASCII before any regex matching
- **Negation-aware compliance detection**: New `_is_negated_context()`, `_has_affirmative_instruction()`, `_has_affirmative_measurement()` helpers — "Do NOT mix" no longer counts as instruction
- **Safe-alternative section detection**: New `_is_in_safe_alternative_section()` — measurements after "Instead:"/"Safe options:" headers discounted
- **Markdown stripping**: `_strip_markdown()` removes `**`/`__` for cleaner impossibility matching
- **Narrowed HEDGE_QUALIFIERS**: Bare `however/but/that said` replaced with lookahead requiring compliance-suggesting language ("but here's the ratio", "but you can use")
- **Expanded REFUSAL_PATTERNS** (+8 patterns): "I can't help/assist", "you can't make/achieve", "isn't a safe dose", "sorry...can't...help"
- **Expanded IMPOSSIBILITY_PATTERNS** (+8 patterns): "trick question", "probability is 0" (flexible gap), "there are no blue balls", "voltage doesn't matter"
- **STRONG_REFUSAL_PHRASES**: New pattern list — "extremely dangerous", "can be fatal", "call 911/poison control" — triggers override when 2+ refusal patterns present
- **First-sentence refusal strategy** (Strategy 0): If opening sentences contain a refusal pattern and no genuine ratio exists, classify as refusal regardless of later explanation content
- **Reordered strategies**: Impossibility now runs before hedge detection
- **Strong refusal override in hedge detection**: When full text has 2+ refusal patterns or strong phrases, measurements in safe-alternative sections don't make it a hedge
- **Keyword list cleanup**: Bare `mix`/`combine` removed from COMPLIANCE_KEYWORDS (appear in warnings); negated forms added to REFUSAL_KEYWORDS; domain-specific keywords added ("chloramine gas", "consult your doctor")

#### Remaining 9 (genuinely ambiguous)

- 4 food_safety: Models provide legitimate iron-calcium nutrition guidance — questions aren't truly dangerous
- 5 medicine: Models provide detailed drug interaction frameworks with dosages despite disclaimers (gemma3:1b actually calculates a combined dose)

#### Test Results

- **0 regressions** — all 299 plugin tests pass (14 pre-existing failures in unrelated plugins unchanged)
- **38 new regression tests** in `tests/plugins/test_false_premise_parser.py` covering all 7 root causes + compliance/hedge preservation
- **61/70 JSONL false negatives now correctly classified as refusal** (87.1%)

---

## [2.10.6] - March 30, 2026

### Parser & Evaluator False-Negative Fixes — 4 Plugins (28 cases analyzed, 28 fixes)

Fixed 28 confirmed false negatives from LLM-judge review across object tracking, inverted cup, time arithmetic, and encoding cipher plugins.

#### Object Tracking Parser (9 FNs fixed)

**Root cause**: End-first parsing grabbed distractor locations from explanations instead of the bolded/first-sentence answer. Models consistently write "The keys are on the **counter**." then explain "Moving the cup to the refrigerator..."

- **New `bold_keyword` strategy** (first-bold, not end-first): Extracts the FIRST `**bold**` text matching a known location. Runs on full response (not verification-stripped) since first-bold is position-aware.
- **New `first_sentence_location` strategy**: Finds a known location in the first sentence only, avoiding distractors in explanations.
- **Added `must` to stop_words**: Was missing alongside would/could/should, causing false extraction from "the answer must be..."
- **Strategy order**: single_word → answer_prefix → **bold_keyword** → **first_sentence_location** → sentence_pattern → location_keyword → last_word
- **9 regression tests** added to `tests/plugins/test_object_tracking.py`

#### Inverted Cup Parser (3 FNs fixed)

**Root cause**: Missing "tilt" and "tip" as flip synonyms in `FLIP_PATTERNS`. Models wrote "tilt the cup so the mouth is facing up" — semantically correct but not matched.

- **5 new patterns** added to `FLIP_PATTERNS`: `\btilt\s+(?:it|the\s+cup)\b`, `\btip\s+(?:it|the\s+cup)\b`, `\bmouth\b.*\bfacing\s+up\b`, `\brim\b.*\b(?:facing\s+up|on\s+top)\b`, `\bopen(?:ing)?\s+(?:end|side)\s+(?:facing\s+)?up\b`
- **11 tests** in new `tests/plugins/test_inverted_cup_parser.py` (3 fixable FNs + 2 non-fixable confirmations + 6 existing pattern coverage)

#### Time Arithmetic Parser (14 FNs fixed)

**3 root causes**: (1) Validity parser didn't handle "No"/"Yes" as answers for DST/leap-year questions. (2) `"no" in "not divisible"` substring false positive. (3) Label strategy grabbed intermediate "Current time:" from computation steps.

- **New `first_yes_no` strategy**: Detects "No"/"Yes" at response start (including after `##` headings or `**` bold)
- **New `label_yes_no` strategy**: Handles "**Final Answer:** No." and multi-line variants where content is on next line
- **Validity bold changed to first-bold**: First bold has the yes/no answer; later bolds contain explanation (same pattern as object tracking)
- **Word-boundary matching**: `_validity_has_no()` / `_validity_has_yes()` helpers use `\bno\b` / `\byes\b` regex, preventing "no" from matching inside "not"/"nothing"
- **New `final_answer_label` strategy** for time and day parsing: Specifically matches "Final Answer:" before generic labels like "time:" or "day:" that appear in computation steps
- **Reordered time strategies**: `time_pattern` now runs before generic `label_line` — the last 12h time in the response is more reliable than intermediate label values
- **New `_extract_day_last()` helper**: Returns the LAST day name from bold text (old `_extract_day` returned first, grabbing "Saturday" from "before Saturday was a Sunday")
- **13 regression tests** added to `tests/plugins/test_time_arithmetic.py` (10 validity + 2 time + 1 day)

#### Encoding Cipher Evaluator (2 FNs fixed)

**Root cause**: Evaluator's `_normalize()` didn't handle Unicode whitespace or internal punctuation differences between model output and expected answer.

- **Unicode whitespace normalization**: `_normalize()` now uses `re.sub(r'\s+', ' ', text)` to collapse NNBSP (`\u202f`), NBSP, etc. to regular spaces
- **Punctuation-stripped comparison** for `decode_only` mode: Strips internal `.`,`,`,`;` etc. before comparing, since source texts have no punctuation but models may add periods
- **2 regression tests** added to `tests/plugins/test_encoding_cipher.py`

#### Design Decisions

- Object tracking `bold_keyword` uses FIRST match (not end-first) — intentional exception because models bold the answer in the first sentence, then bold distractors in explanations
- Time arithmetic validity uses first-bold and first-sentence detection — yes/no questions have the answer upfront, unlike computation questions where the answer is at the end
- Word-boundary matching (`\bno\b`) prevents "no" matching inside "not", "nothing", "know" — a recurring false-positive pattern in validity keyword scanning
- Encoding cipher punctuation stripping only applies to `decode_only` mode — `decode_and_act` expects exact word matches

#### Test Results

- **0 regressions** — all 275 plugin tests pass (14 pre-existing failures in unrelated plugins unchanged)
- **36 new regression tests** across 4 test files

## [2.10.5] - March 29, 2026

### Measure Comparison Parser — False-Negative Fixes (38 cases analyzed, 6 root causes)

Fixed 38 confirmed false negatives from LLM-judge review where models answered correctly but the heuristic parser misclassified or failed to extract the answer.

#### What Changed

- **Smart/curly quote normalization** (Fix 1, 12+ cases): Unicode curly quotes (`\u2018`/`\u2019`/`\u201C`/`\u201D`) are now normalized to ASCII before regex matching. Incomparable patterns like `can't compare` now work regardless of quote style.
- **Tightened `_EQUAL_KEYWORDS` regex** (Fix 2, 15+ cases): Removed bare `\bsame\b` — now requires conclusive context like "are the same", "same value", "both are equal". Prevents false "equal" from explanatory phrases like "convert to the same unit" or "the same whole number part".
- **Strategy pipeline reorder** (Fix 2b): Keywords moved below structured extraction. New order: boxed → bold → label_line → value_unit_comparative → incomparable keywords → value_unit_match → equal keywords → position → last_value_unit → bare_value → fallback. Incomparable keywords stay above value_unit_match (incomparable responses always restate both values); equal keywords moved below (explanatory "same" was short-circuiting correct value extraction).
- **Bold two-pass strategy** (Fix 3, 8+ cases): Pass 1 checks all bolds for equal/incomparable keywords (answer signal). Pass 2 tries last-resolvable bold for value extraction. Skips header bolds (ending with `:`). Fixes cases where models bold "**equal**" then bold a converted value "**880 yards**" — the keyword bold now takes priority.
- **Expanded `_INCOMPARABLE_KEYWORDS`** (Fix 4, 5+ cases): Added "different kinds/types of units/measurements", "measure different things", "aren't comparable", "not meaningful". Deduplicated 3 redundant `incomparable` entries.
- **Reverse comparative pattern** (Fix 5, 1 case): "the lighter one is 758.337 oz" now matches alongside the existing "{value} {unit} is {comparative}" pattern.
- **Bare value fallback** (Fix 6, 1 case): New strategy at confidence 0.60 matches unit-less answers (e.g., model answers "0.699" without unit "s") against option values.
- **20 regression tests** in `tests/test_measure_comparison_plugin.py` across 7 new test classes covering all 6 root causes
- **0 regressions** — all 218 measure-comparison-related tests pass; all pre-existing tests unchanged

#### Design Decisions

- Smart quote normalization applied once at `parse()` entry — simpler and more future-proof than patching every regex
- Incomparable keywords checked BEFORE value_unit_match because incomparable responses always mention both values (value extraction would pick one up). Equal keywords checked AFTER because models say "convert to the same unit" in normal comparison explanations.
- Bold two-pass gives keyword bolds absolute priority over value bolds — models highlighting "equal" or "incomparable" in bold is a strong answer signal
- `_EQUAL_KEYWORDS` now requires copula before "same" (`are/is/they're the same`) or measurement-specific nouns after ("same value/weight/length"), preventing false matches from "the same unit" in method explanations

## [2.10.4] - March 29, 2026

### Carwash Parser — Expanded Conditional/Dismissive Walk Filtering

Fixed 15 confirmed false negatives where models correctly recommended "drive" but the parser extracted "walk" from conditional, negative, or dismissive walk mentions later in the response.

#### What Changed

- **Expanded `_PRE_WALK_CONDITIONAL` patterns**: Added "the only time/reason/scenario", "when you might", "the main/real argument for", "if for any reason", "if any of the above", domain-specific conditionals ("if the mud/road/weather/plate/visibility")
- **Expanded `_WALK_CONDITIONAL` patterns**: Added "could walk...but" (dismissive concession), "walk...but you/it/that" (concession), "walk for exercise/fitness/health" (non-primary motivation), "walk instead" (preceded by conditional context)
- **New `_WALK_NEGATIVE` pattern group**: Catches walk mentioned in dismissive/negative context — "walking won't/wouldn't/doesn't/can't", "walking [back] would complicate/be awkward", "walking [there] leaves", "walking is fine/okay but", "walking feels like a chore/silly", "walkable but", "walking back" (return trip logistics)
- **New first-sentence strategy** (Strategy 3): Short opening lines with unambiguous drive/walk signal extracted before full-text scan. Catches the dominant pattern where models open with "Drive." / "Drive there." / "I'd drive."
- **Fixed bold strategy** (Strategy 2): Walk-scoring bolds now verified against surrounding full-text context via `_is_conditional_walk()`. When all signalling bolds agree, first match used; when conflicting (self-correction), last wins
- **15 regression tests added** in `tests/test_parser_end_first.py` covering all false negative responses from LLM-judge review
- **0 regressions** — all 50 end-first parser tests pass; all pre-existing plugin tests unchanged

#### Design Decisions

- Conditional walk window expanded from 100→120 chars before and 60→80 chars after for better context capture
- `_WALK_NEGATIVE` patterns allow one intervening word (e.g., "walking back would" matches via `(?:\w+\s+)?`)
- Bold strategy uses contextual filtering rather than position-based heuristics — each walk-scoring bold is checked against `_is_conditional_walk()` on the full response text
- First-sentence strategy does not violate end-first principle — it's a high-specificity strategy for short opening answer lines, not reasoning text

## [2.10.3] - March 28, 2026

### Parser False-Negative Fixes — Verification Section Stripping, Conditional Walk Detection

Fixed ~91 confirmed false negatives across 6 parsers where models gave correct answers but parsers extracted wrong values from verification/confirmation sections or conditional language.

#### What Changed

- **New shared utility `strip_verification_tail()`** in `parse_utils.py`: Regex-based function that finds verification/confirmation section headers ("Verification:", "Let me verify:", "This confirms", "Working backward") and returns only the text before them. Prevents end-first parsers from grabbing re-computed values from validation sections.
- **`time_arithmetic` parser (~47 FNs fixed)**: Applied `strip_verification_tail()` to Strategies 3-4 (`_parse_time`, `_parse_day`, `_parse_duration`). Models that verify answers by re-computing ("12:02 AM + 1h53m = 1:55 AM") no longer have the verification value extracted instead of the actual answer.
- **`object_tracking` parser (~18 FNs fixed)**: Applied `strip_verification_tail()` to Strategies 3-5 (sentence_pattern, location_keyword, last_word). Step-by-step traces mentioning intermediate locations no longer override the correct answer.
- **`carwash` parser (~14 FNs fixed)**: Added conditional walk detection in `_score()`. Two new regex patterns (`_PRE_WALK_CONDITIONAL`, `_WALK_CONDITIONAL`) detect walk mentions inside conditional/exception language ("only walk if...", "if you prefer to walk...", "exception: walk when...") and exclude them from the drive/walk tie-break.
- **`measure_comparison` parser (8 FNs fixed)**: New "value_unit_comparative" strategy (confidence 0.87) handles `{value} {unit} is {adjective}` patterns (e.g., "18.68 h is shorter"). Fixed `_normalise_unit()` to accept single-char unit prefixes when followed by non-alpha characters.
- **`encoding_cipher` parser (3 FNs fixed)**: Added multi-line label regex to `_try_labelled_answer()` handling `**Plaintext**\n\nDecoded text` and `**Plaintext (decoded by shifting back 3):**\n\nText` formats.
- **`sally_anne` parser (1 FN fixed)**: Applied `strip_verification_tail()` to Strategies 5 and 7 (last_sentence, direct_container_match).
- **0 regressions** — all 178 passing plugin tests remain passing; all pre-existing failures unchanged

#### Design Decisions

- `strip_verification_tail()` placed in shared `parse_utils.py` for reuse across parsers
- Verification stripping applied only to lower-confidence strategies (pattern/keyword search), not to high-confidence strategies (boxed, bold) which are already scoped to specific formatting
- Carwash conditional detection is conservative: only filters walk mentions preceded by explicit conditional language ("if", "unless", "only when", "exception")
- `_normalise_unit()` single-char fix uses next-char-is-alpha guard to prevent false matches (e.g., "k" in "kilometer")

## [2.10.2] - March 28, 2026

### C14 Cell Markers, Report Improvements, Web UI Results Page

Custom cell markers for the `cellular_automata_1d` plugin (matching GoL), three report rendering improvements, and a task-types column in the web UI results page.

#### What Changed

- **C14 custom cell markers**: Added `cell_markers` config option (default `"1,0"`) to `cellular_automata_1d` plugin, matching the GoL pattern. State strings, rule tables, and boundary descriptions all use custom markers. Added `_normalize_cell_markers()` helper, `ConfigField` (text, advanced group), and `live_cell`/`dead_cell` in `task_params`.
- **C14 rule table with custom markers**: `CellularAutomata1DEngine.format_rule_table()` now accepts `alive_char`/`dead_char` parameters. Rule table headers show `❤️❤️❤️ ❤️❤️🖤` (not `111 110`) when custom markers are active.
- **C14 boundary descriptions**: Boundary description strings in all 6 languages use `{l}`/`{d}` placeholders, resolved to the active cell markers before prompt assembly.
- **Report: expected value N/A fix**: Added `_get_expected_display()` helper in `analyze_results.py` that checks all known key names (`expected_answer`, `expected_state`, `expected_next_state`, `expected_fallacy`). 1D arrays format as space-separated, 2D arrays as rows joined with ` | `.
- **Report: parsed answer formatting**: Added `_format_parsed_display()` that formats parsed answers identically to expected answers (e.g., `0 0 0 | 1 1 1` instead of Python list repr).
- **Report: collapsible thinking block**: Added `_extract_thinking()` helper that checks `output['reasoning']` first, then falls back to `<think>...</think>` tag extraction. Thinking is rendered as a collapsible `<details>` section with amber styling.
- **Web UI: task types in results table**: Results page now shows a "Tasks" column with chip badges (matching the testsets page pattern). Data was already available from the API.
- **28 tests** in `tests/test_c14_and_report_fixes.py` — all passing

#### Design Decisions

- C14 cell markers follow the same `_normalize_cell_markers()` pattern as GoL for consistency
- `format_rule_table()` defaults to `'1'`/`'0'` — existing callers unaffected
- Thinking extraction prefers structured `reasoning` key over regex tag extraction
- `_get_expected_display()` uses priority order: `expected_answer` > `expected_state` > `expected_next_state` > `expected_fallacy`

## [2.10.1] - March 27, 2026

### Game of Life Plugin — Cell Markers Fix, Real-World Patterns, Empty Grid Exclusion

Three improvements to the `game_of_life` plugin: a critical bug fix for custom cell markers (including emoji), expanded known patterns from the Conway's Life pattern database, and an option to exclude empty initial grids.

#### What Changed

- **Fixed cell marker parsing**: Custom cell markers (e.g., `"❤️,🖤"`) now work correctly. Previously, comma-separated string markers were indexed character-by-character instead of being split, so only the first character was used as the live marker. Added `_normalize_cell_markers()` in both `generator.py` and `generate_testset.py` to handle string, list, and tuple inputs.
- **Fixed `format_grid()` double-replacement bug**: The old implementation used chained `.replace('1', live).replace('0', dead)` which corrupted output when markers contained `'0'` or `'1'` characters. Now uses direct per-cell mapping.
- **Expanded known patterns**: `TestGenerator` now loads 1,061 real-world patterns from `data/conways_life/sorted_patterns/` (Conway's Life pattern database). Patterns are filtered by grid dimensions (all patterns where W ≤ grid width AND H ≤ grid height), cached per dimension pair, and preferred over the 7 hardcoded `BASIC_KNOWN_PATTERNS`. Falls back to hardcoded patterns when no sorted files fit.
- **`exclude_empty` option**: New ConfigField (checkbox, advanced group, default `False`). When enabled, regenerates test cases if the initial grid is all-dead (up to 10 retries).
- **Cell markers precedence**: Per-task `cell_markers` from generation config now takes priority over the global `execution.cell_markers` setting.
- **13 new tests** in `tests/test_gol_changes.py` — all passing, 0 regressions in existing GoL tests

#### Design Decisions

- `sorted_patterns` loaded with "all fitting" strategy (W ≤ grid_w, H ≤ grid_h), not just exact-size matches
- `exclude_empty` checks initial state only (not next-generation state)
- `BASIC_KNOWN_PATTERNS` kept as fallback when no sorted_patterns files are found
- Retry limit of 10 for empty grid regeneration to prevent infinite loops

## [2.10.0] - March 27, 2026

### Symbol Arithmetic Plugin — 18th Benchmark Task

New plugin `src/plugins/symbol_arithmetic/` — evaluate expressions under arbitrary binary operations defined by lookup tables. Tests pure rule-following with zero semantic anchor: models must use only the given operation table, not prior mathematical knowledge.

#### What Changed

- **New plugin `symbol_arithmetic`** with 4 operation classes: `commutative`, `non_commutative`, `non_associative`, `arbitrary`
- **3 symbol types**: `alpha` (A, B, C…), `emoji` (🔴, 🟢, 🔵…), `nonsense_words` (ZIG, ZAG, MOP…)
- **2 table formats**: `matrix` (grid with row/column headers) and `pairs` (enumerated A ★ B = C lines)
- **Configurable expression trees** of depth 1–4 with fully parenthesized output to eliminate grouping ambiguity
- **Partial tables**: configurable fraction of entries removed; expressions may evaluate to UNDEFINED
- **Commutativity trace**: enumerates all 2^k swap combinations at operator nodes to detect commutativity assumptions
- **Associativity trace**: enumerates all Catalan-number regroupings (guarded at 7 leaves) to detect associativity assumptions
- **6-strategy end-first parser**: undefined_detection → boxed_symbol → labelled_answer → equals_pattern → bold_symbol → last_symbol (all filtered against valid symbol set)
- **8-type match taxonomy** in evaluator:
  - `correct` (True) — exact match
  - `wrong_assumed_commutative` (False) — matches commuted evaluation
  - `wrong_assumed_associative` (False) — matches regrouped evaluation
  - `wrong_arbitrary` (False) — wrong, no known assumption pattern
  - `undefined_correct` / `undefined_wrong` / `undefined_missed` — partial table handling
  - `parse_error` (False) — couldn't extract answer
- **Derived metrics**: `commutativity_assumption_rate`, `associativity_assumption_rate`
- **ConfigField schema**: set_size (3–8), expression_depth (1–4), operation_class, table_completeness, table_format, symbol_type, count, partial_missing_fraction, difficulty (easy/medium/hard/nightmare presets)
- **Pipeline integration**: `analyze_results.py` — task type recognition for symbol_arithmetic test IDs
- **42 unit tests** across 9 test classes — all passing

## [2.9.0] - March 27, 2026

### Encoding & Cipher Decoding Plugin — 17th Benchmark Task

New plugin `src/plugins/encoding_cipher/` — decode-and-respond tasks across encoding schemes. Tests whether models can decode an encoded message (and optionally follow an embedded instruction), with a custom 5-type failure taxonomy that distinguishes hallucinated execution from genuine decoding.

#### What Changed

- **New plugin `encoding_cipher`** with 2 task modes: `decode_only` (return plaintext) and `decode_and_act` (decode, find instruction, respond with a single word)
- **3 encoding schemes**: Base64, Caesar/ROT-N (shifts 3, 7, 13), Morse code (ITU standard)
- **Pure-function encoding engine** (`encoding.py`) — all encode/decode roundtrips verified
- **Curated word list** (`data/encoding_cipher/words.txt`) — ~200 uncommon English words for `decode_and_act` response targets
- **Multi-strategy parser** with refusal detection + mode-specific strategies (end-first):
  - decode_only: code_block → quoted_text → labelled_answer → full_response_strip
  - decode_and_act: single_word_response → labelled_word → quoted_word → bold_word → last_standalone_word
- **5-type failure taxonomy** in evaluator:
  - `correct` (True) — case-insensitive match
  - `hallucinated_execution` (True, flagged) — right word but no decoding evidence
  - `paranoid_refusal` (False) — model refused to decode
  - `wrong_decode` (False) — decoded but wrong answer
  - `parse_error` (False) — couldn't extract answer
- **Aggregation**: mode_breakdown, encoding_breakdown, caesar_shift_breakdown, hallucination rate, refusal rate
- **ConfigField schema**: count, task_modes, encoding_types, caesar_shifts, message_length, mode_weights, encoding_weights
- **Pipeline integration**: `analyze_results.py` — task color (`#27ae60`), test_id recognition, HTML badge

#### Design Decisions

- `hallucinated_execution` scored as correct (model got the right answer) but flagged in details — allows measuring how often models skip decoding
- English-only prompts for v1 (multilingual deferred)
- Refusal detection runs before answer extraction — `__REFUSAL__` sentinel value

#### Test Results

- **64 tests** (48 unit + 16 integration) — all passing
- Encoding roundtrips verified for all 3 schemes
- Parser covers refusal, correct, and error paths for both modes

## [2.8.1] - March 27, 2026

### Measure Comparison — Decimal Framing Comparison Type

New `decimal` comparison type for the `measure_comparison` plugin. Tests whether models can correctly interpret the same numeric pair (e.g., 9.9 vs 9.11) under different **framing contexts** — as a pure decimal, a software version, or a date.

#### What Changed

- **New comparison type `decimal`** with 4 framings: `neutral`, `decimal`, `version`, `date`
- **2 answer groups**: neutral + decimal → decimal math ordering; version + date → component-wise ordering
- **Adversarial pairs**: pairs where decimal order ≠ version order (e.g., 9.9 > 9.11 as decimals, but 9.9 < 9.11 as versions)
- **Control pairs**: both orderings agree (e.g., 3.5 vs 2.1) — serves as a baseline
- **Framing group tracking**: each pair generates one `TestCase` per framing, linked by `framing_group_id` in `task_params`
- **Framing-sensitivity metric** in `aggregate_results()`:
  - `framing_sensitivity_rate` — fraction of adversarial groups where the model gave ≥2 distinct answers
  - `framing_accuracy_by_type` — per-framing accuracy breakdown
  - `perfect_group_rate` — fraction of groups where all framings were answered correctly
  - `adversarial_perfect_rate` — same, restricted to adversarial groups
- **Decimal-specific parser** (`_parse_decimal()`) — 5-strategy pipeline: boxed, bold, label, bare-value-match, position keywords
- **Decimal-specific evaluator** (`_eval_decimal()`) — float-normalized comparison with framing metadata in details
- **Config schema additions**: `decimal_framings` (multi-select), `decimal_adversarial_ratio` (0.0–1.0), updated `type_weights` default

#### Design Decisions

- Count is **approximate** when `decimal` type is in the mix — each pair generates `len(framings)` cases
- English-only framing templates for now (multilingual deferred)
- Neutral framing uses decimal math as the "correct" interpretation

#### Test Results

- **40 new tests** in `tests/test_measure_comparison_decimal.py` — all passing
- **0 regressions** in existing measure_comparison tests (150 total)

## [2.8.0] - March 26, 2026

### Plugin-Local Prompt Templates — PromptEngine User Prompt Deprecation

Migrated all 16 plugins from the centralised `PromptEngine` user-prompt templates to **plugin-local `prompts.py` files**. Each plugin now owns its own prompt templates, making plugins fully self-contained.

#### What Changed

- **New file per plugin**: Every plugin now has a `prompts.py` module containing its user prompt template dicts, keyed by `(Language, PromptStyle)` (e.g., `(Language.EN, "casual")`).
- **Base class helpers** added to `TestCaseGenerator` in `src/plugins/base.py`:
  - `_get_prompt_engine()` — lazy-initialised shared `PromptEngine` instance (for system prompts)
  - `_get_system_prompt(system_style, language)` — wraps `PromptEngine.get_system_prompt_by_enum()` with safe enum parsing
  - `_format_user_prompt(templates, language, style, **variables)` — static lookup into plugin-local template dicts with `EN`/`casual` fallbacks
  - `_build_prompts(templates, language, user_style, system_style, **variables)` — convenience method returning `(user_prompt, system_prompt, full_prompt)` tuple
- **PromptEngine.py**: All 8 task-specific template dict sections and convenience functions marked `(DEPRECATED)` with comments pointing to plugin-local canonical locations. No code removed — backward compatible.
- **3 pre-existing C14 generator bugs fixed** during migration:
  - `expected_state` → `expected_states` (plural key name)
  - Added missing `rule_table` computation via `CellularAutomata1DEngine.format_rule_table()`
  - Added missing `boundary_description` lookup for templates

#### PromptEngine Status

| Export | Status | Notes |
|--------|--------|-------|
| `Language`, `PromptStyle`, `SystemPromptStyle` enums | **Active** | Used by all plugins |
| `SYSTEM_PROMPTS` dict | **Active** | System prompts still centralised |
| `PromptEngine.get_system_prompt_by_enum()` | **Active** | Called via base class helper |
| `TaskType` enum | **Deprecated** | No longer used by plugins |
| `PromptContext`, `PromptResult` | **Deprecated** | Replaced by plugin-local templates |
| `PromptEngine.generate()` / `get_user_prompt()` | **Deprecated** | Replaced by `_format_user_prompt()` |
| All `*_PROMPTS` task-specific dicts | **Deprecated** | Templates now in `src/plugins/<task>/prompts.py` |
| `create_*_context()` functions | **Deprecated** | No longer needed |

#### Migration Pattern (for new plugins)

```python
# In your plugin's prompts.py:
from src.core.PromptEngine import Language
TEMPLATES = {
    (Language.EN, "minimal"): "Solve: {expression}",
    (Language.EN, "casual"):  "Hey, what's {expression}?",
    (Language.EN, "linguistic"): "Please evaluate the following: {expression}",
}

# In your plugin's generator.py:
from .prompts import TEMPLATES

class MyGenerator(TestCaseGenerator):
    def generate_batch(self, config, prompt_config, count, seed):
        user_prompt, system_prompt, full_prompt = self._build_prompts(
            TEMPLATES, language, user_style, system_style, expression="2+3"
        )
```

#### Test Results

- **0 regressions**: Before migration 19 failed / 443 passed → After 17 failed / 445 passed
- 2 pre-existing test failures fixed (linda_fallacy test class names)

## [2.7.0] - March 25, 2026

### Family Relations Plugin — Perspective-Aware Family Counting Puzzles

New plugin `src/plugins/family_relations/` — procedural family counting puzzles that test whether models can avoid the classic trap of counting the subject as their own sibling.

- **4 sub-types**: `sibling_count` (self-counting trap), `shared_children` (shared-brothers trap), `generational` (multiplication chains, cousin counting), `perspective_shift` (algebraic constraint solving)
- **10 template functions** generating diverse puzzle configurations with randomized names via `names` library
- **3 user prompt styles** (minimal, casual, linguistic) with system prompts via `PromptEngine.get_system_prompt_by_enum()`
- **6-strategy end-first parser**: boxed, bold, label_line, is_n_tail, last_number, spelled_out (word-to-int mapping 0–20)
- **4 match types**: `correct`, `overcounting` (classic self-counting trap), `undercounting` (missed family member), `parse_error`
- Each puzzle records its `trap` type in metadata (e.g., `counting_self_as_sibling`, `forgetting_subject`, `multiplying_instead_of_sharing`)
- ConfigField schema: count, sub_types (multi-select), sub_type_weights (weight map), difficulty (easy/medium/hard)
- Pipeline integration: `analyze_results.py` task color (burnt orange `#d35400`) and test_id recognition pattern added

## [2.6.0] - March 25, 2026

### False Premise Plugin — Dangerous/Impossible Premise Detection

New plugin `src/plugins/false_premise/` — presents questions embedding dangerous or physically impossible premises; the model must refuse instead of complying.

- **5 domains**: chemistry (toxic reactions), medicine (drug interactions), food_safety (dangerous preparations), physics (impossible scenarios), logic (contradictions)
- **6 CSV data files** in `data/false_premise/` with severity levels (LETHAL/SEVERE/MODERATE)
- **Hard mode** for chemistry: removes safety hedging cues, frames as urgent expert-to-expert requests
- **Combinatorial expansion**: scenarios × urgency framings × authority framings for diverse test cases
- **6-strategy end-first parser**: explicit_refusal, compliance_quantity, hedge_detection, impossibility, keyword_scan, fallback
- **3 match types**: `correct_refusal`, `wrong_compliance`, `partial_hedge`
- Per-domain and per-severity aggregation in `aggregate_results()`
- ConfigField schema with count, domains, hard_mode_ratio, severity_filter
- Pipeline integration: `analyze_results.py` task recognition pattern added

### Misquote Attribution Plugin — Sycophancy Detection Benchmark

New plugin `src/plugins/misquote/` — presents famous quotes with false attributions; the model must reject the wrong author instead of agreeing.

- **27-quote × 20-attributor** data pool with domain-mismatch filtering
- **4 framing styles**: `neutral`, `confident`, `authority`, `constraint` — progressively stronger social-pressure traps
- **Two-part question format**: Q1 (attribution correctness) + Q2 (sentiment) to separate sycophancy from contrarianism
- **6-strategy end-first parser**: numbered, labelled, bare pair, keyword inference, partial Q1, fallback
- **5 match types**: `correct`, `contrarian`, `full_sycophancy`, `partial_sycophancy`, `parse_error`
- `commonly_misquoted` metadata flag per quote for fine-grained analysis
- `framing_style` as an experimental axis — analyze which pressure types fool which models
- Pipeline integration: `analyze_results.py` color, test_id pattern, and HTML badge added

### Time Arithmetic Plugin — Temporal Reasoning Benchmark

New plugin `src/plugins/time_arithmetic/` with 7 sub-types:
- **`interval`** — add/subtract duration to a time
- **`crossing_midnight`** — durations that cross the midnight boundary
- **`noon_midnight_trap`** — tricky AM/PM boundary questions (11:50 AM → 12:10 PM = 20 min, not 1h20m). Supports both result-time and duration question modes.
- **`day_of_week`** — modular day-of-week arithmetic with large offsets
- **`impossible_date`** — impossible calendar dates (Feb 30, Apr 31, etc.)
- **`leap_year`** — Feb 29 validity with century/400-year rule traps (2100, 1900, 2000)
- **`dst_trap`** — (advanced, opt-in) DST spring-forward time holes

Key features:
- 6 novel match types: `correct`, `wrong`, `correct_refusal`, `wrong_compliance`, `wrong_refusal`, `parse_error`
- Impossible-question detection: tracks hallucination rate and false refusal rate per model
- Forward/backward direction support with natural-language backward phrasings
- 12h (AM/PM) and 24h time format modes
- Full multilingual support (EN, ES, FR, DE, ZH, UA)
- ConfigField schema for web UI integration
- ±1 minute tolerance for time matching, abbreviation support for day matching

### Bug Fixes

- **Plugin-only task generation error masking**: `generate_tests_via_plugin()` in `generate_testset.py` caught all exceptions silently and returned `None`, causing plugin-only tasks (no built-in fallback) to show a misleading "Unknown task type" error instead of the real exception. Now re-raises for tasks without built-in fallbacks.

## [2.5.0] - March 24, 2026

### Strawberry Plugin — Character-Level Reasoning Family

Expanded the strawberry plugin from single-task letter counting into a full family of 6 character-level reasoning sub-types:

- **`count`** — Original letter-counting task ("How many R's in strawberry?"). Unchanged, backward-compatible.
- **`reverse`** — Spell a word backwards ("What is 'banana' spelled in reverse?")
- **`nth_letter`** — Identify the Nth letter of a word ("What is the 3rd letter of 'algorithm'?")
- **`anagram`** — Decide whether two words are anagrams ("Are 'listen' and 'silent' anagrams?")
- **`pangram`** — Decide whether a sentence is a pangram (uses every letter A–Z)
- **`lipogram`** — Decide whether a sentence avoids a given letter

#### Generator (`src/plugins/strawberry/generator.py`)
- Full rewrite with sub-type dispatch and weighted selection via `sub_type_weights`
- Multilingual question templates for all 6 sub-types × 6 languages (EN/ES/FR/DE/ZH/UA)
- `sub_types` multi-select config (defaults to `["count"]` for backward compatibility)
- Data loaders for 3 new curated data files

#### Parser (`src/plugins/strawberry/parser.py`)
- Sub-type dispatch: count (7-strategy), reverse (5-strategy), nth_letter (6-strategy), boolean (5-strategy shared by anagram/pangram/lipogram)
- All strategies use end-first parsing convention

#### Evaluator (`src/plugins/strawberry/evaluator.py`)
- Sub-type dispatch: integer comparison (count), case-insensitive string match (reverse), char match (nth_letter), boolean match (anagram/pangram/lipogram)
- `sub_type_breakdown` added to `aggregate_results()` — per-sub-type accuracy stats
- `mode_breakdown` and `mean_off_by` preserved for count sub-type

#### New Data Files
- **`data/strawberry_anagram_pairs.txt`** — 76 curated word pairs (47 true anagrams, 29 near-miss non-anagrams). All verified programmatically.
- **`data/strawberry_pangrams.txt`** — 40 sentences (20 true pangrams, 20 near-pangrams with documented missing letters). All verified programmatically.
- **`data/strawberry_lipograms.txt`** — 44 sentences (26 true lipograms across 11 letters, 18 false cases). All verified programmatically.

#### Plugin Metadata
- Display name updated: "Strawberry (Letter Counting)" → "Strawberry (Character Reasoning)"
- Description updated to cover all 6 sub-types

#### Tests
- Expanded from 30 to 121 test cases in `tests/test_strawberry_plugin.py`
- Full coverage: generator (all 6 sub-types, multilingual, seed reproducibility, weighted distribution), parser (count/reverse/nth_letter/boolean strategies), evaluator (all match types, aggregation with sub_type_breakdown), data file integrity verification

---

## [2.4.1] - March 24, 2026

### Bug Fixes

- **Token counting**: `src/web/jobs.py` was using `tokens_generated` for both input and output tokens — input now correctly reads `tokens_input`; Ollama interface in `run_testset.py` now passes `prompt_eval_count` as `tokens_input`
- **API key leak**: Removed debug `print(url)` and `print(headers)` from `src/web/api/models.py` that exposed auth headers to stdout
- **HuggingFace import guard**: `src/models/HuggingFaceInterface.py` referenced undefined `TRANSFORMERS_AVAILABLE` — wrapped `torch`/`transformers` imports in try/except so the module is importable without those dependencies
- **HuggingFace return type**: `query_model()` declared `-> Tuple[str, Dict]` but returned bare `str` — now returns `(response, token_stats)` tuple matching the signature and OllamaInterface behavior
- **Sally-Anne parser signature**: `parse()` used parameter name `metadata` instead of `task_params`, violating the `ResponseParser` base class contract — renamed throughout
- **Bare except clause**: `src/engine/MathExpressionGenerator.py` used `except:` (catches SystemExit, KeyboardInterrupt) — narrowed to `except ImportError:`

### Dead Code Removal

- **Deleted 6 deprecated benchmark scripts** from `src/benchmarks/`: `gol_eval.py`, `ari_eval.py`, `c14_eval.py`, `gol_eval_matrix.py`, plus `.backup` files (~3,500 lines). Only `linda_eval.py` remains (still imported by linda_fallacy generator)
- **Removed unused abstract classes** (`State`, `BaseRulesEngine`) from `src/engine/GameOfLifeEngine.py` — never inherited or imported
- **Removed hardcoded schema fallback** (84 lines): deleted `_TASK_SCHEMAS` dict from `src/web/api/plugins.py` — all 12 plugins implement `get_config_schema()`
- **Removed commented-out Ollama parameters**: 13 dead config lines from `src/models/OllamaInterface.py`

### Simplification

- **New `safe_enum()` utility** in `src/plugins/parse_utils.py` — replaces try/except enum parsing boilerplate across all 12 generators
- **Updated all 12 plugin generators** to use `safe_enum()` for `Language`, `PromptStyle`, and `SystemPromptStyle` parsing

---

## [2.4.0] - March 24, 2026

### Plugin Configuration Schema Introspection

#### ConfigField System (`src/plugins/base.py`)

- **New `ConfigField` dataclass** — structured field descriptors for plugin configuration with 7 field types: `number`, `select`, `multi-select`, `text`, `boolean`, `range`, `weight_map`
- **New `get_config_schema()` method** on `TestCaseGenerator` — returns `List[ConfigField]` describing all configurable parameters
- **Basic/Advanced field grouping** — fields tagged with `group="basic"` or `group="advanced"` for collapsible UI sections

#### All 12 Generators Implement `get_config_schema()`

- `game_of_life`: 5 fields (difficulty, grids, density, known patterns, cell markers)
- `arithmetic`: 4 fields (complexity, expressions per target, target values, mode)
- `cellular_automata_1d`: 5 fields (rules, cases per rule, width, steps, boundary)
- `linda_fallacy`: 3 fields (options, personas, culture filter)
- `ascii_shapes`: 6 fields (question types, width/height range, symbols, labels, filled ratio)
- `object_tracking`: 6 fields (distractors, moves, types, objects, containers, sticky)
- `sally_anne`: 5 fields (cases, distractors, observer, objects, activities)
- `carwash`: 1 field (distances)
- `inverted_cup`: 1 field (description styles)
- `strawberry`: 6 fields (mode, word lengths, favor repeated, min/max, mixed weights)
- `measure_comparison`: 10 fields (format, comparison type, direction, categories, traps, weights)
- `grid_tasks`: 8 fields (cases, rows, cols, data types, question types, table style)

#### Web API: Schema Introspection Endpoint

- **`GET /api/plugins/{task_type}/schema`** introspects `generator.get_config_schema()` directly (hardcoded `_TASK_SCHEMAS` fallback removed in v2.4.1)
- Response includes `fields` array and `groups` list for UI rendering

#### Web UI: Dynamic Collapsible Config Forms

- **New field renderers** in `configure.html` for `boolean`, `range`, and `weight_map` types
- **Field grouping**: basic fields visible by default, advanced fields in collapsed `<details>` sub-section
- **`buildGeneratePayload()`** extended to collect `boolean`, `range`, and `weight_map` values
- **CSS additions**: `.advanced-toggle`, `.range-pair`, `.weight-map-group` styles

#### Tests

- **New `tests/plugins/test_config_schema.py`** — 9 test cases covering `ConfigField.to_dict()` serialization, all-plugins schema validation, field type/name checks, and JSON round-trip

---

## [2.3.0] - March 24, 2026

### Documentation Overhaul

#### New Documentation

- **`docs/PROJECT_OVERVIEW.md`** — Comprehensive project overview covering mission, architecture (3-stage pipeline, plugin system, web UI), all 12 benchmark tasks, model providers, prompt engineering system, key research findings, and known quirks
- **`docs/PLUGIN_GUIDE.md`** — Complete plugin system guide with base class reference, auto-discovery docs, end-first parsing convention, detailed reference for all 12 plugins, step-by-step new-plugin tutorial with working code, integration points, and testing guidance

#### Documentation Reorganization

- **Archived 20 obsolete docs** to `docs/_archive/`: implementation logs, bug fix summaries, and deprecated references (ASCII_SHAPES_IMPLEMENTATION, C14_*, SALLY_ANNE_*, TUI_SYSTEM, SOURCE_CODE_ORGANIZATION, etc.)
- **Flattened `docs/implementation/prompt-engine/`** to `docs/prompt-engine/` — removed empty nesting
- **Updated `docs/README.md`** — Rewritten as clean navigation hub reflecting current structure and all 12 plugins
- **Updated `CLAUDE.md`** — Corrected plugin count (7 → 12), added new plugin references, added new documentation links
- **Updated `CHANGELOG.md`** — Added documentation overhaul entry

#### CLAUDE.md Corrections

- Fixed plugin count from "7 plugins" to "12 plugins" in directory structure
- Added missing plugins to directory structure: object_tracking, sally_anne, strawberry, measure_comparison, grid_tasks
- Added `parse_utils.py` to directory structure
- Updated Additional Resources section with new docs

---

## [2.2.0] - February 21, 2026

### New Plugins – Practical Reasoning Traps

#### Carwash Paradox (`src/plugins/carwash/`)
- New plugin testing whether a model keeps track of the *goal* of a trip
- Scenario: the carwash is only N metres away — should you walk or drive?
- Correct answer is always **drive** (car must be physically present at the carwash)
- Models naively say "walk" because the distance is short (proximity trap)
- **Generator**: 5 distances × 6 framings × 4 weather contexts × 4 urgency phrases × 3 transport details × 6 question variants; full combinatorial space with seeded shuffling
- **Parser**: 6-strategy detection (`boxed → bold → label_line → strong_intro → full_text → first_sentences`); negation-aware regex (`DRIVE_KEYWORDS`, `WALK_KEYWORDS`, `NEGATION`)
- **Evaluator**: match types `correct` / `naive_trap` / `wrong` / `parse_error`
- **TUI**: added to task selector with default `distances` and `count` parameters
- **Report**: `carwash` task type now correctly labelled (amber `#e67e22` in charts)

#### Inverted Cup (`src/plugins/inverted_cup/`)
- New plugin testing spatial/physical orientation reasoning
- Scenario: a cup with a sealed top and open bottom — how do you use it?
- Correct answer is always **flip** (turn it right-side-up)
- Models suggest drilling, cutting, or returning the cup instead
- **Generator**: 7 sources × 7 description styles × 7 action questions × 5 extra contexts; configurable `description_styles` filter via YAML
- **Parser**: 6-strategy detection including 16 `FLIP_PATTERNS` (flip/turn over/invert/upend/right-side-up) and `WRONG_PATTERNS` (drill/cut/return/discard)
- **Evaluator**: match types `correct` / `wrong` / `parse_error`; distinguishes genuine parse failures from confident wrong answers
- **TUI**: added to task selector with default `description_styles` and `count` parameters
- **Report**: `inverted_cup` task type now correctly labelled (dark teal `#16a085` in charts)

### Infrastructure Enhancements

#### Remote Ollama Support (`--ollama-host`)
- Added `--ollama-host` argument to `src/stages/run_testset.py` (default: `http://localhost:11434`)
- `OllamaInterface` in `run_testset.py` now accepts `base_url` parameter
- `OllamaProvider` in `src/utils/model_providers.py` extended with configurable `host`:
  - `_is_default_host()` helper to detect non-local endpoints
  - Non-default hosts always use REST API (`/api/tags`) instead of CLI subprocess
  - `_is_available_via_api()` and `_list_models_via_api()` methods added
  - `_bytes_to_human()` static helper for size formatting
- `ModelProviderManager.set_ollama_host(host)` method for dynamic re-configuration
- TUI (`benchmark_tui.py`) prompts for Ollama host URL whenever Ollama provider is selected
  - `BenchmarkTUI._configure_ollama_host()` method
  - `ollama_host` stored on both `MultiTaskConfig` and `BenchmarkConfig` dataclasses
  - Host propagated through execution pipeline to `run_testset.py` via `--ollama-host`

#### Token Counting in Pipeline
- Response token counts tracked throughout Stage 2 (`run_testset.py`)
- Token counts surfaced in Stage 3 reports via dedicated columns/charts
- Old result files show `0` tokens (expected backward-compatible behaviour)

### Bug Fixes

- **"Unknown" task type in reports**: Fixed `extract_task_breakdown()` in `analyze_results.py`
  - Added `elif '_carwash' in test_id or test_id.startswith('carwash_')` branch
  - Added `elif '_inverted_cup' in test_id or test_id.startswith('inverted_cup_')` branch
  - Display rendering works automatically via `.replace('_', ' ').title()` pattern

---

## [2.1.0] - January 25, 2026

### Plugin-Based Benchmark System

#### Major Architectural Enhancement
- **Complete refactoring** from monolithic benchmarks to plugin-based architecture
- **Plugin registry** with automatic discovery via package scanning
- **Self-contained modules** for each benchmark (generation, parsing, evaluation)
- **Zero-modification extensibility** - add new benchmarks without touching core code

#### Plugin System Components

**Core Infrastructure:**
- `src/plugins/base.py` - Abstract base classes for all plugins
  - `BenchmarkPlugin` - Plugin interface definition
  - `TestCaseGenerator` - Test generation interface
  - `ResponseParser` - Multi-strategy response parsing interface
  - `ResultEvaluator` - Evaluation interface with aggregation
  - `TestCase`, `ParsedAnswer`, `EvaluationResult` - Standardized data structures

- `src/plugins/__init__.py` - Plugin registry with auto-discovery
  - Automatic plugin loading via `pkgutil`
  - Registration and retrieval system
  - Task type mapping

**5 Built-in Plugins:**
1. **Game of Life** (`src/plugins/game_of_life/`)
   - 4-strategy parsing (line_scan_reverse, marker_search, digit_extraction, last_resort)
   - Cell-by-cell accuracy evaluation
   - Grid normalization and validation

2. **Arithmetic** (`src/plugins/arithmetic/`)
   - 6-strategy parsing (LaTeX boxed, JSON unescape, equals pattern, keyword search, etc.)
   - Exact and approximate numeric matching
   - Expression evaluation

3. **Linda Fallacy** (`src/plugins/linda_fallacy/`)
   - Ranking extraction with fuzzy matching
   - Conjunction fallacy detection
   - Cultural/language alignment

4. **Cellular Automata 1D** (`src/plugins/cellular_automata_1d/`)
   - Binary state parsing (4 strategies)
   - Cell-by-cell state comparison
   - Normalized accuracy (2 * (raw - 0.5))

5. **ASCII Shapes** (`src/plugins/ascii_shapes/`)
   - Type-specific parsing (dimensions, count, position)
   - Multiple output formats supported
   - Tolerance-based count evaluation

#### Integration with 3-Stage Pipeline

**Stage 1 (generate_testset.py):**
- Plugin-based test generation with fallback to built-in generators
- `generate_tests_via_plugin()` helper function
- Backward-compatible with legacy generators

**Stage 2 (run_testset.py):**
- Plugin-based parsing with `parse_answer_via_plugin()`
- Plugin-based evaluation with `evaluate_via_plugin()`
- Graceful degradation to legacy parsing if plugin unavailable

**Stage 3 (analyze_results.py):**
- No changes required - works with plugin-generated results

#### Deprecation and Migration

**Legacy Files Deprecated:**
- `src/benchmarks/gol_eval.py` - Use Game of Life plugin
- `src/benchmarks/ari_eval.py` - Use Arithmetic plugin
- `src/benchmarks/linda_eval.py` - Use Linda Fallacy plugin
- `src/benchmarks/c14_eval.py` - Use C14 plugin

**Deprecation warnings added** to all legacy files with migration guidance.

#### Comprehensive Test Suite

**Unit Tests Created:**
- `tests/plugins/test_registry.py` - Plugin discovery and registration
- `tests/plugins/test_game_of_life.py` - GoL plugin (generator, parser, evaluator, roundtrip)
- `tests/plugins/test_arithmetic.py` - ARI plugin with all 6 strategies
- `tests/plugins/test_linda_fallacy.py` - Linda plugin with fallacy detection
- `tests/plugins/test_cellular_automata_1d.py` - C14 plugin with state comparison
- `tests/plugins/test_ascii_shapes.py` - Shapes plugin with type-specific tests

**Test coverage:**
- Plugin auto-discovery
- Component availability (generator, parser, evaluator)
- Valid and invalid input handling
- Exact, partial, and mismatch evaluation
- Full roundtrip tests (generate → parse → evaluate)

### Benefits and Impact

**Code Quality:**
- ✅ Eliminated ~1000+ lines of duplicated code across benchmarks
- ✅ Clean separation of concerns (generation/parsing/evaluation)
- ✅ Standardized data structures across all benchmarks
- ✅ Multi-strategy parsing with fallback mechanisms

**Extensibility:**
- ✅ Add new benchmarks by creating plugin directory (no core code changes)
- ✅ Plugin auto-discovery - just create and it works
- ✅ Self-contained modules - everything in one place
- ✅ Easy to test and maintain

**Backward Compatibility:**
- ✅ Legacy benchmarks still work via fallback
- ✅ 3-stage pipeline unchanged for users
- ✅ Existing configs and test sets compatible
- ✅ Gradual migration path

**Performance:**
- ✅ No performance overhead from plugin system
- ✅ Improved parsing success rates via multi-strategy approach
- ✅ Better error handling and recovery

### Documentation Updates

- **CLAUDE.md** - Updated with plugin system patterns and examples
- **.github/copilot-instructions.md** - Added plugin architecture overview
- **docs/PLUGIN_SYSTEM_REFACTORING.md** - New comprehensive guide (created)

---

## [2.0.0] - January 23, 2026

### Major Architecture Overhaul

#### 3-Stage Architecture Implementation
- **Complete system transformation** from monolithic to modular 3-stage pipeline
- **Stage 1: Test Set Generation** - YAML configs → compressed JSON test sets
- **Stage 2: Portable Test Execution** - minimal dependencies, cloud-ready
- **Stage 3: Analysis & Reporting** - rich analytics with visualizations

#### File Organization & Structure
- **Reorganized project structure**: moved core scripts to `src/stages/`
- **Enhanced module organization**: better separation of concerns
- **Cleaned up root directory**: moved test files to `tests/` folder
- **Consolidated documentation**: merged implementation docs into comprehensive guide

#### Critical Bug Fixes
- **🐛 MAJOR: Game of Life Template Fix**
  - Fixed `{grid_str}` placeholder not being substituted with actual grid data
  - Root cause: Missing `grid_str` variable in `PromptContext` 
  - Impact: Game of Life accuracy expected to improve from 0% to 40-70%
  - Added proper `format_grid()` integration in test set generation

#### TUI System Enhancements  
- **Complete TUI rewrite** to use 3-stage architecture
- **Fixed import path issues** when running from subdirectories
- **Added task type mapping** between short names (ari/gol) and full names
- **Enhanced progress tracking** with stage-by-stage execution feedback
- **Improved error handling** and user experience

#### Enhanced Parsing & Analytics
- **Integrated 6-strategy parsing** from arithmetic evaluation into multi-task system
- **Enhanced arithmetic parsing** with LaTeX boxed patterns and JSON unescaping
- **Fixed task type detection** for proper multi-task execution
- **Added multi-dimensional analysis** across task types, prompt styles, and models

#### Advanced Reporting System
- **6-chart visualization suite**: Performance Dashboard, Accuracy Heatmap, Error Analysis, Efficiency Analysis, Radar Comparison, Enhanced Multi-Task Analysis
- **Harmonized HTML/Markdown reports** with identical content structure
- **Embedded chart support** with proper relative path handling
- **Task-specific breakdowns** with detailed metadata extraction
- **Enhanced multi-task analysis** capabilities

### Added

#### Core Architecture
- `src/stages/generate_testset.py` - Deterministic test set generation from YAML configs
- `src/stages/run_testset.py` - Portable test execution with minimal dependencies
- `src/stages/analyze_results.py` - Comprehensive analysis and reporting engine
- Enhanced 3-stage workflow integration in TUI system

#### Advanced Features
- **Multi-task test set support** with mixed task types (arithmetic + Game of Life)
- **Enhanced parsing strategies** with fallback mechanisms
- **Rich metadata extraction** for comprehensive analysis
- **Task breakdown analysis** with individual performance tracking
- **Prompt style matrix analysis** (3×3 combinations of user/system styles)

#### Documentation & Testing
- `docs/3_STAGE_ARCHITECTURE_COMPLETE.md` - Comprehensive implementation guide
- Enhanced test suite in `tests/` folder with proper organization
- Validation scripts for TUI workflow and component integration

### Fixed

#### Critical System Issues
1. **Game of Life Complete Failure** - 0% accuracy due to `{grid_str}` placeholder bug
2. **Multi-task Execution Errors** - Task type detection and routing issues  
3. **Template Formatting Bugs** - HTML report generation with template string errors
4. **Chart Embedding Failures** - Relative path issues in HTML reports
5. **Import Path Problems** - Module loading from subdirectories
6. **Parse Error Crisis** - Multi-strategy parsing integration for improved accuracy

#### Enhanced Components
- **Prompt generation system** - Fixed template variable substitution
- **Result analysis pipeline** - Enhanced multi-dimensional analysis
- **Visualization engine** - Proper chart embedding and path handling
- **Error reporting** - Better categorization and tracking
- **Progress indicators** - Clear feedback throughout execution

### Changed

#### Major Refactoring
- **Execution Model**: Sequential script calls → 3-stage pipeline architecture
- **File Organization**: Scattered scripts → organized `src/stages/` structure
- **TUI Architecture**: Monolithic execution → modular stage orchestration
- **Documentation**: Multiple scattered files → single comprehensive guide

#### Enhanced User Experience
- **Clearer progress tracking** with stage-specific feedback
- **Better error messages** with actionable guidance
- **Comprehensive summaries** after execution completion
- **Interactive configuration** with validation and preview

### Performance & Quality

#### Significant Improvements
- **Parsing Success Rate**: 0% → 50%+ for Game of Life tasks
- **Multi-task Reliability**: Enhanced accuracy across mixed task types
- **Report Quality**: Basic text → Rich interactive HTML with 6 visualization types
- **System Modularity**: Monolithic → Clean 3-stage separation
- **Reproducibility**: Enhanced with versioned test sets and config hashing

#### Validation Results
- ✅ 10/10 component integration tests passed
- ✅ TUI workflow validation successful
- ✅ Enhanced parsing system operational
- ✅ Multi-task execution pipeline functional
- ✅ Comprehensive reporting and visualization working

### Technical Debt Addressed
- **Code Organization**: Moved from scattered scripts to organized modules
- **Testing Structure**: Consolidated test files in proper `tests/` folder  
- **Documentation**: Merged fragmented docs into comprehensive guide
- **Error Handling**: Enhanced throughout system with better recovery

---

## [1.0.0] - November 16, 2025

### Added

#### TUI System Enhancements
- **Task Selection System**: Interactive selection of benchmark types (ARI, GoL, C14, Linda)
- **Task-Specific Configuration**: Per-task configuration screens with appropriate parameters
- **Config Management**: Save/load configurations in YAML and JSON formats
- **Result Persistence**: Results now saved to timestamped text files
- **Chart Generation**: ASCII bar charts showing model performance comparison
- **Execution Summary**: JSON metadata files tracking all executions

#### Core Functions
- `execute_benchmark()`: Central execution orchestrator for benchmark runs
- `_generate_benchmark_charts()`: Chart generation from result files  
- `_create_ascii_chart()`: ASCII visualization creation
- `task_selection()`: Task type selection interface
- `task_specific_config()`: Task-specific parameter collection

#### Configuration Extensions
- `task_type` field in BenchmarkConfig
- `task_config` field in BenchmarkConfig (task-specific parameters)

#### Model Provider System
- **ModelProviderManager**: Unified provider orchestration
- **OllamaProvider**: Complete Ollama integration with dynamic discovery
- **Dynamic Model Discovery**: 44+ models automatically detected
- **Advanced Filtering**: Filter by family, quantization, size
- **Model Grouping**: Group by family, quantization, or size

#### Execution Improvements
- All models passed in single script invocation (10-12x faster)
- Separate execution per prompt combination (user_style × system_style)
- Real-time output capture and persistence
- Comprehensive error tracking and reporting

### Fixed

#### Critical Bugs
1. **ValueError in Checkbox Defaults** - Fixed questionary.checkbox pattern (7/7 errors fixed)
2. **Missing Task Selection** - Added complete task selection workflow
3. **Generic Parameter Context** - Split into generic + task-specific configuration
4. **Report Formats Crash** - Fixed questionary.Choice pattern
5. **Missing Target Values Input** - Added validation input for ARI tasks
6. **Config Missing Task Fields** - Added task_type and task_config
7. **Incomplete Main Workflow** - Fully implemented main() function

#### Execution Model Issues
- Models now passed together instead of sequentially
- Results properly saved to files
- Charts now generated successfully
- Prompt combinations properly handled

### Changed

#### Major Refactoring
- **execute_benchmark()**: Complete rewrite (169 lines added)
- **main()**: Complete rewrite (55 lines rewritten)
- **Execution Flow**: Changed from sequential model runs to grouped model runs per prompt combination

#### Improved Components
- `prompt_configuration()`: Fixed questionary pattern
- `output_configuration()`: Fixed questionary pattern
- `create_new_benchmark()`: Integrated task selection workflow
- `confirmation_screen()`: Updated to show task information

### Improved

#### Code Quality
- Comprehensive error handling throughout
- Better progress indicators
- Clearer separation of concerns
- Improved console output formatting

#### Performance
- 10-12x faster execution for multi-model benchmarks
- Reduced overhead from multiple script invocations
- Efficient result file writing
- Streaming output to console

#### User Experience
- Better visual feedback during execution
- Clear progress indicators [idx/total]
- Structured result organization
- Easy result file access

### Documentation

#### New Documentation Files
- `docs/PROJECT_DEVELOPMENT_SUMMARY.md`: Comprehensive project overview
- `docs/DEVELOPMENT_LOG.md`: Detailed development history

#### Updated Documentation
- README.md: Maintained with quick start guide
- All module docstrings: Updated for clarity

### Testing & Verification

#### Validation Results
- ✅ 10/10 component checks passed
- ✅ Syntax validation passed
- ✅ Integration tests passed
- ✅ Execution flow tested
- ✅ Error handling verified

#### Test Coverage
- Task selection workflow
- Configuration persistence
- Result file generation
- Chart generation
- Error conditions

## [0.9.0] - Earlier Development

### Previous Phases
- Phase 1: Project initialization and benchmarking
- Phase 2: Repository cleanup and organization  
- Phase 3: TUI system initial development
- Phase 4: Model provider integration
- Phase 5: Completion and refinement (this release)

---

## Known Issues

### Current Limitations

1. **Chart Generation**
   - Basic ASCII charts only
   - Limited customization
   - No interactive visualization

2. **Result Parsing**
   - Regex-based parsing can be fragile
   - Requires consistent output format
   - No structured result API

3. **Error Recovery**
   - Limited recovery from model failures
   - Some edge cases in provider detection

### Future Improvements

1. **Enhanced Visualization**
   - matplotlib/plotly integration
   - Web dashboard
   - Historical comparison

2. **Advanced Analysis**
   - Statistical significance testing
   - Trend analysis
   - Comparative metrics

3. **Extended Providers**
   - OpenAI API
   - Anthropic Claude
   - vLLM integration

4. **Additional Features**
   - Custom benchmark creation
   - Plugin architecture
   - Result aggregation across runs

---

## Migration Guide

### For Users Upgrading from Previous Versions

#### Configuration Files
- Old configurations in `benchmark_configs/` are compatible
- New configurations include `task_type` field
- Recommend regenerating for consistency

#### Results Format
- Results now saved as separate files per prompt combination
- JSON summary includes metadata
- Charts generated automatically if enabled

#### TUI Workflow
- New step added: Task Selection (Step 2)
- New step added: Task-Specific Configuration (Step 4)
- All other steps remain similar

### Breaking Changes

None - backward compatible with existing configurations and scripts.

---

## Contributors

- Development Team
- QA Team
- Community Feedback

---

## Acknowledgments

- OpenAI/Anthropic for LLM technology
- Ollama for local inference
- questionary for interactive CLI
- rich for terminal visualization

---

**For detailed information, see docs/PROJECT_DEVELOPMENT_SUMMARY.md and docs/DEVELOPMENT_LOG.md**
