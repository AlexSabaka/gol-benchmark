# gol-eval

> A procedural benchmark suite for stress-testing LLM reasoning. Started as a weekend project to benchmark Conway's Game of Life across local models. Got out of control. Now 21 plugins, 6 languages, three-stage pipeline, web UI with human-in-the-loop annotation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

---

## What this is

gol-eval is a benchmark framework built around one claim:

> **Failure isn't a binary model property. It's a controllable variable, and the system prompt is the dominant control lever.**

Every test case is procedurally generated from a seed (no static dataset to memorize), every answer is parsed deterministically (no LLM-as-judge for primary scoring), and the same case is run across crossed axes of prompt style × system prompt × language so behavior can be attributed to specific inputs rather than vibes.

Across the current multilingual study (2 × 2 × 6 matrix — linguistic vs minimal user prompt × analytical vs adversarial system prompt × 6 languages, ~25 models, 1,200 cases per model), system prompt condition produces swings of **up to 48 percentage points within a single model**.

---

## Design principles

- **Procedural generation.** Seeds in, test cases out. Same seed + same config = identical cases.
- **Crossed axes.** User prompt style × system prompt × language are independent variables. Run the same model through all combinations and compare.
- **Deterministic parsing.** Every plugin has a multi-strategy parser with explicit confidence levels (boxed=0.95, bold=0.90, label=0.85, pattern=0.80, keyword=0.70, fallback=0.50). LLM-as-judge is available as a secondary audit tool, never as the primary score.
- **Multilingual to the bone.** Content — not just prompt wrappers — generated in 6 languages (EN / ES / FR / DE / ZH / UA). Grammar, gender, case handling per language.
- **Failure modes that actually matter.** Sally-Anne, carwash paradox, inverted cup, misquote attribution, false premise detection, strawberry-style character reasoning — the stuff that shows up in screenshots on r/LocalLLaMA.

---

## What's inside the box

21 plugins grouped by what they probe. Each is self-contained in `src/plugins/<n>/` with its own generator, parser, and evaluator.

### Spatial & simulation

| Plugin                 | Tests                                               | Answer          |
| ---------------------- | --------------------------------------------------- | --------------- |
| `game_of_life`         | Conway's rules applied to a grid                    | 2D binary grid  |
| `cellular_automata_1d` | Wolfram elementary rules (0–255)                    | 1D binary array |
| `ascii_shapes`         | Dimensions / count / position on ASCII art          | int / bool      |
| `picross`              | Nonogram deduction from row/col clues               | 2D binary grid  |
| `inverted_cup`         | Orientation — cup sealed top, open bottom           | "flip"          |
| `object_tracking`      | Track object through container moves and inversions | location name   |

### Computation

| Plugin               | Tests                                                                                                                                             | Answer                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| `arithmetic`         | Expression evaluation with controlled complexity                                                                                                  | number                              |
| `symbol_arithmetic`  | Rule-following on arbitrary binary operation tables — detects silent assumption of commutativity/associativity                                    | symbol                              |
| `picture_algebra`    | Systems of linear equations with variables rendered as emoji / alpha letters / nonsense words — measures GSM-Symbolic-style semantic interference | per-variable values                 |
| `grid_tasks`         | Cell lookup / row sum / column count on formatted tables                                                                                          | varies                              |
| `time_arithmetic`    | Intervals, midnight-crossing, AM/PM traps, impossible dates, leap years                                                                           | time / day / "impossible"           |
| `measure_comparison` | Quantity comparison with unit conversion, equal-value tricks, incomparables, adversarial decimal framing                                          | quantity / "equal" / "incomparable" |

### Reasoning traps

| Plugin             | Tests                                                                             | Answer                       |
| ------------------ | --------------------------------------------------------------------------------- | ---------------------------- |
| `sally_anne`       | Theory of Mind false belief — belief location vs reality                          | container name               |
| `carwash`          | Practical goal tracking — proximity framing tempts walk, answer is always "drive" | "drive"                      |
| `linda_fallacy`    | Conjunction fallacy via probability ranking                                       | ordered ranking              |
| `family_relations` | Perspective-aware counting — classic self-as-sibling trap                         | integer                      |
| `false_premise`    | Dangerous / impossible premise detection across 5 domains                         | refusal / compliance / hedge |
| `misquote`         | Sycophancy probe — false attribution with social-pressure framings                | yes/no (two-part)            |

### Character & encoding

| Plugin            | Tests                                                                                                                               | Answer                       |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| `strawberry`      | Letter count, word reversal, nth-letter, anagram, pangram, lipogram — six sub-types probing sub-token reasoning                     | int / str / bool             |
| `encoding_cipher` | Decode Base64 / Caesar / Morse, optionally follow embedded instruction — with hallucinated-execution detection                      | decoded text / response word |
| `fancy_unicode`   | Decorative Unicode normalization (mathematical alphanumeric, fullwidth, circled) — silent encoding, model must recognize unprompted | original text                |

See [`docs/PLUGIN_GUIDE.md`](docs/PLUGIN_GUIDE.md) for each plugin's config schema, parsing strategies, and failure taxonomy.

---

## Quick start

### Prerequisites

