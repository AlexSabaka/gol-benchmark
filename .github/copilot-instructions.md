# GoL Benchmark - Copilot Instructions

## Project Overview

This is a comprehensive LLM reasoning benchmark suite testing model capabilities across 19 procedural tasks (Game of Life, arithmetic expressions, Linda fallacy, cellular automata, ASCII shapes, object tracking, Sally-Anne, Carwash Paradox, Inverted Cup, Strawberry, Measure Comparison, Grid Tasks, Time Arithmetic, Misquote Attribution, False Premise, Family Relations, Encoding & Cipher Decoding, Symbol Arithmetic, Picross/Nonogram). The system features a modern 3-stage architecture with a **plugin-based benchmark system**, support for multiple model providers (Ollama local & remote, HuggingFace), multilingual prompts (EN/ES/FR/DE/ZH/UA), configurable prompt styles, and advanced analytics.

## Architecture (v2.17.0)

### 🔌 **Plugin-Based Benchmark System**
All benchmarks are now self-contained plugins with auto-discovery:
```
src/plugins/
├── base.py                    # Abstract base classes
├── __init__.py                # Plugin registry
├── game_of_life/              # GoL: generator, parser, evaluator
├── arithmetic/                # ARI: 6-strategy parsing
├── linda_fallacy/             # Linda: conjunction fallacy detection
├── cellular_automata_1d/      # C14: state evolution
├── ascii_shapes/              # Shapes: dimensions/count/position
├── object_tracking/           # Object Tracking: grape test
├── sally_anne/                # Sally-Anne: false belief reasoning
├── carwash/                   # Carwash Paradox: goal-tracking test
├── inverted_cup/              # Inverted Cup: spatial orientation test
├── strawberry/                # Strawberry: character-level reasoning (6 sub-types)
├── measure_comparison/        # Measure Comparison: quantity comparison with units + decimal framing
├── grid_tasks/                # Grid Tasks: table reasoning
├── time_arithmetic/           # Time Arithmetic: temporal reasoning & impossible dates
├── misquote/                  # Misquote Attribution: sycophancy detection
├── false_premise/             # False Premise: dangerous/impossible premise detection
├── family_relations/          # Family Relations: perspective-aware counting puzzles
├── encoding_cipher/           # Encoding & Cipher Decoding: Base64, Caesar, Morse
├── symbol_arithmetic/         # Symbol Arithmetic: custom operation tables
└── picross/                   # Picross (Nonogram): grid puzzle solving
```

**Benefits:**
- ✅ Add new benchmarks without modifying core code
- ✅ Self-contained modules (generation + parsing + evaluation)
- ✅ Automatic plugin discovery
- ✅ Clean separation of concerns

### 🏗️ **3-Stage Pipeline Architecture**
```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  1. GENERATE     │────▶│  2. EXECUTE      │────▶│  3. ANALYZE      │
│  Test Sets       │     │  On Models       │     │  Results         │
└──────────────────┘     └──────────────────┘     └──────────────────┘
   YAML configs            test_sets.json.gz       results.json.gz
   Deterministic           Portable execution      Rich analytics
   testset_xyz.json.gz     results_model_xyz...    reports/charts
```

**Key Benefits:**
- ✅ Generate test sets once, run on many models
- ✅ Portable test runner (cloud VMs, different machines)
- ✅ Offline analysis (no model dependencies)
- ✅ Reproducible (same test set = identical conditions)
- ✅ Version control test sets (git track configs + test sets)

### Core Data Flow (Modern)
```
Web UI/CLI → Stage 1 (generate_testset.py) → Stage 2 (run_testset.py) → Stage 3 (analyze_results.py)
  ↓            ↓                           ↓                         ↓
Config →   Plugin generators →        ModelInterface →        Enhanced Analytics
        (plugin-local prompts.py     (Ollama/HuggingFace)    Multi-dimensional Reports
         + base class helpers)
```

## Project Structure (v2.17.0)

### **Core Architecture (`src/` organization)**

