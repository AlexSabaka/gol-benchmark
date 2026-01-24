# GoL Benchmark Documentation

Documentation for the GoL (Game of Life) Benchmark Suite - a procedural benchmark for testing LLM reasoning capabilities across structured cognitive tasks.

## Quick Navigation

### Getting Started

| Document | Description |
|----------|-------------|
| [Architecture Overview](architecture/SYSTEM_OVERVIEW.md) | Understand the system design |
| [3-Stage Pipeline](architecture/THREE_STAGE_PIPELINE.md) | Modern test execution architecture |
| [Source Code Organization](implementation/SOURCE_CODE_ORGANIZATION.md) | Navigate the codebase |

### For Developers

| Document | Description |
|----------|-------------|
| [TUI System](implementation/TUI_SYSTEM.md) | Interactive benchmark interface |
| [Model Providers](architecture/MODEL_PROVIDERS.md) | Provider architecture |
| [File Management](implementation/FILE_MANAGEMENT.md) | Path manager and file organization |
| [Prompt Engine](implementation/prompt-engine/) | Multilingual prompt generation |

### Research & Findings

| Document | Description |
|----------|-------------|
| [Quantization Study](research/quantization/) | AceMath quantization analysis |
| [Prompt Analysis](research/prompt-analysis/) | Prompt engineering study |
| [Model Catalog](research/MODEL_CATALOG.md) | Available models reference |

---

## Directory Structure

```
docs/
├── README.md                 # This file
├── architecture/             # System design documents
│   ├── SYSTEM_OVERVIEW.md
│   ├── MODEL_PROVIDERS.md
│   └── THREE_STAGE_PIPELINE.md
├── implementation/           # Developer documentation
│   ├── SOURCE_CODE_ORGANIZATION.md
│   ├── TUI_SYSTEM.md
│   ├── FILE_MANAGEMENT.md
│   └── prompt-engine/
│       ├── SYSTEM_PROMPTS.md
│       ├── USER_PROMPTS_GOL.md
│       ├── USER_PROMPTS_MATH.md
│       ├── USER_PROMPTS_LINDA.md
│       └── MIGRATION_GUIDE.md
├── research/                 # Research findings
│   ├── MODEL_CATALOG.md
│   ├── quantization/
│   │   ├── EXECUTIVE_SUMMARY.md
│   │   ├── DETAILED_REPORT.md
│   │   └── FULL_ANALYSIS.md
│   └── prompt-analysis/
│       ├── RESULTS_REPORT.md
│       ├── VISUALIZATIONS_GUIDE.md
│       └── FULL_ANALYSIS.md
├── images/                   # Charts and visualizations
│   ├── acemath_quantization/
│   └── original_gemma3_qwen3/
└── _archive/                 # Superseded documents
```

---

## Key Documents by Topic

| Topic | Primary Document |
|-------|------------------|
| System Architecture | [SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md) |
| 3-Stage Pipeline | [THREE_STAGE_PIPELINE.md](architecture/THREE_STAGE_PIPELINE.md) |
| Code Organization | [SOURCE_CODE_ORGANIZATION.md](implementation/SOURCE_CODE_ORGANIZATION.md) |
| Quantization Research | [EXECUTIVE_SUMMARY.md](research/quantization/EXECUTIVE_SUMMARY.md) |
| Prompt Engineering | [RESULTS_REPORT.md](research/prompt-analysis/RESULTS_REPORT.md) |
| System Prompts | [SYSTEM_PROMPTS.md](implementation/prompt-engine/SYSTEM_PROMPTS.md) |

---

## Benchmark Tasks

| Task | Description | User Prompts |
|------|-------------|--------------|
| **GoL** | Conway's Game of Life | [USER_PROMPTS_GOL.md](implementation/prompt-engine/USER_PROMPTS_GOL.md) |
| **ARI** | Arithmetic expressions | [USER_PROMPTS_MATH.md](implementation/prompt-engine/USER_PROMPTS_MATH.md) |
| **Linda** | Conjunction fallacy | [USER_PROMPTS_LINDA.md](implementation/prompt-engine/USER_PROMPTS_LINDA.md) |
| **C14** | Cellular automata | (Uses GoL prompts) |

---

## Key Research Findings

### Quantization Study
- **Q2_K (2-bit) beats F16** - 2-bit extreme quantization outperforms full precision by +6.18%
- 87.5% model compression with accuracy improvement

### Prompt Engineering
- **Prompt choice matters 4x more than quantization**
- 44+ percentage point swings from prompt engineering alone
- Match system prompt style to model personality:
  - Qwen = Adversarial
  - Gemma = Analytical
  - Llama = Balanced

---

## Quick Commands

```bash
# Run Game of Life benchmark
python -m src.benchmarks.gol_eval --model qwen3:0.6b --difficulty medium

# Run interactive TUI
python -m src.cli.benchmark_tui

# Run 3-stage pipeline
python src/stages/generate_testset.py configs/testsets/example.yaml
python src/stages/run_testset.py testsets/testset_*.json.gz --model qwen3:0.6b
python src/stages/analyze_results.py results/*.json.gz
```

---

## Related Resources

- [Main README](../README.md) - Project overview and quick start
- [CLAUDE.md](../CLAUDE.md) - AI agent instructions
- [CHANGELOG](../CHANGELOG.md) - Version history

---

**Version:** 2.0
**Last Updated:** January 2026
