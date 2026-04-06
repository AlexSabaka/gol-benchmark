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
- **Strawberry**: Character-level reasoning — letter counting, word reversal, nth-letter, anagram, pangram, lipogram
- **Measure Comparison**: Quantity comparison with units, conversion traps, and decimal framing sensitivity
- **Grid Tasks**: Table reasoning — cell lookups, row sums, column counts
- **Misquote Attribution**: Sycophancy detection — false quote attributions with social-pressure framings
- **False Premise**: Dangerous/impossible premise detection — 5 domains (chemistry, medicine, food safety, physics, logic)
- **Family Relations**: Perspective-aware family counting puzzles — sibling count, shared children, generational chains, perspective shifts
- **Encoding & Cipher Decoding**: Decode-and-respond across encoding schemes (Base64, Caesar/ROT-N, Morse) with hallucination detection
- **Symbol Arithmetic**: Custom operation tables on abstract symbol sets — pure rule-following with zero semantic anchor

### Key Characteristics

- **Multilingual**: 6 languages supported (EN, FR, ES, DE, ZH, UA)
- **Multi-provider**: Ollama (local & remote) and HuggingFace integrations
- **Prompt engineering**: 3 user styles × 3 system styles = 9 configurations
- **Reproducible**: Seeded random generation for consistent benchmarks

---

## Quick Commands

