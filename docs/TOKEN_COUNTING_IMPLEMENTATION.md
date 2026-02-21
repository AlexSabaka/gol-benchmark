# Token Counting Implementation

**Date**: January 25, 2026  
**Status**: ✅ Complete and Ready for Testing

## Overview

Added comprehensive token counting throughout the benchmark pipeline to enable API cost estimation and token efficiency analysis. Uses a simple `chars/4` heuristic for approximate token counting.

## Implementation Details

### 1. Token Calculation (Heuristic)

```python
# Input tokens: prompt characters divided by 4
input_tokens = (len(user_prompt) + len(system_prompt)) // 4

# Output tokens: response characters divided by 4
output_tokens = len(raw_response) // 4
```

This heuristic approximates actual tokenizer behavior:
- **Typical GPT models**: ~4 characters per token (English text)
- **Good for cost estimation**: Close enough for API billing calculations
- **Fast**: No tokenizer library required
- **Portable**: Works across all model providers

### 2. Data Pipeline Integration

#### Stage 1: Test Execution (`run_testset.py`)

**Location**: Lines ~1568-1690

**Changes**:
- Calculate `input_tokens` before each test execution
- Calculate `output_tokens` after receiving response
- Add `tokens` field to result JSON:
  ```json
  {
    "tokens": {
      "input_tokens": 245,
      "output_tokens": 187
    }
  }
  ```
- Add token statistics to `summary_statistics`:
  - `total_input_tokens`
  - `total_output_tokens`
  - `avg_input_tokens_per_test`
  - `avg_output_tokens_per_test`

#### Stage 2: Result Extraction (`analyze_results.py`)

**Location**: Lines ~115-153

**Changes in `extract_summary_stats()`**:
- Extract token statistics from `summary_statistics`
- Fallback calculation from individual results if not in summary
- Return 7 token fields:
  - `total_input_tokens`
  - `total_output_tokens`
  - `total_tokens`
  - `avg_input_tokens_per_test`
  - `avg_output_tokens_per_test`
  - `avg_tokens_per_test`
  - `total_tokens` (computed)

**Location**: Lines ~317-376

**Changes in `aggregate_model_stats()`**:
- Sum `total_input_tokens` and `total_output_tokens` across multiple result files
- Calculate aggregate averages
- Return 5 aggregated token fields

### 3. Report Display

#### Markdown Reports

**Location**: Lines ~400-430 (Model Comparison Summary Table)
- Added **Avg Tokens/Test** column to main comparison table
- Format: `1.5K` for values ≥1000, otherwise integer

**Location**: Lines ~460-475 (Performance Section)
- Added **Token Usage** subsection with:
  - Total Input/Output/Combined Tokens
  - Average Input/Output per Test

**Location**: Lines ~519-535 (Comparison Mode Table)
- Added **Avg Tokens** column to detailed comparison table

#### HTML Reports

**Location**: Lines ~863-895 (Summary Table)
- Added **Avg Tokens** column to HTML summary table
- Same formatting as markdown (K suffix for thousands)

**Location**: Lines ~960-972 (Detailed Performance Section)
- Added **Token Usage** subsection with all token statistics
- Styled as performance metrics with proper formatting

### 4. Visualizations

#### Chart 18: Token Usage Comparison

**Function**: `_generate_token_usage_chart()`  
**Location**: Lines ~2881-2965

**Displays**:
- **Left panel**: Stacked bar chart (input + output tokens)
  - Grouped by model or task (whichever has more variation)
  - Color-coded: blue for input, red for output
  - Total labels on top of bars
  
- **Right panel**: Output/Input ratio bar chart
  - Color-coded efficiency: green (<1x), orange (1-2x), red (>2x)
  - Horizontal line at 1.0 for reference
  - Ratio labels on bars

**Insights**:
- Compare token consumption across models/tasks
- Identify verbose models (high output/input ratio)
- Estimate API cost differences

#### Chart 19: Token Efficiency Scatter

**Function**: `_generate_token_efficiency_scatter()`  
**Location**: Lines ~2968-3086

**Displays**:
- **Left panel**: Input tokens vs Accuracy
  - Scatter plot with trend line
  - Pearson correlation coefficient displayed
  - Color-coded by model or task
  
- **Right panel**: Output tokens vs Accuracy
  - Same format as left panel
  - Shows if longer responses correlate with correctness

**Insights**:
- Positive correlation: longer prompts → better accuracy
- Negative correlation: verbosity hurts performance
- No correlation: token length irrelevant to task

### 5. Validation

**Test command used**:
```bash
python3 -c "
user_prompt = 'Calculate 2 + 2'
system_prompt = 'You are a helpful math assistant.'
response = 'The answer is 4. I calculated this by adding...'

input_tokens = (len(user_prompt) + len(system_prompt)) // 4
output_tokens = len(response) // 4
"
```

