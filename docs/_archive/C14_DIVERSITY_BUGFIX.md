# C14 Diversity Bug Fix

**Date:** 2026-01-24  
**Issue:** All C14 test cases generated identical initial states  
**Status:** ✅ FIXED

## Problem Description

When generating C14 (1D Cellular Automata) test sets, all test cases were producing identical initial states. For example, in a 10-test batch, all tests had:
```python
initial_state: [0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0]
```

This resulted in all prompts being identical, making the benchmark meaningless.

## Root Cause

**Two interacting bugs in `CellularAutomata1DEngine.py`:**

1. **`generate_random_state()` method**: Included a `seed` parameter that called `random.seed(seed)` on every invocation, resetting the random number generator state.

2. **`generate_test_case()` method**: Passed `self.seed` to `generate_random_state()`, causing all test cases to use the same seed value.

### Code Flow (Before Fix)
```python
# CellularAutomataTestGenerator.__init__
def __init__(self, seed=42):
    self.seed = seed
    random.seed(seed)  # ✅ Initial seeding - correct

# generate_test_case (called 5 times)
for i in range(5):
    initial_state = generate_random_state(width, density, self.seed)
                                                          # ↑↑↑↑↑↑↑↑
    # Inside generate_random_state:
    random.seed(seed)  # ❌ RESET! Always seed=42
    return [random.random() < density for _ in range(width)]
    # Result: Same sequence every time!
```

## Solution

**Remove seed parameter from `generate_random_state()`:**
- Seeding should only happen once in `CellularAutomataTestGenerator.__init__()`
- The random state should persist across multiple calls
- This allows the RNG to produce different sequences for each test case

### Code Changes

**File:** `src/engine/CellularAutomata1DEngine.py`

**Change 1: Remove seed parameter**
```python
# Before
@staticmethod
def generate_random_state(width: int, density: float = 0.5, seed: Optional[int] = None) -> List[int]:
    if seed is not None:
        random.seed(seed)
    return [1 if random.random() < density else 0 for _ in range(width)]

# After
@staticmethod
def generate_random_state(width: int, density: float = 0.5) -> List[int]:
    return [1 if random.random() < density else 0 for _ in range(width)]
```

**Change 2: Don't pass seed argument**
```python
# Before
if initial_pattern == "random":
    initial_state = CellularAutomata1DEngine.generate_random_state(
        width, density, self.seed  # ❌ Causes reset
    )

# After
if initial_pattern == "random":
    initial_state = CellularAutomata1DEngine.generate_random_state(
        width, density  # ✅ No seed = no reset
    )
```

## Validation

### Test Results

**Unit Test (5 test cases with seed=42):**
```
Test 1: [0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0]
Test 2: [1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0]
Test 3: [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1]
Test 4: [0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0]
Test 5: [0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1]

✅ Unique: 5/5 states
```

**Full Pipeline Test:**
Generated complete test set using Stage 1 (`generate_testset.py`):
```
State 1: [0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0]
State 2: [1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0]
State 3: [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1]
State 4: [0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0]
State 5: [0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1]

✅ Unique: 5/5 states
```

## Impact

- **Before Fix:** 0% diversity (all identical states)
- **After Fix:** 100% diversity (all unique states)
- **Reproducibility:** Preserved - same seed still produces same sequence across runs
- **Backward Compatibility:** No changes to public API or config format

## Testing Commands

```bash
# Quick unit test
python /tmp/test_c14_diversity.py

# Full pipeline test
python src/stages/generate_testset.py /tmp/c14_diversity_test.yaml --output-dir /tmp/c14_test/

# Verify diversity in generated test set
python -c "import json, gzip, glob; \
    files=glob.glob('testsets/testset_c14_diversity_test_*.json.gz'); \
    data=json.load(gzip.open(files[0], 'rt')); \
    states=[tc['task_params']['initial_state'] for tc in data['test_cases']]; \
    unique=len(set(tuple(s) for s in states)); \
    print(f'{unique}/{len(states)} unique states')"
```

## Next Steps

Users should **regenerate all existing C14 test sets** that were created before this fix, as they contain only duplicate test cases.

**Regeneration command:**
```bash
# Through TUI (recommended)
python src/cli/benchmark_tui.py

# Or manually
python src/stages/generate_testset.py <your_config>.yaml
```

---

**Fix committed:** 2026-01-24  
**Tested by:** Validation suite + full pipeline test  
**Status:** ✅ Production ready
