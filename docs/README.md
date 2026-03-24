# GoL Benchmark Documentation

Documentation for the GoL Benchmark Suite — a procedural benchmark for testing LLM reasoning across 12 structured cognitive tasks.

---

## Start Here

| Document | Description |
|----------|-------------|
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | Project mission, architecture, all 12 tasks, research findings, quick start |
| [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) | Plugin system reference, per-plugin docs, adding new plugins |

---

## Architecture

| Document | Description |
|----------|-------------|
| [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md) | System design and component diagram |
| [architecture/THREE_STAGE_PIPELINE.md](architecture/THREE_STAGE_PIPELINE.md) | 3-stage pipeline (generate → run → analyze) |
| [architecture/MODEL_PROVIDERS.md](architecture/MODEL_PROVIDERS.md) | Ollama, HuggingFace, OpenAI-compatible providers |

## Prompt Engine

| Document | Description |
|----------|-------------|
| [prompt-engine/SYSTEM_PROMPTS.md](prompt-engine/SYSTEM_PROMPTS.md) | System prompt styles (analytical, casual, adversarial) |
| [prompt-engine/USER_PROMPTS_GOL.md](prompt-engine/USER_PROMPTS_GOL.md) | Game of Life user prompt templates |
| [prompt-engine/USER_PROMPTS_MATH.md](prompt-engine/USER_PROMPTS_MATH.md) | Arithmetic user prompt templates |
| [prompt-engine/USER_PROMPTS_LINDA.md](prompt-engine/USER_PROMPTS_LINDA.md) | Linda Fallacy user prompt templates |
| [prompt-engine/MIGRATION_GUIDE.md](prompt-engine/MIGRATION_GUIDE.md) | Prompt engine migration guide |

## Research

| Document | Description |
|----------|-------------|
| [research/quantization/EXECUTIVE_SUMMARY.md](research/quantization/EXECUTIVE_SUMMARY.md) | Q2_K beats F16 — quantization study |
| [research/quantization/DETAILED_REPORT.md](research/quantization/DETAILED_REPORT.md) | Full quantization analysis |
| [research/prompt-analysis/RESULTS_REPORT.md](research/prompt-analysis/RESULTS_REPORT.md) | Prompt engineering study — model personalities |
| [research/prompt-analysis/VISUALIZATIONS_GUIDE.md](research/prompt-analysis/VISUALIZATIONS_GUIDE.md) | Charts and visualization guide |
| [research/MODEL_CATALOG.md](research/MODEL_CATALOG.md) | Available models reference |

---

## Benchmark Tasks (12 plugins)

| Task | Plugin | Answer Type |
|------|--------|-------------|
| Conway's Game of Life | `game_of_life` | 2D grid |
| Arithmetic Expressions | `arithmetic` | Number |
| Linda Conjunction Fallacy | `linda_fallacy` | Probability ranking |
| 1D Cellular Automata | `cellular_automata_1d` | 1D binary array |
| ASCII Shapes | `ascii_shapes` | Dimensions / count / boolean |
| Object Tracking (Grape Test) | `object_tracking` | Location name |
| Sally-Anne (Theory of Mind) | `sally_anne` | Container name |
| Carwash Paradox | `carwash` | Always "drive" |
| Inverted Cup | `inverted_cup` | "flip" |
| Strawberry (Letter Counting) | `strawberry` | Integer |
| Measure Comparison | `measure_comparison` | Measurement / "equal" / "incomparable" |
| Grid Tasks (Table Reasoning) | `grid_tasks` | Varies |

See [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for detailed per-plugin documentation.

---

## Directory Structure

```
docs/
├── README.md                   # This file
├── PROJECT_OVERVIEW.md         # Comprehensive project overview
├── PLUGIN_GUIDE.md             # Plugin system guide & reference
├── architecture/               # System design
│   ├── SYSTEM_OVERVIEW.md
│   ├── MODEL_PROVIDERS.md
│   └── THREE_STAGE_PIPELINE.md
├── prompt-engine/              # Prompt template reference
│   ├── SYSTEM_PROMPTS.md
│   ├── USER_PROMPTS_GOL.md
│   ├── USER_PROMPTS_MATH.md
│   ├── USER_PROMPTS_LINDA.md
│   └── MIGRATION_GUIDE.md
├── research/                   # Research findings
│   ├── MODEL_CATALOG.md
│   ├── quantization/           # Q2_K vs F16 study
│   └── prompt-analysis/        # Prompt engineering study
├── images/                     # Charts and visualizations
└── _archive/                   # Superseded documents (25 files)
```

---

## Related Resources

- [Main README](../README.md) — Project overview and quick start
- [CLAUDE.md](../.claude/CLAUDE.md) — AI agent instructions
- [CHANGELOG](../CHANGELOG.md) — Version history

---

**Version:** 2.3.0
**Last Updated:** March 2026