```bash
# ── Web UI (Recommended) ──
python -m src.web                # http://127.0.0.1:8000/
python -m src.web --host 0.0.0.0 # LAN-accessible

# Frontend development (hot-reload)
cd frontend && npm run dev       # http://localhost:5173/ (proxies /api → :8000)

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
│   ├── plugins/           # Plugin-based benchmark system (18 plugins)
│   │   ├── base.py        # Abstract base classes for plugins
│   │   ├── __init__.py    # Plugin registry with auto-discovery
│   │   ├── parse_utils.py # End-first parsing utilities + multilingual keyword merge
│   │   ├── grammar_utils.py # Shared grammar: article(), resolve_vocab(), pick_templates(), vocab_gender()
│   │   ├── game_of_life/  # GoL plugin (generator, parser, evaluator)
│   │   ├── arithmetic/    # ARI plugin
│   │   ├── linda_fallacy/ # Linda plugin
│   │   ├── cellular_automata_1d/  # C14 plugin
│   │   ├── ascii_shapes/  # ASCII Shapes plugin
│   │   ├── object_tracking/ # Object Tracking (Grape Test) plugin
│   │   ├── sally_anne/    # Sally-Anne false belief test plugin
│   │   ├── carwash/       # Carwash Paradox plugin (v2.2.0)
│   │   ├── inverted_cup/  # Inverted Cup plugin (v2.2.0)
│   │   ├── strawberry/    # Character-level reasoning (6 sub-types)
│   │   ├── measure_comparison/ # Quantity comparison plugin (incl. decimal framing)
│   │   ├── grid_tasks/    # Table reasoning plugin
│   │   ├── time_arithmetic/ # Time Arithmetic plugin (temporal reasoning)
│   │   ├── misquote/      # Misquote Attribution (sycophancy detection)
│   │   ├── false_premise/ # False Premise (dangerous/impossible premise detection)
│   │   ├── family_relations/ # Family Relations (perspective-aware counting)
│   │   ├── encoding_cipher/ # Encoding & Cipher Decoding (Base64, Caesar, Morse)
│   │   └── symbol_arithmetic/ # Symbol Arithmetic (custom operation tables)
│   ├── stages/            # 3-stage pipeline (uses plugin system)
│   │   ├── generate_testset.py  # Stage 1: YAML → test sets
│   │   ├── run_testset.py       # Stage 2: Execute tests
│   │   └── analyze_results.py   # Stage 3: Analytics
│   ├── core/              # Types, prompt engine, test generation
│   ├── engine/            # Task-specific logic (GoL, Math)
│   ├── models/            # LLM interfaces (Ollama, HuggingFace)
│   ├── evaluation/        # Result scoring and metrics
│   ├── benchmarks/        # Legacy (only linda_eval.py remains — used by linda plugin)
│   ├── web/               # FastAPI REST API backend (serves React SPA at /)
│   │   ├── app.py         # FastAPI app factory, SPA routing
│   │   ├── api/           # REST endpoints (plugins, models, testsets, jobs, analysis, judge)
│   │   ├── jobs.py        # Background job manager (ProcessPoolExecutor) — submit() + submit_judge()
│   │   ├── judge.py       # LLM-as-a-Judge worker (run_judge_worker, default prompts)
│   │   └── reanalyze.py   # Reanalysis utilities (re-parse/re-evaluate results)
│   ├── visualization/     # Charts, analysis, reporting
│   └── utils/             # Logging, model discovery
│
├── frontend/              # React SPA (Vite 6 + React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui)
│   ├── src/
│   │   ├── api/           # Typed API client layer
│   │   ├── hooks/         # React Query hooks with auto-refresh
│   │   ├── types/         # TypeScript interfaces
│   │   ├── pages/         # Dashboard, Configure, TestSets, Execute, Jobs, Results, Charts, Reports, Judge
│   │   ├── lib/           # Utilities (chart-colors, model-sizes, credential-store, favorite-models, language-flags)
│   │   └── components/    # UI primitives (shadcn), layout, plugin-config, data-table, charts, param-override-modal, judge-setup-sheet
│   ├── vite.config.ts     # base: "/", proxy /api → :8000
│   └── dist/              # Production build output
│
├── tests/                 # Test suite
│   └── plugins/           # Plugin system unit tests
├── scripts/               # Shell scripts for batch processing
├── configs/               # Benchmark configuration YAML files
├── data/                  # (Removed — data co-located in src/plugins/*/data/)
├── docs/                  # Documentation and research reports
└── results/               # Benchmark results (kept at root for easy access)
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| **Plugin System (18 plugins)** | |
| [src/plugins/base.py](src/plugins/base.py) | Abstract base classes + ConfigField schema system |
| [src/plugins/\_\_init\_\_.py](src/plugins/__init__.py) | Plugin registry with auto-discovery |
| [src/plugins/parse\_utils.py](src/plugins/parse_utils.py) | End-first parsing utilities + `safe_enum()` helper |
| [src/plugins/game_of_life/](src/plugins/game_of_life/) | GoL plugin module |
| [src/plugins/arithmetic/](src/plugins/arithmetic/) | ARI plugin module |
| [src/plugins/linda_fallacy/](src/plugins/linda_fallacy/) | Linda Fallacy plugin module |
| [src/plugins/cellular_automata_1d/](src/plugins/cellular_automata_1d/) | C14 plugin module |
| [src/plugins/ascii_shapes/](src/plugins/ascii_shapes/) | ASCII Shapes plugin module |
| [src/plugins/object_tracking/](src/plugins/object_tracking/) | Object Tracking (Grape Test) plugin |
| [src/plugins/sally_anne/](src/plugins/sally_anne/) | Sally-Anne false belief test plugin |
| [src/plugins/carwash/](src/plugins/carwash/) | Carwash Paradox plugin |
| [src/plugins/inverted_cup/](src/plugins/inverted_cup/) | Inverted Cup plugin |
| [src/plugins/strawberry/](src/plugins/strawberry/) | Character-level reasoning plugin (6 sub-types) |
| [src/plugins/measure_comparison/](src/plugins/measure_comparison/) | Quantity comparison plugin (incl. decimal framing) |
| [src/plugins/grid_tasks/](src/plugins/grid_tasks/) | Table reasoning plugin |
| [src/plugins/time_arithmetic/](src/plugins/time_arithmetic/) | Time Arithmetic plugin (temporal reasoning) |
| [src/plugins/misquote/](src/plugins/misquote/) | Misquote Attribution plugin (sycophancy detection) |
| [src/plugins/false_premise/](src/plugins/false_premise/) | False Premise plugin (dangerous/impossible premise detection) |
| [src/plugins/family_relations/](src/plugins/family_relations/) | Family Relations plugin (perspective-aware counting) |
| [src/plugins/encoding_cipher/](src/plugins/encoding_cipher/) | Encoding & Cipher Decoding plugin (Base64, Caesar, Morse) |
| [src/plugins/symbol_arithmetic/](src/plugins/symbol_arithmetic/) | Symbol Arithmetic plugin (custom operation tables) |
| **3-Stage Pipeline** | |
| [src/stages/generate_testset.py](src/stages/generate_testset.py) | Stage 1: Test set generation (uses plugins) |
| [src/stages/run_testset.py](src/stages/run_testset.py) | Stage 2: Test execution (uses plugins) |
| [src/stages/analyze_results.py](src/stages/analyze_results.py) | Stage 3: Analytics and reporting |
| **Core Infrastructure** | |
| [src/core/types.py](src/core/types.py) | All config classes, types, difficulty levels |
| [src/core/PromptEngine.py](src/core/PromptEngine.py) | System prompts + enums (user templates deprecated → plugins) |
| [src/core/TestGenerator.py](src/core/TestGenerator.py) | Test case generation with 1,061 real-world patterns + known patterns |
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
`create_model_interface(provider, model_name, ...)` creates the right interface from a provider string.

### 3. Strategy Pattern
Different prompt/system styles are interchangeable via plugin-local `prompts.py` template dicts and base class helpers. Multi-strategy parsing in parsers (6 strategies for ARI, 4 for GoL).

### 4. Template Method
`ModelInterface` defines the `query(prompt, params)` contract; subclasses implement it.

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

- `safe_enum(enum_cls, value, default)` — parse string to enum with fallback (used by all 12 generators)
- `re_search_last(pattern, text)` — drop-in replacement for `re.search()` that returns the last match
- `strip_verification_tail(text)` — removes trailing verification/confirmation sections before end-first matching (v2.10.3)
- `last_sentences(text, n)` — returns the last N sentences
- `last_keyword_position(text, keywords)` — position of last keyword occurrence
- `merge_keywords(keyword_dict, language)` — merge English + target language keyword lists (English always included as fallback)
- `merge_patterns(pattern_dict, language)` — merge compiled regex pattern lists
- `get_language(task_params)` — extract language from task_params (default `"en"`)
- `build_word_to_int(language)` — multilingual number word→int map (EN + target language merged)
- `build_answer_label_re(language)` — multilingual answer label regex alternation (`"answer|result|respuesta|resultado|..."`)
- Shared multilingual dicts: `WORD_TO_INT`, `ANSWER_LABELS`, `YES_WORDS`, `NO_WORDS` — all 6 languages

**Key exceptions where end-first does NOT apply:**

- `object_tracking` bold_keyword and first_sentence_location — uses FIRST match because models bold the answer in the first sentence, then mention distractor locations in explanations
- `time_arithmetic` validity parsing — uses first-bold and first-sentence yes/no detection because models answer "No"/"Yes" upfront for existence questions
- `measure_comparison` value+unit matching — both options are mentioned, the answer is identified by which matches, not position
- `measure_comparison` decimal type — uses a separate 5-strategy parser (`_parse_decimal`) with end-first bare-value matching
- `inverted_cup` classification — if "flip" is mentioned anywhere, the model understood the key insight (correct answer); "wrong" keywords alongside flip are just creative alternatives
- `linda_fallacy` — extracts ordered rankings, not single answers
- `false_premise` first-sentence refusal — uses FIRST sentences because models lead with "I can't help..." then explain at length; also uses negation-aware compliance detection and safe-alternative section filtering

**Validated**: Re-parsed 1,933 results across 33 files. Zero true regressions from end-first changes. See [CHANGELOG.md](CHANGELOG.md) for detailed parser fix history (v2.10.3–v2.10.7).

---

### 7. Multilingual Content & Grammar System (v2.15.0+)

All 18 plugins generate test content in 6 languages. Each plugin has:
- **`prompts.py`** — user prompt templates per language × style
- **`i18n.py`** or **`*_i18n.py`** — localized vocabulary, question templates, scenario narratives
- **`data/`** — per-language word lists, data files

**Grammar resolution** for gendered languages (UA, ES, FR, DE) via `src/plugins/grammar_utils.py`:
- `article(lang, gender, definite, case)` — returns correct article (el/la, le/la, der/die/das)
- `resolve_vocab(en_key, vocab_dict, lang, case)` — returns case-inflected form (Ukrainian nom/acc/loc)
- `pick_templates(template_dict, lang, gender)` — selects m/f template variants
- `vocab_gender(en_key, vocab_dict, lang)` — gets grammatical gender of a noun

**Subject gender** is randomly assigned (m/f) per test case and stored in `task_params["subject_gender"]`.

### 8. LLM-as-a-Judge (v2.16.0)

Audit incorrect model responses via a judge LLM:
- **Backend**: `src/web/judge.py` — `run_judge_worker()` + default system/user prompts
- **API**: `POST /api/results/judge`, `GET /api/results/judge-results`, `GET /api/results/judge-results/{filename}`
- **Frontend**: `/judge` page with file selector, summary dashboard, filterable judgments table, JSONL/Markdown export
- **Verdicts**: `true_incorrect`, `false_negative`, `parser_failure` (with issue sub-types)
- **Export**: Markdown report structured for agent consumption — grouped by task type, with language, response samples, and actionable summary

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

3. **Create `prompts.py`** (plugin-local user prompt templates — nested dict, NOT tuple keys):
   ```python
   USER_PROMPT_TEMPLATES = {
       "en": {"minimal": "...", "casual": "...", "linguistic": "..."},
       "es": {"minimal": "...", "casual": "...", "linguistic": "..."},
       # ... all 6 languages
   }
   ```

4. **Create `generator.py`** (test case generation):
   ```python
   from src.plugins.base import TestCaseGenerator, TestCase, ConfigField
   from .prompts import TEMPLATES

   class NewTaskGenerator(TestCaseGenerator):
       def generate_batch(self, config, prompt_config, count, seed):
           user_prompt, system_prompt, full_prompt = self._build_prompts(
               TEMPLATES, language, user_style, system_style, **vars
           )
           return [TestCase(...), ...]

       def get_config_schema(self) -> list[ConfigField]:
           return [
               ConfigField(name='count', label='Number of cases', field_type='number',
                           default=10, min_value=1, max_value=200),
           ]
   ```

5. **Create `parser.py`** (response parsing with multi-strategy):
   ```python
   from src.plugins.base import ResponseParser, ParsedAnswer

   class NewTaskParser(ResponseParser):
       def parse(self, response: str, task_params: Dict) -> ParsedAnswer:
           # Try multiple parsing strategies
           return ParsedAnswer(value=..., raw_response=response, parse_strategy='...')
   ```

6. **Create `evaluator.py`** (result evaluation):
   ```python
   from src.plugins.base import ResultEvaluator, EvaluationResult

   class NewTaskEvaluator(ResultEvaluator):
       def evaluate(self, parsed_answer, expected_answer, task_params) -> EvaluationResult:
           # Evaluate correctness
           return EvaluationResult(correct=..., match_type='...', accuracy=...)
   ```

7. **Done!** No changes to `PromptEngine.py` needed. Plugin auto-discovered by registry.

### New Model Provider

1. **Create interface** in `src/models/NewProviderInterface.py`:
   ```python
   from src.models.BaseModelInterface import ModelInterface

   class NewProviderInterface(ModelInterface):
       def __init__(self, model_name: str, **kwargs):
           self.model_name = model_name

       def query(self, prompt: str, params: dict) -> dict:
           # Must return {"response": str, "duration": float, "model_info": {...}}
           ...
   ```

2. **Register in factory** in [src/models/\_\_init\_\_.py](src/models/__init__.py):
   ```python
   # Add to create_model_interface():
   elif provider == "new_provider":
       return NewProviderInterface(model_name, **kwargs)
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

