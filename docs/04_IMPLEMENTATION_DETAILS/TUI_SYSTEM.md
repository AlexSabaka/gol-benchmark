# Benchmark Testing Automation TUI - Implementation Plan

## Overview

Create a comprehensive Terminal User Interface (TUI) for automating benchmark testing across multiple models, prompt configurations, and task types. The system will handle configuration, test execution, result collection, visualization generation, and reporting.

---

## Architecture Design

### 1. Technology Stack

**TUI Framework:** `rich` + `textual`
- Rich: Beautiful terminal rendering
- Textual: Advanced interactive TUI (screens, widgets, event handling)
- Alternative fallback: `questionary` (simpler, no Textual)

**Data Handling:**
- `dataclasses` for config structures
- `YAML` for config persistence
- `JSON` for results serialization

**Visualization:**
- `matplotlib`, `seaborn`, `pandas` for charts
- Automatic PNG generation at 300 DPI

**Task Execution:**
- `subprocess` for running eval scripts
- Real-time output capture and logging

---

## Component Architecture

```
benchmark_runner_tui.py
├── TUI Layer (Textual)
│   ├── MainMenuScreen
│   ├── ModelSelectionScreen (multi-select)
│   ├── PromptConfigScreen
│   ├── TestParametersScreen
│   ├── RunConfirmationScreen
│   └── ProgressScreen (real-time updates)
│
├── Config Management
│   ├── BenchmarkConfig (dataclass)
│   ├── ModelConfig (dataclass)
│   ├── PromptConfig (dataclass)
│   └── ConfigManager (save/load/validate)
│
├── Test Execution Engine
│   ├── TestRunner (orchestrates execution)
│   ├── EvalScriptWrapper (calls ari_eval.py, gol_eval.py, etc.)
│   └── ResultCollector (aggregates outputs)
│
├── Visualization Engine
│   ├── ChartGenerator (creates plots)
│   ├── HeatmapBuilder
│   ├── RadarChartBuilder
│   └── ComparisonPlotter
│
└── Reporting & Persistence
    ├── ConfigSaver (YAML)
    ├── ResultsPersistence (JSON)
    └── ReportGenerator (markdown summary)
```

---

## Detailed Workflow

### Phase 1: Configuration via TUI

**Main Menu Screen:**
- [ ] Start New Benchmark
- [ ] Load Previous Configuration
- [ ] View Recent Results
- [ ] Exit

**Model Selection Screen:**
- Multi-select checklist of available models
- Filter by: size, family, capability
- Shows: model name, size, parameters, status
- Search functionality

**Prompt Configuration Screen:**
- User Prompt Styles: checkboxes (minimal, casual, linguistic, examples, rules_math)
- System Prompt Styles: checkboxes (analytical, casual, adversarial, none)
- Matrix visualization: shows all combinations
- Count display: "9 configurations selected"

**Test Parameters Screen:**
- [ ] Difficulty levels: 1, 2, 3 (checkboxes)
- [ ] Batch size: number input (default 12)
- [ ] Temperature: slider (0.0 - 1.0, default 0.1)
- [ ] Task types: checkboxes (MEG, GoL, Ari, Linda, C14)
- [ ] Language: dropdown (EN, ES, FR, DE, ZH, UK)
- [ ] Thinking/CoT enabled: toggle

**Output Configuration Screen:**
- Output directory: text input (default ./results_run_TIMESTAMP/)
- Save config: toggle
- Generate charts: toggle
- Report format: checkboxes (markdown, HTML, JSON)
- Verbosity: dropdown (quiet, normal, verbose, debug)

**Run Confirmation Screen:**
- Summary of all selections
- Estimated test count: "432 tests" (4 models × 9 configs × 12 tests)
- Estimated time: "~8 hours at 20min per model"
- Confirm button

### Phase 2: Test Execution

**Progress Screen (Real-time Updates):**
```
Benchmark: AceMath Quantization Study
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall Progress:  [████████░░░░░░░░░░░░] 40%

Current Test:      Model: qwen3:0.6b
                   Config: linguistic + casual
                   Status: Running...
                   
Model Progress:    [████████████░░░░░░░░] 61/108

Results So Far:    
  ✓ qwen3:0.6b (63.89% avg)
  ▶ gemma3:1b (in progress...)
  ○ AceMath (pending)

Elapsed:  02:15:30
ETA:      03:45:00
```

**Execution Engine:**
- Fork subprocess for each test
- Capture stdout/stderr in real-time
- Parse results as they complete
- Handle failures gracefully (retry/skip logic)
- Save partial results periodically

### Phase 3: Visualization Generation

**Automatic Chart Generation:**
1. Heatmap: Model × Config performance
2. Radar: Multi-model comparison
3. Bar charts: By quantization/prompt style
4. Box plots: Distribution analysis
5. Line charts: Performance trends
6. Comparison matrices: Before/after or A/B

**Output:**
- 300 DPI PNG files
- Organized in `results_run_*/` directory
- Automatic index HTML for browsing

### Phase 4: Results & Reporting

