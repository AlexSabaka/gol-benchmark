# Sally-Anne False Belief Test - Bug Fixes Summary

**Date**: January 26, 2026  
**Status**: ✅ RESOLVED - All tests passing, generation working

## Issues Encountered & Fixes

### 1. DeprecationWarning: format_grid import ✅ FIXED

**Problem**: 
```
DeprecationWarning: src.benchmarks.gol_eval is deprecated. Please use src.stages.generate_testset or plugin system.
  from src.benchmarks.gol_eval import format_grid
```

**Root Cause**: 
- `generate_testset.py` imported `format_grid()` from deprecated `src.benchmarks.gol_eval` module
- This import was only used once (line 297) for Game of Life test formatting

**Solution**:
- Removed deprecated import: `from src.benchmarks.gol_eval import format_grid`
- Added inline helper function (lines 33-36):
```python
def format_grid(g, live_cell_mark='1', dead_cell_mark='0'):
    """Format grid with custom markers."""
    return "\n".join([" ".join(map(str, row)) for row in g]).replace('1', live_cell_mark).replace('0', dead_cell_mark)
```

**Files Modified**:
- `src/stages/generate_testset.py` (lines 32-36)

---

### 2. Method Signature Mismatch ✅ FIXED

**Problem**:
```
Plugin generation failed for sally_anne: SallyAnneTestCaseGenerator.generate_batch() 
got an unexpected keyword argument 'config'
```

**Root Cause**:
- Sally-Anne generator used old signature: `generate_batch(self, batch_size=None)`
- Plugin system v2.1.0 requires: `generate_batch(self, config, prompt_config, count, seed)`
- Base class `TestCaseGenerator` in `src/plugins/base.py` defines standard interface

**Solution**:
Updated `SallyAnneTestCaseGenerator` to match base class interface:

1. **Constructor** (lines 15-17):
   - Changed from: `__init__(self, config: Dict, scenario_builder: SallyAnneScenarioBuilder)`
   - Changed to: `__init__(self)` (no-args constructor)

2. **generate_batch signature** (lines 19-45):
   - Changed from: `def generate_batch(self, batch_size: Optional[int] = None) -> List[TestCase]`
   - Changed to: `def generate_batch(self, config: Dict, prompt_config: Dict, count: int, seed: Optional[int] = None) -> List[TestCase]`
   - Moved all config extraction from `__init__` to `generate_batch`
   - Changed instance variables (e.g., `self.objects`) to local variables (e.g., `objects`)

3. **_create_test_case** (lines 117-183):
   - Added `prompt_config` parameter
   - Updated test_id format: `f"sally_anne_{config_name}_{idx:03d}"`
   - Added prompt_metadata with user_style and system_style

4. **Plugin __init__.py** (lines 68-70):
   - Removed `scenario_builder` parameter from `SallyAnneTestCaseGenerator()` call
   - Changed from: `return SallyAnneTestCaseGenerator(config, SallyAnneScenarioBuilder())`
   - Changed to: `return SallyAnneTestCaseGenerator()`

**Files Modified**:
- `src/plugins/sally_anne/generator.py` (lines 15-183)
- `src/plugins/sally_anne/__init__.py` (lines 68-70)

---

### 3. KeyError: 'task_type' in metadata ✅ FIXED

**Problem**:
```
✓ Generated 99 sally_anne test cases
✗ Failed to generate test set: 'task_type'
```

**Root Cause**:
- YAML config used `task_types: ["sally_anne"]` (plural)
- Pipeline code expected `task_type: "sally_anne"` (singular)
- Line 909 in `generate_testset.py`: `"task_type": config['metadata']['task_type']`

**Solution**:
Added flexible metadata handling (lines 903-911):
```python
# Handle task_type vs task_types in metadata
if 'task_type' in config['metadata']:
    metadata_task_type = config['metadata']['task_type']
elif 'task_types' in config['metadata']:
    metadata_task_type = config['metadata']['task_types'][0] if isinstance(config['metadata']['task_types'], list) else config['metadata']['task_types']
else:
    metadata_task_type = task_type  # Fallback to derived task type
```

**Files Modified**:
- `src/stages/generate_testset.py` (lines 903-911)

---

### 4. Integration Test Updates ✅ FIXED

**Problem**:
```
TypeError: SallyAnneTestCaseGenerator.__init__() takes 1 positional argument but 3 were given
TypeError: SallyAnneTestCaseGenerator.generate_batch() missing 2 required positional arguments
```

