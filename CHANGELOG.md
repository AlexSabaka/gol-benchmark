# CHANGELOG

All notable changes to the GoL Benchmark project.

## [2.6.0] - March 25, 2026

### False Premise Plugin — Dangerous/Impossible Premise Detection

New plugin `src/plugins/false_premise/` — presents questions embedding dangerous or physically impossible premises; the model must refuse instead of complying.

- **5 domains**: chemistry (toxic reactions), medicine (drug interactions), food_safety (dangerous preparations), physics (impossible scenarios), logic (contradictions)
- **6 CSV data files** in `data/false_premise/` with severity levels (LETHAL/SEVERE/MODERATE)
- **Hard mode** for chemistry: removes safety hedging cues, frames as urgent expert-to-expert requests
- **Combinatorial expansion**: scenarios × urgency framings × authority framings for diverse test cases
- **6-strategy end-first parser**: explicit_refusal, compliance_quantity, hedge_detection, impossibility, keyword_scan, fallback
- **3 match types**: `correct_refusal`, `wrong_compliance`, `partial_hedge`
- Per-domain and per-severity aggregation in `aggregate_results()`
- ConfigField schema with count, domains, hard_mode_ratio, severity_filter
- Pipeline integration: `analyze_results.py` task recognition pattern added

### Misquote Attribution Plugin — Sycophancy Detection Benchmark

New plugin `src/plugins/misquote/` — presents famous quotes with false attributions; the model must reject the wrong author instead of agreeing.

- **27-quote × 20-attributor** data pool with domain-mismatch filtering
- **4 framing styles**: `neutral`, `confident`, `authority`, `constraint` — progressively stronger social-pressure traps
- **Two-part question format**: Q1 (attribution correctness) + Q2 (sentiment) to separate sycophancy from contrarianism
- **6-strategy end-first parser**: numbered, labelled, bare pair, keyword inference, partial Q1, fallback
- **5 match types**: `correct`, `contrarian`, `full_sycophancy`, `partial_sycophancy`, `parse_error`
- `commonly_misquoted` metadata flag per quote for fine-grained analysis
- `framing_style` as an experimental axis — analyze which pressure types fool which models
- Pipeline integration: `analyze_results.py` color, test_id pattern, and HTML badge added

### Time Arithmetic Plugin — Temporal Reasoning Benchmark

New plugin `src/plugins/time_arithmetic/` with 7 sub-types:
- **`interval`** — add/subtract duration to a time
- **`crossing_midnight`** — durations that cross the midnight boundary
- **`noon_midnight_trap`** — tricky AM/PM boundary questions (11:50 AM → 12:10 PM = 20 min, not 1h20m). Supports both result-time and duration question modes.
- **`day_of_week`** — modular day-of-week arithmetic with large offsets
- **`impossible_date`** — impossible calendar dates (Feb 30, Apr 31, etc.)
- **`leap_year`** — Feb 29 validity with century/400-year rule traps (2100, 1900, 2000)
- **`dst_trap`** — (advanced, opt-in) DST spring-forward time holes

Key features:
- 6 novel match types: `correct`, `wrong`, `correct_refusal`, `wrong_compliance`, `wrong_refusal`, `parse_error`
- Impossible-question detection: tracks hallucination rate and false refusal rate per model
- Forward/backward direction support with natural-language backward phrasings
- 12h (AM/PM) and 24h time format modes
- Full multilingual support (EN, ES, FR, DE, ZH, UA)
- ConfigField schema for web UI integration
- ±1 minute tolerance for time matching, abbreviation support for day matching

### Bug Fixes

- **Plugin-only task generation error masking**: `generate_tests_via_plugin()` in `generate_testset.py` caught all exceptions silently and returned `None`, causing plugin-only tasks (no built-in fallback) to show a misleading "Unknown task type" error instead of the real exception. Now re-raises for tasks without built-in fallbacks.

## [2.5.0] - March 24, 2026

### Strawberry Plugin — Character-Level Reasoning Family

Expanded the strawberry plugin from single-task letter counting into a full family of 6 character-level reasoning sub-types:

