# CLAUDE.md - GoL Benchmark Project Guide

> **Quick Reference for Claude Code Agents**
> This document provides context, architecture overview, and common tasks for working with the GoL Benchmark repository.

---

## Project Overview

**GoL Benchmark** is a procedural benchmark suite for testing LLM reasoning capabilities across structured cognitive tasks:

- **Game of Life (GoL)**: Conway's cellular automaton — predict next grid state
- **Arithmetic (ARI)**: Math expression parsing and evaluation
- **Linda Fallacy**: Cognitive bias testing (conjunction fallacy)
- **Cellular Automata (C14)**: Configurable rule-based pattern evolution
- **ASCII Shapes**: Spatial reasoning on ASCII art (dimensions, counts, positions)
- **Object Tracking**: Physical state tracking through container inversions (grape test)
- **Sally-Anne**: Theory of Mind — false belief reasoning
- **Carwash Paradox**: Practical-goal-tracking test — walk or drive? (answer: always drive)
- **Inverted Cup**: Spatial-orientation reasoning — sealed top / open bottom cup (answer: flip it)
- **Strawberry**: Letter counting in words ("How many R's in strawberry?")
- **Measure Comparison**: Quantity comparison with units and conversion traps
- **Grid Tasks**: Table reasoning — cell lookups, row sums, column counts

### Key Characteristics

- **Multilingual**: 6 languages supported (EN, FR, ES, DE, ZH, UA)
- **Multi-provider**: Ollama (local & remote) and HuggingFace integrations
- **Prompt engineering**: 3 user styles × 3 system styles = 9 configurations
- **Reproducible**: Seeded random generation for consistent benchmarks

---

## Quick Commands