```
src/
├── plugins/            # 🔌 Plugin-Based Benchmark System (v2.2.0)
│   ├── base.py         # Abstract base classes (BenchmarkPlugin, TestCaseGenerator, etc.)
│   │                  # + prompt helpers: _build_prompts(), _get_system_prompt(), _format_user_prompt()
│   ├── __init__.py     # Plugin registry with auto-discovery
│   ├── game_of_life/   # GoL plugin (generator.py, parser.py, evaluator.py, prompts.py, __init__.py)
│   ├── arithmetic/     # ARI plugin (6-strategy parsing)
│   ├── linda_fallacy/  # Linda plugin (conjunction fallacy detection)
│   ├── cellular_automata_1d/  # C14 plugin (state evolution)
│   ├── ascii_shapes/   # Shapes plugin (dimensions/count/position)
│   ├── object_tracking/ # Object Tracking plugin (grape test)
│   ├── sally_anne/     # Sally-Anne plugin (false belief)
│   ├── carwash/        # Carwash Paradox plugin (goal-tracking test)
│   ├── inverted_cup/   # Inverted Cup plugin (spatial orientation test)
│   ├── strawberry/     # Strawberry plugin (character-level reasoning, 6 sub-types)
│   ├── measure_comparison/ # Measure Comparison plugin (incl. decimal framing)
│   ├── grid_tasks/     # Grid Tasks plugin (table reasoning)
│   ├── time_arithmetic/ # Time Arithmetic plugin (temporal reasoning)
│   ├── misquote/       # Misquote Attribution plugin (sycophancy detection)
│   ├── false_premise/  # False Premise plugin (dangerous/impossible premise detection)
│   ├── family_relations/ # Family Relations plugin (perspective-aware counting)
│   ├── encoding_cipher/ # Encoding & Cipher Decoding plugin (Base64, Caesar, Morse)
│   ├── symbol_arithmetic/ # Symbol Arithmetic plugin (custom operation tables)
│   └── picross/        # Picross (Nonogram) plugin (grid puzzle solving)
├── stages/             # 3-Stage Pipeline Scripts (uses plugins)
│   ├── generate_testset.py    # Stage 1: YAML → Test Sets (plugin dispatch)
│   ├── run_testset.py         # Stage 2: Execute on Models (plugin parsers)
│   └── analyze_results.py     # Stage 3: Analytics & Reports
├── core/               # Core types, prompt engine, test generation
│   ├── types.py        # Config dataclasses (BaseTestConfig, GameOfLifeTestConfig, etc.)
│   ├── PromptEngine.py # System prompts + enums (user templates DEPRECATED → plugin-local prompts.py)
│   ├── TestGenerator.py# Test case generation with pattern support
│   └── PROMPT_STYLES.py# Prompt style definitions
├── models/             # Model provider interfaces
│   ├── BaseModelInterface.py  # ModelInterface base class
│   ├── OllamaInterface.py     # Ollama (urllib-based, no ollama package needed)
│   ├── HuggingFaceInterface.py# HuggingFace Transformers (CUDA/MPS/CPU)
│   └── OpenAICompatibleInterface.py # OpenAI-compatible API (Groq, OpenRouter, vLLM, etc.)
├── engine/             # Task-specific engines
│   ├── GameOfLifeEngine.py    # Conway's Game of Life rules
│   └── MathExpressionGenerator.py # Arithmetic expression generation
├── evaluation/         # Result evaluation
│   └── TestEvaluator.py# Grid comparison, accuracy calculations
├── benchmarks/         # ⚠️ DEPRECATED: Legacy monolithic scripts
│   ├── ari_eval.py     # Arithmetic evaluation (use plugins instead)
│   └── gol_eval.py     # Game of Life evaluation (use plugins instead)
└── utils/              # Utilities
    └── logger.py       # Logging utilities
```

### **Project Root Organization**
```
gol_eval/
├── src/                # All source code
├── frontend/           # React SPA (Vite 6 + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui)
├── tests/              # Test suites and validation scripts
├── docs/               # Comprehensive documentation
├── testsets/           # Generated test sets (.json.gz)
├── results*/           # Benchmark execution results
├── configs/            # YAML configuration files
└── [clean root]        # No temporary files
```

**Backward Compatibility:** Legacy imports like `from src.types import ...` still work via module aliasing in `src/__init__.py`

## Running Benchmarks (v2.0.0)

### 🎮 **Web UI (Recommended)**
```bash
# Start the backend + frontend
python -m src.web
# Open http://127.0.0.1:8000/

# Frontend development (hot-reload)
cd frontend && npm run dev       # http://localhost:5173/ (proxies /api → :8000)

# Supports:
# - All 19 benchmark plugins with dynamic config forms
# - Model selection with provider detection
# - Multi-language selection with flag emojis
# - Prompt style matrix configuration (3×3 combinations)
# - Automatic 3-stage execution with real-time progress
# - Result analysis and HTML report generation
```