- **`count`** — Original letter-counting task ("How many R's in strawberry?"). Unchanged, backward-compatible.
- **`reverse`** — Spell a word backwards ("What is 'banana' spelled in reverse?")
- **`nth_letter`** — Identify the Nth letter of a word ("What is the 3rd letter of 'algorithm'?")
- **`anagram`** — Decide whether two words are anagrams ("Are 'listen' and 'silent' anagrams?")
- **`pangram`** — Decide whether a sentence is a pangram (uses every letter A–Z)
- **`lipogram`** — Decide whether a sentence avoids a given letter

#### Generator (`src/plugins/strawberry/generator.py`)
- Full rewrite with sub-type dispatch and weighted selection via `sub_type_weights`
- Multilingual question templates for all 6 sub-types × 6 languages (EN/ES/FR/DE/ZH/UA)
- `sub_types` multi-select config (defaults to `["count"]` for backward compatibility)
- Data loaders for 3 new curated data files

#### Parser (`src/plugins/strawberry/parser.py`)
- Sub-type dispatch: count (7-strategy), reverse (5-strategy), nth_letter (6-strategy), boolean (5-strategy shared by anagram/pangram/lipogram)
- All strategies use end-first parsing convention

#### Evaluator (`src/plugins/strawberry/evaluator.py`)
- Sub-type dispatch: integer comparison (count), case-insensitive string match (reverse), char match (nth_letter), boolean match (anagram/pangram/lipogram)
- `sub_type_breakdown` added to `aggregate_results()` — per-sub-type accuracy stats
- `mode_breakdown` and `mean_off_by` preserved for count sub-type

#### New Data Files
- **`data/strawberry_anagram_pairs.txt`** — 76 curated word pairs (47 true anagrams, 29 near-miss non-anagrams). All verified programmatically.
- **`data/strawberry_pangrams.txt`** — 40 sentences (20 true pangrams, 20 near-pangrams with documented missing letters). All verified programmatically.
- **`data/strawberry_lipograms.txt`** — 44 sentences (26 true lipograms across 11 letters, 18 false cases). All verified programmatically.

#### Plugin Metadata
- Display name updated: "Strawberry (Letter Counting)" → "Strawberry (Character Reasoning)"
- Description updated to cover all 6 sub-types

#### Tests
- Expanded from 30 to 121 test cases in `tests/test_strawberry_plugin.py`
- Full coverage: generator (all 6 sub-types, multilingual, seed reproducibility, weighted distribution), parser (count/reverse/nth_letter/boolean strategies), evaluator (all match types, aggregation with sub_type_breakdown), data file integrity verification

---

## [2.4.1] - March 24, 2026

### Bug Fixes

- **Token counting**: `src/web/jobs.py` was using `tokens_generated` for both input and output tokens — input now correctly reads `tokens_input`; Ollama interface in `run_testset.py` now passes `prompt_eval_count` as `tokens_input`
- **API key leak**: Removed debug `print(url)` and `print(headers)` from `src/web/api/models.py` that exposed auth headers to stdout
- **HuggingFace import guard**: `src/models/HuggingFaceInterface.py` referenced undefined `TRANSFORMERS_AVAILABLE` — wrapped `torch`/`transformers` imports in try/except so the module is importable without those dependencies
- **HuggingFace return type**: `query_model()` declared `-> Tuple[str, Dict]` but returned bare `str` — now returns `(response, token_stats)` tuple matching the signature and OllamaInterface behavior
- **Sally-Anne parser signature**: `parse()` used parameter name `metadata` instead of `task_params`, violating the `ResponseParser` base class contract — renamed throughout
- **Bare except clause**: `src/engine/MathExpressionGenerator.py` used `except:` (catches SystemExit, KeyboardInterrupt) — narrowed to `except ImportError:`

### Dead Code Removal

- **Deleted 6 deprecated benchmark scripts** from `src/benchmarks/`: `gol_eval.py`, `ari_eval.py`, `c14_eval.py`, `gol_eval_matrix.py`, plus `.backup` files (~3,500 lines). Only `linda_eval.py` remains (still imported by linda_fallacy generator)
- **Removed unused abstract classes** (`State`, `BaseRulesEngine`) from `src/engine/GameOfLifeEngine.py` — never inherited or imported
- **Removed hardcoded schema fallback** (84 lines): deleted `_TASK_SCHEMAS` dict from `src/web/api/plugins.py` — all 12 plugins implement `get_config_schema()`
- **Removed commented-out Ollama parameters**: 13 dead config lines from `src/models/OllamaInterface.py`

