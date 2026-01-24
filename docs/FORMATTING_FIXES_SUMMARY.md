# Formatting Fixes Summary (2026-01-24)

## Issues Fixed

### 1. ✅ C14 Examples Generation Bug
**Problem**: `{examples}` placeholder appearing literally in EXAMPLES style prompts  
**Root Cause**: `generate_c14_tests()` wasn't setting the `examples` context variable  
**Fix**: Generate 2 example CA evolutions before each test case when `user_style='examples'`

**Implementation**:
```python
# In generate_testset.py, lines ~283-293
if prompt_config['user_style'] == 'examples':
    example_cases = ca_generator.generate_batch(
        rule_numbers=[rule_number],
        width=8,  # Smaller examples
        steps=1,
        cases_per_rule=2
    )
    for i, ex in enumerate(example_cases[:2], 1):
        ex_initial = ' '.join(str(c) for c in ex['initial_state'])
        ex_next = ' '.join(str(c) for c in ex['expected_states'][0])
        examples_text += f"Example {i}:\nCurrent: {ex_initial}\nNext: {ex_next}\n\n"
    context.set('examples', examples_text.strip())
```

**Result**:
```
Example 1:
Current: 0 0 0 0 1 0 0 0
Next: 0 0 0 1 0 1 0 0

Example 2:
Current: 0 0 0 0 1 0 0 0
Next: 0 0 0 1 0 1 0 0
---
Rule 90
Current: 0 1 1 1 0 0 0 1 1 1 1 0 1 1 0 0
Next:
```

---

### 2. ✅ ARI Complexity Refactoring
**Problem**: Confusion between expression depth and target answer values  
**Old Format**: `target_accuracies` represented both complexity and answer value  
**New Format**: Separate `complexity` (expression depth 1-5) and `target_values` (answer numbers)

**YAML Config Changes**:
```yaml
# OLD FORMAT (still supported for backward compatibility)
tasks:
  - type: arithmetic
    generation:
      target_accuracies: [1, 2, 3]  # Both complexity and answer
      expressions_per_target: 10
      
# NEW FORMAT (recommended)
tasks:
  - type: arithmetic
    generation:
      complexity: [2, 3, 4]          # Expression depth (1-5)
      target_values: [0, 5, 10, 100] # What the expression evaluates to
      count: 10                       # Expressions per complexity/target combo
```

**TUI Changes**:
- Complexity selection: 5 checkboxes (1=simple → 5=deeply nested)
- Target values: Comma-separated input (e.g., "0,1,2,5,10")
- Explanatory text to clarify the difference

**Test Case Metadata**:
```json
{
  "task_params": {
    "complexity": 2,           // NEW: Expression depth
    "target_value": 10,        // NEW: What it evaluates to
    "expression": "(-63 - 47) / (1 * -11)",
    "expected_answer": 10,
    "mode": "expression"
  }
}
```

**Backward Compatibility**: Old `target_accuracies` format still works via fallback logic in `generate_arithmetic_tests()`

---

### 3. ✅ C14 Rule Selection (Enhancement)
**Status**: Already working correctly - TUI has full rule difficulty UI  
**Configuration Options**:
- Easy rules: 0, 51, 204, 255 (constant/identity patterns)
- Medium rules: 90, 150, 184 (Sierpiński, complex patterns)
- Hard rules: 30, 110, 45 (chaotic, Class 3/4)
- Custom: Enter specific rule numbers

**Verification**: Test generation respects configured `rule_numbers` from YAML

---

## Testing

### Test Config
Created `configs/testsets/test_formatting_fixes.yaml`:
- C14 with EXAMPLES style → Verify examples generated
- ARI with new complexity/target_values format → Verify separation

### Results
```
✓ Generated test set with 5 test cases
  - 1 C14 test case: Examples properly generated (no {examples} placeholder)
  - 4 ARI test cases: 2 complexity × 2 target_values = 4 combinations
  - All prompts valid, metadata correct
```

### Example Output
**C14 EXAMPLES Style**:
- User prompt: 175 chars with 2 example evolutions
- Preview: "Example 1: Current: 0 0 0 0 1 0 0 0..."

**ARI New Format**:
- Expression: `(-63 - 47) / (1 * -11)`
- Complexity: 2 (moderate nesting)
- Target Value: 10 (evaluates to 10)

---

## Files Modified

1. **`src/stages/generate_testset.py`**:
   - Lines ~66-85: Refactored `generate_arithmetic_tests()` to support both old and new formats
   - Lines ~100-115: Updated arithmetic test case metadata (complexity, target_value)
   - Lines ~283-310: Added C14 examples generation for EXAMPLES style prompts

2. **`src/cli/benchmark_tui.py`**:
   - Lines ~448: Updated Quick Start ARI defaults to new format
   - Lines ~535-565: Refactored ARI config UI (complexity + target_values with explanations)
   - Lines ~1250-1268: Updated YAML generation with backward compatibility

3. **`configs/testsets/test_formatting_fixes.yaml`**: Test config demonstrating new formats

---

## Migration Guide

### For Existing Configs (Old Format)
No changes needed - backward compatibility maintained:
```yaml
# This still works
tasks:
  - type: arithmetic
    generation:
      target_accuracies: [1, 2, 3]
      expressions_per_target: 10
```

### For New Configs (Recommended)
Use separate complexity and target values:
```yaml
tasks:
  - type: arithmetic
    generation:
      complexity: [1, 2, 3]      # How deep can expressions be?
      target_values: [0, 5, 10]  # What should they evaluate to?
      count: 10                   # How many per combo?
```

### C14 EXAMPLES Style
Just set `user_style: examples` - examples auto-generate:
```yaml
tasks:
  - type: cellular_automata_1d
    prompt_configs:
      - user_style: examples  # Examples now auto-generated!
```

---

## Performance Impact

- **C14 EXAMPLES**: Generates 2 extra test cases per prompt (minimal overhead)
- **ARI New Format**: Same performance, just clearer semantics
- **Backward Compatibility**: No performance penalty

---

**Status**: ✅ All fixes tested and working  
**Date**: 2026-01-24  
**Validation**: `test_formatting_fixes.yaml` → 5 test cases generated successfully
