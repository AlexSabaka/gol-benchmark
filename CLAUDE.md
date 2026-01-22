# CLAUDE.md - GoL Benchmark Project Guide

> **Quick Reference for Claude Code Agents**
> This document provides context, architecture overview, and common tasks for working with the GoL Benchmark repository.

---

## Project Overview

**GoL Benchmark** is a procedural benchmark suite for testing LLM reasoning capabilities across structured cognitive tasks:

- **Game of Life (GoL)**: Conway's cellular automaton - predict next grid state
- **Arithmetic (ARI)**: Math expression parsing and evaluation
- **Linda Fallacy**: Cognitive bias testing (conjunction fallacy)
- **Cellular Automata (C14)**: Configurable rule-based pattern evolution

### Key Characteristics

- **Multilingual**: 6 languages supported (EN, FR, ES, DE, ZH, UA)
- **Multi-provider**: Ollama and HuggingFace integrations
- **Prompt engineering**: 3 user styles × 3 system styles = 9 configurations
- **Reproducible**: Seeded random generation for consistent benchmarks

---

## Quick Commands

```bash
# Run Game of Life benchmark
python -m src.benchmarks.gol_eval --model qwen3:0.6b --difficulty medium --batch-size 20

# Run Arithmetic benchmark
python -m src.benchmarks.ari_eval --model llama3.2:3b --difficulty 3

# Run Linda fallacy test
python -m src.benchmarks.linda_eval --model gemma3:1b --language es --trials 10

# Run C14 cellular automata
python -m src.benchmarks.c14_eval --model qwen3:4b --rule 110 --steps 5

# Interactive benchmark TUI
python -m src.cli.benchmark_tui

# Run full test suite
pytest tests/

# Generate visualizations from results
python -m src.visualization.generate_prompt_benchmark_visualizations results/
```

---

## Directory Structure

```
gol_eval/
├── src/                    # All source code
│   ├── core/              # Types, prompt engine, test generation
│   ├── engine/            # Task-specific logic (GoL, Math)
│   ├── models/            # LLM interfaces (Ollama, HuggingFace)
│   ├── evaluation/        # Result scoring and metrics
│   ├── benchmarks/        # Evaluation scripts (gol_eval, ari_eval, etc.)
│   ├── cli/               # CLI tools, TUI, config management
│   ├── visualization/     # Charts, analysis, reporting
│   └── utils/             # Logging, model discovery
│
├── tests/                 # Test suite
├── scripts/               # Shell scripts for batch processing
├── configs/               # Benchmark configuration YAML files
├── data/                  # External data (Conway's Life patterns)
├── docs/                  # Documentation and research reports
└── results/               # Benchmark results (kept at root for easy access)
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| [src/core/types.py](src/core/types.py) | All config classes, types, difficulty levels |
| [src/core/PromptEngine.py](src/core/PromptEngine.py) | Multilingual prompt generation (6 languages) |
| [src/core/TestGenerator.py](src/core/TestGenerator.py) | Test case generation with known patterns |
| [src/models/BaseModelInterface.py](src/models/BaseModelInterface.py) | Abstract base for model providers |
| [src/models/OllamaInterface.py](src/models/OllamaInterface.py) | Ollama integration with retry logic |
| [src/models/HuggingFaceInterface.py](src/models/HuggingFaceInterface.py) | HuggingFace/Transformers integration |
| [src/evaluation/TestEvaluator.py](src/evaluation/TestEvaluator.py) | Grid comparison and accuracy calculation |
| [src/engine/GameOfLifeEngine.py](src/engine/GameOfLifeEngine.py) | Conway's Game of Life rules |
| [src/engine/MathExpressionGenerator.py](src/engine/MathExpressionGenerator.py) | Expression tree generation |

---

## Architecture Patterns

### 1. Factory Pattern
`create_interface(config)` creates appropriate model interface based on config type.

### 2. Strategy Pattern
Different prompt/system styles are interchangeable via PromptEngine.

### 3. Template Method
`BaseModelInterface` defines contract; subclasses implement `query_model()` and `supports_reasoning()`.

### 4. Configuration Inheritance
```
BaseTestConfig (ABC)
├── GameOfLifeTestConfig
├── AriTestConfig
├── C14TestConfig
└── (future tasks...)
```

---

## Adding New Features

### New Benchmark Task

1. **Create config class** in [src/core/types.py](src/core/types.py):
   ```python
   @dataclass
   class NewTaskTestConfig(BaseTestConfig):
       task_param1: int
       task_param2: str

       def __post_init__(self):
           super().__post_init__()
           # Validation logic
   ```

2. **Create evaluation script** in `src/benchmarks/new_task_eval.py`:
   ```python
   from src.core.types import NewTaskTestConfig
   from src.models import create_interface

   def run_new_task_test(config: NewTaskTestConfig):
       interface = create_interface(config)
       # Test logic here
   ```

3. **Add prompts** to [src/core/PromptEngine.py](src/core/PromptEngine.py):
   ```python
   TaskType = Enum('TaskType', [..., 'new_task'])
   ```

4. **Create engine** (if needed) in `src/engine/NewTaskEngine.py`

### New Model Provider

1. **Create interface** in `src/models/NewProviderInterface.py`:
   ```python
   from src.models.BaseModelInterface import BaseModelInterface

   class NewProviderInterface(BaseModelInterface):
       def query_model(self, prompt: str, **kwargs):
           # Implementation

       def supports_reasoning(self) -> bool:
           return True  # or False
   ```

2. **Update factory** in [src/models/\_\_init\_\_.py](src/models/__init__.py):
   ```python
   def create_interface(config: BaseTestConfig):
       if config.interface == "new_provider":
           return NewProviderInterface(config)
       # ... existing logic
   ```

### New Visualization

1. Add to [src/visualization/](src/visualization/) following patterns in [visualization_engine.py](src/visualization/visualization_engine.py)
2. Use matplotlib/seaborn for charts
3. Save to `docs/images/` with descriptive names

---

## Common Configuration

### Command-Line Arguments

```bash
# Prompt styles (user prompt)
--prompt-style minimal|casual|linguistic

