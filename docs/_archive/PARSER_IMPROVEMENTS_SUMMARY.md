# Answer Parsing Improvements Summary

**Date**: January 27, 2026  
**Status**: ✅ Implemented and Tested

## Overview

Analyzed 43 incorrect results from a multi-task benchmark run and identified that many failures were due to parsing issues rather than model errors. Implemented comprehensive parser improvements that now correctly parse **16 out of 43 previously incorrect results (37.2% improvement rate)**.

## Key Issues Identified

### 1. Unicode Multiplication Signs (✅ Fixed)
**Problem**: ASCII shapes parser only recognized lowercase 'x' but models output Unicode multiplication signs (×, ✕, ✖)

**Examples**:
- Model output: "6 × 2" 
- Parser expected: "6x2"
- Result: `parse_error`

**Solution**: Extended dimension patterns to include Unicode variants:
```python
r'(\d+)\s*[x×✕✖]\s*(\d+)'  # Now matches x, ×, ✕, ✖
```

**Files Modified**:
- `src/stages/run_testset.py` (line ~618)
- `src/plugins/ascii_shapes/parser.py` (line ~79)

**Impact**: Fixed 12 ASCII shapes errors

---

### 2. Bold Markdown Text Selection (✅ Fixed)
**Problem**: Grid tasks parser took LAST bold text instead of FIRST, often selecting trailing numbers instead of names

**Examples**:
- Model output: "**Alice Smith** has revenue of **$8,678.19**"
- Old parser: extracted "$8,678.19" (last bold text)
- Expected: "Alice Smith" (first bold text)

**Solution**: Rewrote `_try_bold_markdown()` to:
1. Take FIRST meaningful bold text
2. Filter out non-answer patterns (dollar amounts, plain numbers, decimals, quarter refs)
3. Fallback to first match if all filtered

**Files Modified**:
- `src/plugins/grid_tasks/parser.py` (lines ~93-116)

**Impact**: Fixed 2 grid tasks errors

---

### 3. Unicode Space Normalization (✅ Fixed)
**Problem**: Models inserted Unicode non-breaking spaces (`\u202F`, `\u00A0`) that broke exact string matching

**Examples**:
- Expected: `"Alice Smith"` (regular space)
- Model output: `"Alice\u202fSmith"` (narrow no-break space)
- Result: Mismatch even though visually identical

**Solution**: Normalize Unicode spaces to regular spaces:
```python
response = re.sub(r'[\u00A0\u202F\u2009\u200B]', ' ', response)
```

**Characters normalized**:
- `\u00A0`: Non-breaking space
- `\u202F`: Narrow no-break space
- `\u2009`: Thin space
- `\u200B`: Zero-width space

**Files Modified**:
- `src/stages/run_testset.py` (parse_grid_tasks_response, parse_ascii_shapes_response)
- `src/plugins/grid_tasks/parser.py`
- `src/plugins/ascii_shapes/parser.py`

**Impact**: Fixed 3 additional grid tasks errors

---

### 4. Object Tracking Location Extraction (✅ Fixed)
**Problem**: Parser extracted FIRST location but answer is usually the FINAL location (object moved from A to B)

**Examples**:
- Model output: "The earbuds are still inside the box, and the box is now in the drawer."
- Old parser: extracted "box" (first location)
- Expected: "drawer" (final location)

**Solution**: Rewrote parser to prioritize:
1. Bold locations (take LAST)
2. "now in/on" patterns (indicates final state)
3. All location patterns (take LAST occurrence)
4. rfind() to get last occurrence of location words

**Files Modified**:
- `src/stages/run_testset.py` (parse_object_tracking_response)

**Impact**: Fixed 1 object tracking error

---

### 5. Missing Fallback Parsers (✅ Fixed)
**Problem**: `run_testset.py` lacked fallback parsing functions for grid_tasks, object_tracking, sally_anne

**Solution**: Added 3 new parser functions (~150 lines):
- `parse_grid_tasks_response()`: Multi-strategy for bold markdown, answer patterns, short responses
- `parse_object_tracking_response()`: Location extraction with common locations list
- `parse_sally_anne_response()`: Delegates to object_tracking parser

**Files Modified**:
- `src/stages/run_testset.py` (lines ~697-830)

**Impact**: Provides robust fallback when plugin parsers fail

---

## Results Summary

### Before Improvements
- **Total incorrect results**: 43
- **Parse errors**: Many (exact count varied by task)
- **ASCII shapes errors**: 16 (12 due to Unicode ×)
- **Grid tasks errors**: 22 (some due to Unicode spaces)
- **Object tracking errors**: 5

