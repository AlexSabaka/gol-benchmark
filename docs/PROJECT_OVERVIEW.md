# GoL Benchmark — Project Overview

> **Version 2.26.0** | Last updated: 2026-04-27

GoL Benchmark is a procedural benchmark suite for stress-testing LLM reasoning across structured cognitive tasks. It generates test cases algorithmically (not from static datasets), measures model performance across diverse prompt configurations, and produces publication-ready analytics.

For the plugin enumeration and per-task summaries, see [README.md](README.md). For per-plugin internals and the parser convention, see [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md). For the annotation workflow and Improvement Report, see [HUMAN_REVIEW_GUIDE.md](HUMAN_REVIEW_GUIDE.md). For versioned system prompts, see [PROMPT_STUDIO.md](PROMPT_STUDIO.md).

---

## Table of Contents

- [Project Mission & Philosophy](#project-mission--philosophy)
- [Architecture Overview](#architecture-overview)
- [Model Providers](#model-providers)
- [Prompt Engineering System](#prompt-engineering-system)
- [Web UI](#web-ui)
- [Key Research Findings](#key-research-findings)
- [Quick Start](#quick-start)
- [CLI Reference Appendix](#cli-reference-appendix)

---

## Project Mission & Philosophy

### What It Tests

The suite measures how well language models handle:

- **Rule application** — Conway's Game of Life, Wolfram 1D cellular automata
- **Mathematical evaluation** — Arithmetic expression parsing, picture algebra (system-of-equations under semantic surface noise)
- **Cognitive bias resistance** — Linda conjunction fallacy
- **Spatial reasoning** — ASCII shapes, inverted cup orientation
- **Physical state tracking** — Object tracking through container inversions
- **Theory of Mind** — Sally-Anne false belief test
- **Practical goal tracking** — Carwash paradox (walk vs drive)
- **Character-level reasoning** — Letter counting, word reversal, nth-letter, anagram/pangram/lipogram detection (strawberry); fancy Unicode normalization
- **Temporal reasoning** — Time arithmetic, calendar math, impossible date detection, AM/PM traps
- **Tabular reasoning** — Grid-based data lookups, sums, counts; Picross/Nonogram deduction
- **Safety reasoning** — Detecting dangerous or impossible premises (false premise)
- **Sycophancy resistance** — Misquote attribution under social pressure
- **Perspective-aware reasoning** — Family counting puzzles with self-reference traps
- **Encoding comprehension** — Decoding Base64, Caesar cipher, and Morse code messages, then following embedded instructions
- **Pure rule following** — Symbol arithmetic on custom operation tables

Full task list with answer types: [README.md § Benchmark Tasks](README.md#benchmark-tasks-21-plugins).

### Design Principles

1. **Procedural generation** — Test cases are generated algorithmically with seeded randomness. Same seed + same config = identical test cases. No static dataset to memorize.
2. **Prompt-first evaluation** — The same model is tested across multiple prompt configurations (user style × system style × language) to isolate prompt engineering effects from model capability. All plugins support 6 languages with multilingual response parsing.
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

All benchmark tasks are implemented as self-contained plugins in `src/plugins/`. The `PluginRegistry` ([src/plugins/__init__.py](../src/plugins/__init__.py)) auto-discovers plugins at runtime by scanning subdirectories for a module-level `plugin` variable. Each plugin provides a generator, a parser, and an evaluator. The registry is the single source of truth for the active plugin set — `PluginRegistry.list_task_types()` is what every consumer (analytics, reanalysis, badges, this doc set) should call rather than hardcoding a list.

Full plugin scaffold + parser convention details: [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md).

### Project Layout (orientation only)

For the full annotated tree, browse the repo. The high-level shape:

```
src/
  plugins/        # 21 task plugins + base.py + parse_utils.py + grammar_utils.py
  stages/         # 3-stage pipeline
  core/           # types, PromptEngine (legacy system-prompt enums)
  web/            # FastAPI backend + JobStore + PromptStore + AnnotationStore + judge worker
  models/         # ModelInterface + Ollama / HuggingFace / OpenAI-compatible
  evaluation/     # grid comparison + accuracy metrics
  visualization/  # matplotlib chart generation
  utils/          # logging, model discovery, path manager
frontend/         # React 19 + Vite 6 + Tailwind v4 + shadcn/ui SPA
tests/plugins/    # per-plugin unit tests + cross-plugin parsing validation
docs/             # this directory
```

`data/` was removed in earlier refactors — per-plugin data lives co-located in `src/plugins/<task>/data/`. `frontend/dist/` is the built SPA, served at `/` by the FastAPI app.

### Web UI

A modern single-page application built with **React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui**, backed by a **FastAPI** REST API. Provides dashboard, configuration with dynamic plugin forms, test set management, job execution with real-time progress, result analysis, judge runs, and the human-review annotation workspace — all through the browser.

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

Direct model loading via the `transformers` library with automatic device placement (CUDA/MPS/CPU).

```bash
python src/stages/run_testset.py testset.json.gz \
    --model microsoft/DialoGPT-medium --provider huggingface
```

### OpenAI-Compatible

Any OpenAI-compatible API endpoint (vLLM, LM Studio, text-generation-inference, OpenRouter, Groq, …).

### Factory Pattern

```python
from src.models import create_model_interface
interface = create_model_interface("ollama", "qwen3:0.6b", ollama_host="http://localhost:11434")
result = interface.query(prompt, {"temperature": 0.1, "max_tokens": 2048})
```

Adding a new provider: see the `add-model-provider` skill.

---

## Prompt Engineering System

Prompt generation has two independent layers:

1. **User prompts** (per-task) — plugin-local templates in `src/plugins/<task>/prompts.py`. Migrated from `PromptEngine.py` in v2.8.0; the `PromptEngine` user-template surface is deprecated. See [PLUGIN_GUIDE.md § Prompt Template Architecture](PLUGIN_GUIDE.md#prompt-template-architecture) for the current shape; the v2.8 migration is archived at [_archive/MIGRATION_GUIDE.md](_archive/MIGRATION_GUIDE.md).
2. **System prompts** — versioned, user-managed via Prompt Studio (v2.13+). Built-ins (`builtin_analytical` / `builtin_casual` / `builtin_adversarial` / `builtin_none`) seed from the legacy `PromptEngine.SYSTEM_PROMPTS` enum and become editable. Editing creates a new immutable version; old result files pinned to `(prompt_id, version)` keep replaying forever. Full schema, API, replay safety: [PROMPT_STUDIO.md](PROMPT_STUDIO.md).

### User Prompt Styles

| Style | Approach | Best For |
|-------|----------|----------|
| `linguistic` | Formal, rule-based, detailed instructions | Models that thrive on structure |
| `casual` | Conversational, approachable | Balanced models |
| `minimal` | Bare minimum instructions | Testing baseline capability |

The legacy `examples` and `rules_math` styles exist in old code but are deprecated — new plugins should use the three above.

### System Prompt Styles (legacy enum, still active as resolution fallback)

| Style | Approach | Best For |
|-------|----------|----------|
| `analytical` | Rigorous, step-by-step reasoning | Gemma models (+22pp boost) |
| `casual` | Friendly, supportive tone | Balanced interaction |
| `adversarial` | Efficiency-focused, direct | Qwen models (+18pp boost) |
| `none` | Empty system prompt | Baseline measurement |

These now resolve via Prompt Studio's built-in prompts (`builtin_analytical` etc.); the enum surface is the legacy fallback path when no `prompt_id` is stashed on a test case.

### Languages

English (EN), French (FR), Spanish (ES), German (DE), Chinese (ZH), Ukrainian (UA).

All plugins support all 6 languages for prompts, generated content, data, and response parsing (since v2.15.0). Generated test content (scenarios, questions, grid data, narratives, encoded text, relationship terms, vocabulary) is produced in the requested language — not just the prompt wrappers. Gendered languages (UA, ES, FR, DE) use proper grammatical gender via `src/plugins/grammar_utils.py`: articles resolved by noun gender, Ukrainian nouns decline by case (nominative/accusative/locative), past-tense verbs conjugate by randomly selected subject gender (m/f).

### Why This Matters

The combinatorial matrix (up to 3 user styles × 3 system styles × 6 languages = 54 configurations per task) enables systematic study of how prompt engineering affects model performance. Research with this system found that prompt choice alone can swing accuracy by 44+ percentage points on the same model.

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
| `/configure` | Configure | 4-step wizard: Setup → Plugins → Prompts → Review |
| `/testsets` | Test Sets | Create, list, inspect, regenerate with param overrides |
| `/execute` | Execute | Landing page with two tiles — Simple run (4-step wizard) or Matrix run (5-step cartesian sweep) |
| `/jobs` | Jobs | Monitor execution + judge jobs; pause/resume; cooperative cancellation |
| `/results` | Results | Browse with sortable DataTable + faceted filters; reanalyze; rerun |
| `/charts` | Charts | Heatmap, bar comparison, scaling scatter |
| `/reports` | Reports | View generated HTML reports |
| `/judge` | Judge | LLM-as-a-Judge: file selector, summary, filterable judgments table, JSONL/Markdown export |
| `/review` | Review | Human annotation wizard (two-column workspace, keyboard-first). See [HUMAN_REVIEW_GUIDE.md](HUMAN_REVIEW_GUIDE.md) |
| `/prompts` | Prompts | Prompt Studio list / detail / multi-language editor / version history (frontend integration in progress — see [PROMPT_STUDIO.md](PROMPT_STUDIO.md)) |

### API Endpoints

| Router | Prefix | Purpose |
|--------|--------|---------|
| `plugins.py` | `/api/plugins` | Plugin discovery, task-specific form schemas |
| `models.py` | `/api/models` | Model listing from Ollama/HF/OpenAI providers |
| `testsets.py` | `/api/testsets` | Test set generation, listing, upload, `config-to-yaml` export |
| `matrix.py` | `/api/matrix` | Cartesian-sweep generation + execution |
| `execution.py` (jobs) | `/api/jobs` | Job submission, status polling, progress, pause/resume |
| `analysis.py` | `/api/results` | Result listing, summary statistics, breakdowns, reanalysis, judge |
| `human_review.py` | `/api/human-review` | Annotation cases, sidecar persistence, improvement report, translation |
| `prompts.py` | `/api/prompts` | Prompt Studio CRUD + versioning |
| `metadata.py` | `/api/metadata` | Aggregate metadata for matrix/wizard population |

### Background Jobs

The `JobManager` (`src/web/jobs.py`) uses `ProcessPoolExecutor` for concurrent model execution. Jobs track state through `PENDING → RUNNING → COMPLETED/FAILED/CANCELLED/PAUSED` with progress counters for real-time UI updates. All persistence routes through `src/web/job_store.py` (the only place to swap when migrating to Redis/Postgres). Credentials encrypted at rest under `data/jobs/` (Fernet via `src/web/crypto.py`).

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

Q2_K achieves 87.5% model size reduction with a net accuracy gain. Hypothesis: quantization acts as implicit regularization. Full study: [research/quantization/](research/quantization/).

### 3. Chain-of-Thought Hurts Structured Tasks

- **GoL / Arithmetic / Cellular Automata**: `--no-think` improves accuracy — models overthink simple rule application.
- **Linda Fallacy**: CoT helps — reasoning through the logic catches the bias trap.

### 4. End-First Parsing

LLMs reason first, answer last. Searching from the end of responses instead of the beginning improved carwash accuracy from 14.3% to 27.6% with zero regressions across 1,933 re-parsed results. Subsequent cross-plugin alignment work (`strip_verification_tail`, `normalize_unicode`, multilingual answer-label regexes) extended end-first to nearly every parser. Full convention + Phase 1–8 adoption: [PLUGIN_GUIDE.md § End-First Parsing Convention](PLUGIN_GUIDE.md#end-first-parsing-convention).

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

### Run Tests

```bash
pytest tests/                                  # All tests
pytest tests/plugins/                          # Plugin-specific tests
pytest tests/test_parser_end_first.py -v       # End-first parsing validation
```

---

## CLI Reference Appendix

### Common Flags

```bash
# Prompt styles (user prompt)
--prompt-style minimal|casual|linguistic

# System prompt styles (legacy enum; Prompt Studio resolves via prompt_id when set)
--system-prompt-style analytical|casual|adversarial|none

# Languages
--prompt-language en|es|fr|de|zh|uk

# Cell markers (GoL / C14 only — emoji supported since v2.10.1, but numeric recommended)
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

### Difficulty Levels

| Level | GoL Grid Size | ARI Complexity | Description |
|-------|--------------|----------------|-------------|
| `easy` | 3×3 | Level 1 | Simple patterns, basic operations |
| `medium` | 5×5 | Level 2 | Moderate complexity |
| `hard` | 7×7 | Level 3 | Complex patterns, nested operations |
| `nightmare` | 10×10 | Level 4 | Extreme complexity |

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GOL_LOG_FILE` | `gol_eval.log` | Log file path (`src/utils/logger.py`) |
| `GOL_JOBS_FILE` | `jobs.json` | Legacy job store path (still honored; new layout under `data/jobs/`) |
| `GOL_SECRET_KEY` | autogen → `data/.secret_key` | Fernet key for at-rest credential encryption |
| `TRANSLATOR_PROVIDER` | `google` | Translation backend (`google` / `libre` / `mymemory`) |

### Quirks Worth Knowing

- **`--no-think`** is critical for structured tasks (GoL, Arithmetic, C14). Always pass it for those benchmarks.
- **Cell markers**: emoji work since v2.10.1+, but models still perform best with numeric `"1,0"`. Emoji markers are a valid robustness test, not a default.
- **Temperature 0.1** is the recommended default. Higher temperatures hurt reproducibility and accuracy on structured tasks.
- **First Ollama query is slow** (~3–5 s model load). Subsequent queries are fast.

---

*See also: [README.md](README.md) for the index, [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for plugin internals, [HUMAN_REVIEW_GUIDE.md](HUMAN_REVIEW_GUIDE.md) for annotation, [CHANGELOG.md](../CHANGELOG.md) for version history, [TECHDEBT.md](../TECHDEBT.md) for incomplete refactors.*