```bash
# ── Web UI (Recommended) ──
python -m src.web                # http://127.0.0.1:8000
python -m src.web --host 0.0.0.0 # LAN-accessible

# Run Game of Life benchmark
python -m src.benchmarks.gol_eval --model qwen3:0.6b --difficulty medium --batch-size 20

# Run Arithmetic benchmark
python -m src.benchmarks.ari_eval --model llama3.2:3b --difficulty 3

# Run Linda fallacy test
python -m src.benchmarks.linda_eval --model gemma3:1b --language es --trials 10

# Run C14 cellular automata
python -m src.benchmarks.c14_eval --model qwen3:4b --rule 110 --steps 5

# Run Carwash Paradox (via 3-stage pipeline — no legacy script)
# 1) Generate, 2) run, 3) analyze — or use TUI
python src/cli/benchmark_tui.py  # select 'Carwash Paradox' task

# Interactive benchmark TUI
python -m src.cli.benchmark_tui

# Run on a remote Ollama instance
python src/stages/run_testset.py testsets/testset_xyz.json.gz \
    --model qwen3:0.6b --provider ollama \
    --ollama-host http://192.168.1.50:11434

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
│   ├── plugins/           # Plugin-based benchmark system (12 plugins)
│   │   ├── base.py        # Abstract base classes for plugins
│   │   ├── __init__.py    # Plugin registry with auto-discovery
│   │   ├── parse_utils.py # End-first parsing utilities
│   │   ├── game_of_life/  # GoL plugin (generator, parser, evaluator)
│   │   ├── arithmetic/    # ARI plugin
│   │   ├── linda_fallacy/ # Linda plugin
│   │   ├── cellular_automata_1d/  # C14 plugin
│   │   ├── ascii_shapes/  # ASCII Shapes plugin
│   │   ├── object_tracking/ # Object Tracking (Grape Test) plugin
│   │   ├── sally_anne/    # Sally-Anne false belief test plugin
│   │   ├── carwash/       # Carwash Paradox plugin (v2.2.0)
│   │   ├── inverted_cup/  # Inverted Cup plugin (v2.2.0)
│   │   ├── strawberry/    # Letter counting plugin
│   │   ├── measure_comparison/ # Quantity comparison plugin
│   │   └── grid_tasks/    # Table reasoning plugin
│   ├── stages/            # 3-stage pipeline (uses plugin system)
│   │   ├── generate_testset.py  # Stage 1: YAML → test sets
│   │   ├── run_testset.py       # Stage 2: Execute tests
│   │   └── analyze_results.py   # Stage 3: Analytics
│   ├── core/              # Types, prompt engine, test generation
│   ├── engine/            # Task-specific logic (GoL, Math)
│   ├── models/            # LLM interfaces (Ollama, HuggingFace)
│   ├── evaluation/        # Result scoring and metrics
│   ├── benchmarks/        # DEPRECATED: Legacy monolithic scripts
│   ├── cli/               # CLI tools, TUI (deprecated), config management
│   ├── web/               # FastAPI + HTMX web UI (replaces TUI)
│   │   ├── app.py         # FastAPI app factory, page routes
│   │   ├── api/           # REST endpoints (plugins, models, testsets, jobs, analysis)
│   │   ├── jobs.py        # Background job manager (ProcessPoolExecutor)
│   │   ├── templates/     # Jinja2 + HTMX templates
│   │   └── static/        # CSS, JS
│   ├── visualization/     # Charts, analysis, reporting
│   └── utils/             # Logging, model discovery
│
├── tests/                 # Test suite
│   └── plugins/           # Plugin system unit tests
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
| **Plugin System (12 plugins)** | |
| [src/plugins/base.py](src/plugins/base.py) | Abstract base classes + ConfigField schema system |
| [src/plugins/\_\_init\_\_.py](src/plugins/__init__.py) | Plugin registry with auto-discovery |
| [src/plugins/parse\_utils.py](src/plugins/parse_utils.py) | End-first parsing utilities |
| [src/plugins/game_of_life/](src/plugins/game_of_life/) | GoL plugin module |
| [src/plugins/arithmetic/](src/plugins/arithmetic/) | ARI plugin module |
| [src/plugins/linda_fallacy/](src/plugins/linda_fallacy/) | Linda Fallacy plugin module |
| [src/plugins/cellular_automata_1d/](src/plugins/cellular_automata_1d/) | C14 plugin module |
| [src/plugins/ascii_shapes/](src/plugins/ascii_shapes/) | ASCII Shapes plugin module |
| [src/plugins/object_tracking/](src/plugins/object_tracking/) | Object Tracking (Grape Test) plugin |
| [src/plugins/sally_anne/](src/plugins/sally_anne/) | Sally-Anne false belief test plugin |
| [src/plugins/carwash/](src/plugins/carwash/) | Carwash Paradox plugin |
| [src/plugins/inverted_cup/](src/plugins/inverted_cup/) | Inverted Cup plugin |
| [src/plugins/strawberry/](src/plugins/strawberry/) | Letter counting plugin |
| [src/plugins/measure_comparison/](src/plugins/measure_comparison/) | Quantity comparison plugin |
| [src/plugins/grid_tasks/](src/plugins/grid_tasks/) | Table reasoning plugin |
| **3-Stage Pipeline** | |
| [src/stages/generate_testset.py](src/stages/generate_testset.py) | Stage 1: Test set generation (uses plugins) |
| [src/stages/run_testset.py](src/stages/run_testset.py) | Stage 2: Test execution (uses plugins) |
| [src/stages/analyze_results.py](src/stages/analyze_results.py) | Stage 3: Analytics and reporting |
| **Core Infrastructure** | |
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

### 1. Plugin Pattern (v2.2.0)
Self-contained benchmark modules with auto-discovery via package scanning.
```python
from src.plugins import PluginRegistry
plugin = PluginRegistry.get('game_of_life')
generator = plugin.get_generator()
parser = plugin.get_parser()
evaluator = plugin.get_evaluator()
```

### 2. Factory Pattern
`create_interface(config)` creates appropriate model interface based on config type.

### 3. Strategy Pattern
Different prompt/system styles are interchangeable via PromptEngine. Multi-strategy parsing in parsers (6 strategies for ARI, 4 for GoL).

### 4. Template Method
`BaseModelInterface` defines contract; subclasses implement `query_model()` and `supports_reasoning()`.

### 5. Configuration Inheritance
```
BaseTestConfig (ABC)
├── GameOfLifeTestConfig
├── AriTestConfig
├── C14TestConfig
└── (future tasks...)
```

---

### 6. End-First Parsing Convention

All response parsers follow the principle of searching from the **end** of the model response toward the start. LLMs reason through problems first and give final answers at the end — using `re.search()` (which finds the first match) systematically extracts intermediate values instead of final answers.

**Shared utilities** in [`src/plugins/parse_utils.py`](src/plugins/parse_utils.py):

- `re_search_last(pattern, text)` — drop-in replacement for `re.search()` that returns the last match
- `last_sentences(text, n)` — returns the last N sentences
- `last_keyword_position(text, keywords)` — position of last keyword occurrence

**Key exceptions where end-first does NOT apply:**

- `measure_comparison` value+unit matching — both options are mentioned, the answer is identified by which matches, not position
- `inverted_cup` classification — if "flip" is mentioned anywhere, the model understood the key insight (correct answer); "wrong" keywords alongside flip are just creative alternatives
- `linda_fallacy` — extracts ordered rankings, not single answers

**Validated**: Re-parsed 1,933 results across 33 files. Zero true regressions from end-first changes. Carwash accuracy improved from 14.3% to 27.6% (+13pp).

---

## Adding New Features

### New Benchmark Task (Plugin System - v2.1.0)

**Modern approach using the plugin system:**

1. **Create plugin directory** `src/plugins/new_task/`:
   ```bash
   mkdir src/plugins/new_task
   cd src/plugins/new_task
   ```

2. **Create `__init__.py`** with plugin instance:
   ```python
   from src.plugins.base import BenchmarkPlugin
   from src.plugins.new_task.generator import NewTaskGenerator
   from src.plugins.new_task.parser import NewTaskParser
   from src.plugins.new_task.evaluator import NewTaskEvaluator

   class NewTaskPlugin(BenchmarkPlugin):
       @property
       def task_type(self) -> str:
           return "new_task"

       @property
       def display_name(self) -> str:
           return "New Task Display Name"

       def get_generator(self):
           return NewTaskGenerator()

       def get_parser(self):
           return NewTaskParser()

       def get_evaluator(self):
           return NewTaskEvaluator()

   plugin = NewTaskPlugin()  # Auto-discovered!
   ```

3. **Create `generator.py`** (test case generation):
   ```python
   from src.plugins.base import TestCaseGenerator, TestCase, ConfigField

   class NewTaskGenerator(TestCaseGenerator):
       def generate_batch(self, config, prompt_config, count, seed):
           # Generate test cases
           return [TestCase(...), ...]

       def get_config_schema(self) -> list[ConfigField]:
           # Return field descriptors for the web UI config form
           return [
               ConfigField(name='count', label='Number of cases', field_type='number',
                           default=10, min_value=1, max_value=200),
               # ... more fields (types: number, select, multi-select, text, boolean, range, weight_map)
           ]
   ```

4. **Create `parser.py`** (response parsing with multi-strategy):
   ```python
   from src.plugins.base import ResponseParser, ParsedAnswer

   class NewTaskParser(ResponseParser):
       def parse(self, response: str, task_params: Dict) -> ParsedAnswer:
           # Try multiple parsing strategies
           return ParsedAnswer(value=..., raw_response=response, parse_strategy='...')
   ```

5. **Create `evaluator.py`** (result evaluation):
   ```python
   from src.plugins.base import ResultEvaluator, EvaluationResult

   class NewTaskEvaluator(ResultEvaluator):
       def evaluate(self, parsed_answer, expected_answer, task_params) -> EvaluationResult:
           # Evaluate correctness
           return EvaluationResult(correct=..., match_type='...', accuracy=...)
   ```

6. **Add prompts** to [src/core/PromptEngine.py](src/core/PromptEngine.py):
   ```python
   TaskType = Enum('TaskType', [..., 'new_task'])
   ```

7. **Add config class** (if needed) in [src/core/types.py](src/core/types.py):
   ```python
   @dataclass
   class NewTaskTestConfig(BaseTestConfig):
       task_param1: int
       task_param2: str
   ```

**That's it! The plugin is automatically discovered and integrated into:**
- Stage 1 (generate_testset.py)
- Stage 2 (run_testset.py)
- Stage 3 (analyze_results.py)
- Web UI `/configure` page (dynamic form via `get_config_schema()`)

### Legacy Approach (Deprecated)

<details>
<summary>Click to see legacy monolithic approach (not recommended)</summary>

1. Create evaluation script in `src/benchmarks/new_task_eval.py`
2. Add to TUI manually
3. Duplicate parsing/evaluation logic

**Note:** This approach is deprecated. Use the plugin system instead.
</details>

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
# Plugin System
from src.plugins import PluginRegistry, ConfigField
from src.plugins.base import (
    BenchmarkPlugin, TestCaseGenerator, ResponseParser, ResultEvaluator,
    TestCase, ParsedAnswer, EvaluationResult, ConfigField
)

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

- **Project Overview**: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) — Architecture, tasks, research findings, quick start
- **Plugin Guide**: [docs/PLUGIN_GUIDE.md](docs/PLUGIN_GUIDE.md) — Plugin reference, end-first parsing, adding new plugins
- **Architecture**: [docs/architecture/SYSTEM_OVERVIEW.md](docs/architecture/SYSTEM_OVERVIEW.md)
- **Research — Quantization**: [docs/research/quantization/EXECUTIVE_SUMMARY.md](docs/research/quantization/EXECUTIVE_SUMMARY.md)
- **Research — Prompt Analysis**: [docs/research/prompt-analysis/RESULTS_REPORT.md](docs/research/prompt-analysis/RESULTS_REPORT.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

*Last updated: 2026-03-24*
*Version: 2.4.0*
*Key additions: Plugin config schema introspection • ConfigField system • Dynamic web UI forms*
*For questions or issues: Check [README.md](README.md) or create an issue*