### 🛠️ **Manual 3-Stage Execution**
```bash
# Stage 1: Generate test set from YAML config
python src/stages/generate_testset.py configs/testsets/multi_task_baseline.yaml

# Stage 2: Execute on models (portable, minimal dependencies)
python src/stages/run_testset.py testsets/testset_multi_task_v1.json.gz \
    --model qwen3:0.6b --provider ollama --output-dir results/

python src/stages/run_testset.py testsets/testset_multi_task_v1.json.gz \
    --model gemma3:1b --provider ollama --output-dir results/

# Stage 3: Analyze and generate reports
python src/stages/analyze_results.py results/results_*.json.gz \
    --output reports/comparison_report.md --visualize --output-dir reports/charts/
```

### 📊 **Legacy Individual Benchmarks (Still Supported)**
```bash
# Game of Life benchmark
python src/benchmarks/gol_eval.py --model qwen3:0.6b gemma3:1b --difficulty medium --batch-size 20

# Arithmetic expressions  
python src/benchmarks/ari_eval.py --model qwen3:0.6b --difficulty 3 --batch-size 10
```

**Key CLI patterns:**
- `--model` accepts multiple models (space-separated)
- `--no-think` disables chain-of-thought for models that support it
- `--seed` ensures reproducible test generation
- Results auto-save to timestamped directories with comprehensive metadata

## Configuration Patterns

### **Multi-Task YAML Configs (New)**
```yaml
# configs/testsets/multi_task_baseline.yaml
metadata:
  name: "multi_task_baseline_v1"
  description: "Arithmetic + Game of Life combined test"
  
tasks:
  - type: "arithmetic"
    generation:
      seed: 42
      difficulties: [2, 3]
      expressions_per_difficulty: 10
    prompt_configs:
      - name: "minimal_analytical"
        user_style: "minimal"
        system_style: "analytical"
        
  - type: "game_of_life" 
    generation:
      seed: 42
      difficulty_levels: ["EASY", "MEDIUM"]
      grids_per_difficulty: 5
      density: 0.3
    prompt_configs:
      - name: "casual_casual"
        user_style: "casual"
        system_style: "casual"

sampling:
  temperature: 0.1
  max_tokens: 512
  
execution:
  no_thinking: true
  cell_markers: ["1", "0"]  # Numeric recommended; emoji now supported (v2.10.1)
```

### **Config Dataclasses (in `src/core/types.py`)**
All test configs inherit from `BaseTestConfig`. Task-specific configs add their own fields:

```python
# Base fields available to all tasks
models, batch_size, temperature, ctx_len, num_predict, prompt_language, prompt_style, system_prompt_style

# Multi-task specific (MultiTaskTestConfig)
tasks: List[TaskConfig], global_params, execution_hints

# GoL-specific (GameOfLifeTestConfig)  
difficulty: DifficultyLevel, density, known_patterns_ratio, live_dead_cell_markers

# Ari-specific (AriTestConfig)
difficulties: List[int], mode: "expression"|"equation", variables
```

### **Prompt Style Matrix**
The benchmark systematically tests 3×3 prompt combinations:
- **User styles**: `minimal`, `casual`, `linguistic` (in `PromptStyle` enum)
- **System styles**: `analytical`, `casual`, `adversarial` (in `SystemPromptStyle` enum)

## Code Conventions

### **Adding New Benchmark Tasks (Plugin System v2.8.0)**
**Modern approach - create a self-contained plugin:**

1. **Create plugin directory**: `src/plugins/new_task/`
2. **Create `__init__.py`**: Define `NewTaskPlugin` class and export `plugin` instance
3. **Create `prompts.py`**: Define user prompt templates keyed by `(Language, style_string)`
4. **Create `generator.py`**: Implement `TestCaseGenerator` using `self._build_prompts()` helper
5. **Create `parser.py`**: Implement `ResponseParser` with multi-strategy `parse()` method
6. **Create `evaluator.py`**: Implement `ResultEvaluator` with `evaluate()` method
7. **Done!** Plugin auto-discovered by registry, integrated into all 3 stages. No changes to `PromptEngine.py`.

**Legacy approach (deprecated):**
- Adding to `src/benchmarks/` requires manual integration
- Code duplication across generation/parsing/evaluation
- No longer recommended

### **Enhanced Response Parsing (v2.0.0)**
Model responses use multi-strategy parsing with fallback mechanisms:

**Arithmetic**: 6-strategy approach with LaTeX `\boxed{}` pattern support, JSON unescaping, keyword detection
**Game of Life**: 4-strategy grid parsing with flexible formatting, marker normalization, rectangular pattern detection

```python
# Enhanced parsing integrated in run_testset.py
parsed_answer = parse_answer(response, task_type)  # Multi-strategy parsing
evaluation = evaluate_result(parsed_answer, expected_answer, task_type)
```

