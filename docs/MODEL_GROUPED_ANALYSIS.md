# Model-Grouped Analysis Enhancement

## Overview
Enhanced `analyze_results.py` to support model-centric analysis when processing multiple result files from different tasks. This enables unified comparison reports when analyzing benchmarks across multiple task types.

## Feature Summary

### **Model Grouping Capability**
When using the `--comparison` flag, `analyze_results.py` now:
1. **Groups** result files by model name (and quantization variant)
2. **Aggregates** metrics across all tasks for each model
3. **Generates** unified comparison reports with model-centric views
4. **Shows** task-level breakdowns within each model section

### **Benefits**
- ✅ Single unified report for multi-task benchmarks
- ✅ Easy model comparison across different task types
- ✅ Automatic handling of quantization variants (e.g., Q4_K_M vs full)
- ✅ Task-level performance breakdowns per model
- ✅ Aggregated statistics (accuracy, parse errors, timing)

## Usage

### **Basic Command**
```bash
bin/python -m src.stages.analyze_results \
    results/**/results_*.json.gz \
    --comparison \
    --output reports/model_comparison.md \
    --visualize
```

### **Example Scenarios**

#### **Scenario 1: Compare Models Across Multiple Tasks**
```bash
# You ran:
# - qwen3:0.6b on arithmetic, game_of_life, grid_tasks
# - gemma3:1b on arithmetic, game_of_life, grid_tasks
# - llama2:7b on arithmetic, game_of_life

# Analyze with model grouping:
bin/python -m src.stages.analyze_results \
    results/results_qwen3_arithmetic_*.json.gz \
    results/results_qwen3_gol_*.json.gz \
    results/results_qwen3_grid_*.json.gz \
    results/results_gemma3_arithmetic_*.json.gz \
    results/results_gemma3_gol_*.json.gz \
    results/results_gemma3_grid_*.json.gz \
    results/results_llama2_arithmetic_*.json.gz \
    results/results_llama2_gol_*.json.gz \
    --comparison \
    --output reports/three_model_comparison.md
```

#### **Scenario 2: Analyze All Results with Glob Pattern**
```bash
# Find all result files recursively and group by model
bin/python -m src.stages.analyze_results \
    "results/**/results_*.json.gz" \
    --comparison \
    --output reports/all_models_report.html \
    --visualize \
    --output-dir reports/charts
```

#### **Scenario 3: Without Grouping (Original Behavior)**
```bash
# Per-file analysis (no grouping)
bin/python -m src.stages.analyze_results \
    results/results_qwen3_arithmetic.json.gz \
    --output reports/qwen3_arithmetic_report.md
```

## Report Output

### **Model Comparison Summary Table**
```
| Model          | Result Files | Total Tests | Accuracy | Parse Error Rate | Avg Time/Test | Tasks Covered                  |
|----------------|--------------|-------------|----------|------------------|---------------|--------------------------------|
| gemma3:1b      | 3            | 65          | 72.3%    | 8.1%            | 0.45s         | arithmetic, game_of_life, grid |
| qwen3:0.6b     | 3            | 65          | 68.5%    | 12.4%           | 0.32s         | arithmetic, game_of_life, grid |
| llama2:7b      | 2            | 40          | 65.2%    | 15.3%           | 1.23s         | arithmetic, game_of_life       |
```

### **Per-Model Detailed Analysis**

For each model, the report includes:

1. **Aggregated Metrics**
   - Total tests across all tasks
   - Overall accuracy (weighted by test count)
   - Parse error rate
   - Average execution time
   - Total duration

2. **Task Breakdown Table**
   ```
   | Task Type       | Tests | Correct | Accuracy | Parse Errors |
   |-----------------|-------|---------|----------|--------------|
   | Arithmetic      | 20    | 16      | 80.0%    | 5.0%        |
   | Game of Life    | 25    | 18      | 72.0%    | 8.0%        |
   | Grid Tasks      | 20    | 13      | 65.0%    | 15.0%       |
   ```

3. **Individual Result File Details**
   - Testset name
   - Task type
   - Number of tests
   - Accuracy
   - Execution timestamp

## HTML Report Features

The HTML report (generated alongside markdown) includes:

### **Interactive Dashboard**
- 📊 Model comparison summary cards
- 🎯 Sortable comparison table
- 📈 Per-model metric cards (accuracy, parse errors, timing)
- 📋 Task breakdown with progress bars
- 🎨 Color-coded badges (green = high accuracy, orange = medium, red = low)

### **Visual Elements**
- Gradient metric cards
- Progress bars for task-level accuracy
- Badge indicators for result counts and accuracy levels
- Hover effects on tables
- Responsive grid layout

## Implementation Details

### **New Functions**

#### **`group_results_by_model(results: List[Dict]) -> Dict[str, List[Dict]]`**
Groups result files by model name, handling quantization variants.

**Logic:**
- Extracts `model_name` and `quantization` from each result
- Creates unique keys like `"gemma3:1b (Q4_K_M)"` for quantized models
- Returns dict mapping model keys to lists of result files

#### **`aggregate_model_stats(model_results: List[Dict]) -> Dict`**
Aggregates statistics across multiple result files for the same model.