**Saved Artifacts:**
```
results_run_20251116_142530/
├── config.yaml                    (exact reproduction config)
├── results.json                   (raw results data)
├── summary_report.md              (findings summary)
├── detailed_report.md             (full analysis)
├── charts/
│   ├── 01_heatmap_all_models.png
│   ├── 02_radar_comparison.png
│   ├── 03_bars_by_config.png
│   └── [etc]
└── index.html                     (interactive viewer)
```

**Report Contents:**
- Executive summary
- Performance leaderboard
- Key findings & insights
- Statistical analysis
- Recommendations
- Configuration details
- Links to all charts

---

## Data Structures

### BenchmarkConfig (Dataclass)

```python
@dataclass
class ModelSpec:
    name: str
    tags: List[str]  # ["1b", "qwen", "math", "quantized"]
    
@dataclass
class PromptSpec:
    user_styles: List[str]  # ["minimal", "casual", "linguistic"]
    system_styles: List[str]  # ["analytical", "casual", "adversarial"]

@dataclass
class TestParams:
    difficulties: List[int]  # [1, 2, 3]
    batch_size: int  # 12
    temperature: float  # 0.1
    task_types: List[str]  # ["MEG", "GoL", "Ari"]
    language: str  # "en"
    thinking_enabled: bool
    
@dataclass
class BenchmarkConfig:
    name: str
    description: str
    models: List[ModelSpec]
    prompts: PromptSpec
    params: TestParams
    output_dir: str
    save_config: bool
    generate_charts: bool
    report_formats: List[str]  # ["markdown", "html", "json"]
    verbosity: str  # "normal"
    timestamp: str
```

---

## Implementation Steps

### Step 1: Set Up Dependencies
```bash
pip install textual rich pyyaml pytest
```

### Step 2: Create Config Management Module
- `benchmark_config.py` - dataclasses + ConfigManager

### Step 3: Create TUI Framework
- `benchmark_tui.py` - Textual screens + navigation

### Step 4: Create Test Runner
- `test_executor.py` - subprocess management + result collection

### Step 5: Create Visualization Engine
- `visualization_engine.py` - automatic chart generation

### Step 6: Create Main Orchestrator
- `benchmark_runner_tui.py` - ties everything together

### Step 7: Testing & Polish
- Handle edge cases
- Add error recovery
- Optimize performance

---

## User Experience Flow

```
START
  ↓
[Main Menu]
  ↓ (New Benchmark)
[Model Selection] → Multi-select from available models
  ↓
[Prompt Config] → Select user & system prompt styles
  ↓
[Test Parameters] → Set difficulty, temperature, batch size, etc.
  ↓
[Output Config] → Choose output directory, formats
  ↓
[Confirmation] → Review all selections, estimated time
  ↓ (Confirm)
[Progress Screen] → Real-time progress with live updates
  ↓ (Complete)
[Results Screen] → Summary of findings + links to charts
  ↓
[Save Results] → Config + results + charts saved to disk
  ↓
END
```

---

## Key Features

### 1. **Model Selection**
- Automatic detection from MODEL_CATALOG.md
- Multi-select with filtering
- Shows model details (size, family, type)
- Quick presets: "Quick Test (3 models)", "Full Suite (20 models)"

### 2. **Prompt Combinatorics**
- Visual matrix showing all possible combinations
- Auto-calculates total test count
- Validation: prevents invalid combinations

### 3. **Real-time Feedback**
- Live progress bar with ETA
- Current test status
- Results accumulating in real-time
- Can pause/resume between models

### 4. **Reproducibility**
- All configs saved to YAML
- Can load and re-run previous configs
- Diff tool to compare configs
- Full command used for each test

### 5. **Automatic Analysis**
- Generates charts as tests complete
- Identifies best/worst configurations
- Computes statistical summaries
- Flags anomalies/interesting findings

### 6. **Result Persistence**
- Timestamped run directories
- Config saved for reproduction
- Raw + processed results
- Multiple export formats

---

## Advanced Features (Phase 2)

- [ ] Result comparison (run1 vs run2)
- [ ] Trend analysis across multiple runs
- [ ] Interactive result browser (web interface)
- [ ] Email alerts on completion
- [ ] Slack integration
- [ ] Database backend for long-term tracking
- [ ] Collaborative result sharing

---

## Edge Cases & Error Handling

1. **Model availability** - Check ollama ls before using
2. **Failed tests** - Retry logic, partial result handling
3. **Disk space** - Check before generating visualizations
4. **Timeout** - Maximum test duration per model
5. **Interrupted runs** - Save progress, allow resume
6. **Invalid config** - Validation before execution
7. **Missing dependencies** - Clear error messages + fix suggestions

---

## Success Criteria

✅ TUI is intuitive and fast to navigate
✅ All configurations properly saved/loaded
✅ Tests execute reliably with real-time progress
✅ Charts auto-generate correctly
✅ Reports are professional and insightful
✅ Full reproducibility (can re-run from saved config)
✅ Handles 100+ tests without issues
✅ Estimated time accuracy ±30%