### Simplification

- **New `safe_enum()` utility** in `src/plugins/parse_utils.py` — replaces try/except enum parsing boilerplate across all 12 generators
- **Updated all 12 plugin generators** to use `safe_enum()` for `Language`, `PromptStyle`, and `SystemPromptStyle` parsing

---

## [2.4.0] - March 24, 2026

### Plugin Configuration Schema Introspection

#### ConfigField System (`src/plugins/base.py`)

- **New `ConfigField` dataclass** — structured field descriptors for plugin configuration with 7 field types: `number`, `select`, `multi-select`, `text`, `boolean`, `range`, `weight_map`
- **New `get_config_schema()` method** on `TestCaseGenerator` — returns `List[ConfigField]` describing all configurable parameters
- **Basic/Advanced field grouping** — fields tagged with `group="basic"` or `group="advanced"` for collapsible UI sections

#### All 12 Generators Implement `get_config_schema()`

- `game_of_life`: 5 fields (difficulty, grids, density, known patterns, cell markers)
- `arithmetic`: 4 fields (complexity, expressions per target, target values, mode)
- `cellular_automata_1d`: 5 fields (rules, cases per rule, width, steps, boundary)
- `linda_fallacy`: 3 fields (options, personas, culture filter)
- `ascii_shapes`: 6 fields (question types, width/height range, symbols, labels, filled ratio)
- `object_tracking`: 6 fields (distractors, moves, types, objects, containers, sticky)
- `sally_anne`: 5 fields (cases, distractors, observer, objects, activities)
- `carwash`: 1 field (distances)
- `inverted_cup`: 1 field (description styles)
- `strawberry`: 6 fields (mode, word lengths, favor repeated, min/max, mixed weights)
- `measure_comparison`: 10 fields (format, comparison type, direction, categories, traps, weights)
- `grid_tasks`: 8 fields (cases, rows, cols, data types, question types, table style)

#### Web API: Schema Introspection Endpoint

- **`GET /api/plugins/{task_type}/schema`** introspects `generator.get_config_schema()` directly (hardcoded `_TASK_SCHEMAS` fallback removed in v2.4.1)
- Response includes `fields` array and `groups` list for UI rendering

#### Web UI: Dynamic Collapsible Config Forms

- **New field renderers** in `configure.html` for `boolean`, `range`, and `weight_map` types
- **Field grouping**: basic fields visible by default, advanced fields in collapsed `<details>` sub-section
- **`buildGeneratePayload()`** extended to collect `boolean`, `range`, and `weight_map` values
- **CSS additions**: `.advanced-toggle`, `.range-pair`, `.weight-map-group` styles

#### Tests

- **New `tests/plugins/test_config_schema.py`** — 9 test cases covering `ConfigField.to_dict()` serialization, all-plugins schema validation, field type/name checks, and JSON round-trip

---

## [2.3.0] - March 24, 2026

### Documentation Overhaul

#### New Documentation

- **`docs/PROJECT_OVERVIEW.md`** — Comprehensive project overview covering mission, architecture (3-stage pipeline, plugin system, web UI), all 12 benchmark tasks, model providers, prompt engineering system, key research findings, and known quirks
- **`docs/PLUGIN_GUIDE.md`** — Complete plugin system guide with base class reference, auto-discovery docs, end-first parsing convention, detailed reference for all 12 plugins, step-by-step new-plugin tutorial with working code, integration points, and testing guidance

#### Documentation Reorganization

- **Archived 20 obsolete docs** to `docs/_archive/`: implementation logs, bug fix summaries, and deprecated references (ASCII_SHAPES_IMPLEMENTATION, C14_*, SALLY_ANNE_*, TUI_SYSTEM, SOURCE_CODE_ORGANIZATION, etc.)
- **Flattened `docs/implementation/prompt-engine/`** to `docs/prompt-engine/` — removed empty nesting
- **Updated `docs/README.md`** — Rewritten as clean navigation hub reflecting current structure and all 12 plugins
- **Updated `CLAUDE.md`** — Corrected plugin count (7 → 12), added new plugin references, added new documentation links
- **Updated `CHANGELOG.md`** — Added documentation overhaul entry

