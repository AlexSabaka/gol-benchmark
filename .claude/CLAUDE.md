# CLAUDE.md - GoL Benchmark Project Guide

> **Quick Reference for Claude Code Agents**
> This document provides context, architecture overview, and common tasks for working with the GoL Benchmark repository.

---

## Project Overview

**GoL Benchmark** is a procedural benchmark suite for testing LLM reasoning capabilities across structured cognitive tasks:

- **Game of Life (GoL)**: Conway's cellular automaton — predict next grid state
- **Arithmetic (ARI)**: Math expression parsing and evaluation
- **Linda Fallacy**: Cognitive bias testing (conjunction fallacy)
- **Cellular Automata (C14)**: Configurable rule-based pattern evolution
- **ASCII Shapes**: Spatial reasoning on ASCII art (dimensions, counts, positions)
- **Object Tracking**: Physical state tracking through container inversions (grape test)
- **Sally-Anne**: Theory of Mind — false belief reasoning
- **Carwash Paradox**: Practical-goal-tracking test — walk or drive? (answer: always drive)
- **Inverted Cup**: Spatial-orientation reasoning — sealed top / open bottom cup (answer: flip it)
- **Strawberry**: Character-level reasoning — letter counting, word reversal, nth-letter, anagram, pangram, lipogram
- **Measure Comparison**: Quantity comparison with units, conversion traps, and decimal framing sensitivity
- **Grid Tasks**: Table reasoning — cell lookups, row sums, column counts
- **Misquote Attribution**: Sycophancy detection — false quote attributions with social-pressure framings
- **False Premise**: Dangerous/impossible premise detection — 5 domains (chemistry, medicine, food safety, physics, logic)
- **Family Relations**: Perspective-aware family counting puzzles — sibling count, shared children, generational chains, perspective shifts
- **Encoding & Cipher Decoding**: Decode-and-respond across encoding schemes (Base64, Caesar/ROT-N, Morse) with hallucination detection
- **Symbol Arithmetic**: Custom operation tables on abstract symbol sets — pure rule-following with zero semantic anchor
- **Picross (Nonogram)**: Grid-based deductive reasoning — solve puzzles from row/column clue constraints

### Key Characteristics

- **Multilingual**: 6 languages supported (EN, FR, ES, DE, ZH, UA)
- **Multi-provider**: Ollama (local & remote) and HuggingFace integrations
- **Prompt engineering**: 3 user styles × 3 system styles = 9 configurations
- **Reproducible**: Seeded random generation for consistent benchmarks

---

## Quick Commands

```bash
# ── Web UI (Recommended) ──
python -m src.web                # http://127.0.0.1:8000/
python -m src.web --host 0.0.0.0 # LAN-accessible

# Frontend development (hot-reload)
cd frontend && npm run dev       # http://localhost:5173/ (proxies /api → :8000)

# Run on a remote Ollama instance
python src/stages/run_testset.py testsets/testset_xyz.json.gz \
    --model qwen3:0.6b --provider ollama \
    --ollama-host http://192.168.1.50:11434

# Run full test suite
pytest tests/

# Generate visualizations from results
python -m src.visualization.generate_prompt_benchmark_visualizations results/
```

---

## Directory Structure