# System prompt styles
--system-prompt-style analytical|casual|adversarial

# Languages
--prompt-language en|es|fr|de|zh|uk

# Cell markers (GoL only - NEVER use emoji!)
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

---

## Known Issues & Gotchas

### Critical Issues

1. **Emoji markers cause 0% accuracy**
   - Always use `--live-dead-cell-markers "1,0"` for GoL
   - Never use "⚪⚫" or other emoji - models parse incorrectly

2. **`--no-think` is critical for structured tasks**
   - Chain-of-thought hurts performance on GoL/ARI
   - Can improve Linda fallacy reasoning

3. **Ollama must be running**
   - Start with `ollama serve` before benchmarks
   - Connection errors if daemon not running

4. **Model preloading**
   - First query is slow (model loading time)
   - Subsequent queries are cached and faster

### Import Patterns

After reorganization, use these import patterns:

```python
# Core
from src.core.types import GameOfLifeTestConfig, DifficultyLevel
from src.core.PromptEngine import PromptEngine, Language, PromptStyle
from src.core.TestGenerator import TestGenerator

# Models
from src.models import create_interface
from src.models.BaseModelInterface import BaseModelInterface

# Evaluation
from src.evaluation.TestEvaluator import TestEvaluator

# Engines
from src.engine.GameOfLifeEngine import GameOfLifeEngine
from src.engine.MathExpressionGenerator import MathExpressionGenerator

# Utils
from src.utils.logger import get_logger
from src.utils.model_providers import ModelProvider
```

---

## Research Findings

### Key Discoveries from Benchmark Studies

1. **Prompt engineering dominates model selection**
   - 44+ percentage point swings from prompt choice alone
   - Same model, different prompts → 0% to 44% accuracy

2. **System prompts are reasoning switches**
   - Analytical: Step-by-step, methodical
   - Casual: Intuitive, conversational
   - Adversarial: Direct, efficient

3. **Model personalities matter**
   - Qwen = pragmatist (adversarial prompts work best)
   - Gemma = analyst (analytical prompts work best)
   - Llama = generalist (balanced across styles)

4. **Q2_K quantization beats F16**
   - 2-bit extreme quantization outperforms full precision (+6.18%)
   - Likely due to noise reduction in attention heads

5. **Chain-of-thought hurts structured tasks**
   - GoL/ARI: --no-think improves accuracy
   - Linda: thinking helps detect fallacy

See [docs/PROMPT_BENCHMARK_NOVEMBER_2025_REPORT.md](docs/PROMPT_BENCHMARK_NOVEMBER_2025_REPORT.md) for full analysis.

---

## Testing

### Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_comprehensive_workflow.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run integration tests
pytest tests/test_provider_integration.py
```

### Manual Testing

```bash
# Test GoL with known pattern
python -m src.benchmarks.gol_eval \
  --model qwen3:0.6b \
  --difficulty easy \
  --batch-size 5 \
  --seed 42 \
  --no-think \
  --live-dead-cell-markers "1,0"

# Test ARI with specific targets
python -m src.benchmarks.ari_eval \
  --model llama3.2:3b \
  --target 0 1 2 \
  --difficulty 2 \
  --mode expression \
  --batch-size 10