#### CLAUDE.md Corrections

- Fixed plugin count from "7 plugins" to "12 plugins" in directory structure
- Added missing plugins to directory structure: object_tracking, sally_anne, strawberry, measure_comparison, grid_tasks
- Added `parse_utils.py` to directory structure
- Updated Additional Resources section with new docs

---

## [2.2.0] - February 21, 2026

### New Plugins – Practical Reasoning Traps

#### Carwash Paradox (`src/plugins/carwash/`)
- New plugin testing whether a model keeps track of the *goal* of a trip
- Scenario: the carwash is only N metres away — should you walk or drive?
- Correct answer is always **drive** (car must be physically present at the carwash)
- Models naively say "walk" because the distance is short (proximity trap)
- **Generator**: 5 distances × 6 framings × 4 weather contexts × 4 urgency phrases × 3 transport details × 6 question variants; full combinatorial space with seeded shuffling
- **Parser**: 6-strategy detection (`boxed → bold → label_line → strong_intro → full_text → first_sentences`); negation-aware regex (`DRIVE_KEYWORDS`, `WALK_KEYWORDS`, `NEGATION`)
- **Evaluator**: match types `correct` / `naive_trap` / `wrong` / `parse_error`
- **TUI**: added to task selector with default `distances` and `count` parameters
- **Report**: `carwash` task type now correctly labelled (amber `#e67e22` in charts)

#### Inverted Cup (`src/plugins/inverted_cup/`)
- New plugin testing spatial/physical orientation reasoning
- Scenario: a cup with a sealed top and open bottom — how do you use it?
- Correct answer is always **flip** (turn it right-side-up)
- Models suggest drilling, cutting, or returning the cup instead
- **Generator**: 7 sources × 7 description styles × 7 action questions × 5 extra contexts; configurable `description_styles` filter via YAML
- **Parser**: 6-strategy detection including 16 `FLIP_PATTERNS` (flip/turn over/invert/upend/right-side-up) and `WRONG_PATTERNS` (drill/cut/return/discard)
- **Evaluator**: match types `correct` / `wrong` / `parse_error`; distinguishes genuine parse failures from confident wrong answers
- **TUI**: added to task selector with default `description_styles` and `count` parameters
- **Report**: `inverted_cup` task type now correctly labelled (dark teal `#16a085` in charts)

### Infrastructure Enhancements

#### Remote Ollama Support (`--ollama-host`)
- Added `--ollama-host` argument to `src/stages/run_testset.py` (default: `http://localhost:11434`)
- `OllamaInterface` in `run_testset.py` now accepts `base_url` parameter
- `OllamaProvider` in `src/utils/model_providers.py` extended with configurable `host`:
  - `_is_default_host()` helper to detect non-local endpoints
  - Non-default hosts always use REST API (`/api/tags`) instead of CLI subprocess
  - `_is_available_via_api()` and `_list_models_via_api()` methods added
  - `_bytes_to_human()` static helper for size formatting
- `ModelProviderManager.set_ollama_host(host)` method for dynamic re-configuration
- TUI (`benchmark_tui.py`) prompts for Ollama host URL whenever Ollama provider is selected
  - `BenchmarkTUI._configure_ollama_host()` method
  - `ollama_host` stored on both `MultiTaskConfig` and `BenchmarkConfig` dataclasses
  - Host propagated through execution pipeline to `run_testset.py` via `--ollama-host`

#### Token Counting in Pipeline
- Response token counts tracked throughout Stage 2 (`run_testset.py`)
- Token counts surfaced in Stage 3 reports via dedicated columns/charts
- Old result files show `0` tokens (expected backward-compatible behaviour)

### Bug Fixes