```
gol_eval/
├── src/                    # All source code
│   ├── plugins/           # Plugin-based benchmark system (19 plugins)
│   │   ├── base.py        # Abstract base classes for plugins
│   │   ├── __init__.py    # Plugin registry with auto-discovery
│   │   ├── parse_utils.py # End-first parsing utilities + multilingual keyword merge
│   │   ├── grammar_utils.py # Shared grammar: article(), resolve_vocab(), pick_templates(), vocab_gender()
│   │   ├── game_of_life/  # GoL plugin (generator, parser, evaluator)
│   │   ├── arithmetic/    # ARI plugin
│   │   ├── linda_fallacy/ # Linda plugin
│   │   ├── cellular_automata_1d/  # C14 plugin
│   │   ├── ascii_shapes/  # ASCII Shapes plugin
│   │   ├── object_tracking/ # Object Tracking (Grape Test) plugin
│   │   ├── sally_anne/    # Sally-Anne false belief test plugin
│   │   ├── carwash/       # Carwash Paradox plugin (v2.2.0)
│   │   ├── inverted_cup/  # Inverted Cup plugin (v2.2.0)
│   │   ├── strawberry/    # Character-level reasoning (6 sub-types)
│   │   ├── measure_comparison/ # Quantity comparison plugin (incl. decimal framing)
│   │   ├── grid_tasks/    # Table reasoning plugin
│   │   ├── time_arithmetic/ # Time Arithmetic plugin (temporal reasoning)
│   │   ├── misquote/      # Misquote Attribution (sycophancy detection)
│   │   ├── false_premise/ # False Premise (dangerous/impossible premise detection)
│   │   ├── family_relations/ # Family Relations (perspective-aware counting)
│   │   ├── encoding_cipher/ # Encoding & Cipher Decoding (Base64, Caesar, Morse)
│   │   ├── symbol_arithmetic/ # Symbol Arithmetic (custom operation tables)
│   │   └── picross/       # Picross (Nonogram) grid puzzle solving
│   ├── stages/            # 3-stage pipeline (uses plugin system)
│   │   ├── generate_testset.py  # Stage 1: YAML → test sets
│   │   ├── run_testset.py       # Stage 2: Execute tests
│   │   └── analyze_results.py   # Stage 3: Analytics
│   ├── core/              # Types, prompt engine, test generation
│   ├── engine/            # Task-specific logic (GoL, Math)
│   ├── models/            # LLM interfaces (Ollama, HuggingFace)
│   ├── evaluation/        # Result scoring and metrics
│   ├── benchmarks/        # Legacy (only linda_eval.py remains — used by linda plugin)
│   ├── web/               # FastAPI REST API backend (serves React SPA at /)
│   │   ├── app.py         # FastAPI app factory, SPA routing
│   │   ├── api/           # REST endpoints (plugins, models, testsets, jobs, analysis, judge, human-review)
│   │   ├── jobs.py        # Background job manager (ProcessPoolExecutor) — submit() + submit_judge()
│   │   ├── judge.py       # LLM-as-a-Judge worker (run_judge_worker, default prompts)
│   │   ├── human_review_aggregator.py # Human-review improvement-report builder (span grouping, auto-regex, ordering hints)
│   │   ├── translation.py # deep-translator wrapper (Google/LibreTranslate/MyMemory) with LRU cache
│   │   └── reanalyze.py   # Reanalysis utilities (re-parse/re-evaluate results)
│   ├── visualization/     # Charts, analysis, reporting
│   └── utils/             # Logging, model discovery
│
├── frontend/              # React SPA (Vite 6 + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui)
│   ├── src/
│   │   ├── api/           # Typed API client layer
│   │   ├── hooks/         # React Query hooks with auto-refresh
│   │   ├── types/         # TypeScript interfaces
│   │   ├── pages/         # Dashboard, Configure, TestSets, Execute (landing + execute/simple-wizard.tsx + execute/matrix-wizard.tsx), Jobs, Results, Charts, Reports, Judge, Review
│   │   ├── lib/           # Utilities (chart-colors, model-sizes, credential-store, favorite-models, language-flags)
│   │   └── components/    # UI primitives (shadcn), layout, plugin-config, data-table, charts, wizard (StepButton/StepFooter), model-selection (ModelList/Ollama/OpenAI/HF), review (stimulus/response panels, annotation-dock, classification-bar, case-progress, verdict-pill, translation-panel, improvement-report-dialog), param-override-modal, judge-setup-sheet, language-filter-chip, prompt-style-badge
│   ├── vite.config.ts     # base: "/", proxy /api → :8000
│   └── dist/              # Production build output
│
├── tests/                 # Test suite
│   └── plugins/           # Plugin system unit tests
├── scripts/               # Shell scripts for batch processing
├── configs/               # Benchmark configuration YAML files
├── data/                  # (Removed — data co-located in src/plugins/*/data/)
├── docs/                  # Documentation and research reports
└── results/               # Benchmark results (kept at root for easy access)
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| **Plugin System (19 plugins)** | |
| [src/plugins/base.py](src/plugins/base.py) | Abstract base classes + ConfigField schema system |
| [src/plugins/\_\_init\_\_.py](src/plugins/__init__.py) | Plugin registry with auto-discovery |
| [src/plugins/parse\_utils.py](src/plugins/parse_utils.py) | End-first parsing utilities + `safe_enum()` helper |
| [src/plugins/game_of_life/](src/plugins/game_of_life/) | GoL plugin module |
| [src/plugins/arithmetic/](src/plugins/arithmetic/) | ARI plugin module |
| [src/plugins/linda_fallacy/](src/plugins/linda_fallacy/) | Linda Fallacy plugin module |
| [src/plugins/cellular_automata_1d/](src/plugins/cellular_automata_1d/) | C14 plugin module |
| [src/plugins/ascii_shapes/](src/plugins/ascii_shapes/) | ASCII Shapes plugin module |
| [src/plugins/object_tracking/](src/plugins/object_tracking/) | Object Tracking (Grape Test) plugin |
| [src/plugins/sally_anne/](src/plugins/sally_anne/) | Sally-Anne false belief test plugin |
| [src/plugins/carwash/](src/plugins/carwash/) | Carwash Paradox plugin |
| [src/plugins/inverted_cup/](src/plugins/inverted_cup/) | Inverted Cup plugin |
| [src/plugins/strawberry/](src/plugins/strawberry/) | Character-level reasoning plugin (6 sub-types) |
| [src/plugins/measure_comparison/](src/plugins/measure_comparison/) | Quantity comparison plugin (incl. decimal framing) |
| [src/plugins/grid_tasks/](src/plugins/grid_tasks/) | Table reasoning plugin |
| [src/plugins/time_arithmetic/](src/plugins/time_arithmetic/) | Time Arithmetic plugin (temporal reasoning) |
| [src/plugins/misquote/](src/plugins/misquote/) | Misquote Attribution plugin (sycophancy detection) |
| [src/plugins/false_premise/](src/plugins/false_premise/) | False Premise plugin (dangerous/impossible premise detection) |
| [src/plugins/family_relations/](src/plugins/family_relations/) | Family Relations plugin (perspective-aware counting) |
| [src/plugins/encoding_cipher/](src/plugins/encoding_cipher/) | Encoding & Cipher Decoding plugin (Base64, Caesar, Morse) |
| [src/plugins/symbol_arithmetic/](src/plugins/symbol_arithmetic/) | Symbol Arithmetic plugin (custom operation tables) |
| [src/plugins/picross/](src/plugins/picross/) | Picross (Nonogram) plugin (grid puzzle solving) |
| **3-Stage Pipeline** | |
| [src/stages/generate_testset.py](src/stages/generate_testset.py) | Stage 1: Test set generation (uses plugins) |
| [src/stages/run_testset.py](src/stages/run_testset.py) | Stage 2: Test execution (uses plugins) |
| [src/stages/analyze_results.py](src/stages/analyze_results.py) | Stage 3: Analytics and reporting |
| **Core Infrastructure** | |
| [src/core/types.py](src/core/types.py) | All config classes, types, difficulty levels |
| [src/core/PromptEngine.py](src/core/PromptEngine.py) | System prompts + enums (user templates deprecated → plugins) |
| [src/core/TestGenerator.py](src/core/TestGenerator.py) | Test case generation with 1,061 real-world patterns + known patterns |
| [src/models/BaseModelInterface.py](src/models/BaseModelInterface.py) | Abstract base for model providers |
| [src/models/OllamaInterface.py](src/models/OllamaInterface.py) | Ollama integration with retry logic |
| [src/models/HuggingFaceInterface.py](src/models/HuggingFaceInterface.py) | HuggingFace/Transformers integration |
| [src/evaluation/TestEvaluator.py](src/evaluation/TestEvaluator.py) | Grid comparison and accuracy calculation |
| [src/engine/GameOfLifeEngine.py](src/engine/GameOfLifeEngine.py) | Conway's Game of Life rules |
| [src/engine/MathExpressionGenerator.py](src/engine/MathExpressionGenerator.py) | Expression tree generation |
| **Human Review (v2.20.0) + Improvement Report (v2.1–v2.4)** | |
| [src/web/api/human_review.py](src/web/api/human_review.py) | `/api/human-review/*` router: `GET /cases`, `POST /annotate`, GET + DELETE `/annotations/{id}`, `POST /report`, `POST /translate` |
| [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py) | Pure-function improvement-report builder. Key helpers: `_span_analysis` (per-group rollup), `_context_anchored_regex` + `_merged_label_disjunction` (v2.4 regex generators, replace legacy `_auto_regex`), `_filter_candidates` (low-support cut), `_parser_span_alignment` (aligned / misaligned / no-output split), `_regex_test_harness` (capture quality + sample captures), `_data_quality` (warnings + suppressed-sections), `_model_answer_stats` (distribution + raw variants). `REPORT_FORMAT_VERSION = "2.4"` |
| [src/web/translation.py](src/web/translation.py) | `deep-translator` wrapper with LRU cache; provider via `TRANSLATOR_PROVIDER` env (google / libre / mymemory) |
| [frontend/src/pages/review.tsx](frontend/src/pages/review.tsx) | `/review` wizard — two-column workspace with keyboard-first annotation |
| [frontend/src/components/review/improvement-report-dialog.tsx](frontend/src/components/review/improvement-report-dialog.tsx) | Improvement-report modal: 9 tabs (Summary / Spans / Strategy / Languages / Misses / Answers / Anchors / Ordering / Classes / Notes), data-quality banner, parser-span alignment callout, expandable span-group cards with structural signals / prefix anchors (type-chipped) / regex test rows (capture quality pill + sample captures) |

---

## Architecture Patterns

### 1. Plugin Pattern (v2.2.0)
Self-contained benchmark modules with auto-discovery via package scanning.
```python
from src.plugins import PluginRegistry
plugin = PluginRegistry.get('game_of_life')
generator = plugin.get_generator()
parser = plugin.get_parser()
evaluator = plugin.get_evaluator()
```

### 2. Factory Pattern
`create_model_interface(provider, model_name, ...)` creates the right interface from a provider string.

### 3. Strategy Pattern
Different prompt/system styles are interchangeable via plugin-local `prompts.py` template dicts and base class helpers. Multi-strategy parsing in parsers (6 strategies for ARI, 4 for GoL).

### 4. Template Method
`ModelInterface` defines the `query(prompt, params)` contract; subclasses implement it.

### 5. Configuration Inheritance
```
BaseTestConfig (ABC)
├── GameOfLifeTestConfig
├── AriTestConfig
├── C14TestConfig
└── (future tasks...)
```

---

### 6. End-First Parsing Convention

All response parsers follow the principle of searching from the **end** of the model response toward the start. LLMs reason through problems first and give final answers at the end — using `re.search()` (which finds the first match) systematically extracts intermediate values instead of final answers.

**Shared utilities** in [`src/plugins/parse_utils.py`](src/plugins/parse_utils.py):

- `safe_enum(enum_cls, value, default)` — parse string to enum with fallback (used by all 12 generators)
- `re_search_last(pattern, text)` — drop-in replacement for `re.search()` that returns the last match
- `strip_verification_tail(text)` — removes trailing verification/confirmation sections before end-first matching (v2.10.3)
- `last_sentences(text, n)` — returns the last N sentences
- `last_keyword_position(text, keywords)` — position of last keyword occurrence
- `merge_keywords(keyword_dict, language)` — merge English + target language keyword lists (English always included as fallback)
- `merge_patterns(pattern_dict, language)` — merge compiled regex pattern lists
- `get_language(task_params)` — extract language from task_params (default `"en"`)
- `build_word_to_int(language)` — multilingual number word→int map (EN + target language merged)
- `build_answer_label_re(language)` — multilingual answer label regex alternation (`"answer|result|respuesta|resultado|..."`)
- Shared multilingual dicts: `WORD_TO_INT`, `ANSWER_LABELS`, `YES_WORDS`, `NO_WORDS` — all 6 languages

**Key exceptions where end-first does NOT apply:**

- `object_tracking` bold_keyword and first_sentence_location — uses FIRST match because models bold the answer in the first sentence, then mention distractor locations in explanations
- `time_arithmetic` validity parsing — uses first-bold and first-sentence yes/no detection because models answer "No"/"Yes" upfront for existence questions
- `measure_comparison` value+unit matching — both options are mentioned, the answer is identified by which matches, not position
- `measure_comparison` decimal type — uses a separate 5-strategy parser (`_parse_decimal`) with end-first bare-value matching
- `inverted_cup` classification — if "flip" is mentioned anywhere, the model understood the key insight (correct answer); "wrong" keywords alongside flip are just creative alternatives
- `linda_fallacy` — extracts ordered rankings, not single answers
- `false_premise` first-sentence refusal — uses FIRST sentences because models lead with "I can't help..." then explain at length; also uses negation-aware compliance detection and safe-alternative section filtering

**Validated**: Re-parsed 1,933 results across 33 files. Zero true regressions from end-first changes. See [CHANGELOG.md](CHANGELOG.md) for detailed parser fix history (v2.10.3–v2.10.7).

---

### 7. Multilingual Content & Grammar System (v2.15.0+)

All 19 plugins generate test content in 6 languages. Each plugin has:
- **`prompts.py`** — user prompt templates per language × style
- **`i18n.py`** or **`*_i18n.py`** — localized vocabulary, question templates, scenario narratives
- **`data/`** — per-language word lists, data files

**Grammar resolution** for gendered languages (UA, ES, FR, DE) via `src/plugins/grammar_utils.py`:
- `article(lang, gender, definite, case)` — returns correct article (el/la, le/la, der/die/das)
- `resolve_vocab(en_key, vocab_dict, lang, case)` — returns case-inflected form (Ukrainian nom/acc/loc)
- `pick_templates(template_dict, lang, gender)` — selects m/f template variants
- `vocab_gender(en_key, vocab_dict, lang)` — gets grammatical gender of a noun

**Subject gender** is randomly assigned (m/f) per test case and stored in `task_params["subject_gender"]`.

### 8. LLM-as-a-Judge (v2.16.0)

Audit incorrect model responses via a judge LLM:
- **Backend**: `src/web/judge.py` — `run_judge_worker()` + default system/user prompts
- **API**: `POST /api/results/judge`, `GET /api/results/judge-results`, `GET /api/results/judge-results/{filename}`
- **Frontend**: `/judge` page with file selector, summary dashboard, filterable judgments table, JSONL/Markdown export
- **Verdicts**: `true_incorrect`, `false_negative`, `parser_failure` (with issue sub-types)
- **Export**: Markdown report structured for agent consumption — grouped by task type, with language, response samples, and actionable summary

### 9. Version Management (v2.19.0+)

- **Single source of truth**: `src/__init__.py` — `__version__` field
- `src/web/app.py` imports `__version__` automatically; no separate hardcoding needed
- `frontend/package.json` is the npm source of truth — kept in sync manually when cutting releases
- **All locations to update when bumping version**: `src/__init__.py`, `frontend/package.json` (+`package-lock.json`), `.github/copilot-instructions.md`, CHANGELOG.md, CLAUDE.md footer

### 11. Human Review & Annotation (v2.20.0 + Improvement Report v2.1 → v2.4)

Human annotation workflow for parser diagnosis and improvement. Every labelled response becomes a parser test case in waiting. The **Improvement Report** aggregates annotations into a JSON artifact whose explicit purpose is to seed a coding-agent task refactoring plugin parsers — so its shape is agent-facing and has iterated fast.

**Workspace + sidecars (stable since v2.20.0):**

- Backend router [src/web/api/human_review.py](src/web/api/human_review.py) (`/api/human-review/*`): `GET /cases`, `POST /annotate`, `GET|DELETE /annotations/{id}`, `POST /report`, `POST /translate`
- Aggregator module [src/web/human_review_aggregator.py](src/web/human_review_aggregator.py) — pure-function, no I/O — computes the full report shape from sidecar payloads (+ optional source-result-payload backfill for legacy sidecars)
- Translation [src/web/translation.py](src/web/translation.py) — `deep-translator` wrapper, `TRANSLATOR_PROVIDER` env (`google` default, `libre`, `mymemory`), LRU-cached
- Sidecars: gzipped JSON at `{result_stem}_annotations.json.gz`, atomic `temp + os.replace`; `has_annotations` flag surfaces on `/api/results` summaries
- Response classes (7): `hedge`, `gibberish`, `refusal`, `language_error`, `verbose_correct`, `parser_ok`, **`parser_false_positive`** (uniquely coexists with spans — span is the evidence, verdict is the diagnosis)
- Annotation invariant (relaxed in v2.20.0): ≥1 of `spans` / `response_class`; both may coexist
- Format: `bold` / `italic` / `strikethrough` / `header` / `boxed` / `label` / `plain` / `other` (italic/strike/header added in v2.2)
- Frontend `/review` ([pages/review.tsx](frontend/src/pages/review.tsx)): two-column editorial workspace; keyboard shortcuts `←/→` navigate, `1`–`7` classify, `S` skip, `Space`/`Enter` commit drag-selection

**Improvement Report schema — `format_version` rolls forward additively:**

| Version | Additions |
|---------|-----------|
| `"2"` (v2.20.0) | `summary`, `span_groups`, `ordering_hints`, `response_classes`, `confusion_matrix`, `language_breakdown` / `config_breakdown` / `user_style_breakdown`, `strategy_breakdown`, `answer_when_missed`, `anchor_frequency`, `annotator_notes`, `false_positive_rate` |
| `"2.1"` | Span examples gain `sentence` (containing-sentence extract); each span group gains `structural_ratios` (`line_start` / `paragraph_start` / `list_marker` / `label_colon` / `bold_wrap` / `quote_wrap` / `answer_label_match`), `prefix_anchors` (trailing N-gram phrases of `before`), `regex_test` harness with `match_rate` / `matched_count` / `total`. Context window widened from 24 → **120 chars** |
| `"2.2"` | **Context-anchored regex generator** — replaces span-text LCP as primary regex shape. Emits `context_anchor` / `format_only` / `text_pattern` kinds. Span examples gain `parser_extracted` + `parser_match_type` (inline parser-vs-annotator diff). Per-group `label_taxonomy` breaks down `answer_label_match` into specific label words. `model_answer_distribution` (markdown-stripped histogram of annotated spans) |
| `"2.3"` | Top-level **`parser_span_alignment`** — `aligned_with_parser` / `misaligned_with_parser` / `no_parser_output` split, resolving the "parser_missed: N" framing when `parser_extracted` is actually aligned with the annotated span. Summary gains `parser_missed_aligned` / `parser_missed_misaligned` / `parser_missed_no_output`. Regex harness gains `capture_exact_rate` / `capture_contains_rate` / `sample_captures` (capture quality ≠ match rate). Top-level **`data_quality.warnings[]` + `suppressed_sections[]`** — auto-detects `no_parse_strategy`, `uniform_language` / `uniform_system_style` / `uniform_user_style`, `uniform_expected`. Single-bucket axis breakdowns are **omitted from output** and reported as suppressed |
| `"2.4"` | **Merged label disjunction** — when a group has ≥2 distinct label-type atoms, emits `(?i)(?:atom1\|atom2)\s*[:：]\s*{capture}` as highest-priority candidate (`kind: "merged_label_disjunction"`, `participating_atoms`). Prefix anchors gain **`type`**: `label` / `format` / `phrase` (label > format > phrase at equal count). Post-harness **low-support filter** drops candidates with `match_rate < 0.1 AND capture_contains_rate < 0.1` and `support < 2 AND support/group_size < 0.1` (always keeps `format_only`). New **`model_answer_variants`** preserves raw text variants per normalized bucket (top 10) so the agent sees `Walk` / `WALK` / `**Walk**` / `Walk to the carwash` separately under `walk` |

**Key agent-facing distinctions (future-you, read this):**

- **`match_rate` vs `capture_contains_rate`** — "regex fires" is *not* "regex extracts the right answer." A pattern like `(?i)recommendation:\s*([^.\n]+?)(?:[.\n]|$)` can match 100% and capture `Definitively walk to the carwash` — agent-useful only if `capture_contains_rate` is also high.
- **Parser alignment ≠ parser correctness** — v2.3 split. `aligned_with_parser` means `parser_extracted` matches the annotated span (even when model was wrong). `parser_missed_extractable` alone is misleading; always pair with `parser_span_alignment`.
- **Markdown-stripped buckets collapse case + wrappers but NOT stems** — `walk` and `walking` are separate buckets on purpose; surfacing that difference is the agent's signal to add stemming.
- **Single-bucket axes auto-suppress** — if every annotated case shares one language/style/expected answer, `language_breakdown` etc. are omitted (reported in `data_quality.suppressed_sections`). Don't assume a missing field means a bug.

**One-click word marking** + drag-select + sticky annotation dock + parser-match highlight (amber dashed underline) + persistent parser-disagreement callout + 🌐 translation panels (`select-none` — translated text is never an annotation target).

### 12. Plugin Task Type List — Single Source of Truth (v2.19.0+)

`PluginRegistry.list_task_types()` is the canonical list of active plugin task types — **do not maintain separate hardcoded lists**.

- `src/stages/analyze_results.py` — `_KNOWN_TASK_TYPES` is derived from the registry at import time
- `src/web/reanalyze.py` — `_TASK_TYPE_SUFFIXES` is derived from the registry at import time
- Adding a new plugin in `src/plugins/` automatically propagates to all task-type inference and badge detection with no other changes required
- `_LEGACY_TASK_TYPES = ["fancy_unicode"]` — the only manually maintained list; for task types removed from the plugin system that may still appear in old result files

### 13. Job Persistence & Pause/Resume (v2.21.0+)

All job I/O is confined to **`src/web/job_store.py`** (`JobStore` class) — the single place to swap when upgrading to NoSQL/Redis. To change the backend, only `job_store.py` changes.

- **Storage**: `jobs.json` at project root (path configurable via `GOL_JOBS_FILE` env var)
- **Lifespan**: `src/web/app.py` lifespan context manager calls `job_manager.load_from_store()` on startup and `save_to_store()` on shutdown; each terminal transition also persists immediately
- **Startup recovery**: PENDING/RUNNING jobs found in store → set to FAILED ("Interrupted by server restart"); PAUSED jobs survive and remain resumable
- **Pause**: `POST /api/jobs/{id}/pause` — sets `pause_requested` flag in shared dict; worker finishes current test case, saves `partial_<job_id>.json.gz`, returns `"paused"` status with checkpoint index
- **Resume**: `POST /api/jobs/{id}/resume` — paused job → CANCELLED (superseded), new job submitted from `paused_at_index`; inherits all execution params; merges partial + new results into final file, deletes partial on completion
- **Job states**: `pending` → `running` → `completed` / `failed` / `cancelled` / **`paused`** (PAUSED is not terminal — it can be resumed)
- **Judge jobs**: support cancel only — multi-file batching makes checkpointing significantly more complex
- **Credentials caveat**: `api_key` / `api_base` are stored in `jobs.json` — see TECHDEBT TD-085

---

## Adding New Features

### New Benchmark Task (Plugin System - v2.1.0)

**Modern approach using the plugin system:**

1. **Create plugin directory** `src/plugins/new_task/`:
   ```bash
   mkdir src/plugins/new_task
   cd src/plugins/new_task
   ```

2. **Create `__init__.py`** with plugin instance:
   ```python
   from src.plugins.base import BenchmarkPlugin
   from src.plugins.new_task.generator import NewTaskGenerator
   from src.plugins.new_task.parser import NewTaskParser
   from src.plugins.new_task.evaluator import NewTaskEvaluator

   class NewTaskPlugin(BenchmarkPlugin):
       @property
       def task_type(self) -> str:
           return "new_task"

       @property
       def display_name(self) -> str:
           return "New Task Display Name"

       def get_generator(self):
           return NewTaskGenerator()

       def get_parser(self):
           return NewTaskParser()

       def get_evaluator(self):
           return NewTaskEvaluator()

   plugin = NewTaskPlugin()  # Auto-discovered!
   ```

3. **Create `prompts.py`** (plugin-local user prompt templates — nested dict, NOT tuple keys):
   ```python
   USER_PROMPT_TEMPLATES = {
       "en": {"minimal": "...", "casual": "...", "linguistic": "..."},
       "es": {"minimal": "...", "casual": "...", "linguistic": "..."},
       # ... all 6 languages
   }
   ```

4. **Create `generator.py`** (test case generation):
   ```python
   from src.plugins.base import TestCaseGenerator, TestCase, ConfigField
   from .prompts import TEMPLATES

   class NewTaskGenerator(TestCaseGenerator):
       def generate_batch(self, config, prompt_config, count, seed):
           user_prompt, system_prompt, full_prompt = self._build_prompts(
               TEMPLATES, language, user_style, system_style, **vars
           )
           return [TestCase(...), ...]

       def get_config_schema(self) -> list[ConfigField]:
           return [
               ConfigField(name='count', label='Number of cases', field_type='number',
                           default=10, min_value=1, max_value=200),
           ]
   ```

5. **Create `parser.py`** (response parsing with multi-strategy):
   ```python
   from src.plugins.base import ResponseParser, ParsedAnswer

   class NewTaskParser(ResponseParser):
       def parse(self, response: str, task_params: Dict) -> ParsedAnswer:
           # Try multiple parsing strategies
           return ParsedAnswer(value=..., raw_response=response, parse_strategy='...')
   ```

6. **Create `evaluator.py`** (result evaluation):
   ```python
   from src.plugins.base import ResultEvaluator, EvaluationResult

   class NewTaskEvaluator(ResultEvaluator):
       def evaluate(self, parsed_answer, expected_answer, task_params) -> EvaluationResult:
           # Evaluate correctness
           return EvaluationResult(correct=..., match_type='...', accuracy=...)
   ```

7. **Done!** No changes to `PromptEngine.py` needed. Plugin auto-discovered by registry.

### New Model Provider

1. **Create interface** in `src/models/NewProviderInterface.py`:
   ```python
   from src.models.BaseModelInterface import ModelInterface

   class NewProviderInterface(ModelInterface):
       def __init__(self, model_name: str, **kwargs):
           self.model_name = model_name

       def query(self, prompt: str, params: dict) -> dict:
           # Must return {"response": str, "duration": float, "model_info": {...}}
           ...
   ```

2. **Register in factory** in [src/models/\_\_init\_\_.py](src/models/__init__.py):
   ```python
   # Add to create_model_interface():
   elif provider == "new_provider":
       return NewProviderInterface(model_name, **kwargs)
   ```

### New Visualization

1. Add to [src/visualization/](src/visualization/) following patterns in [visualization_engine.py](src/visualization/visualization_engine.py)
2. Use matplotlib/seaborn for charts
3. Save to `docs/images/` with descriptive names

---

## Common Configuration

### Command-Line Arguments

```bash
# Prompt styles (user prompt)
--prompt-style minimal|casual|linguistic

# System prompt styles
--system-prompt-style analytical|casual|adversarial

# Languages
--prompt-language en|es|fr|de|zh|uk

# Cell markers (GoL only — emoji supported since v2.10.1, but numeric recommended)
--live-dead-cell-markers "1,0"

# Disable chain-of-thought (recommended for structured tasks)
--no-think

# Sampling parameters
--temperature 0.1
--top-k 40
--min-p 0.05

# Reproducibility
--seed 42
```

### Environment Variables

- **`GOL_LOG_FILE`** — log file path (default: `gol_eval.log`); configured in `src/utils/logger.py`
- **`GOL_JOBS_FILE`** — job history JSON path (default: `jobs.json` at project root); configured in `src/web/app.py`

### Difficulty Levels

| Level | GoL Grid Size | ARI Complexity | Description |
|-------|--------------|----------------|-------------|
| `easy` | 3×3 | Level 1 | Simple patterns, basic operations |
| `medium` | 5×5 | Level 2 | Moderate complexity |
| `hard` | 7×7 | Level 3 | Complex patterns, nested operations |
| `nightmare` | 10×10 | Level 4 | Extreme complexity |

---

## Known Issues & Gotchas

### Critical Issues

1. **Emoji markers now work but reduce accuracy**
   - Custom cell markers (including emoji) are supported for GoL (v2.10.1) and C14 (v2.10.2)
   - `--live-dead-cell-markers "1,0"` remains recommended for best model accuracy
   - Emoji markers are a valid robustness test but expect lower scores

2. **`--no-think` is critical for structured tasks**
   - Chain-of-thought hurts performance on GoL/ARI
   - Can improve Linda fallacy reasoning

3. **Ollama must be running**
   - Start with `ollama serve` before benchmarks
   - Connection errors if daemon not running

4. **Model preloading**
   - First query is slow (model loading time)
   - Subsequent queries are cached and faster

5. **Reanalyze must pass language to parser**
   - `reanalyze.py` merges `prompt_metadata` (language, user_style) into `task_params` before re-parsing
   - Without this, parser defaults to English keywords and misses multilingual responses
   - Bug was: `task_params` doesn't contain `language` — it's in `input.prompt_metadata`

6. **FastAPI route ordering matters**
   - Specific routes (`/judge-results`, `/reports`) MUST be declared before `/{filename}` catch-all
   - Otherwise `/{filename}` catches everything — e.g. `/judge-results` matches as `filename="judge-results"`

7. **Testset count = per prompt config**
   - `generate_testset.py` passes `count=total_count` to each `generate_batch()` call
   - Total cases = count × len(prompt_configs)
   - e.g. count=100 with 72 prompt combos → 7,200 total cases

8. **Multilingual evaluators need `expected_answer_localized`**
   - Object Tracking and Sally-Anne store both `expected_answer` (English) and `expected_answer_localized` in task_params
   - Evaluator checks both — if model responds in Ukrainian "тумбочці", it matches localized "тумбочці" even though expected is "nightstand"
   - Match type: `localized_match`

9. **prompt_metadata must be merged into task_params for parsers**
   - `run_testset.py` and `src/web/jobs.py` now merge `prompt_metadata` (language, user_style, system_style) into `task_params` before calling plugin parsers/evaluators
   - Without this, parsers default to English keywords and miss multilingual responses
   - Fixed in v2.16.1 for both CLI and Web UI execution paths

10. **Long testset filenames can exceed filesystem limits**
    - `path_manager.py` truncates task list if >120 chars → `N_tasks`, total filename capped at 240 chars
    - Without truncation, configs with many test types could produce filenames too long for some filesystems

11. **`jobs.json` is a runtime artifact — add to `.gitignore`**
    - Created at server startup if not present; accumulates all job history across restarts
    - Contains `api_key` / `api_base` in plaintext if non-Ollama providers were used — do not commit (see TECHDEBT TD-085)
    - `partial_<job_id>.json.gz` files in the results dir are intermediate pause checkpoints; orphaned if server crashes between pause signal and worker exit (see TECHDEBT TD-087)
    - If `jobs.json` becomes corrupt the server starts cleanly — store returns `[]` on parse error and logs a warning

12. **Annotation invariant is relaxed** (v2.20.0)
    - Pre-v2.20.0 rule was `spans XOR response_class`; that was too strict
    - Current rule: at least one of `spans` / `response_class` must be populated — **both may coexist**
    - Load-bearing case: `parser_false_positive` carries both the evidence (span) and the diagnosis (class). `verbose_correct` + span also makes sense (parser grabbed the wrong occurrence of a correct answer buried in verbose reasoning)
    - Backend enforces this in `POST /api/human-review/annotate`; frontend classification buttons no longer wipe spans

13. **Translation panels must be `select-none`** (v2.20.0)
    - Annotation spans refer to char offsets in the *original* response string
    - If the translated text were selectable, annotators could mark offsets that refer to the translation — span coordinates would then be meaningless when the annotation is re-read
    - Enforced in `components/review/translation-panel.tsx` — do not remove

14. **Improvement report: `match_rate` ≠ capture quality** (Improvement Report v2.3+)
    - `regex_test[].match_rate` means "this regex fires on the example context," NOT "this regex captures the right token"
    - Always pair with `capture_exact_rate` / `capture_contains_rate` — a pattern with match_rate 1.0 and capture_contains_rate 0.3 fires correctly but grabs the wrong substring (classic case: `(?i)recommendation:\s*([^.\n]+?)(?:[.\n]|$)` matches but captures `Definitively walk to the carwash` instead of `walk`)
    - Frontend `CaptureQualityPill` tones on `capture_contains_rate`; backend sorts harness rows by `match_rate` first but the agent should read both. Green-pill (≥0.8) on both is a drop-in regex; anything else needs post-processing or anchor refinement

15. **Improvement report: uniform-axis breakdowns are suppressed, not missing** (Improvement Report v2.3+)
    - When every annotated case shares one language / system_style / user_style / expected answer, the corresponding `language_breakdown` / `config_breakdown` / `user_style_breakdown` is **omitted from the JSON** (not emitted as empty)
    - The absence is reported in `data_quality.suppressed_sections` + a `uniform_*` warning code
    - Frontend `DataQualityBanner` surfaces this; downstream consumers should check `data_quality.warnings` before assuming a missing section is a bug
    - Related: `parser_missed_extractable: 100` can be misleading — always pair with top-level `parser_span_alignment` (a fully aligned `parser_extracted` still lands in `parser_missed_extractable` when the annotator used spans-only workflow instead of marking `parser_ok`)

### Import Patterns

After reorganization, use these import patterns:

```python
# Plugin System
from src.plugins import PluginRegistry, ConfigField
from src.plugins.base import (
    BenchmarkPlugin, TestCaseGenerator, ResponseParser, ResultEvaluator,
    TestCase, ParsedAnswer, EvaluationResult, ConfigField
)
from src.plugins.parse_utils import safe_enum, re_search_last, strip_verification_tail, merge_keywords, get_language, build_word_to_int

# Grammar utilities (gendered languages)
from src.plugins.grammar_utils import article, resolve_vocab, pick_templates, vocab_gender

# Plugin-local prompt templates (inside each plugin's generator.py)
from .prompts import USER_PROMPT_TEMPLATES  # Each plugin defines its own (nested dict: lang → style → template)

# Core (PromptEngine: system prompts + enums are active; user templates are legacy)
from src.core.types import GameOfLifeTestConfig, DifficultyLevel
from src.core.PromptEngine import Language, PromptStyle, SystemPromptStyle  # Active enums
# Legacy (still used by generate_testset.py — not yet removed): TaskType, PromptContext, PromptResult, create_*_context()
from src.core.TestGenerator import TestGenerator

# Models
from src.models import create_model_interface, ModelInterface
from src.models import OllamaInterface, HuggingFaceInterface, OpenAICompatibleInterface

# Evaluation
from src.evaluation.TestEvaluator import TestEvaluator

# Engines
from src.engine.GameOfLifeEngine import GameOfLifeEngine
from src.engine.MathExpressionGenerator import MathExpressionGenerator

# Utils
from src.utils.logger import get_logger
from src.utils.model_providers import ModelProvider
```

---

## Research Findings

### Key Discoveries from Benchmark Studies

1. **Prompt engineering dominates model selection**
   - 44+ percentage point swings from prompt choice alone
   - Same model, different prompts → 0% to 44% accuracy

2. **System prompts are reasoning switches**
   - Analytical: Step-by-step, methodical
   - Casual: Intuitive, conversational
   - Adversarial: Direct, efficient

3. **Model personalities matter**
   - Qwen = pragmatist (adversarial prompts work best)
   - Gemma = analyst (analytical prompts work best)
   - Llama = generalist (balanced across styles)

4. **Q2_K quantization beats F16**
   - 2-bit extreme quantization outperforms full precision (+6.18%)
   - Likely due to noise reduction in attention heads

5. **Chain-of-thought hurts structured tasks**
   - GoL/ARI: --no-think improves accuracy
   - Linda: thinking helps detect fallacy

See [docs/PROMPT_BENCHMARK_NOVEMBER_2025_REPORT.md](docs/PROMPT_BENCHMARK_NOVEMBER_2025_REPORT.md) for full analysis.

---

## Testing

### Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/plugins/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Manual Testing

Use the Web UI (`python -m src.web`) or the 3-stage pipeline directly:

```bash
# Generate a test set, run it, then analyze
python src/stages/generate_testset.py configs/my_config.yaml
python src/stages/run_testset.py testsets/testset_xyz.json.gz --model qwen3:0.6b --provider ollama
python src/stages/analyze_results.py results/
```

---

## Batch Processing

### Run Multi-Model Benchmark

```bash
# Edit scripts/run_multi_model_benchmark.sh to configure:
# - MODELS array
# - USER_STYLES and SYSTEM_STYLES
# - DIFFICULTY, BATCH_SIZE, etc.

bash scripts/run_multi_model_benchmark.sh
```

### Monitor Progress

```bash
# Watch benchmark progress
bash scripts/monitor_benchmark.sh

# Or use watch command
watch -n 5 'ls -1 results/multi_model_*/  *.json | wc -l'
```

---

## Troubleshooting

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'src.types'`
**Fix**: Use new import paths:
```python
# Old (broken)
from src.types import GameOfLifeTestConfig

# New (correct)
from src.core.types import GameOfLifeTestConfig
```