# Cell markers (GoL only — emoji supported since v2.10.1, but numeric recommended)
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

1. **Emoji markers now work but reduce accuracy**
   - Custom cell markers (including emoji) are supported for GoL (v2.10.1) and C14 (v2.10.2)
   - `--live-dead-cell-markers "1,0"` remains recommended for best model accuracy
   - Emoji markers are a valid robustness test but expect lower scores

2. **`--no-think` is critical for structured tasks**
   - Chain-of-thought hurts performance on GoL/ARI
   - Can improve Linda fallacy reasoning

3. **Ollama must be running**
   - Start with `ollama serve` before benchmarks
   - Connection errors if daemon not running

4. **Model preloading**
   - First query is slow (model loading time)
   - Subsequent queries are cached and faster

5. **Reanalyze must pass language to parser**
   - `reanalyze.py` merges `prompt_metadata` (language, user_style) into `task_params` before re-parsing
   - Without this, parser defaults to English keywords and misses multilingual responses
   - Bug was: `task_params` doesn't contain `language` — it's in `input.prompt_metadata`

6. **FastAPI route ordering matters**
   - Specific routes (`/judge-results`, `/reports`) MUST be declared before `/{filename}` catch-all
   - Otherwise `/{filename}` catches everything — e.g. `/judge-results` matches as `filename="judge-results"`