- **"Unknown" task type in reports**: Fixed `extract_task_breakdown()` in `analyze_results.py`
  - Added `elif '_carwash' in test_id or test_id.startswith('carwash_')` branch
  - Added `elif '_inverted_cup' in test_id or test_id.startswith('inverted_cup_')` branch
  - Display rendering works automatically via `.replace('_', ' ').title()` pattern

---

## [2.1.0] - January 25, 2026

### Plugin-Based Benchmark System

#### Major Architectural Enhancement
- **Complete refactoring** from monolithic benchmarks to plugin-based architecture
- **Plugin registry** with automatic discovery via package scanning
- **Self-contained modules** for each benchmark (generation, parsing, evaluation)
- **Zero-modification extensibility** - add new benchmarks without touching core code

#### Plugin System Components

**Core Infrastructure:**
- `src/plugins/base.py` - Abstract base classes for all plugins
  - `BenchmarkPlugin` - Plugin interface definition
  - `TestCaseGenerator` - Test generation interface
  - `ResponseParser` - Multi-strategy response parsing interface
  - `ResultEvaluator` - Evaluation interface with aggregation
  - `TestCase`, `ParsedAnswer`, `EvaluationResult` - Standardized data structures

- `src/plugins/__init__.py` - Plugin registry with auto-discovery
  - Automatic plugin loading via `pkgutil`
  - Registration and retrieval system
  - Task type mapping

**5 Built-in Plugins:**
1. **Game of Life** (`src/plugins/game_of_life/`)
   - 4-strategy parsing (line_scan_reverse, marker_search, digit_extraction, last_resort)
   - Cell-by-cell accuracy evaluation
   - Grid normalization and validation

2. **Arithmetic** (`src/plugins/arithmetic/`)
   - 6-strategy parsing (LaTeX boxed, JSON unescape, equals pattern, keyword search, etc.)
   - Exact and approximate numeric matching
   - Expression evaluation

3. **Linda Fallacy** (`src/plugins/linda_fallacy/`)
   - Ranking extraction with fuzzy matching
   - Conjunction fallacy detection
   - Cultural/language alignment

4. **Cellular Automata 1D** (`src/plugins/cellular_automata_1d/`)
   - Binary state parsing (4 strategies)
   - Cell-by-cell state comparison
   - Normalized accuracy (2 * (raw - 0.5))

5. **ASCII Shapes** (`src/plugins/ascii_shapes/`)
   - Type-specific parsing (dimensions, count, position)
   - Multiple output formats supported
   - Tolerance-based count evaluation

#### Integration with 3-Stage Pipeline

**Stage 1 (generate_testset.py):**
- Plugin-based test generation with fallback to built-in generators
- `generate_tests_via_plugin()` helper function
- Backward-compatible with legacy generators

**Stage 2 (run_testset.py):**
- Plugin-based parsing with `parse_answer_via_plugin()`
- Plugin-based evaluation with `evaluate_via_plugin()`
- Graceful degradation to legacy parsing if plugin unavailable

**Stage 3 (analyze_results.py):**
- No changes required - works with plugin-generated results

#### Deprecation and Migration

**Legacy Files Deprecated:**
- `src/benchmarks/gol_eval.py` - Use Game of Life plugin
- `src/benchmarks/ari_eval.py` - Use Arithmetic plugin
- `src/benchmarks/linda_eval.py` - Use Linda Fallacy plugin
- `src/benchmarks/c14_eval.py` - Use C14 plugin

**Deprecation warnings added** to all legacy files with migration guidance.

#### Comprehensive Test Suite

**Unit Tests Created:**
- `tests/plugins/test_registry.py` - Plugin discovery and registration
- `tests/plugins/test_game_of_life.py` - GoL plugin (generator, parser, evaluator, roundtrip)
- `tests/plugins/test_arithmetic.py` - ARI plugin with all 6 strategies
- `tests/plugins/test_linda_fallacy.py` - Linda plugin with fallacy detection
- `tests/plugins/test_cellular_automata_1d.py` - C14 plugin with state comparison
- `tests/plugins/test_ascii_shapes.py` - Shapes plugin with type-specific tests

**Test coverage:**
- Plugin auto-discovery
- Component availability (generator, parser, evaluator)
- Valid and invalid input handling
- Exact, partial, and mismatch evaluation
- Full roundtrip tests (generate → parse → evaluate)

