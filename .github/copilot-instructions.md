# GoL Benchmark - Copilot Instructions

## Project Overview

This is an LLM reasoning benchmark suite testing model capabilities across procedural tasks (Game of Life, arithmetic expressions, Linda fallacy, cellular automata). The system supports multiple model providers (Ollama, HuggingFace), multilingual prompts (EN/ES/FR/DE/ZH/UA), and configurable prompt styles.

## Architecture

### Core Data Flow
```
Eval Script (gol_eval.py, ari_eval.py, etc.)
  → TestGenerator (creates test cases)
  → PromptEngine (builds system + user prompts)
  → BaseModelInterface (queries model via OllamaInterface/HuggingFaceInterface)
  → TestEvaluator (scores response accuracy)
```

### Project Structure (`src/` organization)

```
src/
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
└── utils/              # Utilities
    └── logger.py       # Logging utilities
```

**Backward Compatibility:** Legacy imports like `from src.types import ...` still work via module aliasing in `src/__init__.py`

### Benchmark Orchestration (Root Level)

- `benchmark_runner.py` → Main workflow orchestrator (TUI → Config → Execute → Visualize)
- `benchmark_config.py` → Config dataclasses: `BenchmarkConfig`, `ModelSpec`, `PromptSpec`, `TestParams`
- `benchmark_tui.py` → Interactive terminal UI using questionary
- `test_executor.py` → Subprocess-based test execution, result collection
- `visualization_engine.py` → Chart generation (matplotlib)

## Running Benchmarks

```bash
# Game of Life benchmark (most common)
python gol_eval.py --model qwen3:0.6b gemma3:1b --difficulty medium --batch-size 20 --prompt-style linguistic --system-prompt-style casual

# Arithmetic expressions
python ari_eval.py --model qwen3:0.6b --difficulty 3 --batch-size 10

# Linda fallacy (cognitive bias test)  
python linda_eval.py --models llama3.2:3b --language es --trials 10

# Interactive TUI workflow
python benchmark_runner.py
```

**Key CLI patterns:**
- `--model` accepts multiple models (space-separated)
- `--no-think` disables chain-of-thought for models that support it
- `--seed` ensures reproducible test generation
- Results auto-save to `results/` directory as JSON

## Configuration Patterns

### Config Dataclasses (in `src/types.py`)
All test configs inherit from `BaseTestConfig`. Task-specific configs add their own fields:

```python
# Base fields available to all tasks
models, batch_size, temperature, ctx_len, num_predict, prompt_language, prompt_style, system_prompt_style

# GoL-specific (GameOfLifeTestConfig)
difficulty: DifficultyLevel, density, known_patterns_ratio, live_dead_cell_markers

# Ari-specific (AriTestConfig)  
difficulties: List[int], mode: "expression"|"equation", variables
```

### Prompt Style Combinations
The benchmark systematically tests 3×3 prompt matrices:
- **User styles**: `minimal`, `casual`, `linguistic` (in `PromptStyle` enum)
- **System styles**: `analytical`, `casual`, `adversarial` (in `SystemPromptStyle` enum)

## Code Conventions

### Adding New Benchmark Tasks
1. Create `{task}_eval.py` at root with argparse CLI
2. Add config dataclass in `src/types.py` inheriting from `BaseTestConfig`
3. Add prompt templates in `src/PromptEngine.py` under the new `TaskType`
4. Register in `benchmark_tui.py` task selection

### Response Parsing
Model responses are parsed to extract structured outputs (grids, numbers). Parse errors are tracked separately from accuracy. See `TestEvaluator.compare_grids()` for the grid comparison pattern.

### Model Interface Pattern
```python
# Always use the factory function
from src.models.BaseModelInterface import create_interface  # or: from src.BaseModelInterface import create_interface

interface = create_interface(config)  # Returns OllamaInterface or HuggingFaceInterface
response, tokens = interface.query_model(model_name, prompt, system_prompt)
```

## Testing

```bash
# Validation tests (no pytest markers, just assertions)
python test_comprehensive_workflow.py
python test_tui_workflow.py
```

Tests validate TUI workflow, config serialization, and component integration.

## External Dependencies

- **Ollama** must be running (`ollama serve`) for local model testing
- Pattern files in `conways_life/known_patterns/` (.cells, .rle formats)
- Results and visualizations output to `results/` and `docs/images/`

## Known Quirks

- Emoji cell markers (`🟩/🟥`) cause model failures—always use `1/0` markers
- The `--no-think` flag is critical for structured output tasks (thinking mode hurts accuracy)
- Quantized models (Q2_K) sometimes outperform full precision (see README findings)
