# CHANGELOG

All notable changes to the GoL Benchmark project.

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