### Benefits and Impact

**Code Quality:**
- ✅ Eliminated ~1000+ lines of duplicated code across benchmarks
- ✅ Clean separation of concerns (generation/parsing/evaluation)
- ✅ Standardized data structures across all benchmarks
- ✅ Multi-strategy parsing with fallback mechanisms

**Extensibility:**
- ✅ Add new benchmarks by creating plugin directory (no core code changes)
- ✅ Plugin auto-discovery - just create and it works
- ✅ Self-contained modules - everything in one place
- ✅ Easy to test and maintain

**Backward Compatibility:**
- ✅ Legacy benchmarks still work via fallback
- ✅ 3-stage pipeline unchanged for users
- ✅ Existing configs and test sets compatible
- ✅ Gradual migration path

**Performance:**
- ✅ No performance overhead from plugin system
- ✅ Improved parsing success rates via multi-strategy approach
- ✅ Better error handling and recovery

### Documentation Updates

- **CLAUDE.md** - Updated with plugin system patterns and examples
- **.github/copilot-instructions.md** - Added plugin architecture overview
- **docs/PLUGIN_SYSTEM_REFACTORING.md** - New comprehensive guide (created)

---

## [2.0.0] - January 23, 2026

### Major Architecture Overhaul

#### 3-Stage Architecture Implementation
- **Complete system transformation** from monolithic to modular 3-stage pipeline
- **Stage 1: Test Set Generation** - YAML configs → compressed JSON test sets
- **Stage 2: Portable Test Execution** - minimal dependencies, cloud-ready
- **Stage 3: Analysis & Reporting** - rich analytics with visualizations

#### File Organization & Structure
- **Reorganized project structure**: moved core scripts to `src/stages/`
- **Enhanced module organization**: better separation of concerns
- **Cleaned up root directory**: moved test files to `tests/` folder
- **Consolidated documentation**: merged implementation docs into comprehensive guide

#### Critical Bug Fixes
- **🐛 MAJOR: Game of Life Template Fix**
  - Fixed `{grid_str}` placeholder not being substituted with actual grid data
  - Root cause: Missing `grid_str` variable in `PromptContext` 
  - Impact: Game of Life accuracy expected to improve from 0% to 40-70%
  - Added proper `format_grid()` integration in test set generation

#### TUI System Enhancements  
- **Complete TUI rewrite** to use 3-stage architecture
- **Fixed import path issues** when running from subdirectories
- **Added task type mapping** between short names (ari/gol) and full names
- **Enhanced progress tracking** with stage-by-stage execution feedback
- **Improved error handling** and user experience

#### Enhanced Parsing & Analytics
- **Integrated 6-strategy parsing** from arithmetic evaluation into multi-task system
- **Enhanced arithmetic parsing** with LaTeX boxed patterns and JSON unescaping
- **Fixed task type detection** for proper multi-task execution
- **Added multi-dimensional analysis** across task types, prompt styles, and models

#### Advanced Reporting System
- **6-chart visualization suite**: Performance Dashboard, Accuracy Heatmap, Error Analysis, Efficiency Analysis, Radar Comparison, Enhanced Multi-Task Analysis
- **Harmonized HTML/Markdown reports** with identical content structure
- **Embedded chart support** with proper relative path handling
- **Task-specific breakdowns** with detailed metadata extraction
- **Enhanced multi-task analysis** capabilities

### Added

#### Core Architecture
- `src/stages/generate_testset.py` - Deterministic test set generation from YAML configs
- `src/stages/run_testset.py` - Portable test execution with minimal dependencies
- `src/stages/analyze_results.py` - Comprehensive analysis and reporting engine
- Enhanced 3-stage workflow integration in TUI system

#### Advanced Features
- **Multi-task test set support** with mixed task types (arithmetic + Game of Life)
- **Enhanced parsing strategies** with fallback mechanisms
- **Rich metadata extraction** for comprehensive analysis
- **Task breakdown analysis** with individual performance tracking
- **Prompt style matrix analysis** (3×3 combinations of user/system styles)