### **Model Interface Pattern** 
```python
# Use the factory function
from src.models import create_model_interface

interface = create_model_interface("ollama", "qwen3:0.6b", ollama_host="http://localhost:11434")
result = interface.query(prompt, {"temperature": 0.1, "max_tokens": 2048, "system_prompt": "..."})
# result = {"response": "...", "tokens_generated": 42, "duration": 1.2, "model_info": {...}}

# Or import directly
from src.models import OllamaInterface, HuggingFaceInterface, OpenAICompatibleInterface
```

## Testing & Validation

### **Test Suite Organization**
```bash
# Comprehensive test suite in tests/ folder
pytest tests/                                   # All tests
python tests/test_enhanced_reports_demo.py      # Analytics validation
```

Tests validate 3-stage pipeline, config serialization, parsing enhancements, and component integration.

## External Dependencies & Setup

### **Required Services**
- **Ollama** must be running (`ollama serve`) for local model testing
- **Models**: Pull required models (`ollama pull qwen3:0.6b gemma3:1b`)

### **Optional Dependencies**
- **HuggingFace**: Install `transformers` and `torch` for HuggingFace provider
- **Visualization**: `matplotlib`, `seaborn` for enhanced charts (auto-installed)

### **Data Files**
- Plugin data files co-located in `src/plugins/<task>/data/` (e.g., Conway's Life patterns in `src/plugins/game_of_life/data/known_patterns/`, strawberry word lists in `src/plugins/strawberry/data/`)
- Results and visualizations output to `results*/` and `docs/images/`

## Critical Fixes & Known Issues (v2.2.0)

### ✅ **Major Fixes Implemented**
1. **Game of Life Template Bug**: Fixed `{grid_str}` placeholder not being substituted (was causing 0% accuracy)
2. **Multi-Task Parsing**: Enhanced parsing with 6-strategy fallback for arithmetic, 4-strategy for GoL  
3. **Task Type Detection**: Fixed multi-task execution routing issues
4. **Report Generation**: Harmonized HTML/Markdown reports with embedded visualizations
5. **"Unknown" task type in reports (2026-02-21)**: Fixed `extract_task_breakdown()` in `analyze_results.py` — added `carwash` and `inverted_cup` recognition patterns
8. **Remote Ollama support (2026-02-21)**: `OllamaProvider` now accepts a `host` parameter; non-default hosts use REST API for discovery and availability checks
9. **prompt_metadata propagation (2026-04-08)**: `run_testset.py` and `src/web/jobs.py` now merge `prompt_metadata` (language, user_style, system_style) into `task_params` before calling plugin parsers/evaluators — fixes multilingual parsing in both CLI and Web UI
10. **Measure Comparison localized units (2026-04-08)**: Imperial/customary unit display names localized for ZH/UA/DE/FR/ES; decimal framing templates for all 6 languages
11. **Filename truncation (2026-04-08)**: `path_manager.py` truncates long testset filenames (task list >120 chars → `N_tasks`, total filename capped at 240 chars)

### ⚠️ **Known Limitations**
- **Emoji cell markers** (`🟩/🟥`) now work correctly for GoL (v2.10.1) and C14 (v2.10.2), but models still perform best with `1/0` markers  
- **Thinking mode** can hurt structured output accuracy—use `--no-think` for best results
- **Quantized models** (Q2_K) sometimes outperform full precision (counterintuitive but documented)
- **Cloud model timeouts**: Some cloud providers have longer response times

### 🎯 **Performance Expectations (Post-Fix)**
- **Arithmetic Tasks**: 60-90% accuracy with enhanced parsing
- **Game of Life**: 40-70% accuracy (dramatically improved from 0% after grid_str fix)
- **Cellular Automata 1D**: Expected 50-80% accuracy (Stage 1 complete, Stage 2 pending)
- **Carwash Paradox**: Expected 40-80% accuracy (v2.10.4 expanded conditional/dismissive walk filtering fixes most false negatives; remaining failures are genuine model errors)
- **Inverted Cup**: Expected 60-90% accuracy (the flip answer is usually obvious)
- **Time Arithmetic**: Expected 50-80% accuracy (noon/midnight traps and impossible dates are the hardest)
- **Misquote Attribution**: Expected 40-70% accuracy (authority/constraint framings are the hardest sycophancy traps)
- **Family Relations**: Expected 40-70% accuracy (self-counting traps are the classic failure mode)
- **False Premise**: Expected 60-90% accuracy; v2.10.7 fixed 61 false negatives (smart quote normalization, negation-aware compliance detection, safe-alternative section filtering, first-sentence refusal strategy, expanded refusal/impossibility patterns)
- **Measure Comparison (decimal)**: Expected 40-80% accuracy; framing sensitivity rate reveals how often models change answers based on framing context. v2.10.5 fixed 38 false negatives (smart quote normalization, tightened equal keywords, pipeline reorder, expanded incomparable patterns)
- **Encoding & Cipher Decoding**: Expected 50-80% accuracy (Base64 easiest, Morse hardest; hallucinated execution is the interesting failure mode)
- **Symbol Arithmetic**: Expected 40-70% accuracy (commutativity/associativity assumptions are the classic failure modes; partial tables and emoji symbols are hardest)
- **Picross (Nonogram)**: Expected 30-70% accuracy (trivial 3×3 puzzles near-solvable, hard 10×10 requires sustained deductive reasoning; grid_header format helps spatial grounding; line-solvable constraint ensures fair puzzles)
- **Multi-Task Combined**: 50-80% overall accuracy depending on model capability
- **Parse Error Rate**: <20% with enhanced multi-strategy parsing (down from 100% in some cases)

## Quick Start Guide

### **Option 1: Web UI (Easiest)**
```bash
# Start the backend + frontend
python -m src.web
# Open http://127.0.0.1:8000/

# The React SPA supports:
# 1. All 19 benchmark plugins with dynamic config forms
# 2. Model selection with provider detection
# 3. Multi-language selection with flag emojis
# 4. Prompt style matrix (3×3 combinations)
# 5. Real-time progress during execution
# 6. HTML report generation and viewing
```

### **Option 2: Quick Manual Test**
```bash
# Generate a small test set
echo "metadata: {name: 'quick_test'}" > /tmp/quick_config.yaml
echo "tasks: [{type: 'arithmetic', generation: {seed: 42, difficulties: [2], expressions_per_difficulty: 3}}]" >> /tmp/quick_config.yaml
echo "sampling: {temperature: 0.1}" >> /tmp/quick_config.yaml

# Run the 3-stage pipeline
python src/stages/generate_testset.py /tmp/quick_config.yaml --output-dir /tmp/
python src/stages/run_testset.py /tmp/testset_*.json.gz --model qwen3:0.6b --output-dir /tmp/results/
python src/stages/analyze_results.py /tmp/results/*.json.gz --output /tmp/report.md --visualize
```

### **Option 3: Legacy Individual Benchmark**
```bash
# Quick arithmetic test
python src/benchmarks/ari_eval.py --model qwen3:0.6b --batch-size 5 --difficulty 2
```

## Troubleshooting

### **Common Issues**
1. **"No models found"**: Ensure Ollama is running (`ollama serve`) and models are pulled
2. **Parse errors**: Check that `--no-think` flag is used for structured output tasks
3. **Import errors**: Run from project root directory, ensure Python path is correct
4. **Template errors**: Verify YAML config syntax, especially for multi-task configs
5. **Performance issues**: Use smaller batch sizes for initial testing

### **Getting Help**
- Check `docs/3_STAGE_ARCHITECTURE_COMPLETE.md` for comprehensive implementation guide
- Review `tests/` folder for working examples
- Examine `configs/` folder for YAML configuration patterns
- Check recent results in `results*/` for successful run examples

---

**Version**: 2.17.0 (April 8, 2026)
**Status**: Production Ready 🚀
**Key Features**:
- React SPA frontend (Vite 6 + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui)
- Plugin-based benchmark system with auto-discovery (19 plugins)
- **LLM-as-a-Judge** — audit incorrect model responses via judge LLM; classifies as true_incorrect / false_negative / parser_failure; setup sheet with model selection, editable prompts, sampling params; background job execution; judge output files with verdict summaries
- **Deep multilingual content localization** — all 19 plugins generate test content in 6 languages with per-plugin i18n modules
- **Grammatical gender** — `grammar_utils.py` for article resolution, case-form lookup, gender-aware templates; zero slash patterns in UA/ES/FR/DE
- **Multilingual evaluator fix** — Object Tracking + Sally-Anne evaluators accept localized expected answers
- Modern 3-stage architecture with enhanced parsing and analytics
- **Multi-provider Execute page** — Ollama + multiple OpenAI-compatible endpoints + HuggingFace
- **Reanalysis, custom system prompts, "By Dimension" charts, favorites, encrypted credentials**
- **Task type inference** — `_infer_task_type_from_id()` with aliases for all 19 task types
- **Compact Results toolbar** — icon-only buttons with count badges, per-row dropdown actions, filter-aware select-all, testset grouping
- **Localized measure comparison** — unit display names + decimal framing templates in all 6 languages
