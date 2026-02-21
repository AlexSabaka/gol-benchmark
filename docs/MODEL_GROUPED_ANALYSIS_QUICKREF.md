# Model-Grouped Analysis Enhancement - Quick Reference

## What's New?

Added `--comparison` flag to `analyze_results.py` that **groups results by model** for unified multi-task analysis.

## Quick Start

```bash
# Analyze multiple result files with model grouping
bin/python -m src.stages.analyze_results \
    results/**/results_*.json.gz \
    --comparison \
    --output reports/model_comparison.md \
    --visualize
```

## Before vs After

### **Before (Without Grouping)**
```
qwen3:0.6b (arithmetic): 75.0% accuracy
qwen3:0.6b (game_of_life): 60.0% accuracy
gemma3:1b (arithmetic): 82.0% accuracy
gemma3:1b (game_of_life): 70.0% accuracy
```
8 separate entries, hard to compare models overall

### **After (With --comparison)**
```
Model Comparison Summary:
┌─────────────┬──────┬────────┬──────────┬─────────────┐
│ Model       │Files │Tests   │Accuracy  │Tasks        │
├─────────────┼──────┼────────┼──────────┼─────────────┤
│gemma3:1b    │2     │45      │76.0%     │arith, gol   │
│qwen3:0.6b   │2     │45      │67.5%     │arith, gol   │
└─────────────┴──────┴────────┴──────────┴─────────────┘

gemma3:1b (aggregated from 2 files):
  Overall: 76.0% accuracy, 8.9% parse errors
  Task Breakdown:
    arithmetic: 82.0% (25 tests)
    game_of_life: 70.0% (20 tests)
```
Unified model view with task breakdowns

## Key Features

✅ **Automatic Grouping**: Groups by model name + quantization variant  
✅ **Aggregated Metrics**: Combined accuracy, parse errors, timing across tasks  
✅ **Task Breakdown**: Per-task performance within each model  
✅ **Beautiful Reports**: Enhanced HTML with badges, progress bars, metric cards  
✅ **Backward Compatible**: Works without --comparison flag (original behavior)

## Report Output

### Markdown (.md)
- Model comparison summary table
- Per-model detailed sections
- Task breakdowns
- Individual file listings

### HTML (.html)
- 🎨 Color-coded metric cards
- 📊 Sortable comparison tables
- 📈 Progress bars for task accuracy
- 🎯 Badge indicators (success/warning/danger)

## Testing

```bash
# Run unit tests
bin/python tests/test_model_grouping.py

# Run interactive demo
bin/python tests/demo_model_grouping.py
```

## Use Cases

1. **Multi-Task Benchmarks**: Compare models across arithmetic, GoL, grid_tasks, etc.
2. **Quantization Studies**: Compare Q4_K_M vs full precision performance
3. **Model Selection**: Identify best model for specific task combinations
4. **Progress Tracking**: Monitor model improvements across multiple dimensions

## Implementation

### New Functions
- `group_results_by_model()`: Groups files by model+quantization
- `aggregate_model_stats()`: Combines metrics across tasks

### Modified Functions
- `generate_markdown_report()`: Added `grouped_by_model` parameter
- `generate_html_report()`: Enhanced with model-grouped views
- `analyze_results()`: Auto-enables grouping with `--comparison`

## Files Changed

- ✅ `src/stages/analyze_results.py` (enhanced)
- ✅ `tests/test_model_grouping.py` (new)
- ✅ `tests/demo_model_grouping.py` (new)
- ✅ `docs/MODEL_GROUPED_ANALYSIS.md` (new)

## Next Steps

Try it on your existing results:
```bash
bin/python -m src.stages.analyze_results \
    "results/**/results_*.json.gz" \
    --comparison \
    --output reports/all_models.html
```

Then open `reports/all_models.html` in your browser! 🚀

---

**Version**: 2.2.0  
**Date**: 2026-01-25  
**Status**: Production Ready ✅