#### Documentation & Testing
- `docs/3_STAGE_ARCHITECTURE_COMPLETE.md` - Comprehensive implementation guide
- Enhanced test suite in `tests/` folder with proper organization
- Validation scripts for TUI workflow and component integration

### Fixed

#### Critical System Issues
1. **Game of Life Complete Failure** - 0% accuracy due to `{grid_str}` placeholder bug
2. **Multi-task Execution Errors** - Task type detection and routing issues  
3. **Template Formatting Bugs** - HTML report generation with template string errors
4. **Chart Embedding Failures** - Relative path issues in HTML reports
5. **Import Path Problems** - Module loading from subdirectories
6. **Parse Error Crisis** - Multi-strategy parsing integration for improved accuracy

#### Enhanced Components
- **Prompt generation system** - Fixed template variable substitution
- **Result analysis pipeline** - Enhanced multi-dimensional analysis
- **Visualization engine** - Proper chart embedding and path handling
- **Error reporting** - Better categorization and tracking
- **Progress indicators** - Clear feedback throughout execution

### Changed

#### Major Refactoring
- **Execution Model**: Sequential script calls → 3-stage pipeline architecture
- **File Organization**: Scattered scripts → organized `src/stages/` structure
- **TUI Architecture**: Monolithic execution → modular stage orchestration
- **Documentation**: Multiple scattered files → single comprehensive guide

#### Enhanced User Experience
- **Clearer progress tracking** with stage-specific feedback
- **Better error messages** with actionable guidance
- **Comprehensive summaries** after execution completion
- **Interactive configuration** with validation and preview

### Performance & Quality

#### Significant Improvements
- **Parsing Success Rate**: 0% → 50%+ for Game of Life tasks
- **Multi-task Reliability**: Enhanced accuracy across mixed task types
- **Report Quality**: Basic text → Rich interactive HTML with 6 visualization types
- **System Modularity**: Monolithic → Clean 3-stage separation
- **Reproducibility**: Enhanced with versioned test sets and config hashing

#### Validation Results
- ✅ 10/10 component integration tests passed
- ✅ TUI workflow validation successful
- ✅ Enhanced parsing system operational
- ✅ Multi-task execution pipeline functional
- ✅ Comprehensive reporting and visualization working

### Technical Debt Addressed
- **Code Organization**: Moved from scattered scripts to organized modules
- **Testing Structure**: Consolidated test files in proper `tests/` folder  
- **Documentation**: Merged fragmented docs into comprehensive guide
- **Error Handling**: Enhanced throughout system with better recovery

---

## [1.0.0] - November 16, 2025

### Added

#### TUI System Enhancements
- **Task Selection System**: Interactive selection of benchmark types (ARI, GoL, C14, Linda)
- **Task-Specific Configuration**: Per-task configuration screens with appropriate parameters
- **Config Management**: Save/load configurations in YAML and JSON formats
- **Result Persistence**: Results now saved to timestamped text files
- **Chart Generation**: ASCII bar charts showing model performance comparison
- **Execution Summary**: JSON metadata files tracking all executions

#### Core Functions
- `execute_benchmark()`: Central execution orchestrator for benchmark runs
- `_generate_benchmark_charts()`: Chart generation from result files  
- `_create_ascii_chart()`: ASCII visualization creation
- `task_selection()`: Task type selection interface
- `task_specific_config()`: Task-specific parameter collection

#### Configuration Extensions
- `task_type` field in BenchmarkConfig
- `task_config` field in BenchmarkConfig (task-specific parameters)

#### Model Provider System
- **ModelProviderManager**: Unified provider orchestration
- **OllamaProvider**: Complete Ollama integration with dynamic discovery
- **Dynamic Model Discovery**: 44+ models automatically detected
- **Advanced Filtering**: Filter by family, quantization, size
- **Model Grouping**: Group by family, quantization, or size

#### Execution Improvements
- All models passed in single script invocation (10-12x faster)
- Separate execution per prompt combination (user_style × system_style)
- Real-time output capture and persistence
- Comprehensive error tracking and reporting

### Fixed