- Python 3.9+
- [Ollama](https://ollama.com/) for local models (or an OpenAI-compatible endpoint / OpenRouter API key)

### Install

```bash
git clone https://github.com/AlexSabaka/gol-eval.git
cd gol-eval
pip install -r requirements.txt
ollama serve   # or point to a remote instance below
```

### Web UI (recommended)

```bash
python -m src.web
# Then navigate to http://127.0.0.1:8000/
```

Configure a run through the 4-step wizard (Setup → Plugins → Prompts → Review), submit, watch the Jobs page for live progress, then browse Results / Charts / Reports. The Human Review tool lets you annotate parser misses and auto-generate regex improvement reports.

### CLI — three-stage pipeline

```bash
# 1. Generate test set from YAML config
python src/stages/generate_testset.py configs/my_benchmark.yaml

# 2. Run against a model
python src/stages/run_testset.py testsets/testset_*.json.gz \
    --model qwen3:0.6b --provider ollama

#    Remote Ollama:
#    --provider ollama --ollama-host http://host:11434
#
#    OpenAI-compatible (OpenRouter, vLLM, LM Studio, etc.):
#    --provider openai --endpoint https://openrouter.ai/api/v1 --model openai/gpt-4o-mini

# 3. Analyze
python src/stages/analyze_results.py results/*.json.gz --visualize
```

Each stage is independent. Stage 2 (execution) is designed to be portable — minimal dependencies, just Python and a model endpoint — so it can be relocated to a remote machine for long-running jobs. This path isn't extensively tested in practice; the common case is running all three stages on one host.

---

## Architecture

```plain
Stage 1:
    Step 1: Create YAML config
    Step 2: Generate test set .json.gz
Stage 2: 
    Step 1: Run test set
    Step 2: Collect results .json.gz
Stage 3: 
    Step 1: Analyze results
    Step 2: Generate reports and charts
```

All 21 plugins are auto-discovered by `PluginRegistry` at runtime — adding a new plugin is a subdirectory under `src/plugins/`, no pipeline edits needed. See [`docs/PLUGIN_GUIDE.md`](docs/PLUGIN_GUIDE.md) for the plugin contract and [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md) for the full system layout.

---

## Web UI

Single-page React app (Vite 6 + React 19 + TypeScript + Tailwind v4 + shadcn/ui) backed by FastAPI. Feature surface:

- **Configure** — 4-step wizard, YAML import/export, per-plugin config schemas rendered from `ConfigField` introspection
- **Execute** — simple (single-model) and matrix (cross-product sweep) modes
- **Jobs** — live progress, cooperative pause/resume/cancel of running inference and judge work
- **Results** — faceted browsing, reanalysis without re-inference, param-override rerun
- **LLM-as-Judge** — optional audit pass on incorrect responses using a separate judge model
- **Human Review** — per-case annotation with 7 response classes (including `parser_false_positive`), response-hash-keyed sidecars, improvement report with auto-generated regex candidates
- **Charts** — per-axis breakdowns, language filters with flags, log-scale toggles

---

## Known limitations

Things worth knowing before you run anything:

- **Three plugins are EN-only.** `measure_comparison` decimal-framing sub-type, `encoding_cipher`, and `fancy_unicode` currently fall back to English templates in other languages — they run, but they aren't really multilingual for those sub-types (TD-003 / TD-004 / TD-092).
- **Carwash ZH data artifact.** ~10 of 93 Chinese carwash prompts contain the phrase "开去" (drive to) in the premise, which inflates ZH accuracy for that plugin. Flagged; not retroactively re-run.
- **13 plugin tests are red on `dev`.** Across `ascii_shapes`, `cellular_automata_1d`, `linda_fallacy`. Pre-existing, not caused by the most recent changes; tracked as TD-101 but mentioned here so you know the full plugin suite isn't green.

Full register of technical debt and known limitations: [`TECHDEBT.md`](TECHDEBT.md).

---

## Documentation

| Document                                                       | Purpose                                                                                |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [`docs/README.md`](docs/README.md)                             | Documentation index — start here                                                       |
| [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md)         | Architecture, pipeline, directory layout, quick reference                              |
| [`docs/PLUGIN_GUIDE.md`](docs/PLUGIN_GUIDE.md)                 | Plugin contract, adding new plugins, end-first parsing convention (Phases 1–8)         |
| [`docs/HUMAN_REVIEW_GUIDE.md`](docs/HUMAN_REVIEW_GUIDE.md)     | Annotation workflow, v4 mark types, Improvement Report (v2.7) contract                 |
| [`docs/FRONTEND_GUIDE.md`](docs/FRONTEND_GUIDE.md)             | React SPA conventions — React Query, Tailwind v4 tokens, design system                 |
| [`docs/MODEL_PROVIDERS.md`](docs/MODEL_PROVIDERS.md)           | Ollama / HuggingFace / OpenAI-compatible provider reference                            |
| [`docs/PROMPT_STUDIO.md`](docs/PROMPT_STUDIO.md)               | Versioned system prompts (v2.13+), `PromptStore` API, replay safety                    |
| [`docs/SYSTEM_PROMPTS.md`](docs/SYSTEM_PROMPTS.md)             | Reference text for the four built-in system prompts                                    |
| [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)       | Pre-release checklist (versions, plugin counts, footers, frontend gates)               |
| [`CHANGELOG.md`](CHANGELOG.md)                                 | Version history                                                                        |
| [`TECHDEBT.md`](TECHDEBT.md)                                   | Open technical debt, incomplete refactors, god-module candidates                       |

---

## Status

Active development. Solo-maintained pet project that got out of control and intends to keep going, regardless of whether anyone else shows up. Current version: **v2.25.2** (April 2026). PRs welcome for new plugins, model coverage, or parser fixes — annotation sidecars and improvement reports from the Human Review tool make parser contributions particularly high-leverage.

## License

MIT. See [LICENSE](LICENSE).