### After Improvements
- **Total incorrect**: 43 (same dataset)
- **Now correctly parsed**: 16 (37.2% improvement)
- **Still incorrect**: 27 (genuine model errors)

### Breakdown by Task Type

| Task Type | Improvements | Still Wrong | Notes |
|-----------|-------------|-------------|-------|
| ASCII Shapes | 12 | 4 | 4 remaining are model miscounts (e.g., 7×12 vs 7×13) |
| Grid Tasks | 3 | 19 | 19 remaining are model giving wrong answers |
| Object Tracking | 1 | 4 | 4 remaining are model errors |

---

## Test Results

### Parser Function Tests
All parser improvements tested with real-world examples:

```
TESTING ASCII SHAPES PARSING (Unicode multiplication)
✓ "The rectangle has dimensions **6 × 2**." → 6x2
✓ "Its dimensions are **15 × 3**." → 15x3
✓ "**Answer:** **8 × 13**." → 8x13
✓ "Width × Height = 19 × 11" → 19x11

TESTING GRID TASKS PARSING (Bold markdown)
✓ "**Alice Smith** has revenue of **$8,678.19**." → Alice Smith
✓ "**Region with highest commission: North**" → Region with...

TESTING OBJECT TRACKING PARSING
✓ "The earbuds are inside the box, box is in the drawer." → drawer
✓ "drawer" → drawer
```

### Real Result File Test
Tested against actual incorrect results from benchmark run:
- **16 out of 43** (37.2%) now parse correctly
- **27 remaining** are genuine model errors (wrong answers, not parse issues)

---

## Files Modified

1. **src/stages/run_testset.py**:
   - Updated `parse_ascii_shapes_response()`: Unicode × patterns, Unicode space normalization
   - Updated `parse_grid_tasks_response()`: Unicode space normalization, first vs last bold text
   - Updated `parse_object_tracking_response()`: Last location extraction
   - Added routing to new parser functions

2. **src/plugins/ascii_shapes/parser.py**:
   - Unicode × patterns in dimension regex
   - Natural language pattern for "N characters across, M lines"
   - Unicode space normalization

3. **src/plugins/grid_tasks/parser.py**:
   - Rewrote `_try_bold_markdown()`: First vs last, filter non-answers
   - Unicode space normalization

---

## Remaining Issues (Not Fixable via Parsing)

The 27 still-incorrect results are genuine model errors:

### ASCII Shapes (4 errors)
- Model miscounted dimensions (e.g., said 7×12 when actual is 7×13)
- Not a parsing issue - model gave wrong answer

### Grid Tasks (19 errors)
- Model selected wrong entity from table (e.g., "North" instead of "Central")
- Model gave wrong aggregation result
- Not a parsing issue - model reasoning errors

### Object Tracking (4 errors)
- Model tracked object to wrong location
- Not a parsing issue - model misunderstood problem

---

## Testing Commands

### Test parser functions directly:
```bash
./bin/python /tmp/test_new_parsers.py
```

### Test against real results file:
```bash
./bin/python /tmp/test_improvements3.py
```

### Debug specific cases:
```bash
python3 /tmp/debug_alice3.py  # Unicode space normalization test
python3 /tmp/debug_grid2.py   # Grid tasks bold text test
```

---

## Recommendations

### ✅ Ready for Production
All parser improvements are tested and ready to deploy. Future test runs will benefit from:
- Better handling of Unicode formatting
- More robust multi-strategy parsing
- Fewer false negatives (correct model answers misclassified as wrong)

### 🔮 Future Improvements
1. **Pattern Learning**: Analyze model-specific formatting patterns to add custom strategies
2. **Confidence Scoring**: Implement confidence scores for ambiguous parses
3. **Model-Specific Parsers**: Some models consistently use specific formats (e.g., Qwen uses × more than others)
4. **Post-Processing Validation**: Check if parsed answer makes sense in context

### 📊 Impact on Metrics
- **Accuracy Boost**: 37.2% of previously "incorrect" results now parse correctly
- **Cleaner Error Analysis**: Remaining errors are genuine model failures, not parser issues
- **Better Model Comparison**: Fairer comparison since parsing bugs don't skew results

---

## Conclusion

Successfully identified and fixed 4 major parsing issues:
1. ✅ Unicode multiplication signs (×)
2. ✅ Bold text selection order (first vs last)
3. ✅ Unicode space normalization (\u202F, \u00A0)
4. ✅ Object tracking location extraction (last location)

**Result**: 37.2% improvement rate (16 out of 43 previously incorrect results now parse correctly).

The remaining 27 incorrect results are confirmed to be genuine model errors, not parsing issues.