### Model Connection Issues

**Error**: `ollama.ResponseError: connection refused`
**Fix**: Start Ollama daemon:
```bash
ollama serve
```

### Pattern File Not Found

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'conways_life/...'`
**Fix**: Update path reference:
```python
# Old
from conways_life.parser import parse_rle

# New
from data.conways_life.parser import parse_rle
```

### 0% Accuracy with Emoji Markers

**Error**: All tests return 0% accuracy
**Fix**: Always use numeric markers:
```bash
# Wrong
--live-dead-cell-markers "⚪⚫"

# Correct
--live-dead-cell-markers "1,0"
```

---

## Q&A for Claude Code Agents

### Q: How do I run a quick GoL benchmark?

Use the Web UI (`python -m src.web`) — select Game of Life, configure parameters, and run.
Or use the 3-stage pipeline with a YAML config.

### Q: How do I add a new difficulty level?

1. Edit `src/core/types.py`:
   ```python
   class DifficultyLevel(Enum):
       EASY = "easy"
       MEDIUM = "medium"
       HARD = "hard"
       NIGHTMARE = "nightmare"
       ULTRA = "ultra"  # New
   ```

2. Update `GameOfLifeTestConfig._get_grid_size()`:
   ```python
   def _get_grid_size(self, difficulty: DifficultyLevel) -> int:
       sizes = {
           DifficultyLevel.EASY: 3,
           DifficultyLevel.MEDIUM: 5,
           DifficultyLevel.HARD: 7,
           DifficultyLevel.NIGHTMARE: 10,
           DifficultyLevel.ULTRA: 15,  # New
       }
       return sizes[difficulty]
   ```

### Q: How do I debug why a model is scoring 0%?

1. **Check cell markers**: `"1,0"` recommended (emoji now supported but models perform worse with them)
2. **Inspect raw output**: Add `print(response)` before `parse_response()`
3. **Check prompt**: Ensure format matches expected output
4. **Try simpler test**: Use `--difficulty easy --batch-size 1`

### Q: How do I add support for a new LLM API?

See "New Model Provider" section above. Key steps:
1. Create interface extending `ModelInterface`
2. Implement `query(prompt, params)` method
3. Register in `create_model_interface()` factory in `src/models/__init__.py`

### Q: Where are benchmark results stored?

- **Default**: `results/` at repository root
- **Multi-model runs**: `results/multi_model_TIMESTAMP/`
- **Custom**: Use `--results-dir` flag

### Q: How do I reproduce exact benchmark results?

Use the `seed` parameter in your YAML config or the Web UI. Same seed + same config = identical test cases.

---

## Dependencies

### Required

- Python 3.8+
- Ollama running locally (`ollama serve`)
- PyTorch, Transformers, NumPy, Pandas

### Installation

```bash
# Install requirements
pip install -r requirements.txt

