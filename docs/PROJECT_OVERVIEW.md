# GoL Benchmark — Project Overview

> **Version 2.19.0** | Last updated: 2026-04-14

GoL Benchmark is a procedural benchmark suite for stress-testing LLM reasoning across structured cognitive tasks. It generates test cases algorithmically (not from static datasets), measures model performance across diverse prompt configurations, and produces publication-ready analytics.

---

## Table of Contents

- [Project Mission & Philosophy](#project-mission--philosophy)
- [Architecture Overview](#architecture-overview)
- [Directory Structure](#directory-structure)
- [Supported Benchmark Tasks](#supported-benchmark-tasks)
- [Model Providers](#model-providers)
- [Prompt Engineering System](#prompt-engineering-system)
- [Web UI](#web-ui)
- [Key Research Findings](#key-research-findings)
- [Known Quirks & Gotchas](#known-quirks--gotchas)
- [Quick Start](#quick-start)

---

## Project Mission & Philosophy

### What It Tests

The suite measures how well language models handle:

- **Rule application** — Conway's Game of Life, Wolfram 1D cellular automata
- **Mathematical evaluation** — Arithmetic expression parsing
- **Cognitive bias resistance** — Linda conjunction fallacy
- **Spatial reasoning** — ASCII shapes, inverted cup orientation
- **Physical state tracking** — Object tracking through container inversions
- **Theory of Mind** — Sally-Anne false belief test
- **Practical goal tracking** — Carwash paradox (walk vs drive)
- **Character-level reasoning** — Letter counting, word reversal, nth-letter, anagram/pangram/lipogram detection (strawberry), measurement comparison
- **Temporal reasoning** — Time arithmetic, calendar math, impossible date detection, AM/PM traps
- **Tabular reasoning** — Grid-based data lookups, sums, counts
- **Safety reasoning** — Detecting dangerous or impossible premises (false premise)
- **Perspective-aware reasoning** — Family counting puzzles with self-reference traps (family relations)
- **Encoding comprehension** — Decoding Base64, Caesar cipher, and Morse code messages, then following embedded instructions (encoding cipher)
- **Grid deduction** — Solving Picross/Nonogram puzzles from row and column clue constraints (picross)

### Design Principles

1. **Procedural generation** — Test cases are generated algorithmically with seeded randomness. Same seed + same config = identical test cases. No static dataset to memorize.
2. **Prompt-first evaluation** — The same model is tested across multiple prompt configurations (user style x system style x language) to isolate prompt engineering effects from model capability. All 19 plugins support 6 languages with multilingual response parsing.
3. **Plugin architecture** — Each benchmark task is a self-contained plugin with auto-discovery. Adding a new task requires zero changes to the pipeline.
4. **Portable pipeline** — The 3-stage architecture decouples generation, execution, and analysis. Stage 2 (execution) has near-zero dependencies, making it runnable on remote machines with only Python + a model API.

### Key Thesis

> Prompt engineering dominates model selection: the same model with different prompts can swing 44+ percentage points in accuracy.

---

## Architecture Overview

### 3-Stage Pipeline

```
┌─────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ YAML Config │────▶│  Stage 1:         │────▶│ testset_*.json.gz │
│             │     │  generate_testset │     │ (testsets/)       │
└─────────────┘     └───────────────────┘     └────────┬──────────┘
                                                       │
                    ┌──────────────────┐               ▼
                    │  Stage 2:        │◀──── testset + model name
                    │  run_testset     │────▶ results_*.json.gz
                    │  (+ model API)   │      (results/)
                    └──────────────────┘               │
                                                       ▼
                    ┌──────────────────┐     ┌───────────────────┐
                    │  Stage 3:        │────▶│  Reports + Charts │
                    │  analyze_results │     │  (reports/)       │
                    └──────────────────┘     └───────────────────┘
```

| Stage | Script | Input | Output |
|-------|--------|-------|--------|
| **1. Generate** | `src/stages/generate_testset.py` | YAML config | Compressed JSON.gz test set |
| **2. Run** | `src/stages/run_testset.py` | Test set + model + provider | Compressed JSON.gz results |
| **3. Analyze** | `src/stages/analyze_results.py` | Result files | Markdown/HTML reports + PNG charts |

Each stage is independently runnable. Stage 2 includes minimal self-contained model interfaces (no dependency on `src/models/`) so it can be copied to a remote machine.

### Plugin System

All 19 benchmark tasks are implemented as self-contained plugins in `src/plugins/`. The `PluginRegistry` auto-discovers plugins at runtime by scanning subdirectories for a module-level `plugin` variable.

Each plugin provides three components:

- **Generator** — produces `TestCase` objects; exposes `get_config_schema()` returning `ConfigField` descriptors for the web UI
- **Parser** — extracts answers from LLM responses via multi-strategy parsing
- **Evaluator** — scores correctness and aggregates statistics

See [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for full details.

### Web UI

A modern single-page application built with **React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui**, backed by a **FastAPI** REST API. Provides dashboard, configuration with dynamic plugin forms, test set management, job execution with real-time progress, and result analysis — all through the browser. Frontend source lives in `frontend/`, served at `/`.

---

## Directory Structure

```
gol_eval/
├── src/
│   ├── plugins/                        # Plugin-based benchmark system (19 plugins)
│   │   ├── base.py                     #   Abstract base classes + ConfigField
│   │   ├── __init__.py                 #   PluginRegistry with auto-discovery
│   │   ├── parse_utils.py              #   End-first parsing utilities + multilingual keyword merge helpers
│   │   ├── game_of_life/               #   Conway's Game of Life
│   │   ├── arithmetic/                 #   Math expression evaluation
│   │   ├── linda_fallacy/              #   Conjunction fallacy
│   │   ├── cellular_automata_1d/       #   Wolfram 1D rules
│   │   ├── ascii_shapes/               #   Spatial reasoning on ASCII art
│   │   ├── object_tracking/            #   Physical state tracking (grape test)
│   │   ├── sally_anne/                 #   Theory of Mind (false belief)
│   │   ├── carwash/                    #   Practical goal tracking
│   │   ├── inverted_cup/               #   Spatial orientation puzzle
│   │   ├── strawberry/                 #   Character-level reasoning (6 sub-types)
│   │   ├── measure_comparison/         #   Quantity comparison with units + decimal framing
│   │   ├── grid_tasks/                 #   Table reasoning
│   │   ├── time_arithmetic/            #   Temporal reasoning & impossible dates
│   │   ├── misquote/                   #   Sycophancy detection via false quote attributions
│   │   ├── false_premise/              #   Dangerous/impossible premise detection
│   │   ├── family_relations/           #   Perspective-aware family counting puzzles
│   │   ├── encoding_cipher/            #   Encoding & cipher decoding (Base64, Caesar, Morse)
│   │   ├── symbol_arithmetic/          #   Custom operation tables on abstract symbol sets
│   │   └── picross/                    #   Picross (Nonogram) grid puzzle solving
│   │
│   ├── stages/                         # 3-stage pipeline
│   │   ├── generate_testset.py         #   Stage 1: YAML → test sets
│   │   ├── run_testset.py              #   Stage 2: Execute tests against models
│   │   └── analyze_results.py          #   Stage 3: Analytics & reporting
│   │
│   ├── core/                           # Shared infrastructure
│   │   ├── types.py                    #   Config dataclasses, DifficultyLevel, enums
│   │   ├── PromptEngine.py             #   System prompts + enums (user templates deprecated → plugins)
│   │   └── TestGenerator.py            #   Test case generation helpers
│   │
│   ├── web/                            # FastAPI REST API backend
│   │   ├── app.py                      #   FastAPI application factory
│   │   ├── jobs.py                     #   Background job manager (ProcessPoolExecutor)
│   │   ├── api/                        #   REST API endpoints
│   │   │   ├── plugins.py              #     Plugin discovery & schemas
│   │   │   ├── models.py               #     Model provider discovery
│   │   │   ├── testsets.py             #     Test set creation & listing
│   │   │   ├── execution.py            #     Job submission & status
│   │   │   └── analysis.py             #     Result analysis
│   │   ├── reanalyze.py                #   Reanalysis utilities (re-parse/re-evaluate results)
│   │   └── config.py                   #   Web server configuration
│   │
│   ├── models/                         # LLM provider interfaces
│   │   ├── BaseModelInterface.py       #   ModelInterface base class
│   │   ├── OllamaInterface.py          #   Ollama (urllib-based, no ollama pkg)
│   │   ├── HuggingFaceInterface.py     #   HuggingFace Transformers (CUDA/MPS/CPU)
│   │   ├── OpenAICompatibleInterface.py#   OpenAI-compatible API (Groq, OpenRouter, etc.)
│   │   └── __init__.py                 #   Factory: create_model_interface(provider, model)
│   │
│   ├── engine/                         # Core task algorithms
│   │   ├── GameOfLifeEngine.py         #   Conway's GoL rules
│   │   ├── CellularAutomata1DEngine.py #   Wolfram 1D rules (0-255)
│   │   ├── MathExpressionGenerator.py  #   Expression tree generation
│   │   └── AsciiShapesEngine.py        #   ASCII shape rendering
│   │
│   ├── evaluation/                     # Result scoring
│   │   └── TestEvaluator.py            #   Grid comparison, accuracy metrics
│   │
│   ├── visualization/                  # Charts & reports
│   │   └── visualization_engine.py     #   matplotlib/seaborn visualizations
│   │
│   ├── utils/                          # Utilities
│   │   ├── logger.py                   #   Structured logging
│   │   ├── model_providers.py          #   Provider abstraction & model discovery
│   │   ├── path_manager.py             #   Centralized path resolution
│   │   └── text_table.py              #   Terminal table formatting
│   │
│   └── benchmarks/                     # DEPRECATED legacy monolithic scripts
│
├── tests/                              # Test suite
│   ├── plugins/                        #   Per-plugin unit tests
│   ├── test_comprehensive_workflow.py  #   End-to-end pipeline tests
│   ├── test_parser_end_first.py        #   End-first parsing validation
│   └── ...
│
├── scripts/                            # Batch processing utilities
├── data/                               # (Removed — data co-located in src/plugins/*/data/)
├── testsets/                           # Generated test sets (JSON.gz)
├── results/                            # Benchmark results (JSON.gz)
├── reports/                            # Generated reports & charts
├── frontend/                           # React SPA (Vite + React 19 + TypeScript + Tailwind + shadcn/ui)
│   ├── src/
│   │   ├── api/                        #   Typed API client layer
│   │   ├── hooks/                      #   React Query data-fetching hooks
│   │   ├── types/                      #   TypeScript interfaces
│   │   ├── pages/                      #   Dashboard, Configure, TestSets, Execute, Jobs, Results, Reports
│   │   ├── components/                 #   UI primitives (shadcn), layout, plugin-config, data-table
│   │   └── App.tsx                     #   Router + providers
│   ├── vite.config.ts                  #   base: "/", proxy /api → :8000
│   └── dist/                           #   Production build output
└── docs/                               # Documentation & research reports
```

---

## Supported Benchmark Tasks

| Plugin | Display Name | What It Tests | Answer Type |
|--------|-------------|---------------|-------------|
| `game_of_life` | Conway's Game of Life | Rule-based grid transformation | 2D grid of 0s/1s |
| `arithmetic` | Arithmetic Expression Evaluation | Math expression evaluation | Numeric value |
| `linda_fallacy` | Linda Conjunction Fallacy | Cognitive bias resistance | Probability ranking |
| `cellular_automata_1d` | 1D Cellular Automata | Wolfram rule application | 1D binary array |
| `ascii_shapes` | ASCII Shapes Spatial Reasoning | Spatial reasoning on ASCII art | Dimensions / count / boolean |
| `object_tracking` | Object Tracking (Grape Test) | Physical state tracking with inversions | Location name |
| `sally_anne` | Sally-Anne Test | Theory of Mind (false belief) | Container name (belief, not reality) |
| `carwash` | Carwash Paradox | Practical goal tracking | Always "drive" |
| `inverted_cup` | Inverted Cup | Spatial orientation reasoning | "flip" |
| `strawberry` | Strawberry (Character Reasoning) | Letter counting, reversal, nth-letter, anagram, pangram, lipogram | Integer / String / Boolean |
| `measure_comparison` | Measure Comparison | Quantity comparison with units + decimal framing sensitivity | Measurement / "equal" / "incomparable" |
| `grid_tasks` | Grid Tasks (Table Reasoning) | Tabular data lookups, sums, counts | Varies by question |
| `time_arithmetic` | Time Arithmetic | Temporal reasoning, calendar math, impossible date detection | Time / Day / Duration / "impossible" |
| `misquote` | Misquote Attribution | Sycophancy detection via false quote attributions | Yes/No (two-part) |
| `false_premise` | False Premise | Dangerous/impossible premise detection | Refusal / Compliance / Hedge |
| `family_relations` | Family Relations | Perspective-aware family counting puzzles | Integer (person count) |
| `encoding_cipher` | Encoding & Cipher Decoding | Decode Base64/Caesar/Morse and follow instructions | Decoded text / response word |
| `symbol_arithmetic` | Symbol Arithmetic | Evaluate expressions under arbitrary binary operations | Symbol from operation table |

Each plugin is self-contained in `src/plugins/<task_type>/` with its own generator, parser, and evaluator.

---

## Model Providers

### Ollama (Primary)

Local and remote inference via Ollama's REST API.

```bash
# Local (default)
python src/stages/run_testset.py testset.json.gz --model qwen3:0.6b --provider ollama

# Remote instance
python src/stages/run_testset.py testset.json.gz --model qwen3:0.6b --provider ollama \
    --ollama-host http://192.168.1.50:11434
```

Features: dynamic model discovery, quantization detection (F16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q2_K), retry logic, remote host support.

### HuggingFace / Transformers

Direct model loading via the `transformers` library with automatic device placement.

```bash
python src/stages/run_testset.py testset.json.gz \
    --model microsoft/DialoGPT-medium --provider huggingface
```

### OpenAI-Compatible

Any OpenAI-compatible API endpoint (e.g., vLLM, LM Studio, text-generation-inference).

### Factory Pattern

```python
from src.models import create_model_interface
interface = create_model_interface("ollama", "qwen3:0.6b", ollama_host="http://localhost:11434")
result = interface.query(prompt, {"temperature": 0.1, "max_tokens": 2048})
```

---

## Prompt Engineering System

### Architecture (v2.8.0)

Prompt generation follows a **plugin-local template** pattern. Each plugin defines its own user prompt templates in a `prompts.py` file, while system prompts remain centralised in `PromptEngine`.

```
src/plugins/<task>/
├── prompts.py          # User prompt templates keyed by (Language, style)
└── generator.py        # Uses _build_prompts() base class helper

src/core/PromptEngine.py  # System prompts + Language/PromptStyle/SystemPromptStyle enums
                           # (task-specific user templates DEPRECATED)
```

Base class helpers in `TestCaseGenerator`:
- `_build_prompts(templates, language, user_style, system_style, **vars)` → `(user, system, full)`
- `_get_system_prompt(system_style, language)` — wraps PromptEngine with safe fallbacks
- `_format_user_prompt(templates, language, style, **vars)` — template lookup with EN/casual fallback

### User Prompt Styles

| Style | Approach | Best For |
|-------|----------|----------|
| `linguistic` | Formal, rule-based, detailed instructions | Models that thrive on structure |
| `casual` | Conversational, approachable | Balanced models |
| `minimal` | Bare minimum instructions | Testing baseline capability |
| `examples` | Includes worked examples | Few-shot learning (deprecated) |
| `rules_math` | Mathematical notation | Math-oriented tasks (deprecated) |

### System Prompt Styles

| Style | Approach | Best For |
|-------|----------|----------|
| `analytical` | Rigorous, step-by-step reasoning | Gemma models (+22pp boost) |
| `casual` | Friendly, supportive tone | Balanced interaction |
| `adversarial` | Efficiency-focused, direct | Qwen models (+18pp boost) |
| `none` | Empty system prompt | Baseline measurement |

### Languages

English (EN), French (FR), Spanish (ES), German (DE), Chinese (ZH), Ukrainian (UA)

All 19 plugins now support all 6 languages for prompts, generated content, data, and response parsing (v2.15.0). Since v2.15.0, all generated test content (scenarios, questions, grid data, narratives, encoded text, relationship terms, vocabulary) is produced in the requested language — not just the prompt wrappers. Each plugin has a dedicated i18n module with localized templates and vocabulary. Gendered languages (Ukrainian, Spanish, French, German) use proper grammatical gender: articles resolved by noun gender, Ukrainian nouns decline by case (nominative/accusative/locative), past-tense verbs conjugate by randomly selected subject gender (m/f), and zero slash patterns remain in generated prompts. The shared `grammar_utils.py` module provides article resolution, case-form lookup, and gender-aware template selection.

### Why This Matters

The combinatorial matrix (up to 3 user styles x 3 system styles x 6 languages = 54 configurations per task) enables systematic study of how prompt engineering affects model performance. Research with this system found that prompt choice alone can swing accuracy by 44+ percentage points on the same model.

> **Note**: The `examples` and `rules_math` user styles and the `adversarial` system style exist in legacy code but are deprecated. New plugins should use `minimal`, `casual`, and `linguistic`.

---

## Web UI

**Stack**: FastAPI (REST API) + React 19 + TypeScript + Vite 6 + Tailwind CSS v4 + shadcn/ui

```bash
python -m src.web                    # http://127.0.0.1:8000/
python -m src.web --host 0.0.0.0     # LAN-accessible

# Development (hot-reload frontend)
cd frontend && npm run dev           # http://localhost:5173/ (proxies /api → :8000)
```

### Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Dashboard | Summary of available plugins, models, recent runs |
| `/configure` | Configure | 4-step wizard: **Setup** (build from scratch or import via file/URL/paste YAML), **Plugins** (expandable table rows — checkbox auto-expands row with `ConfigForm`), **Prompts** (style matrix + hidden custom prompt revealed by "custom" toggle), **Review** (summary + Generate, Copy YAML, Download YAML) |
| `/testsets` | Test Sets | Create, list, inspect (tabbed detail with paginated cases), regenerate with param overrides, switch between `Table` and grouped `Cards`, and use collapsible grouped rows in table mode |
| `/execute` | Execute | Landing page with two choice tiles — **Simple run** (4-step wizard: Test Sets → Models → Settings → Review) for running existing test sets, and **Matrix run** (5-step wizard: Setup → Axes → Models → Settings → Review) for generating a cartesian sweep and optionally launching it. Mode carried in `?mode=simple\|matrix` query param; `/matrix-execution` redirects to `/execute?mode=matrix` |
| `/jobs` | Jobs | Monitor all execution jobs with state filters, progress bars, cancel/view actions, and cooperative cancellation for already-running inference or judge work |
| `/results` | Results | Browse results with sortable DataTable, model/task/language faceted filters (language chips show flag + full name); reanalyze, rerun with params, switch between `Table` and grouped `Cards`, and use collapsible grouped rows for task/model/run grouping |
| `/charts` | Charts | Heatmap, bar comparison, scaling scatter; task type + language filtering, log/linear scale toggle |
| `/reports` | Reports | View generated HTML reports in iframe |

### Frontend Architecture

```
frontend/src/
├── api/          # Typed fetch client (client.ts, plugins.ts, models.ts, testsets.ts, jobs.ts, results.ts)
├── hooks/        # React Query hooks with auto-refresh (use-plugins, use-models, use-testsets, use-jobs, use-results)
├── types/        # TypeScript interfaces mirroring backend schemas
├── pages/        # Route pages (Dashboard, Configure, TestSets, Execute [landing + execute/simple-wizard + execute/matrix-wizard], Jobs, Results, Charts, Reports, Judge)
├── components/
│   ├── ui/              # shadcn/ui primitives (19 components incl. textarea)
│   ├── layout/          # AppLayout, Sidebar, Header
│   ├── wizard/          # StepButton, StepFooter — shared by Execute, Configure, and Matrix wizards
│   ├── model-selection/ # ModelList, OllamaSection, OpenAIEndpointSection, HuggingFaceSection + SelectedModel types
│   ├── plugin-config/   # Dynamic ConfigField renderer (number, select, multi-select, boolean, range, weight_map)
│   ├── charts/          # AccuracyHeatmap, ModelBarChart, ScalingScatter, ChartFilters, ChartCard
│   ├── data-table/      # Generic sortable/filterable DataTable with optional collapsible grouping
│   └── param-override-modal.tsx  # Shared modal for rerun/regenerate with param overrides
└── App.tsx       # BrowserRouter + QueryClientProvider + ThemeProvider
```

### API Endpoints

| Router | Prefix | Purpose |
|--------|--------|---------|
| `plugins.py` | `/api/plugins` | Plugin discovery, task-specific form schemas |
| `models.py` | `/api/models` | Model listing from Ollama/HF/OpenAI providers |
| `testsets.py` | `/api/testsets` | Test set generation, listing, upload (YAML/gz), `config-to-yaml` export |
| `execution.py` | `/api/jobs` | Job submission, status polling, progress |
| `analysis.py` | `/api/results` | Result listing, summary statistics, breakdowns, reanalysis, LLM-as-a-Judge |

### Background Jobs

The `JobManager` (`src/web/jobs.py`) uses `ProcessPoolExecutor` for concurrent model execution. Jobs track state through `PENDING → RUNNING → COMPLETED/FAILED/CANCELLED` with progress counters for real-time UI updates. Queued jobs cancel immediately; already-running inference and judge workers use a shared cancellation flag so the Jobs page can stop active work cooperatively without losing terminal-state correctness.

---

## Key Research Findings

### 1. System Prompts Are Reasoning Switches

Identical system prompts produce opposite effects on different models:

| Model | Personality | Best System Style | Worst System Style |
|-------|------------|-------------------|-------------------|
| **Qwen3** | Pragmatist / risk-taker | Adversarial (+18pp) | Analytical (no effect) |
| **Gemma3** | Permission-based analyst | Analytical (+22pp) | Adversarial (-7pp) |
| **Llama** | Generalist | Balanced across styles | — |

### 2. Extreme Quantization Beats Full Precision

Testing AceMath-1.5B across quantization levels:

| Quantization | Accuracy | vs F16 Baseline |
|-------------|----------|-----------------|
| Q2_K (2-bit) | 37.76% | **+6.18pp** |
| Q4_K_M (4-bit) | 33.23% | +1.65pp |
| F16 (baseline) | 31.58% | — |
| Q8_0 (8-bit) | 31.17% | -0.41pp |

Q2_K achieves 87.5% model size reduction with a net accuracy gain. Hypothesis: quantization acts as implicit regularization.

### 3. Chain-of-Thought Hurts Structured Tasks

- **GoL / Arithmetic**: `--no-think` improves accuracy — models overthink simple rule application
- **Linda Fallacy**: CoT helps — reasoning through the logic catches the bias trap

### 4. End-First Parsing

LLMs reason first, answer last. Searching from the end of responses instead of the beginning improved carwash accuracy from 14.3% to 27.6% with zero regressions across 1,933 re-parsed results. v2.10.3 added `strip_verification_tail()` to handle models that append verification sections, fixing ~91 additional false negatives. v2.10.4 expanded the carwash parser's conditional/dismissive walk filtering (3 pattern groups, first-sentence strategy, contextual bold filtering), fixing 15 additional false negatives with 0 regressions. v2.10.5 overhauled the measure comparison parser (smart quote normalization, tightened equal keywords, pipeline reorder, bold two-pass, expanded incomparable patterns), fixing 38 false negatives with 0 regressions. v2.10.6 added first-bold/first-sentence strategies to object tracking and time arithmetic parsers for tasks where models state the answer upfront then explain with distractors — fixing 28 false negatives across 4 plugins (object tracking, inverted cup, time arithmetic, encoding cipher) with 0 regressions. v2.10.7 overhauled the false_premise parser (smart quote normalization, negation-aware compliance detection, safe-alternative section filtering, first-sentence refusal strategy, narrowed hedge qualifiers, expanded refusal/impossibility patterns), fixing 61 false negatives across all 5 domains with 0 regressions. See [PLUGIN_GUIDE.md — End-First Parsing Convention](PLUGIN_GUIDE.md#end-first-parsing-convention).

---

## Known Quirks & Gotchas

### Cell Markers — Emoji Now Supported (v2.10.1+)

Custom cell markers (including emoji like `"❤️,🖤"`) are now fully supported for both **Game of Life** (v2.10.1) and **Cellular Automata 1D** (v2.10.2). Earlier versions had a parsing bug that silently ignored non-default markers.

```bash
# All of these now work correctly:
--live-dead-cell-markers "1,0"        # numeric (recommended for best model accuracy)
--live-dead-cell-markers "❤️,🖤"      # emoji (works, but models may parse less reliably)
--live-dead-cell-markers "X,O"        # letters
```

For C14, custom markers appear in state strings, rule tables, and boundary descriptions.

> **Note:** While the generator and pipeline handle any markers correctly, models still tend to perform best with numeric `"1,0"` markers. Emoji markers are a valid stress test for model robustness.

### `--no-think` for Structured Tasks

Chain-of-thought reasoning hurts performance on rule-application tasks (GoL, Arithmetic, Cellular Automata). Always use `--no-think` for these benchmarks.

### Ollama Must Be Running

Start the Ollama daemon before running benchmarks:
```bash
ollama serve
```

### First Query Is Slow

Ollama loads models into VRAM on first query (~3-5 seconds). Subsequent queries are cached and fast (<1 second).

### Temperature 0.1

The recommended default. Higher temperatures introduce randomness that hurts reproducibility and accuracy on structured tasks.

### End-First Parsing

All plugin parsers search from the **end** of model responses toward the start. This is a deliberate architectural decision, not a bug. See [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md#end-first-parsing-convention) for details and exceptions.

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
ollama serve  # Start Ollama daemon
```

### Web UI (Recommended)

```bash
python -m src.web
# Open http://127.0.0.1:8000/
```

### CLI — 3-Stage Pipeline

```bash
# Stage 1: Generate test set from a YAML config
python src/stages/generate_testset.py my_benchmark_config.yaml

# Stage 2: Run test set against a model
python src/stages/run_testset.py testsets/testset_*.json.gz \
    --model qwen3:0.6b --provider ollama --output-dir results/

# Stage 3: Analyze results
python src/stages/analyze_results.py results/*.json.gz \
    --visualize --output-dir reports/
```

### CLI — Legacy Benchmark Scripts

```bash
# Game of Life
python -m src.benchmarks.gol_eval --model qwen3:0.6b --difficulty medium \
    --batch-size 20 --no-think --live-dead-cell-markers "1,0"

# Arithmetic
python -m src.benchmarks.ari_eval --model llama3.2:3b --difficulty 3

# Linda Fallacy
python -m src.benchmarks.linda_eval --model gemma3:1b --language es --trials 10
```

### Run Tests

```bash
pytest tests/                                  # All tests
pytest tests/plugins/                          # Plugin-specific tests
pytest tests/test_parser_end_first.py -v       # End-first parsing validation
```

---

*See also: [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for plugin architecture, per-plugin reference, and how to add new benchmarks.*