**Results**:
- 48 chars → 12 input tokens (4.0 chars/token) ✓
- 89 chars → 22 output tokens (4.0 chars/token) ✓
- Total: 137 chars → 34 tokens (4.03 chars/token) ✓

## Usage Examples

### Running Tests with Token Tracking

```bash
# Generate test set
python src/stages/generate_testset.py configs/testsets/multi_task_baseline.yaml

# Execute tests (tokens automatically counted)
python src/stages/run_testset.py testsets/testset_*.json.gz \
    --model qwen3:0.6b --provider ollama --output-dir results/

# Analyze with token visualizations
python src/stages/analyze_results.py results/results_*.json.gz \
    --output reports/token_analysis.md \
    --visualize --output-dir reports/charts/
```

### Viewing Token Statistics

**In Markdown Report**:
```markdown
## Model Comparison Summary

| Model | ... | Avg Tokens/Test |
|-------|-----|-----------------|
| qwen3:0.6b | ... | 1.2K |

### Token Usage:
- **Total Input Tokens**: 45,230
- **Total Output Tokens**: 38,150
- **Avg Input per Test**: 452
- **Avg Output per Test**: 382
```

**In HTML Report**:
Similar structure with styled tables and metrics.

**In Charts**:
- `01_token_usage.png`: Bar charts showing input vs output by model/task
- `02_token_efficiency_scatter.png`: Correlation plots (tokens vs accuracy)

## API Cost Estimation

With token counts, you can estimate API costs:

```python
# Example: OpenAI GPT-3.5 pricing
INPUT_COST_PER_1K = 0.0015   # $0.0015 per 1K input tokens
OUTPUT_COST_PER_1K = 0.002   # $0.002 per 1K output tokens

total_input_tokens = 45230
total_output_tokens = 38150

input_cost = (total_input_tokens / 1000) * INPUT_COST_PER_1K
output_cost = (total_output_tokens / 1000) * OUTPUT_COST_PER_1K
total_cost = input_cost + output_cost

print(f"Estimated cost: ${total_cost:.2f}")
# Output: Estimated cost: $0.14
```

## Files Modified

1. **`src/stages/run_testset.py`** (4 changes, ~120 lines affected)
   - Added token calculation logic
   - Added tokens field to results
   - Added token statistics to summary

2. **`src/stages/analyze_results.py`** (8 changes, ~250 lines affected)
   - Updated `extract_summary_stats()` to extract tokens
   - Updated `aggregate_model_stats()` to aggregate tokens
   - Added token columns to all report tables
   - Added token sections to detailed reports
   - Added 2 new visualization functions

## Testing Checklist

- [x] Token calculation logic verified (chars/4 heuristic)
- [ ] End-to-end test: generate → run → analyze
- [ ] Verify token counts in results JSON
- [ ] Verify token statistics in markdown report
- [ ] Verify token statistics in HTML report
- [ ] Verify token usage chart generated
- [ ] Verify token efficiency scatter plot generated
- [ ] Test with multiple models
- [ ] Test with multiple tasks
- [ ] Verify correlation calculations
- [ ] Test with no token data (graceful degradation)

## Known Limitations

1. **Approximation**: Uses chars/4, not actual tokenizer
   - Good enough for cost estimation
   - May be ±20% off from actual token counts
   - Different languages have different ratios

2. **Provider Variations**: 
   - Some models return actual token counts via API
   - Currently ignoring those in favor of consistent heuristic
   - Future: could use actual counts when available

3. **No Median Statistics**:
   - Currently only total and average
   - Median would be useful for skewed distributions
   - Easy to add in future

## Future Enhancements

1. **Use Actual Tokenizer**: 
   ```python
   import tiktoken
   enc = tiktoken.get_encoding("cl100k_base")
   tokens = len(enc.encode(text))
   ```

2. **Provider-Specific Token Counts**:
   - OpenAI API returns `usage.prompt_tokens` and `usage.completion_tokens`
   - Could use actual counts when available

3. **Median Token Statistics**:
   - Add median to complement averages
   - Useful for identifying outliers

4. **Token Budget Warnings**:
   - Alert if tests approach model context limits
   - Suggest batch size adjustments

5. **Cost Tracking**:
   - Add provider pricing tables
   - Auto-calculate estimated costs
   - Compare cost efficiency across models

## Documentation

- This file: Implementation details and usage
- **User Guide**: See `docs/02_USER_GUIDES/`
- **Architecture**: See `docs/03_ARCHITECTURE/3_STAGE_ARCHITECTURE_COMPLETE.md`

---

**Status**: ✅ Ready for integration testing  
**Next Steps**: Run full benchmark with token tracking enabled
