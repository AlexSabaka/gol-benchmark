# GoL Benchmark Suite - Documentation# GoL Benchmark Suite - Documentation



**Project Version:** 1.0.0  **Project Version:** 1.0.0  

**Last Updated:** November 16, 2025  **Last Updated:** November 16, 2025  

**Status:** Production Ready**Status:** Production Ready



------



## Quick Start## 🚀 Quick Start



I want to:### I want to



- **Run benchmarks** → [Getting Started Guide](./00_GETTING_STARTED/)- **Run benchmarks** → [Getting Started Guide](./00_GETTING_STARTED/)

- **Configure tests** → [Configuration Guide](./02_USER_GUIDES/CONFIGURATION_GUIDE.md)- **Configure tests** → [Configuration Guide](./02_USER_GUIDES/CONFIGURATION_GUIDE.md)

- **Understand the system** → [System Architecture](./03_ARCHITECTURE/SYSTEM_OVERVIEW.md)- **Understand the system** → [System Architecture](./03_ARCHITECTURE/SYSTEM_OVERVIEW.md)

- **Check research findings** → [Research](#research)- **Check research findings** → [Research & Analysis](#research--analysis)

- **Contribute code** → [Implementation Details](./04_IMPLEMENTATION_DETAILS/)- **Contribute code** → [Implementation Details](./04_IMPLEMENTATION_DETAILS/)



------



## Documentation Structure## 📚 Documentation Structure



### Getting Started (00_GETTING_STARTED)### 🟢 **[00_GETTING_STARTED](./00_GETTING_STARTED/)**

**For first-time users**

For first-time users:- Quick Start Guide

- Quick Start Guide- Installation & Setup

- Installation & Setup- First Benchmark Run

- First Benchmark Run- Troubleshooting

- Troubleshooting

### 🟡 **[02_USER_GUIDES](./02_USER_GUIDES/)**

### User Guides (02_USER_GUIDES)**For regular users**

- Running Benchmarks

For regular users:- Configuration Options

- Running Benchmarks- Interpreting Results

- Configuration Options- Advanced Usage

- Interpreting Results

- Advanced Usage### 🔵 **[03_ARCHITECTURE](./03_ARCHITECTURE/)**

**For developers & architects**

### Architecture (03_ARCHITECTURE)- **[SYSTEM_OVERVIEW.md](./03_ARCHITECTURE/SYSTEM_OVERVIEW.md)** — Complete project architecture

- **[MODEL_PROVIDERS.md](./03_ARCHITECTURE/MODEL_PROVIDERS.md)** — Model provider system

For developers & architects:- **[BENCHMARK_TASKS.md](./03_ARCHITECTURE/BENCHMARK_TASKS.md)** — The 4 benchmark tasks (ARI, GoL, C14, Linda)

- **[PROMPT_ENGINE.md](./03_ARCHITECTURE/PROMPT_ENGINE.md)** — Prompt engineering system

- **SYSTEM_OVERVIEW.md** — Complete project architecture

- **MODEL_PROVIDERS.md** — Model provider system### 🟠 **[04_IMPLEMENTATION_DETAILS](./04_IMPLEMENTATION_DETAILS/)**

- **BENCHMARK_TASKS.md** — The 4 benchmark tasks (ARI, GoL, C14, Linda)**For developers implementing features**

- **PROMPT_ENGINE.md** — Prompt engineering system- **[TUI_SYSTEM.md](./04_IMPLEMENTATION_DETAILS/TUI_SYSTEM.md)** — Interactive TUI architecture

- **[SOURCE_CODE_ORGANIZATION.md](./04_IMPLEMENTATION_DETAILS/SOURCE_CODE_ORGANIZATION.md)** — Directory structure & modules

### Implementation Details (04_IMPLEMENTATION_DETAILS)- **[DEVELOPMENT_WORKFLOW.md](./04_IMPLEMENTATION_DETAILS/DEVELOPMENT_WORKFLOW.md)** — Contributing guidelines



For developers implementing features:### 🟣 **[05_RESEARCH](./05_RESEARCH/)**

**For researchers & analysts**

- **TUI_SYSTEM.md** — Interactive TUI architecture

- **SOURCE_CODE_ORGANIZATION.md** — Directory structure & modules#### Quantization Study

- **DEVELOPMENT_WORKFLOW.md** — Contributing guidelines- **[EXECUTIVE_SUMMARY.md](./05_RESEARCH/QUANTIZATION_STUDY/EXECUTIVE_SUMMARY.md)** — Key findings at a glance

- **[DETAILED_REPORT.md](./05_RESEARCH/QUANTIZATION_STUDY/DETAILED_REPORT.md)** — Complete analysis of 4 quantization formats

### Research (05_RESEARCH)

#### Prompt Analysis

For researchers & analysts:- **[RESULTS_REPORT.md](./05_RESEARCH/PROMPT_ANALYSIS/RESULTS_REPORT.md)** — Comprehensive prompt engineering study

- **[VISUALIZATIONS_GUIDE.md](./05_RESEARCH/PROMPT_ANALYSIS/VISUALIZATIONS_GUIDE.md)** — Chart explanations & insights

#### Quantization Study

#### Model Reference

- **EXECUTIVE_SUMMARY.md** — Key findings at a glance- **[CATALOG.md](./05_RESEARCH/MODEL_FAMILIES/CATALOG.md)** — Complete model availability reference

- **DETAILED_REPORT.md** — Complete analysis of 4 quantization formats

### 🟤 **[06_REFERENCE](./06_REFERENCE/)**

#### Prompt Analysis**Reference materials**

- CHANGELOG (from root)

- **RESULTS_REPORT.md** — Comprehensive prompt engineering study- Version history

- **VISUALIZATIONS_GUIDE.md** — Chart explanations & insights- API Reference



#### Model Reference### 📦 **[_archive](./\_archive/)**

**Legacy & superseded documents**

- **CATALOG.md** — Complete model availability reference- Old model selection docs

- Generation scripts

### Reference (06_REFERENCE)- Archived implementation notes



Reference materials:---



- CHANGELOG (from root)## 🎯 Key Concepts

- Version history

- API Reference### 4 Benchmark Tasks



### Archive (_archive)| Task | Purpose | File |

|------|---------|------|

Legacy & superseded documents:| **ARI** | Arithmetic Expression Evaluation | `ari_eval.py` |

| **GoL** | Game of Life Simulation | `gol_eval.py` |

- Old model selection docs| **C14** | Cellular Automata Pattern Recognition | `c14_eval.py` |

- Generation scripts| **Linda** | Conjunction Fallacy Problem | `linda_eval.py` |

- Archived implementation notes

### 2 Model Providers

---

| Provider | Status | Models |

## Key Concepts|----------|--------|--------|

| **Ollama** | ✅ Full Support | 44+ available |

### 4 Benchmark Tasks| **HuggingFace** | 🔄 Planned | Expanding |



| Task | Purpose | File |### Core Components

|------|---------|------|

| ARI | Arithmetic Expression Evaluation | `ari_eval.py` || Component | Location | Purpose |

| GoL | Game of Life Simulation | `gol_eval.py` ||-----------|----------|---------|

| C14 | Cellular Automata Pattern Recognition | `c14_eval.py` || **TUI System** | `benchmark_tui.py` | Interactive configuration & execution |

| Linda | Conjunction Fallacy Problem | `linda_eval.py` || **Config Manager** | `benchmark_config.py` | Persistent configuration storage |

| **Model Abstraction** | `model_providers.py` | Unified provider interface |

### 2 Model Providers| **Prompt Engine** | `src/core/PromptEngine.py` | Multi-language prompt generation |

| **Test Evaluator** | `src/core/TestEvaluator.py` | Result evaluation & aggregation |

| Provider | Status | Models |

|----------|--------|--------|---

| Ollama | ✅ Full Support | 44+ available |

| HuggingFace | 🔄 Planned | Expanding |## 📊 Research & Analysis



### Core Components### ✨ Recent Major Studies



| Component | Location | Purpose |#### AceMath-1.5B Quantization Analysis

|-----------|----------|---------|**Finding:** 2-bit quantization (Q2_K) surprisingly outperforms full precision!

| TUI System | `benchmark_tui.py` | Interactive configuration & execution |

| Config Manager | `benchmark_config.py` | Persistent configuration storage |- **Q2_K (2-bit):** 37.76% ± 7.21% ✅ **Best**

| Model Abstraction | `model_providers.py` | Unified provider interface |- **Q4_K_M (4-bit):** 33.23% ± 6.06%

| Prompt Engine | `src/core/PromptEngine.py` | Multi-language prompt generation |- **F16 (baseline):** 31.58% ± 4.31%

| Test Evaluator | `src/core/TestEvaluator.py` | Result evaluation & aggregation |- **Q8_0 (8-bit):** 31.17% ± 4.12%



---**Impact:** 87.5% compression with +6.18% accuracy boost  

📖 [Full Report →](./05_RESEARCH/QUANTIZATION_STUDY/)

## Research

#### Prompt Engineering Study

### AceMath-1.5B Quantization Analysis**Finding:** Prompt choice has 4× more impact than quantization choice



**Finding:** 2-bit quantization (Q2_K) surprisingly outperforms full precision!- **Best config:** 50.00% accuracy

- **Worst config:** 24.07% accuracy

- Q2_K (2-bit): 37.76% ± 7.21% ✅ **Best**- **System prompt dominance:** 7.2 percentage point impact

- Q4_K_M (4-bit): 33.23% ± 6.06%- **Test coverage:** 9 prompt configurations × 2 models × 108 tests = 1,944 evaluations

- F16 (baseline): 31.58% ± 4.31%

- Q8_0 (8-bit): 31.17% ± 4.12%📖 [Full Report →](./05_RESEARCH/PROMPT_ANALYSIS/)



**Impact:** 87.5% compression with +6.18% accuracy boost---



[Full Report →](./05_RESEARCH/QUANTIZATION_STUDY/)## 🛠️ Common Tasks



### Prompt Engineering Study### Run Interactive TUI

```bash

**Finding:** Prompt choice has 4× more impact than quantization choicepython benchmark_tui.py

```

- Best config: 50.00% accuracy

- Worst config: 24.07% accuracy### Run Direct Benchmark

- System prompt dominance: 7.2 percentage point impact```bash

- Test coverage: 9 prompt configurations × 2 models × 108 tests = 1,944 evaluationspython ari_eval.py --model qwen3:0.5b --difficulty 1 --batch-size 10

```

[Full Report →](./05_RESEARCH/PROMPT_ANALYSIS/)

### View Results

---```bash

ls results_run_auto_*/

## Common Taskscat results_run_auto_*/execution_summary_*.json

```

### Run Interactive TUI

### Check Configuration History

```bash```bash

python benchmark_tui.pyls benchmark_configs/

``````



### Run Direct Benchmark---



```bash## 📋 System Requirements

python ari_eval.py --model qwen3:0.5b --difficulty 1 --batch-size 10

```- **Python:** 3.8+

- **Dependencies:** See [requirements.txt](../requirements.txt)

### View Results- **Ollama:** Required for Ollama provider (optional if using HuggingFace)



```bash---

ls results_run_auto_*/

cat results_run_auto_*/execution_summary_*.json## 📞 Support & Resources

```

### Quick Links

### Check Configuration History- **Main Project:** [README.md](../README.md)

- **Requirements:** [requirements.txt](../requirements.txt)

```bash- **License:** [LICENSE](../LICENSE)

ls benchmark_configs/- **CHANGELOG:** [CHANGELOG.md](../CHANGELOG.md)

```

### Documentation Sections

---1. **Getting Started** - Installation & first run

2. **User Guides** - Configuration & execution

## System Requirements3. **Architecture** - System design

4. **Implementation** - Code & development

- **Python:** 3.8+5. **Research** - Studies & analysis

- **Dependencies:** See requirements.txt6. **Reference** - Changelogs & API docs

- **Ollama:** Required for Ollama provider (optional if using HuggingFace)

---

---

## 🗂️ Full Directory Structure

## Support & Resources

```

### Quick Linksdocs/

├── 00_README.md (this file)

- **Main Project:** README.md│

- **Requirements:** requirements.txt├── 00_GETTING_STARTED/

- **License:** LICENSE│   ├── QUICKSTART.md

- **CHANGELOG:** CHANGELOG.md│   ├── INSTALLATION.md

│   └── FIRST_RUN.md

### Documentation Sections│

├── 02_USER_GUIDES/

1. Getting Started - Installation & first run│   ├── RUNNING_BENCHMARKS.md

2. User Guides - Configuration & execution│   ├── CONFIGURATION_GUIDE.md

3. Architecture - System design│   └── INTERPRETING_RESULTS.md

4. Implementation - Code & development│

5. Research - Studies & analysis├── 03_ARCHITECTURE/

6. Reference - Changelogs & API docs│   ├── SYSTEM_OVERVIEW.md

│   ├── MODEL_PROVIDERS.md

---│   ├── BENCHMARK_TASKS.md

│   └── PROMPT_ENGINE.md

## Full Directory Structure│

├── 04_IMPLEMENTATION_DETAILS/

```│   ├── TUI_SYSTEM.md

docs/│   ├── SOURCE_CODE_ORGANIZATION.md

├── 00_README.md (this file)│   └── DEVELOPMENT_WORKFLOW.md

││

├── 00_GETTING_STARTED/├── 05_RESEARCH/

│   ├── QUICKSTART.md│   ├── QUANTIZATION_STUDY/

│   ├── INSTALLATION.md│   │   ├── EXECUTIVE_SUMMARY.md

│   └── FIRST_RUN.md│   │   └── DETAILED_REPORT.md

││   ├── PROMPT_ANALYSIS/

├── 02_USER_GUIDES/│   │   ├── RESULTS_REPORT.md

│   ├── RUNNING_BENCHMARKS.md│   │   └── VISUALIZATIONS_GUIDE.md

│   ├── CONFIGURATION_GUIDE.md│   └── MODEL_FAMILIES/

│   └── INTERPRETING_RESULTS.md│       └── CATALOG.md

││

├── 03_ARCHITECTURE/├── 06_REFERENCE/

│   ├── SYSTEM_OVERVIEW.md│   ├── CHANGELOG.md → (links to root)

│   ├── MODEL_PROVIDERS.md│   └── API_REFERENCE.md

│   ├── BENCHMARK_TASKS.md│

│   └── PROMPT_ENGINE.md├── prompt_engine/

││   ├── PROMPT_ENGINE_DESIGN.md

├── 04_IMPLEMENTATION_DETAILS/│   ├── PROMPT_ENGINE_SUMMARY.md

│   ├── TUI_SYSTEM.md│   └── ...

│   ├── SOURCE_CODE_ORGANIZATION.md│

│   └── DEVELOPMENT_WORKFLOW.md├── images/

││   ├── quantization_study/

├── 05_RESEARCH/│   └── prompt_analysis/

│   ├── QUANTIZATION_STUDY/│

│   │   ├── EXECUTIVE_SUMMARY.md├── _archive/

│   │   └── DETAILED_REPORT.md│   └── (legacy & superseded documents)

│   ├── PROMPT_ANALYSIS/│

│   │   ├── RESULTS_REPORT.md└── INDEX.md (deprecated - use 00_README.md instead)

│   │   └── VISUALIZATIONS_GUIDE.md```

│   └── MODEL_FAMILIES/

│       └── CATALOG.md---

│

├── 06_REFERENCE/## 🎓 Learning Path

│   ├── CHANGELOG.md

│   └── API_REFERENCE.md### For End Users

│1. [QUICKSTART.md](./00_GETTING_STARTED/QUICKSTART.md) — 5 min read

├── prompt_engine/2. [RUNNING_BENCHMARKS.md](./02_USER_GUIDES/RUNNING_BENCHMARKS.md) — Your first test

│   ├── PROMPT_ENGINE_DESIGN.md3. [CONFIGURATION_GUIDE.md](./02_USER_GUIDES/CONFIGURATION_GUIDE.md) — Customize & optimize

│   ├── PROMPT_ENGINE_SUMMARY.md

│   └── ...### For Developers

│1. [SYSTEM_OVERVIEW.md](./03_ARCHITECTURE/SYSTEM_OVERVIEW.md) — Understand architecture

├── images/2. [SOURCE_CODE_ORGANIZATION.md](./04_IMPLEMENTATION_DETAILS/SOURCE_CODE_ORGANIZATION.md) — Navigate codebase

│   ├── quantization_study/3. [TUI_SYSTEM.md](./04_IMPLEMENTATION_DETAILS/TUI_SYSTEM.md) — Deep dive on TUI

│   └── prompt_analysis/4. [DEVELOPMENT_WORKFLOW.md](./04_IMPLEMENTATION_DETAILS/DEVELOPMENT_WORKFLOW.md) — Start contributing

│

├── _archive/### For Researchers

│   └── (legacy & superseded documents)1. [EXECUTIVE_SUMMARY.md](./05_RESEARCH/QUANTIZATION_STUDY/EXECUTIVE_SUMMARY.md) — Key findings (quantization)

│2. [RESULTS_REPORT.md](./05_RESEARCH/PROMPT_ANALYSIS/RESULTS_REPORT.md) — Prompt engineering insights

└── INDEX.md (deprecated - use 00_README.md instead)3. [DETAILED_REPORT.md](./05_RESEARCH/QUANTIZATION_STUDY/DETAILED_REPORT.md) — Full quantization analysis

```4. [VISUALIZATIONS_GUIDE.md](./05_RESEARCH/PROMPT_ANALYSIS/VISUALIZATIONS_GUIDE.md) — Chart interpretations



------



## Learning Path## ✅ Version Info



### For End Users- **Current Version:** 1.0.0

- **Release Date:** November 16, 2025

1. QUICKSTART.md — 5 min read- **Status:** Production Ready

2. RUNNING_BENCHMARKS.md — Your first test- **Python Support:** 3.8+

3. CONFIGURATION_GUIDE.md — Customize & optimize

For detailed version history, see [../CHANGELOG.md](../CHANGELOG.md)

### For Developers

---

1. SYSTEM_OVERVIEW.md — Understand architecture

2. SOURCE_CODE_ORGANIZATION.md — Navigate codebase**Last Updated:** November 16, 2025  

3. TUI_SYSTEM.md — Deep dive on TUI**Maintained By:** GoL Benchmark Team  

4. DEVELOPMENT_WORKFLOW.md — Start contributing**Repository:** [gol-benchmark](https://github.com/AlexSabaka/gol-benchmark)


### For Researchers

1. EXECUTIVE_SUMMARY.md — Key findings (quantization)
2. RESULTS_REPORT.md — Prompt engineering insights
3. DETAILED_REPORT.md — Full quantization analysis
4. VISUALIZATIONS_GUIDE.md — Chart interpretations

---

## Version Info

- **Current Version:** 1.0.0
- **Release Date:** November 16, 2025
- **Status:** Production Ready
- **Python Support:** 3.8+

For detailed version history, see CHANGELOG.md

---

**Last Updated:** November 16, 2025  
**Maintained By:** GoL Benchmark Team  
**Repository:** [gol-benchmark](https://github.com/AlexSabaka/gol-benchmark)
