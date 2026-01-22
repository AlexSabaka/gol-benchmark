# GoL Benchmark - Documentation Index

**Project Version:** 1.0.0  
**Last Updated:** November 16, 2025

---

## Quick Navigation

### 📖 Getting Started

1. **[README.md](../README.md)** - Project overview and quick start guide
2. **[PROJECT_DEVELOPMENT_SUMMARY.md](./PROJECT_DEVELOPMENT_SUMMARY.md)** - Complete project documentation
3. **[SOURCE_CODE_ORGANIZATION.md](./SOURCE_CODE_ORGANIZATION.md)** - New directory structure and imports

### 📝 Development & Changes

4. **[CHANGELOG.md](../CHANGELOG.md)** - Version history and release notes
5. **[DEVELOPMENT_LOG.md](./DEVELOPMENT_LOG.md)** - Phase 5 development details

### 🏗️ Architecture Documentation

6. **[BENCHMARK_TUI_PLAN.md](./BENCHMARK_TUI_PLAN.md)** - TUI system architecture
7. **[MODEL_PROVIDER_ARCHITECTURE.md](./MODEL_PROVIDER_ARCHITECTURE.md)** - Model provider system design
8. **[PROMPT_ANALYSIS_REPORT.md](./PROMPT_ANALYSIS_REPORT.md)** - Prompt system analysis

### 📊 Research & Analysis

9. **[ACEMATH_QUANTIZATION_REPORT.md](./ACEMATH_QUANTIZATION_REPORT.md)** - Quantization study results
10. **[EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md)** - High-level overview
11. **[MODEL_CATALOG.md](./MODEL_CATALOG.md)** - Available models reference

### 🔍 Additional Resources

- **[prompt_engine/](./prompt_engine/)** - PromptEngine documentation
- **[images/](./images/)** - Visualization files and charts

---

## Documentation by Purpose

### For Users

- **Want to run benchmarks?** → [README.md](../README.md) + [BENCHMARK_TUI_PLAN.md](./BENCHMARK_TUI_PLAN.md)
- **Need configuration options?** → [PROJECT_DEVELOPMENT_SUMMARY.md](./PROJECT_DEVELOPMENT_SUMMARY.md)
- **Looking for available models?** → [MODEL_CATALOG.md](./MODEL_CATALOG.md)

### For Developers

- **Understanding project structure?** → [SOURCE_CODE_ORGANIZATION.md](./SOURCE_CODE_ORGANIZATION.md)
- **Contributing new features?** → [DEVELOPMENT_LOG.md](./DEVELOPMENT_LOG.md)
- **Modifying model providers?** → [MODEL_PROVIDER_ARCHITECTURE.md](./MODEL_PROVIDER_ARCHITECTURE.md)
- **Working with prompts?** → [prompt_engine/](./prompt_engine/)

### For Researchers

- **Benchmark results?** → [ACEMATH_QUANTIZATION_REPORT.md](./ACEMATH_QUANTIZATION_REPORT.md)
- **Project overview?** → [EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md)
- **Complete analysis?** → [PROJECT_DEVELOPMENT_SUMMARY.md](./PROJECT_DEVELOPMENT_SUMMARY.md)

---

## Core Concepts

### 4 Benchmark Tasks

| Task | File | Purpose |
|------|------|---------|
| ARI | `ari_eval.py` | Arithmetic Expression Evaluation |
| GoL | `gol_eval.py` | Game of Life simulation |
| C14 | `c14_eval.py` | Cellular Automata testing |
| Linda | `linda_eval.py` | Conjunction Fallacy testing |

### 2 Model Providers

| Provider | File | Status |
|----------|------|--------|
| Ollama | `src/models/OllamaInterface.py` | Full support, 44+ models |
| HuggingFace | `src/models/HuggingFaceInterface.py` | Planned expansion |

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| TUI System | `benchmark_tui.py` | Interactive configuration and execution |
| Configuration | `benchmark_config.py` | Config management and persistence |
| Model Providers | `model_providers.py` | Provider abstraction and discovery |
| Prompt Engine | `src/core/PromptEngine.py` | Multi-language prompt generation |
| Test Evaluator | `src/core/TestEvaluator.py` | Result evaluation and aggregation |