7. **Testset count = per prompt config**
   - `generate_testset.py` passes `count=total_count` to each `generate_batch()` call
   - Total cases = count × len(prompt_configs)
   - e.g. count=100 with 72 prompt combos → 7,200 total cases

8. **Multilingual evaluators need `expected_answer_localized`**
   - Object Tracking and Sally-Anne store both `expected_answer` (English) and `expected_answer_localized` in task_params
   - Evaluator checks both — if model responds in Ukrainian "тумбочці", it matches localized "тумбочці" even though expected is "nightstand"
   - Match type: `localized_match`

### Import Patterns

After reorganization, use these import patterns:

```python
# Plugin System
from src.plugins import PluginRegistry, ConfigField
from src.plugins.base import (
    BenchmarkPlugin, TestCaseGenerator, ResponseParser, ResultEvaluator,
    TestCase, ParsedAnswer, EvaluationResult, ConfigField
)
from src.plugins.parse_utils import safe_enum, re_search_last, strip_verification_tail, merge_keywords, get_language, build_word_to_int

# Grammar utilities (gendered languages)
from src.plugins.grammar_utils import article, resolve_vocab, pick_templates, vocab_gender

# Plugin-local prompt templates (inside each plugin's generator.py)
from .prompts import USER_PROMPT_TEMPLATES  # Each plugin defines its own (nested dict: lang → style → template)

# Core (PromptEngine: system prompts + enums are active; user templates are deprecated)
from src.core.types import GameOfLifeTestConfig, DifficultyLevel
from src.core.PromptEngine import Language, PromptStyle, SystemPromptStyle  # Active enums
# DEPRECATED: Do NOT import TaskType, PromptContext, PromptResult, create_*_context()
from src.core.TestGenerator import TestGenerator

# Models
from src.models import create_model_interface, ModelInterface
from src.models import OllamaInterface, HuggingFaceInterface, OpenAICompatibleInterface

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
pytest tests/plugins/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Manual Testing

Use the Web UI (`python -m src.web`) or the 3-stage pipeline directly:

```bash
# Generate a test set, run it, then analyze
python src/stages/generate_testset.py configs/my_config.yaml
python src/stages/run_testset.py testsets/testset_xyz.json.gz --model qwen3:0.6b --provider ollama
python src/stages/analyze_results.py results/
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