**Returns:**
```python
{
    'model_name': 'qwen3:0.6b',
    'result_count': 3,
    'task_types': ['arithmetic', 'game_of_life', 'grid_tasks'],
    'total_tests': 65,
    'successful_tests': 62,
    'accuracy': 0.685,
    'parse_error_rate': 0.124,
    'task_breakdown': {
        'arithmetic': {'total': 20, 'correct': 16, 'accuracy': 0.8, ...},
        'game_of_life': {'total': 25, 'correct': 18, 'accuracy': 0.72, ...},
        ...
    },
    'individual_results': [...]  # Original per-file stats
}
```

#### **Updated `generate_markdown_report()` and `generate_html_report()`**
Now accept `grouped_by_model: bool` parameter:
- `True`: Generates model-grouped unified report
- `False`: Falls back to original per-file reporting

### **CLI Integration**

Updated `main()` function:
- `--comparison` flag triggers model grouping
- Warns if comparison mode used with <2 files
- Passes `grouped_by_model` flag through pipeline
- Console summary also supports grouped output

## Testing

Comprehensive test suite in `tests/test_model_grouping.py`:

### **Test Coverage**
1. ✅ **Model Grouping**: Correctly groups 4 results into 2 models
2. ✅ **Statistics Aggregation**: Aggregates 30 tests across 2 tasks
3. ✅ **Quantization Handling**: Separates quantized vs non-quantized variants
4. ✅ **Multiple Task Types**: Handles 3+ different task types

### **Running Tests**
```bash
bin/python tests/test_model_grouping.py
```

**Expected Output:**
```
============================================================
Model Grouping Tests
============================================================

Test 1: Model Grouping
------------------------------------------------------------
✓ Grouped 4 results into 2 models
✓ All models correctly grouped

Test 2: Statistics Aggregation
------------------------------------------------------------
Model: qwen3:0.6b
Result Count: 2
Total Tests: 30
Successful Tests: 26
Overall Accuracy: 61.5%

Task Breakdown:
  Arithmetic: 60.0% (12/20)
  Game of Life: 40.0% (4/10)

✓ Statistics correctly aggregated

Test 3: Quantization Handling
------------------------------------------------------------
Models found: ['gemma3:4b (Q4_K_M)', 'gemma3:4b']
✓ Quantization correctly handled in grouping

Test 4: Multiple Task Types
------------------------------------------------------------
Task types covered: ['arithmetic', 'game_of_life', 'grid_tasks']
✓ Multiple task types correctly handled

============================================================
Results: 4 passed, 0 failed
============================================================
```

## Backward Compatibility

✅ **Fully backward compatible:**
- Without `--comparison`: Original per-file behavior
- Single file analysis: No grouping applied
- Existing scripts: Continue to work unchanged
- Console output: Adapts based on mode

## Future Enhancements

### **Potential Additions**
1. **Model Ranking**: Automatic leaderboard generation
2. **Statistical Significance**: Confidence intervals for accuracy differences
3. **Cost Analysis**: Token usage and cost comparisons
4. **Performance Trends**: Track model improvements over time
5. **Custom Aggregation**: User-defined grouping criteria

### **Visualization Ideas**
- Radar charts comparing models across dimensions
- Heatmaps showing task×model performance matrix
- Time series for execution speed vs accuracy
- Sankey diagrams for parse error flow

## Examples

### **Before (Without Grouping)**
```bash
$ bin/python -m src.stages.analyze_results results/*.json.gz

qwen3:0.6b (arithmetic): 70.0% accuracy
qwen3:0.6b (game_of_life): 55.0% accuracy
gemma3:1b (arithmetic): 75.0% accuracy
gemma3:1b (game_of_life): 68.0% accuracy
```

**Problem:** Hard to see overall model performance across tasks

### **After (With Grouping)**
```bash
$ bin/python -m src.stages.analyze_results results/*.json.gz --comparison

Model-Grouped Summary:
================================================================================

qwen3:0.6b (2 files):
  Total Tests: 50
  Accuracy: 62.5%
  Parse Errors: 10.2%
  Avg Time: 0.32s/test
  Task Breakdown:
    arithmetic: 70.0% acc, 20 tests
    game_of_life: 55.0% acc, 30 tests

gemma3:1b (2 files):
  Total Tests: 50
  Accuracy: 71.5%
  Parse Errors: 7.8%
  Avg Time: 0.45s/test
  Task Breakdown:
    arithmetic: 75.0% acc, 20 tests
    game_of_life: 68.0% acc, 30 tests
```

**Benefit:** Clear model comparison with aggregated metrics

## Version History

- **v2.2.0** (2026-01-25): Initial implementation of model grouping
  - Added `group_results_by_model()` function
  - Added `aggregate_model_stats()` function
  - Enhanced markdown/HTML reports with grouped views
  - Added comprehensive test suite
  - Updated CLI with `--comparison` flag

---

**Related Documentation:**
- [3-Stage Architecture](03_ARCHITECTURE/3_STAGE_ARCHITECTURE_COMPLETE.md)
- [Analyze Results Guide](02_USER_GUIDES/analyze_results_guide.md)
- [Testing Guide](06_REFERENCE/testing_guide.md)