#### Critical Bugs
1. **ValueError in Checkbox Defaults** - Fixed questionary.checkbox pattern (7/7 errors fixed)
2. **Missing Task Selection** - Added complete task selection workflow
3. **Generic Parameter Context** - Split into generic + task-specific configuration
4. **Report Formats Crash** - Fixed questionary.Choice pattern
5. **Missing Target Values Input** - Added validation input for ARI tasks
6. **Config Missing Task Fields** - Added task_type and task_config
7. **Incomplete Main Workflow** - Fully implemented main() function

#### Execution Model Issues
- Models now passed together instead of sequentially
- Results properly saved to files
- Charts now generated successfully
- Prompt combinations properly handled

### Changed

#### Major Refactoring
- **execute_benchmark()**: Complete rewrite (169 lines added)
- **main()**: Complete rewrite (55 lines rewritten)
- **Execution Flow**: Changed from sequential model runs to grouped model runs per prompt combination

#### Improved Components
- `prompt_configuration()`: Fixed questionary pattern
- `output_configuration()`: Fixed questionary pattern
- `create_new_benchmark()`: Integrated task selection workflow
- `confirmation_screen()`: Updated to show task information

### Improved

#### Code Quality
- Comprehensive error handling throughout
- Better progress indicators
- Clearer separation of concerns
- Improved console output formatting

#### Performance
- 10-12x faster execution for multi-model benchmarks
- Reduced overhead from multiple script invocations
- Efficient result file writing
- Streaming output to console

#### User Experience
- Better visual feedback during execution
- Clear progress indicators [idx/total]
- Structured result organization
- Easy result file access

### Documentation

#### New Documentation Files
- `docs/PROJECT_DEVELOPMENT_SUMMARY.md`: Comprehensive project overview
- `docs/DEVELOPMENT_LOG.md`: Detailed development history

#### Updated Documentation
- README.md: Maintained with quick start guide
- All module docstrings: Updated for clarity

### Testing & Verification

#### Validation Results
- ✅ 10/10 component checks passed
- ✅ Syntax validation passed
- ✅ Integration tests passed
- ✅ Execution flow tested
- ✅ Error handling verified

#### Test Coverage
- Task selection workflow
- Configuration persistence
- Result file generation
- Chart generation
- Error conditions

## [0.9.0] - Earlier Development

### Previous Phases
- Phase 1: Project initialization and benchmarking
- Phase 2: Repository cleanup and organization  
- Phase 3: TUI system initial development
- Phase 4: Model provider integration
- Phase 5: Completion and refinement (this release)

---

## Known Issues

### Current Limitations

1. **Chart Generation**
   - Basic ASCII charts only
   - Limited customization
   - No interactive visualization

2. **Result Parsing**
   - Regex-based parsing can be fragile
   - Requires consistent output format
   - No structured result API

3. **Error Recovery**
   - Limited recovery from model failures
   - Some edge cases in provider detection

### Future Improvements

1. **Enhanced Visualization**
   - matplotlib/plotly integration
   - Web dashboard
   - Historical comparison

2. **Advanced Analysis**
   - Statistical significance testing
   - Trend analysis
   - Comparative metrics

3. **Extended Providers**
   - OpenAI API
   - Anthropic Claude
   - vLLM integration

4. **Additional Features**
   - Custom benchmark creation
   - Plugin architecture
   - Result aggregation across runs

---

## Migration Guide

### For Users Upgrading from Previous Versions

#### Configuration Files
- Old configurations in `benchmark_configs/` are compatible
- New configurations include `task_type` field
- Recommend regenerating for consistency

#### Results Format
- Results now saved as separate files per prompt combination
- JSON summary includes metadata
- Charts generated automatically if enabled

#### TUI Workflow
- New step added: Task Selection (Step 2)
- New step added: Task-Specific Configuration (Step 4)
- All other steps remain similar

### Breaking Changes

None - backward compatible with existing configurations and scripts.

---

## Contributors

- Development Team
- QA Team
- Community Feedback

---

## Acknowledgments

- OpenAI/Anthropic for LLM technology
- Ollama for local inference
- questionary for interactive CLI
- rich for terminal visualization

---

**For detailed information, see docs/PROJECT_DEVELOPMENT_SUMMARY.md and docs/DEVELOPMENT_LOG.md**