Use the Web UI (`python -m src.web`) — select Game of Life, configure parameters, and run.
Or use the 3-stage pipeline with a YAML config.

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

1. **Check cell markers**: `"1,0"` recommended (emoji now supported but models perform worse with them)
2. **Inspect raw output**: Add `print(response)` before `parse_response()`
3. **Check prompt**: Ensure format matches expected output
4. **Try simpler test**: Use `--difficulty easy --batch-size 1`

### Q: How do I add support for a new LLM API?

See "New Model Provider" section above. Key steps:
1. Create interface extending `ModelInterface`
2. Implement `query(prompt, params)` method
3. Register in `create_model_interface()` factory in `src/models/__init__.py`

### Q: Where are benchmark results stored?

- **Default**: `results/` at repository root
- **Multi-model runs**: `results/multi_model_TIMESTAMP/`
- **Custom**: Use `--results-dir` flag

### Q: How do I reproduce exact benchmark results?

Use the `seed` parameter in your YAML config or the Web UI. Same seed + same config = identical test cases.

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

# Run quick test via web UI
python -m src.web
# Open http://127.0.0.1:8000/
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
- **Architecture**: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)
- **Research — Quantization**: [docs/research/quantization/EXECUTIVE_SUMMARY.md](docs/research/quantization/EXECUTIVE_SUMMARY.md)
- **Research — Prompt Analysis**: [docs/research/prompt-analysis/RESULTS_REPORT.md](docs/research/prompt-analysis/RESULTS_REPORT.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

*Last updated: 2026-04-06*
*Version: 2.16.0*
*Key additions: LLM-as-a-Judge — new feature for auditing incorrect model responses via judge LLM (true_incorrect / false_negative / parser_failure classification); judge setup sheet with model selection + editable prompts; background job execution; judge output files with summary stats • Multilingual evaluator fix — Object Tracking + Sally-Anne evaluators now accept localized expected answers • Deep multilingual content localization + grammatical gender fix (grammar_utils.py) • Multi-provider Execute, reanalysis, custom system prompts, encrypted credentials • React SPA (Vite 6 + React 19 + TS + Tailwind v4 + shadcn/ui)*
*For questions or issues: Check [README.md](README.md) or create an issue*