# Optional: Install with dev dependencies
pip install -r requirements.txt pytest pytest-cov black ruff
```

### Verify Installation

```bash
# Check Python version
python --version

# Check Ollama connection
ollama list

# Run quick test via web UI
python -m src.web
# Open http://127.0.0.1:8000/
```

---

## Contributing

### Code Style

- Use type hints for all functions
- Follow PEP 8 naming conventions
- Add docstrings to public methods
- Keep functions < 50 lines when possible

### Before Committing

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Run tests
pytest tests/
```

---

## Additional Resources

- **Project Overview**: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) — Architecture, tasks, research findings, quick start
- **Plugin Guide**: [docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md) — Plugin reference, end-first parsing, adding new plugins
- **Architecture**: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)
- **Research — Quantization**: [docs/research/quantization/EXECUTIVE_SUMMARY.md](docs/research/quantization/EXECUTIVE_SUMMARY.md)
- **Research — Prompt Analysis**: [docs/research/prompt-analysis/RESULTS_REPORT.md](docs/research/prompt-analysis/RESULTS_REPORT.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

*Last updated: 2026-04-16*
*Version: 2.21.0*

**Recent key additions:**

- **Improvement Report v2.4** — `format_version: "2.4"`, agent-facing seed artifact for parser refactor work. Context-anchored regex generator replaces legacy span-text LCP (locates via `before` prefix + format-aware capture); merged label disjunction synthesizes across multiple `Label:` anchors into one pattern (carwash: `recommendation:` + `conclusion:` → single ~100% regex); regex candidates carry weighted `kind` (`merged_label_disjunction` > `context_anchor` > `format_only` > `text_pattern`) with `support` + post-harness low-support filtering
- **Capture quality metrics (v2.3)** — `regex_test[]` rows now carry `capture_exact_rate` / `capture_contains_rate` / `sample_captures` so `match_rate` is never read in isolation; frontend `CaptureQualityPill` tones on capture quality
- **Parser-span alignment (v2.3)** — top-level `parser_span_alignment` splits "parser missed" into `aligned` / `misaligned` / `no_output`, corrects the "parser_missed: 100" misleading headline when parser_extracted is actually correct but annotator didn't mark `parser_ok`
- **Data quality warnings + auto-suppression (v2.3)** — `data_quality.warnings[]` flags `no_parse_strategy`, `uniform_language`/`uniform_system_style`/`uniform_user_style`/`uniform_expected`; single-bucket axis breakdowns are **omitted from the JSON** (not emitted empty); frontend surfaces as collapsible amber banner
- **Span context enrichment (v2.1 → v2.2)** — context windows widened 24 → 120 chars, each span example carries a `sentence` field + `parser_extracted` + `parser_match_type` (inline parser-vs-annotator diff); per-group `structural_ratios` (line_start / label_colon / bold_wrap / answer_label_match / …), `prefix_anchors` with `type` (label / format / phrase), `label_taxonomy` (specific label-word counts)
- **Model answer distribution + variants** — `model_answer_distribution` (normalized histogram) + `model_answer_variants` (raw text forms per normalized bucket) so the agent sees both "model mostly says walk" and "it writes `Walk` / `WALK` / `**Walk**` / `Walk to the carwash`"
- **New span formats: italic / strikethrough / header** — frontend `autoFormat` detects `_walk_` / `*walk*` / `~~walk~~` / `# heading`; backend `FORMAT_TO_STRATEGY` maps to `italic_keyword` / `strikethrough_keyword` / `header_line`
- **Modal UX polish** — dialog auto-fits content up to `min(95vw, 1200px)` (no more truncated tabs); 9 tabs kept on one row via horizontal scroll; Summary grid balanced to 4×2 with a `Parser accuracy` card; SpanGroupCard expansion reveals structural signals chips, prefix anchors table (type-chipped), and regex test rows with capture quality + click-to-expand sample captures
- **Human Review & Annotation** (`/review`, v2.20.0) — two-column editorial workspace for human labelling of model responses; 7 response classes including `parser_false_positive` which uniquely coexists with answer spans; one-click word-marking with hover affordance; drag-select with sticky annotation dock; parser-match highlight + "Jump to parser match"; persistent parser-disagreement callout; session-wide target-language preference
- **Annotation sidecars** — gzipped JSON (`{stem}_annotations.json.gz`) next to result files; atomic temp+rename writes; `has_annotations` flag surfaced on every result summary → `PenLine` badge on annotated rows; DELETE endpoint is idempotent
- **Machine translation** — `deep-translator` wrapper with LRU cache; provider configurable via `TRANSLATOR_PROVIDER` env var (default `google`, zero-config); read-only translation panels (select-none preserves span offsets); language selector in Review header
- **Invariant relaxation** — spans and `response_class` may now coexist (pre-v2.20.0 was `spans XOR response_class`); unlocks `verbose_correct` + span and `parser_false_positive` + span workflows
- **Execute page unified** — `/execute` landing with "Simple run" / "Matrix run" tiles; `?mode=simple|matrix` deep-links; lazy-loaded sub-wizards (`pages/execute/simple-wizard.tsx`, `pages/execute/matrix-wizard.tsx`); `/matrix-execution` redirects via `<Navigate />`
- **Matrix Exec wizard** — 5-step flow: Setup → Axes → Models → Settings → Review; reuses `StepButton`/`StepFooter` primitives
- **Shared component extraction** — `components/wizard/` (StepButton, StepFooter) + `components/model-selection/` (ModelList, OllamaSection, OpenAIEndpointSection, HuggingFaceSection); removes ~300 lines of duplication
- **Configure page wizard** — 4-step Setup → Plugins → Prompts → Review; import via URL/paste YAML; expandable plugin rows; custom system prompt toggle; YAML copy/download split button
- **`POST /api/testsets/config-to-yaml`** — returns YAML string from `GenerateRequest` without generating a file
- **Picross (Nonogram) plugin** — 19th benchmark; grid-based deductive reasoning with line solver, 3 clue formats, partial-solution mode
- **Backend simplification** — extracted `_build_yaml_config()` and `_find_result_file()` helpers eliminating ~80 lines of duplication; fixed `cancel()` dead code; moved inline imports to module level; bare `except` blocks now log warnings
- **Version single-sourced** — `src/__init__.py` is canonical; `src/web/app.py` imports `__version__` automatically
- **Plugin task types auto-discovered** — `_KNOWN_TASK_TYPES` and `_TASK_TYPE_SUFFIXES` derived from `PluginRegistry`; fixed missing `picross` in reanalyze inference
- **`TASK_COLORS`** — added missing entries for `time_arithmetic`, `false_premise`, `symbol_arithmetic`, `picross`
- **LLM-as-a-Judge** — `/judge` page; verdicts: `true_incorrect`, `false_negative`, `parser_failure`; Markdown export
- **Multilingual content** — deep localization + grammatical gender across all 19 plugins
- **React SPA** — Vite 6 + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui
- **Job persistence + pause/resume** — `src/web/job_store.py` single-place JSON backend (swap for NoSQL without touching other files); `PAUSED` state with checkpoint index; resume continues from `paused_at_index`, merging partial results; history survives server restarts; `GOL_JOBS_FILE` env var configures path

*For questions or issues: Check [README.md](README.md) or create an issue*