```

---

## Batch Processing

### Run Multi-Model Benchmark

```bash
# Edit scripts/run_multi_model_benchmark.sh to configure:
# - MODELS array
# - USER_STYLES and SYSTEM_STYLES
# - DIFFICULTY, BATCH_SIZE, etc.

bash scripts/run_multi_model_benchmark.sh
```

### Monitor Progress

```bash
# Watch benchmark progress
bash scripts/monitor_benchmark.sh

# Or use watch command
watch -n 5 'ls -1 results/multi_model_*/  *.json | wc -l'
```

---

## Troubleshooting

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'src.types'`
**Fix**: Use new import paths:
```python
# Old (broken)
from src.types import GameOfLifeTestConfig

# New (correct)
from src.core.types import GameOfLifeTestConfig
```

### Model Connection Issues

**Error**: `ollama.ResponseError: connection refused`
**Fix**: Start Ollama daemon:
```bash
ollama serve
```

### Pattern File Not Found

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'conways_life/...'`
**Fix**: Update path reference:
```python
# Old
from conways_life.parser import parse_rle

# New
from data.conways_life.parser import parse_rle
```

### 0% Accuracy with Emoji Markers

**Error**: All tests return 0% accuracy
**Fix**: Always use numeric markers:
```bash
# Wrong
--live-dead-cell-markers "⚪⚫"

# Correct
--live-dead-cell-markers "1,0"
```

---

## Q&A for Claude Code Agents

### Q: How do I run a quick GoL benchmark?

```bash
python -m src.benchmarks.gol_eval \
  --model qwen3:0.6b \
  --difficulty medium \
  --batch-size 20 \
  --no-think \
  --live-dead-cell-markers "1,0"
```

### Q: How do I add a new difficulty level?

1. Edit `src/core/types.py`:
   ```python
   class DifficultyLevel(Enum):
       EASY = "easy"
       MEDIUM = "medium"
       HARD = "hard"
       NIGHTMARE = "nightmare"
       ULTRA = "ultra"  # New
   ```

2. Update `GameOfLifeTestConfig._get_grid_size()`:
   ```python
   def _get_grid_size(self, difficulty: DifficultyLevel) -> int:
       sizes = {
           DifficultyLevel.EASY: 3,
           DifficultyLevel.MEDIUM: 5,
           DifficultyLevel.HARD: 7,
           DifficultyLevel.NIGHTMARE: 10,
           DifficultyLevel.ULTRA: 15,  # New
       }
       return sizes[difficulty]
   ```

### Q: How do I debug why a model is scoring 0%?

1. **Check cell markers**: Must be `"1,0"`, not emoji
2. **Inspect raw output**: Add `print(response)` before `parse_response()`
3. **Check prompt**: Ensure format matches expected output
4. **Try simpler test**: Use `--difficulty easy --batch-size 1`

### Q: How do I add support for a new LLM API?

See "New Model Provider" section above. Key steps:
1. Create interface extending `BaseModelInterface`
2. Implement `query_model()` method
3. Update factory in `src/models/__init__.py`

### Q: Where are benchmark results stored?

- **Default**: `results/` at repository root
- **Multi-model runs**: `results/multi_model_TIMESTAMP/`
- **Custom**: Use `--results-dir` flag

### Q: How do I reproduce exact benchmark results?

Use `--seed` flag for deterministic random generation:
```bash
python -m src.benchmarks.gol_eval --seed 42 --batch-size 20
```

Same seed + same config = identical test cases.

---

## Dependencies

### Required

- Python 3.8+
- Ollama running locally (`ollama serve`)
- PyTorch, Transformers, NumPy, Pandas

### Installation

```bash
# Install requirements
pip install -r requirements.txt

# Optional: Install with dev dependencies
pip install -r requirements.txt pytest pytest-cov black ruff
```

### Verify Installation

```bash
# Check Python version
python --version

# Check Ollama connection
ollama list

# Run quick test
python -m src.benchmarks.gol_eval --model qwen3:0.6b --difficulty easy --batch-size 1
```

---

## Contributing

### Code Style

- Use type hints for all functions
- Follow PEP 8 naming conventions
- Add docstrings to public methods
- Keep functions < 50 lines when possible

### Before Committing

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Run tests
pytest tests/
```

---

## Additional Resources

- **Architecture**: [docs/03_ARCHITECTURE/SYSTEM_OVERVIEW.md](docs/03_ARCHITECTURE/SYSTEM_OVERVIEW.md)
- **Research Reports**: [docs/05_RESEARCH/](docs/05_RESEARCH/)
- **Full Documentation Index**: [docs/INDEX.md](docs/INDEX.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

*Last updated: 2026-01-22*
*For questions or issues: Check [README.md](README.md) or create an issue*