---

## Recent Changes (Phase 5)

### ✅ Completed Work

1. **TUI Error Fixes** (7/7 fixed)
   - ValueError in checkbox defaults
   - Missing task selection
   - Generic parameters
   - Report formats crash
   - Target values input
   - Config fields
   - Main workflow completion

2. **Execution Model Improvements**
   - All models in single invocation
   - Prompt combination strategy
   - Result persistence
   - Chart generation

3. **Project Cleanup**
   - 12 temporary files removed (~2000 lines)
   - Documentation consolidated
   - CHANGELOG updated
   - Source code reorganized

See [DEVELOPMENT_LOG.md](./DEVELOPMENT_LOG.md) for details.

---

## File Organization

```
docs/
├── INDEX.md (this file)
├── PROJECT_DEVELOPMENT_SUMMARY.md  ← Start here for overview
├── DEVELOPMENT_LOG.md
├── SOURCE_CODE_ORGANIZATION.md
├── CHANGELOG.md (root)
├── BENCHMARK_TUI_PLAN.md
├── MODEL_PROVIDER_ARCHITECTURE.md
├── PROMPT_ANALYSIS_REPORT.md
├── ACEMATH_QUANTIZATION_REPORT.md
├── EXECUTIVE_SUMMARY.md
├── MODEL_CATALOG.md
├── VISUALIZATIONS_GUIDE.md
├── ACEMATH_QUANTIZATION_STUDY_SUMMARY.md
├── MODEL_SELECTION_IMPLEMENTATION.md
├── MODEL_SELECTION_ENHANCEMENT.md
├── prompt_engine/
│   ├── PROMPT_ENGINE_DESIGN.md
│   ├── PROMPT_ENGINE_SUMMARY.md
│   ├── PROMPT_ENGINE_INDEX.md
│   ├── MIGRATION_GUIDE.md
│   └── REFACTORING_SUMMARY.md
└── images/
    └── (visualizations)
```

---

## Common Tasks

### Run Benchmark

```bash
python benchmark_tui.py
```

### Direct Script Execution

```bash
python ari_eval.py --model qwen3:0.5b --difficulty 1 --batch-size 10
```

### View Results

```bash
ls results_run_auto_*/
cat results_run_auto_*/execution_summary_*.json
```

### Check Saved Configs

```bash
ls benchmark_configs/
```

---

## Version Information

- **Current Version:** 1.0.0
- **Release Date:** November 16, 2025
- **Python Version:** 3.8+
- **Status:** Production Ready

For version history, see [CHANGELOG.md](../CHANGELOG.md).

---

## Support & Resources

### Documentation References

- **Python Guide:** [SOURCE_CODE_ORGANIZATION.md](./SOURCE_CODE_ORGANIZATION.md)
- **Architecture:** [MODEL_PROVIDER_ARCHITECTURE.md](./MODEL_PROVIDER_ARCHITECTURE.md)
- **Prompts:** [prompt_engine/PROMPT_ENGINE_DESIGN.md](./prompt_engine/PROMPT_ENGINE_DESIGN.md)

### Quick Links

- Main README: [README.md](../README.md)
- Requirements: [requirements.txt](../requirements.txt)
- License: [LICENSE](../LICENSE)

---

## Key Statistics

| Metric | Value |
|--------|-------|
| Total Code | 5000+ lines |
| Benchmark Tasks | 4 |
| Model Providers | 2 |
| Supported Languages | 6 |
| Available Models (Ollama) | 44+ |
| Configuration Options | 100+ |
| Documentation Pages | 15+ |
| Test Coverage | High |

---

**Last Updated:** November 16, 2025  
**Maintained By:** GoL Benchmark Team