**Root Cause**:
- Tests used old generator signature with `(config, scenario_builder)` constructor
- Tests called `generate_batch(batch_size)` instead of new signature

**Solution**:
Updated test cases to match new generator interface:

1. **test_test_case_generator** (lines 140-160):
```python
# Added prompt_config parameter
prompt_config = {
    'name': 'test_config',
    'user_style': 'minimal',
    'system_style': 'analytical',
    'language': 'en'
}

# Updated constructor and method calls
generator = SallyAnneTestCaseGenerator()
test_cases = generator.generate_batch(config, prompt_config, count=3, seed=42)
```

2. **test_end_to_end_plugin_workflow** (lines 330-370):
```python
# Added prompt_config
prompt_config = {
    'name': 'end_to_end_test',
    'user_style': 'minimal',
    'system_style': 'analytical',
    'language': 'en'
}

# Used plugin.get_generator() instead of create_generator()
generator = plugin.get_generator()
test_cases = generator.generate_batch(config, prompt_config, count=2, seed=999)
```

**Files Modified**:
- `tests/test_sally_anne_integration.py` (lines 140-160, 330-370)

---

## Verification

### Test Generation
```bash
$ ./bin/python src/stages/generate_testset.py configs/testsets/sally_anne_demo.yaml --output-dir /tmp/test_sally_anne

Generating multi-task test set with 1 task types
  [1/1] Generating sally_anne tests...
    ✓ Generated 99 sally_anne test cases
✓ Generated test set: /tmp/test_sally_anne/testset_sally_anne_baseline_v1_sally_anne_7d528b53_20260126_120546.json.gz
  - 99 test cases (expected: 99)
  - 3 prompt configs
  - Task types: sally_anne
```

### Sample Test Case
```json
{
  "test_id": "multi_0000_sally_anne",
  "task_type": "sally_anne",
  "prompts": {
    "user": "Ethan puts his marble in the basket.\nEthan leaves the room.\nWhile Ethan is away, David takes the marble from the basket and puts it in the box.\nEthan returns.\n\nWhere will Ethan look for his marble?",
    "system": "...",
    "full": "..."
  },
  "task_params": {
    "subject_a": "Ethan",
    "subject_a_gender": "male",
    "subject_b": "David",
    "subject_b_gender": "male",
    "object": "marble",
    "container_a": "basket",
    "container_b": "box",
    "expected_answer": "basket",
    "reality_trap": "box",
    ...
  }
}
```

### Random Name Examples
```
- Ethan (male) + David (male) → "his marble" 
- Hannah (female) + Frank (male) → "her book"
- Sally (female) + Anne (female) → "her toy"
```

### Integration Tests
```bash
$ ./bin/python tests/test_sally_anne_integration.py

============================================================
SALLY-ANNE FALSE BELIEF TEST - INTEGRATION TESTS
============================================================

✓ Plugin registration verified
✓ Random scenario generation verified
✓ Observer scenario verified
✓ Narrative and question generation verified
✓ Generated 3 test cases
✓ Response parser verified (5 strategies)
✓ Result evaluator verified
✓ Aggregate results: 40% accuracy, 1 reality traps
✓ PromptEngine integration verified
✓ TUI integration verified
✓ analyze_results task extraction verified
✓ End-to-end workflow verified

============================================================
✓ ALL TESTS PASSED
============================================================
```

---

## Summary

**Total Issues**: 4  
**Status**: ✅ All resolved  
**Files Modified**: 4 files, ~50 lines changed  
**Test Coverage**: 12 integration tests passing  

The Sally-Anne false belief test plugin is now fully integrated with the GoL Benchmark plugin system v2.1.0 and ready for production use.

### Key Features Working
- ✅ Random name generation with `names` library
- ✅ Gender-based pronoun handling (he/she/his/her)
- ✅ Configurable leave activities
- ✅ Observer variant option
- ✅ 6 languages × 4 prompt styles = 24 templates
- ✅ Multi-strategy response parsing (5 strategies)
- ✅ Reality trap detection
- ✅ TUI integration (8 configuration parameters)
- ✅ 3-stage pipeline compatibility

### Next Steps
1. ✅ Generate baseline test sets
2. ⏭️ Run on models (Stage 2: `run_testset.py`)
3. ⏭️ Analyze results (Stage 3: `analyze_results.py`)
4. ⏭️ Compare with other Theory of Mind benchmarks
