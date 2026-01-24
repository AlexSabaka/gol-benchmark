# File Management Refactoring

## Overview

The benchmark suite now uses a centralized `PathManager` for all file and directory operations, providing:

✅ **Consistent naming conventions** - Descriptive filenames with task types, models, and metadata  
✅ **Organized directory structure** - Clean separation of configs, testsets, and results  
✅ **Better traceability** - Run metadata tracking and searchable history  
✅ **No scattered mkdir** - Single source of truth for directory creation  

## New Directory Structure

```
workspace/
├── configs/
│   └── testsets/              # YAML configs for test generation
│       └── baseline_ari-gol_20260123_143000.yaml
├── testsets/                  # Generated test sets (compressed JSON)
│   └── testset_baseline_ari-gol_a3f5c2_20260123_143000.json.gz
├── results/
│   ├── runs/                  # Individual test runs
│   │   └── baseline_ari-gol_qwen3-gemma3_run_abc123_20260123_143000.json.gz
│   └── reports/               # Analysis reports and visualizations
│       ├── comparison_20260123_143000.md
│       ├── comparison_20260123_143000.html
│       └── comparison_20260123_143000_charts/
│           ├── performance_dashboard.png
│           └── error_analysis.png
└── .benchmark_metadata/       # Internal run tracking (git-ignored)
    └── run_abc123.json
```

## File Naming Conventions

### Test Set Configs
Format: `{name}_{tasks}_{timestamp}.yaml`
Example: `baseline_ari-gol_20260123_143000.yaml`

### Generated Test Sets  
Format: `testset_{name}_{tasks}_{hash}_{timestamp}.json.gz`
Example: `testset_baseline_ari-gol_a3f5c2_20260123_143000.json.gz`

### Results Files
Format: `{testset}_{models}_run_{id}_{timestamp}.json.gz`
Example: `baseline_ari-gol_qwen3-gemma3_run_abc123_20260123_143000.json.gz`

### Reports
Format: `{name}_{timestamp}.{format}`
Example: `multi_model_comparison_20260123_143000.md`

## Usage

### Python API

```python
from src.utils.path_manager import get_path_manager

# Get the path manager instance
path_mgr = get_path_manager()

# Generate paths for different file types
config_path = path_mgr.get_testset_config_path(
    name="baseline",
    task_types=["arithmetic", "game_of_life"]
)

testset_path = path_mgr.get_testset_path(
    config_name="baseline",
    task_types=["ari", "gol"],
    config_hash="a3f5c2"
)

results_path = path_mgr.get_results_path(
    models=["qwen3:0.6b", "gemma3:1b"],
    testset_name="baseline_ari-gol"
)

report_path = path_mgr.get_report_path(
    report_name="comparison",
    format="md"
)

viz_dir = path_mgr.get_visualization_dir(
    report_name="comparison"
)
```

### Run Metadata Tracking

```python
from src.utils.path_manager import RunMetadata

# Save run metadata for traceability
metadata = RunMetadata(
    run_id="abc123",
    timestamp="2026-01-23T14:30:00",
    models=["qwen3:0.6b"],
    task_types=["arithmetic", "game_of_life"],
    testset_path="testsets/baseline_ari-gol_a3f5c2.json.gz",
    description="Baseline evaluation on small models",
    config_hash="a3f5c2"
)
path_mgr.save_run_metadata(metadata)

# Retrieve recent runs
recent_runs = path_mgr.get_recent_runs(limit=10)
for run in recent_runs:
    print(f"{run.timestamp}: {run.description}")
```

## Migration Notes

### Before (Old Style)
```python
# Scattered mkdir calls
Path("results").mkdir(parents=True, exist_ok=True)
Path("configs/testsets").mkdir(parents=True, exist_ok=True)

# Unclear filenames
filename = f"results_model_20260123_143000.json.gz"

# No metadata tracking
# No easy way to find related files
```

### After (New Style)
```python
# Centralized path management
path_mgr = get_path_manager()
results_path = path_mgr.get_results_path(
    models=["qwen3:0.6b"],
    testset_name="baseline_ari-gol"
)

# Descriptive filenames automatically generated
# Metadata tracked in .benchmark_metadata/
# Easy to find and correlate runs
```

## Benefits

### For Users
- **Clear organization**: Know exactly where files are
- **Descriptive names**: Understand what's in a file from its name
- **Easy cleanup**: Standard structure makes it simple to clean old runs
- **Run history**: Track what has been tested and when

### For Developers
- **Single source of truth**: All path logic in one place
- **Consistent patterns**: Same API across all modules
- **Easier testing**: Can inject test workspace root
- **Maintainable**: Changes to naming/structure happen in one file

## Backward Compatibility

The new PathManager maintains backward compatibility:
- Old import paths still work via module aliasing
- Existing result files can still be analyzed
- CLI interfaces remain unchanged

## Future Enhancements

Potential improvements to PathManager:
- Archive old runs automatically
- Search runs by model, task type, date range
- Export run history as CSV/database
- Integration with experiment tracking tools
- Cloud storage backends (S3, GCS)
