# GoL Benchmark - Copilot Instructions

## Project Overview

This is a comprehensive LLM reasoning benchmark suite testing model capabilities across procedural tasks (Game of Life, arithmetic expressions, Linda fallacy, cellular automata). The system features a modern 3-stage architecture with support for multiple model providers (Ollama, HuggingFace), multilingual prompts (EN/ES/FR/DE/ZH/UA), configurable prompt styles, and advanced analytics.

## Architecture (v2.0.0)

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
TUI/CLI → Stage 1 (generate_testset.py) → Stage 2 (run_testset.py) → Stage 3 (analyze_results.py)
  ↓            ↓                           ↓                         ↓
Config →   TestGenerator →            ModelInterface →        Enhanced Analytics
        PromptEngine                  (Ollama/HuggingFace)    Multi-dimensional Reports
```

## Project Structure (v2.0.0)

### **Core Architecture (`src/` organization)**

```
src/
├── stages/             # 3-Stage Pipeline Scripts
│   ├── generate_testset.py    # Stage 1: YAML → Test Sets
│   ├── run_testset.py         # Stage 2: Execute on Models  
│   └── analyze_results.py     # Stage 3: Analytics & Reports
├── cli/                # Command Line Interfaces
│   └── benchmark_tui.py       # Interactive Terminal UI
├── core/               # Core types, prompt engine, test generation
│   ├── types.py        # Config dataclasses (BaseTestConfig, GameOfLifeTestConfig, etc.)
│   ├── PromptEngine.py # Multi-language, multi-style prompt templates
│   ├── TestGenerator.py# Test case generation with pattern support
│   └── PROMPT_STYLES.py# Prompt style definitions
├── models/             # Model provider interfaces
│   ├── BaseModelInterface.py  # Abstract interface + create_interface() factory
│   ├── OllamaInterface.py     # Local Ollama implementation
│   └── HuggingFaceInterface.py# HuggingFace implementation
├── engine/             # Task-specific engines
│   ├── GameOfLifeEngine.py    # Conway's Game of Life rules
│   └── MathExpressionGenerator.py # Arithmetic expression generation
├── evaluation/         # Result evaluation
│   └── TestEvaluator.py# Grid comparison, accuracy calculations
├── benchmarks/         # Legacy individual benchmark scripts
│   ├── ari_eval.py     # Arithmetic evaluation (legacy)
│   └── gol_eval.py     # Game of Life evaluation (legacy)
└── utils/              # Utilities
    └── logger.py       # Logging utilities
```

### **Project Root Organization**
```
gol_eval/
├── src/                # All source code
├── tests/              # Test suites and validation scripts
├── docs/               # Comprehensive documentation
├── testsets/           # Generated test sets (.json.gz)
├── results*/           # Benchmark execution results
├── configs/            # YAML configuration files
└── [clean root]        # No temporary files
```

**Backward Compatibility:** Legacy imports like `from src.types import ...` still work via module aliasing in `src/__init__.py`

## Running Benchmarks (v2.0.0)

### 🎮 **Interactive TUI (Recommended)**
```bash
# Modern interactive workflow
python src/cli/benchmark_tui.py

# Supports:
# - Multi-task test sets (arithmetic + Game of Life combined)
# - Model selection with provider detection
# - Prompt style matrix configuration (3x3 combinations)
# - Automatic 3-stage execution
# - Enhanced reporting and visualizations
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
  cell_markers: ["1", "0"]  # Critical: avoid emoji markers
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

### **Adding New Benchmark Tasks**
1. Add task type to `src/core/types.py` (`TaskType` enum)
2. Add config dataclass inheriting from `BaseTestConfig`
3. Add prompt templates in `src/core/PromptEngine.py` under the new `TaskType`
4. Add generation logic in `src/stages/generate_testset.py`
5. Add parsing logic in `src/stages/run_testset.py`
6. Register in `src/cli/benchmark_tui.py` task selection
7. Optional: Create legacy individual benchmark script in `src/benchmarks/`

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
# Always use the factory function (backward compatible)
from src.models.BaseModelInterface import create_interface

interface = create_interface(config)  # Returns OllamaInterface or HuggingFaceInterface
response_data = interface.query(prompt, query_params)
```

## Testing & Validation

### **Test Suite Organization**
```bash
# Comprehensive test suite in tests/ folder
python tests/test_comprehensive_workflow.py     # Full 3-stage workflow
python tests/test_tui_workflow.py              # TUI integration tests  
python tests/test_enhanced_reports_demo.py     # Analytics validation
python tests/test_provider_integration.py      # Model provider tests
```

Tests validate TUI workflow, 3-stage pipeline, config serialization, parsing enhancements, and component integration.

## External Dependencies & Setup

### **Required Services**
- **Ollama** must be running (`ollama serve`) for local model testing
- **Models**: Pull required models (`ollama pull qwen3:0.6b gemma3:1b`)

### **Optional Dependencies**
- **HuggingFace**: Install `transformers` and `torch` for HuggingFace provider
- **Visualization**: `matplotlib`, `seaborn` for enhanced charts (auto-installed)

### **Data Files**
- Pattern files in `conways_life/known_patterns/` (.cells, .rle formats) for Game of Life
- Results and visualizations output to `results*/` and `docs/images/`

## Critical Fixes & Known Issues (v2.0.0)

### ✅ **Major Fixes Implemented**
1. **Game of Life Template Bug**: Fixed `{grid_str}` placeholder not being substituted (was causing 0% accuracy)
2. **Multi-Task Parsing**: Enhanced parsing with 6-strategy fallback for arithmetic, 4-strategy for GoL  
3. **Task Type Detection**: Fixed multi-task execution routing issues
4. **Report Generation**: Harmonized HTML/Markdown reports with embedded visualizations
5. **Import Path Issues**: Fixed module loading from subdirectories in TUI system

### ⚠️ **Known Limitations**
- **Emoji cell markers** (`🟩/🟥`) cause model failures—always use `1/0` markers  
- **Thinking mode** can hurt structured output accuracy—use `--no-think` for best results
- **Quantized models** (Q2_K) sometimes outperform full precision (counterintuitive but documented)
- **Cloud model timeouts**: Some cloud providers have longer response times

### 🎯 **Performance Expectations (Post-Fix)**
- **Arithmetic Tasks**: 60-90% accuracy with enhanced parsing
- **Game of Life**: 40-70% accuracy (dramatically improved from 0% after grid_str fix)
- **Multi-Task Combined**: 50-80% overall accuracy depending on model capability
- **Parse Error Rate**: <20% with enhanced multi-strategy parsing (down from 100% in some cases)

## Quick Start Guide

### **Option 1: Interactive TUI (Easiest)**
```bash
# Start interactive benchmark
python src/cli/benchmark_tui.py

# Follow prompts:
# 1. Select task types (arithmetic, game_of_life, or multi-task)  
# 2. Choose models (auto-detected from Ollama)
# 3. Configure prompt styles and parameters
# 4. Execute 3-stage pipeline automatically
# 5. View comprehensive reports and visualizations
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

**Version**: 2.0.0 (January 2026)  
**Status**: Production Ready 🚀  
**Key Feature**: Modern 3-stage architecture with enhanced parsing and analytics
