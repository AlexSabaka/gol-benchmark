# Plugin System Guide

> **Version 2.4.0** | Last updated: 2026-03-24

Comprehensive guide to the GoL Benchmark plugin architecture: how plugins work, reference documentation for all 12 benchmark plugins, and a step-by-step walkthrough for adding new ones.

---

## Table of Contents

- [Plugin Architecture](#plugin-architecture)
- [Auto-Discovery System](#auto-discovery-system)
- [End-First Parsing Convention](#end-first-parsing-convention)
- [Plugin Reference](#plugin-reference)
  - [Game of Life](#1-game-of-life)
  - [Arithmetic](#2-arithmetic)
  - [Linda Fallacy](#3-linda-fallacy)
  - [Cellular Automata 1D](#4-cellular-automata-1d)
  - [ASCII Shapes](#5-ascii-shapes)
  - [Object Tracking](#6-object-tracking-grape-test)
  - [Sally-Anne](#7-sally-anne-test)
  - [Carwash Paradox](#8-carwash-paradox)
  - [Inverted Cup](#9-inverted-cup)
  - [Strawberry](#10-strawberry-letter-counting)
  - [Measure Comparison](#11-measure-comparison)
  - [Grid Tasks](#12-grid-tasks)
- [Adding a New Plugin](#adding-a-new-plugin)
- [Integration Points](#integration-points)
- [Testing Plugins](#testing-plugins)

---

## Plugin Architecture

### Overview

```
PluginRegistry (auto-discovers at first access)
    │
    ├── game_of_life ──▶ GameOfLifePlugin
    │                       ├── GoLTestCaseGenerator    → List[TestCase]
    │                       ├── GoLResponseParser       → ParsedAnswer
    │                       └── GoLResultEvaluator      → EvaluationResult
    │
    ├── arithmetic ────▶ ArithmeticPlugin
    │                       ├── ArithmeticTestCaseGenerator
    │                       ├── ArithmeticResponseParser
    │                       └── ArithmeticResultEvaluator
    │
    ├── carwash ───────▶ CarwashPlugin
    │                       ├── CarwashGenerator
    │                       ├── CarwashParser
    │                       └── CarwashEvaluator
    │
    └── ... (12 plugins total)
```

### Base Classes

Defined in `src/plugins/base.py`:

| Class | Type | Key Methods |
|-------|------|-------------|
| `BenchmarkPlugin` | ABC | `task_type` (property), `display_name` (property), `description` (property), `version` (property), `get_generator()`, `get_parser()`, `get_evaluator()`, `get_config_class()`, `validate_config()` |
| `TestCaseGenerator` | ABC | `generate_batch(config, prompt_config, count, seed)` → `List[TestCase]`, `get_default_config()`, `get_config_schema()` → `List[ConfigField]` |
| `ConfigField` | dataclass | Field descriptor for web UI forms. Fields: `name`, `label`, `field_type`, `default`, `help`, `group`, `min_value`, `max_value`, `step`, `options`, `range_min_default`, `range_max_default`, `weight_keys`. Method: `to_dict()` |
| `ResponseParser` | ABC | `parse(response, task_params)` → `ParsedAnswer`, `get_strategies()` |
| `ResultEvaluator` | ABC | `evaluate(parsed_answer, expected_answer, task_params)` → `EvaluationResult`, `aggregate_results(results)` |

### Data Structures

**TestCase** — standard format for all test cases:

| Field | Type | Description |
|-------|------|-------------|
| `test_id` | `str` | Unique identifier (e.g., `"gol_0001"`) |
| `task_type` | `str` | Benchmark type (e.g., `"game_of_life"`) |
| `config_name` | `str` | Prompt configuration name |
| `prompts` | `Dict[str, str]` | Keys: `"system"`, `"user"`, `"full"` |
| `task_params` | `Dict[str, Any]` | Task-specific parameters + expected answer |
| `prompt_metadata` | `Dict[str, str]` | Language, user_style, system_style |
| `generation_metadata` | `Dict[str, Any]` | Seed, timestamp, version |

**ParsedAnswer** — result of parsing a model response:

| Field | Type | Description |
|-------|------|-------------|
| `value` | `Any` | Extracted answer (type depends on task) |
| `raw_response` | `str` | Original model response |
| `parse_strategy` | `str` | Name of strategy that succeeded |
| `confidence` | `float` | 0.0–1.0, default 1.0 |
| `error` | `Optional[str]` | Error message if parsing failed |
| `.success` | property | `True` if `error is None and value is not None` |

**EvaluationResult** — result of evaluating correctness:

| Field | Type | Description |
|-------|------|-------------|
| `correct` | `bool` | Whether the answer is correct |
| `match_type` | `str` | E.g., `"exact"`, `"partial"`, `"parse_error"` |
| `accuracy` | `float` | Score 0.0–1.0 |
| `details` | `Dict[str, Any]` | Task-specific evaluation details |
| `error` | `Optional[str]` | Error message if evaluation failed |

---

## Auto-Discovery System

### How It Works

The `PluginRegistry` (in `src/plugins/__init__.py`) discovers plugins lazily on first access:

1. `PluginRegistry.get("game_of_life")` is called
2. If not yet loaded, `_auto_discover()` runs
3. Scans all subdirectories of `src/plugins/`
4. Skips directories starting with `_` and `__pycache__`
5. Imports `src.plugins.<dirname>` as a module
6. Looks for a module-level `plugin` variable
7. Validates it is a `BenchmarkPlugin` instance
8. Registers it via `PluginRegistry.register(plugin)`

### Registry API

```python
from src.plugins import PluginRegistry

# Get one plugin
plugin = PluginRegistry.get("game_of_life")  # Returns BenchmarkPlugin or None

# Get all plugins
all_plugins = PluginRegistry.get_all()       # Dict[str, BenchmarkPlugin]

# List task types
types = PluginRegistry.list_task_types()     # ["game_of_life", "arithmetic", ...]

# List with metadata
info = PluginRegistry.list_plugins()         # [{"task_type": ..., "display_name": ...}, ...]

# Force reload
PluginRegistry.reload()

# Check for discovery errors
errors = PluginRegistry.get_discovery_errors()  # Non-fatal — other plugins still load
```

### Key Design Decisions

- **Lazy loading**: Plugins are not imported until first registry access. This keeps import-time fast.
- **Non-fatal errors**: If one plugin fails to import, all others still load. Errors are captured in `_discovery_errors`.
- **Convention over configuration**: No registration file. Just export `plugin = MyPlugin()` at module level.
- **No hot-reload**: Call `PluginRegistry.reload()` explicitly if you add plugins at runtime.

---

## End-First Parsing Convention

### The Problem

LLMs reason through problems step-by-step before presenting a final answer. When a model response contains multiple candidate answers, `re.search()` returns the **first** match — which is typically intermediate reasoning, not the final answer.

```
Model response:
  "Let me think... the sum could be 15... wait, I made an error.
   Recalculating: 3 + 4 + 5 = 12. The answer is 12."

re.search(r'\d+', response)  →  "15" (WRONG — intermediate)
re_search_last(r'\d+', response)  →  "12" (CORRECT — final answer)
```

### The Solution

`src/plugins/parse_utils.py` provides drop-in replacements:

```python
from src.plugins.parse_utils import re_search_last, re_findall_last, last_sentences, last_keyword_position

# Drop-in for re.search() — returns LAST match
match = re_search_last(r"answer:\s*(\d+)", response)

# Last N results from findall
matches = re_findall_last(r"\d+", response, n=3)

# Last N sentences
sentences = last_sentences(response, n=3)

# Position of last keyword occurrence
pos = last_keyword_position(response, ["answer", "result", "therefore"])
```

### Where It Applies

Every parser uses end-first search by default. Common patterns:
- Reversed line scanning (iterate lines from bottom)
- `re_search_last()` instead of `re.search()`
- Checking last code block before first
- Taking the last number when multiple appear

### Exceptions

Three plugins deviate from strict end-first parsing:

| Plugin | Exception | Reason |
|--------|-----------|--------|
| `measure_comparison` | `value_unit_match` strategy does NOT reverse | Both options are mentioned in the response. The match identifies *which* option was chosen, not position. |
| `inverted_cup` | "flip" anywhere = correct | If the model mentions "flip" at all, it demonstrated the key insight. Wrong alternatives (drill, cut) don't negate a correct understanding. |
| `linda_fallacy` | Extracts ordered rankings | The task requires parsing a ranked list, not finding a single positional answer. |

### Validation

Re-parsed 1,933 results across 33 result files after implementing end-first parsing:
- **Zero true regressions** from the change
- Carwash accuracy improved from **14.3% → 27.6%** (+13 percentage points)

---

## Plugin Reference

### 1. Game of Life

**Path**: `src/plugins/game_of_life/`
**task_type**: `game_of_life`
**Tests**: Conway's Game of Life next-state prediction

Given an initial grid state, the model must predict the next generation by applying cellular automaton rules (cells with 2-3 neighbors survive, dead cells with exactly 3 neighbors are born, all others die).

**Generator** (`generator.py`):
- Grid sizes by difficulty: EASY 3x3, MEDIUM 5x5, HARD 8x8, NIGHTMARE 10x10
- Configurable cell density and known-pattern ratio
- Uses `GameOfLifeEngine` from `src/engine/` for computing expected state
- Supports known Conway patterns from `data/conways_life/`
- Config: `difficulty_levels`, `density`, `known_patterns_ratio`, `cell_markers`

**Parser** (`parser.py`) — 4 strategies (end-first):
1. `line_scan_reverse` — Scan from end for rows of 0s/1s
2. `marker_search` — Keywords ("next:", "result:", "grid:") from end
3. `digit_extraction` — Rectangular binary pattern from end
4. `last_resort` — All digits arranged into expected grid shape

**Evaluator** (`evaluator.py`):
- Cell-by-cell comparison
- Match types: `exact`, `partial`, `mismatch`, `dimension_mismatch`, `parse_error`
- Accuracy normalized: 50% random chance → 0.0 score

**Quirk**: Emoji markers (`"⚪⚫"`) cause 0% accuracy. Always use `"1,0"`.

---

### 2. Arithmetic

**Path**: `src/plugins/arithmetic/`
**task_type**: `arithmetic`
**Tests**: Mathematical expression evaluation

**Generator** (`generator.py`):
- Uses `MathExpressionGenerator` (expression tree builder) from `src/engine/`
- Complexity levels 1–5, configurable target values
- Operators: `+, -, *, /, %, ^`
- Config: `complexity`, `target_values`, `expressions_per_target`, `mode` (expression/equation)

**Parser** (`parser.py`) — 6 strategies (end-first):
1. `json_unescape_latex` — Handle escaped LaTeX in JSON
2. `latex_boxed` — `\boxed{N}` (last match)
3. `keyword_search` — "answer:", "result:" from reversed lines
4. `equals_pattern` — `= N` patterns (last match)
5. `last_number` — Last standalone number (skips percentages)
6. `answer_patterns` — Regex variants (last match)

**Evaluator** (`evaluator.py`):
- Exact and approximate float matching (tolerance: 1e-9)
- Match types: `exact`, `approximate`, `mismatch`, `conversion_error`, `parse_error`

---

### 3. Linda Fallacy

**Path**: `src/plugins/linda_fallacy/`
**task_type**: `linda_fallacy`
**Tests**: Susceptibility to the conjunction fallacy cognitive bias

A persona is described (e.g., "Linda is a philosophy major, politically active..."), and the model must rank statements by probability. The conjunction "A AND B" must be ranked lower than either component "A" or "B" alone. Ranking it higher = falling for the fallacy.

**Generator** (`generator.py`):
- Uses persona descriptions with culture-aligned scenarios
- Language-to-culture mapping for multilingual support
- Config: `num_options`, `culture_filter`, `personas_per_config`

**Parser** (`parser.py`) — 4 strategies:
1. `explicit_ranking_section` — Headers like "RANKING:", "CLASIFICACION:"
2. `numbered_list_fallback` — Numbered list patterns (`1. ... 2. ...`)
3. `probability_keyword` — "most probable", "least probable" keywords
4. `sentence_extraction` — Persona-related statements

**Evaluator** (`evaluator.py`):
- Checks whether conjunction is ranked higher than components
- Match types: `fallacy_detected` (model avoided fallacy = correct), `no_fallacy` (model fell for it), `conjunction_not_found`, `components_not_found`, `parse_error`
- Reports: `fallacy_rate`, `success_rate`

**End-first exception**: Extracts ordered rankings, not single answers.

---

### 4. Cellular Automata 1D

**Path**: `src/plugins/cellular_automata_1d/`
**task_type**: `cellular_automata_1d`
**Tests**: Wolfram 1D cellular automaton rule application

Given a rule number (0–255), initial binary state, and boundary condition, predict the next generation.

**Generator** (`generator.py`):
- Uses `CellularAutomata1DEngine` / `CellularAutomataTestGenerator` from `src/engine/`
- Rule difficulty tiers: Easy (0, 51, 204, 255), Medium (90, 150, 184), Hard (30, 110, 45)
- Config: `rules`, `width`, `steps`, `boundary` (wrap/dead/alive), `tests_per_rule`

**Parser** (`parser.py`) — 4 strategies (end-first):
1. `marker_search` — "Final Answer:", "Next state:" from end
2. `line_scan` — Reversed scan for space-separated 0s/1s
3. `code_block` — Last code block first
4. `digit_extraction` — Last N binary digits

**Evaluator** (`evaluator.py`):
- Element-by-element comparison
- Match types: `exact`, `partial`, `mismatch`, `length_mismatch`, `parse_error`
- Breakdown by rule number

---

### 5. ASCII Shapes

**Path**: `src/plugins/ascii_shapes/`
**task_type**: `ascii_shapes`
**Tests**: Spatial reasoning on ASCII art

Three question types: dimensions (WxH), symbol count, position query (is symbol at coordinate).

**Generator** (`generator.py`):
- Random shapes with configurable dimensions and symbols
- Uses `AsciiShapesEngine` from `src/engine/`
- Config: `width_range`, `height_range`, `symbols`, `question_types`, `filled_ratio`

**Parser** (`parser.py`) — question-type specific:
- **Dimensions**: Patterns like "8x5", "8 by 5", "width=8, height=5" (end-first)
- **Count**: Numeric patterns, "answer: N", last number fallback
- **Position**: Boolean (yes/no/true/false), end position wins on conflict

**Evaluator** (`evaluator.py`):
- Type-specific evaluation (string match for dimensions, exact int for count, bool for position)
- Detects dimension swap errors (WxH vs HxW)
- Breakdown by question type

---

### 6. Object Tracking (Grape Test)

**Path**: `src/plugins/object_tracking/`
**task_type**: `object_tracking`
**Tests**: Physical state tracking through container inversions

The critical test: when a container (cup) holding an object (grape) is inverted, the object falls out due to gravity and stays at that location. If the container is then moved elsewhere, the object remains where it fell.

**Example**: Grape in cup on counter → cup inverted → grape on counter → cup moved to microwave → **grape is still on counter** (not microwave).

**Generator** (`generator.py`):
- Procedural scenario builder with objects, containers, locations
- Configurable distractor steps and post-inversion moves
- Config: `object`, `container`, `location_initial`, `distractor_count`, `post_inversion_moves`, `sticky_objects`

**Parser** (`parser.py`) — 5 strategies (end-first):
1. `single_word` — Single-word response matching known location
2. `answer_prefix` — "Answer:", "Location:" label lines from end
3. `sentence_pattern` — "{object} is on the {location}" from end
4. `location_keyword` — Last occurrence of known location names
5. `last_word` — Final word in response

**Evaluator** (`evaluator.py`):
- Location string match with synonym normalization
- Match types: `correct`, `wrong`, `parse_error`

---

### 7. Sally-Anne Test

**Path**: `src/plugins/sally_anne/`
**task_type**: `sally_anne`
**Tests**: Theory of Mind — false belief reasoning

Classic false belief scenario: Sally puts marble in basket → Sally leaves → Anne moves marble to box → Sally returns → Where will Sally look?

**Correct answer**: Basket (where Sally *believes* it is). Common error: Box (where it actually is — the "reality trap").

**Key difference from Object Tracking**: Tests mental state attribution, not physical causality.

**Generator** (`generator.py`):
- `SallyAnneScenarioBuilder` creates scenarios with subject pairs, objects, containers, leave activities
- Config: `cases_per_config`, `subject_pairs`, `objects`, `containers`, `distractor_count`, `leave_activities`, `include_observer`

**Parser** (`parser.py`) — 7 strategies (end-first):
1. `boxed` — `\boxed{container}`
2. `bold_markdown` — `**container**`
3. `answer_pattern` — "Answer:", "Solution:" labels
4. `look_pattern` — "will look in the..." from end
5. `last_sentence` — Last sentence containing a container
6. `json` — JSON response parsing
7. `direct_match` — Context-weighted occurrence counting

**Evaluator** (`evaluator.py`):
- Container name match with synonym support
- Match types: `correct`, `reality_trap`, `wrong`, `parse_error`

---

### 8. Carwash Paradox

**Path**: `src/plugins/carwash/`
**task_type**: `carwash`
**Tests**: Practical goal tracking

The carwash is only 50 meters away — should you walk or drive? **Always drive.** The car must be physically present at the carwash. Models naively say "walk" because the distance is short, missing the goal of the trip.

**Generator** (`generator.py`):
- Combinatorial: distances x framings x weather x urgency x transport x question variants
- Self-contained prompt templates (does not use central PromptEngine)
- Multi-prompt styles (minimal, casual, linguistic)

**Parser** (`parser.py`) — 6 strategies (end-first):
1. `boxed` — `\boxed{drive}` / `\boxed{walk}`
2. `bold` — `**drive**` / `**walk**`
3. `label_line` — "Answer:", "Recommendation:", "Decision:"
4. `strong_recommendation` — Strong phrasing patterns
5. `full_text` — Keyword scoring with negation detection; end-position tiebreaker when both "drive" and "walk" appear
6. `last_sentences` — Final 3–5 sentences

**Evaluator** (`evaluator.py`):
- Match types: `correct` (drive), `naive_trap` (walk), `wrong`, `parse_error`

---

### 9. Inverted Cup

**Path**: `src/plugins/inverted_cup/`
**task_type**: `inverted_cup`
**Tests**: Spatial orientation reasoning

A cup with a sealed top and open bottom is already inverted. The correct action is to **flip it over**. Models often suggest impractical alternatives (drilling, cutting, returning to store).

**Generator** (`generator.py`):
- Combinatorial: sources x descriptions x questions x contexts
- Various ways to describe the upside-down cup orientation

**Parser** (`parser.py`) — 6 strategies (end-first):
1. `boxed` — `\boxed{flip}`
2. `bold` — `**flip**`
3. `label_line` — "Answer:", "Solution:", "Action:"
4. `strong_recommendation` — Strong phrasing
5. `full_text` — Keyword scan
6. `last_sentences` — Final sentences

**End-first exception**: If "flip" (or synonyms: turn over, invert, rotate) appears **anywhere** in the response, the model demonstrated the key insight. Wrong keywords (drill, cut, return) only classify the answer as wrong when "flip" is entirely absent.

**Evaluator** (`evaluator.py`):
- Match types: `correct` (flip), `wrong`, `parse_error`

---

### 10. Strawberry (Letter Counting)

**Path**: `src/plugins/strawberry/`
**task_type**: `strawberry`
**Tests**: "How many R's in strawberry?" — counting letter occurrences

**Modes**:
- `real` — Word from curated list, letter is present
- `absent_letter` — Letter NOT in word (answer = 0, a trap)
- `random` — Random character sequence
- `mixed` — Weighted blend (default: 60% real, 20% absent, 20% random)

**Generator** (`generator.py`):
- Curated word list from `data/strawberry_words.txt`, bucketed by length
- Multilingual support (EN, ES, FR, DE, ZH, UA)
- Favors letters that appear more than once (harder counting)
- Config: `mode`, `mixed_weights`, `word_lengths`, `favor_repeated`

**Parser** (`parser.py`) — 7 strategies (end-first):
1. `boxed` — `\boxed{N}`
2. `bold` — `**N**`
3. `label_line` — "Count:", "Answer:", "Result:"
4. `is_n_tail` — "is N" / "are N" at sentence end
5. `last_number` — Last standalone integer
6. `first_number` — First number (fallback)
7. `spelled_out` — Word-to-int: "three" → 3, "zero" → 0 (supports 0–20)

**Evaluator** (`evaluator.py`):
- Exact integer match
- Tracks `off_by` distance for near-misses
- Breakdown by mode (real/absent_letter/random)

---

### 11. Measure Comparison

**Path**: `src/plugins/measure_comparison/`
**task_type**: `measure_comparison`
**Tests**: Comparing two quantities with units

"Which is longer, 0.1 mm or 1 mm?" — models get tripped by decimal precision, digit counts, and unit conversions.

**Comparison types**:
- `same_unit` — Pure numerical comparison (both values share a unit)
- `mixed_unit` — Requires unit conversion (e.g., cm vs inch)
- `equal` — Trick: values are equivalent after conversion (e.g., 1000g vs 1kg)
- `incomparable` — Trick: different physical dimensions (e.g., 98°C vs 2kg)

**Number formats**: integer, decimal (with adversarial traps), fraction

**Unit categories**: length, mass, temperature, volume, speed, time

**Generator** (`generator.py`):
- Unit system with conversion factors for normalization
- Adversarial decimal traps (e.g., "0.9" vs "0.10" — trailing zeros)
- Config: `number_format`, `comparison_type`, `unit_categories`, `decimal_trap_ratio`

**Parser** (`parser.py`) — 9 strategies:
1. `boxed` — `\boxed{answer}`
2. `bold` — `**answer**`
3. `keyword_equal` — "equal", "same", "equivalent" (multilingual)
4. `keyword_incomparable` — "cannot compare", "different dimensions"
5. `label_line` — "Answer:" labels
6. `value_unit_match` — Extract value+unit, match against known options
7. `position_match` — "first" / "second" keywords
8. `last_value_unit` — Last value+unit found
9. `fallback`

**End-first exception**: `value_unit_match` (strategy 6) does NOT reverse because both options are mentioned in the response. Identification is by which option matches, not by position.

**Evaluator** (`evaluator.py`):
- Match types: `correct`, `wrong`, `parse_error`, `correct_equal`, `correct_incomparable`, `missed_equal`, `missed_incomparable`
- Rich aggregation: breakdowns by comparison type, number format, category
- Decimal trap accuracy tracking, position bias analysis

---

### 12. Grid Tasks

**Path**: `src/plugins/grid_tasks/`
**task_type**: `grid_tasks`
**Tests**: Tabular data reasoning — reading formatted tables and answering questions

**Data types**: Sales, HR, grades, inventory tables.
**Question types**: Cell lookups, row sums, column counts, max/min.

**Generator** (`generator.py`):
- Generates formatted text tables with various data types
- Config: row/col ranges, `data_types`, `question_types`, `table_style`

**Parser** (`parser.py`) — 8 strategies (end-first):
1. `boxed_latex` — `\boxed{answer}`
2. `bold_markdown` — `**answer**`
3. `answer_pattern` — Label lines
4. `json_extraction` — JSON response
5. `code_block` — Code block content
6. `quoted` — Quoted strings
7. `last_line` — Last non-empty line
8. `last_number` — Last numeric value

**Evaluator** (`evaluator.py`):
- Normalized value comparison with numeric tolerance
- Match types: `exact`, `approximate`, `wrong`, `parse_error`

---

## Adding a New Plugin

This walkthrough creates a hypothetical `word_scramble` plugin that tests whether models can unscramble anagrams.

### Step 1: Create the Plugin Directory

```bash
mkdir src/plugins/word_scramble
touch src/plugins/word_scramble/__init__.py
touch src/plugins/word_scramble/generator.py
touch src/plugins/word_scramble/parser.py
touch src/plugins/word_scramble/evaluator.py
```

### Step 2: Define the Plugin (`__init__.py`)

```python
"""
Word Scramble Benchmark Plugin

Tests whether models can unscramble anagrammed words.
"""
from src.plugins.base import BenchmarkPlugin
from .generator import WordScrambleGenerator
from .parser import WordScrambleParser
from .evaluator import WordScrambleEvaluator


class WordScramblePlugin(BenchmarkPlugin):
    @property
    def task_type(self) -> str:
        return "word_scramble"

    @property
    def display_name(self) -> str:
        return "Word Scramble"

    @property
    def description(self) -> str:
        return "Tests ability to unscramble anagrammed words."

    def get_generator(self):
        return WordScrambleGenerator()

    def get_parser(self):
        return WordScrambleParser()

    def get_evaluator(self):
        return WordScrambleEvaluator()


# This variable MUST be named 'plugin' for auto-discovery
plugin = WordScramblePlugin()
```

### Step 3: Implement the Generator (`generator.py`)

```python
import random
from typing import Any, Dict, List, Optional

from src.plugins.base import TestCaseGenerator, TestCase


class WordScrambleGenerator(TestCaseGenerator):

    WORDS = ["python", "algorithm", "benchmark", "reasoning", "language"]

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None,
    ) -> List[TestCase]:
        rng = random.Random(seed)
        test_cases = []

        for i in range(count):
            word = rng.choice(self.WORDS)
            chars = list(word)
            rng.shuffle(chars)
            scrambled = "".join(chars)

            user_style = prompt_config.get("user_style", "minimal")
            system_style = prompt_config.get("system_style", "none")
            config_name = prompt_config.get("name", f"{user_style}_{system_style}")

            # Build prompts
            system_prompt = "You are a word puzzle solver." if system_style != "none" else ""
            user_prompt = f"Unscramble this word: {scrambled}"

            test_cases.append(TestCase(
                test_id=f"word_scramble_{i:04d}",
                task_type="word_scramble",
                config_name=config_name,
                prompts={
                    "system": system_prompt,
                    "user": user_prompt,
                    "full": f"{system_prompt}\n\n{user_prompt}".strip(),
                },
                task_params={
                    "scrambled": scrambled,
                    "expected_answer": word,
                },
                prompt_metadata={
                    "user_style": user_style,
                    "system_style": system_style,
                    "language": prompt_config.get("language", "en"),
                },
                generation_metadata={
                    "seed": seed,
                    "index": i,
                },
            ))

        return test_cases

    def get_default_config(self) -> Dict[str, Any]:
        return {"word_list": "default"}

    def get_config_schema(self) -> List[ConfigField]:
        """Return field descriptors for the web UI config form."""
        from src.plugins.base import ConfigField
        return [
            ConfigField(name='word_list', label='Word list', field_type='select',
                        default='default', options=['default', 'advanced']),
        ]
```

### Step 4: Implement the Parser (`parser.py`)

```python
import re
from typing import Any, Dict, List

from src.plugins.base import ResponseParser, ParsedAnswer
from src.plugins.parse_utils import re_search_last, last_sentences


class WordScrambleParser(ResponseParser):

    def parse(self, response: str, task_params: Dict[str, Any]) -> ParsedAnswer:
        if not response or not response.strip():
            return ParsedAnswer(
                value=None, raw_response=response,
                parse_strategy="none", confidence=0.0,
                error="Empty response",
            )

        # Strategy 1: Boxed answer (highest confidence)
        m = re_search_last(r"\\boxed\{(\w+)\}", response)
        if m:
            return ParsedAnswer(
                value=m.group(1).lower(), raw_response=response,
                parse_strategy="boxed", confidence=0.95,
            )

        # Strategy 2: Bold answer
        m = re_search_last(r"\*\*(\w+)\*\*", response)
        if m:
            return ParsedAnswer(
                value=m.group(1).lower(), raw_response=response,
                parse_strategy="bold", confidence=0.90,
            )

        # Strategy 3: "Answer:" label
        m = re_search_last(r"(?:answer|word|result)\s*[:=]\s*(\w+)", response, re.IGNORECASE)
        if m:
            return ParsedAnswer(
                value=m.group(1).lower(), raw_response=response,
                parse_strategy="label_line", confidence=0.85,
            )

        # Strategy 4: Last word in last sentence (lowest confidence)
        sentences = last_sentences(response, n=1)
        if sentences:
            words = re.findall(r"\b[a-zA-Z]+\b", sentences[0])
            if words:
                return ParsedAnswer(
                    value=words[-1].lower(), raw_response=response,
                    parse_strategy="last_word", confidence=0.50,
                )

        return ParsedAnswer(
            value=None, raw_response=response,
            parse_strategy="none", confidence=0.0,
            error="Could not extract answer",
        )

    def get_strategies(self) -> List[str]:
        return ["boxed", "bold", "label_line", "last_word"]
```

### Step 5: Implement the Evaluator (`evaluator.py`)

```python
from typing import Any, Dict, List

from src.plugins.base import ResultEvaluator, ParsedAnswer, EvaluationResult


class WordScrambleEvaluator(ResultEvaluator):

    def evaluate(
        self,
        parsed_answer: ParsedAnswer,
        expected_answer: Any,
        task_params: Dict[str, Any],
    ) -> EvaluationResult:
        if not parsed_answer.success:
            return EvaluationResult(
                correct=False, match_type="parse_error",
                accuracy=0.0, error=parsed_answer.error,
            )

        answer = str(parsed_answer.value).lower().strip()
        expected = str(expected_answer).lower().strip()

        if answer == expected:
            return EvaluationResult(
                correct=True, match_type="exact", accuracy=1.0,
            )

        # Check if it's a valid anagram (right letters, wrong word)
        if sorted(answer) == sorted(expected):
            return EvaluationResult(
                correct=False, match_type="valid_anagram", accuracy=0.0,
                details={"note": "Valid anagram but not the target word"},
            )

        return EvaluationResult(
            correct=False, match_type="wrong", accuracy=0.0,
        )
```

### Step 6: Verify Auto-Discovery

No pipeline changes needed. Verify it works:

```python
from src.plugins import PluginRegistry

# Force reload to pick up the new plugin
PluginRegistry.reload()

assert "word_scramble" in PluginRegistry.list_task_types()

plugin = PluginRegistry.get("word_scramble")
print(plugin.display_name)  # "Word Scramble"
```

### Step 7 (Optional): Add Config Class

If your task has unique configuration beyond the standard fields, add a dataclass to `src/core/types.py`:

```python
@dataclass
class WordScrambleTestConfig(BaseTestConfig):
    word_list: str = "default"
    min_length: int = 4
    max_length: int = 12
```

### Step 8 (Optional): Add PromptEngine Support

If you want your plugin to use the central `PromptEngine` for multilingual prompts, add a `TaskType` entry in `src/core/PromptEngine.py`. Many newer plugins (carwash, inverted_cup, strawberry, measure_comparison) define their own prompt templates within the generator instead.

---

## Integration Points

### Stage 1: Test Set Generation

`src/stages/generate_testset.py` uses plugins for generation:

```python
from src.plugins import PluginRegistry

plugin = PluginRegistry.get(task_type)
if plugin:
    generator = plugin.get_generator()
    test_cases = generator.generate_batch(config, prompt_config, count, seed)
```

Falls back to built-in generators if the plugin system is unavailable.

### Stage 2: Test Execution

`src/stages/run_testset.py` uses plugins for parsing and evaluation:

```python
plugin = PluginRegistry.get(task_type)
parser = plugin.get_parser()
evaluator = plugin.get_evaluator()

# For each test case:
parsed = parser.parse(model_response, test_case["task_params"])
result = evaluator.evaluate(parsed, expected_answer, test_case["task_params"])
```

### Stage 3: Analysis

`src/stages/analyze_results.py` uses evaluator aggregation:

```python
evaluator = plugin.get_evaluator()
summary = evaluator.aggregate_results(all_results)
# Returns: {"accuracy": 0.72, "correct": 36, "total": 50, "match_types": {...}}
```

### Web UI

- `GET /api/plugins` — Lists all registered plugins with metadata
- `GET /api/plugins/{task_type}/schema` — Returns config schema from `generator.get_config_schema()` (field types: number, select, multi-select, text, boolean, range, weight_map)
- `POST /api/testsets/generate` — Calls `plugin.get_generator().generate_batch()`
- `POST /api/jobs` — Submits execution jobs that use plugin parsers/evaluators
- Dynamic configuration forms are rendered from `get_config_schema()` with basic/advanced field grouping

---

## Testing Plugins

### What to Test

1. **Parser with realistic LLM output** — Include reasoning before the answer
2. **Parser with adversarial input** — Wrong answer first, correct at end; empty response; mixed formats
3. **End-first behavior** — Verify the last match wins when multiple candidates exist
4. **Evaluator edge cases** — Correct, wrong, parse_error, task-specific match types
5. **Generator determinism** — Same seed produces identical test cases

### Example Test

```python
import pytest
from src.plugins.word_scramble.parser import WordScrambleParser
from src.plugins.word_scramble.evaluator import WordScrambleEvaluator


class TestWordScrambleParser:
    def setup_method(self):
        self.parser = WordScrambleParser()
        self.task_params = {"scrambled": "nyhopt", "expected_answer": "python"}

    def test_boxed_answer(self):
        response = "The word is \\boxed{python}"
        result = self.parser.parse(response, self.task_params)
        assert result.value == "python"
        assert result.parse_strategy == "boxed"

    def test_end_first_multiple_answers(self):
        response = "Maybe it's typhon... no wait, the answer is python"
        result = self.parser.parse(response, self.task_params)
        # Should extract "python" (last), not "typhon" (first)
        assert result.value == "python"

    def test_empty_response(self):
        result = self.parser.parse("", self.task_params)
        assert not result.success
        assert result.error is not None


class TestWordScrambleEvaluator:
    def setup_method(self):
        self.evaluator = WordScrambleEvaluator()

    def test_correct_answer(self):
        from src.plugins.base import ParsedAnswer
        parsed = ParsedAnswer(value="python", raw_response="python", parse_strategy="boxed")
        result = self.evaluator.evaluate(parsed, "python", {})
        assert result.correct
        assert result.match_type == "exact"
```

### Running Tests

```bash
# Run tests for a specific plugin
pytest tests/plugins/test_word_scramble.py -v

# Run all plugin tests
pytest tests/plugins/ -v

# Run end-first parsing validation
pytest tests/test_parser_end_first.py -v

# Run all tests with coverage
pytest tests/ --cov=src/plugins
```

---

*See also: [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for the full project context, architecture, and research findings.*
