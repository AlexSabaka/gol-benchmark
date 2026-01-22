# Prompt Analysis Visualizations Guide

## Overview

This directory contains 9 comprehensive visualizations analyzing prompt engineering effects on LLM performance. All images are generated from the complete test matrix of **108 test cases per configuration** across two models.

## File Manifest

### 1. **heatmap_complete_matrix.png**
**What it shows:** Side-by-side heatmaps of the complete 3×3 performance matrix
- **X-axis:** System prompt style (adversarial, casual, analytical)
- **Y-axis:** User prompt style (minimal, casual, linguistic)
- **Color:** Performance accuracy (darker green = higher accuracy)

**Key insight:** Clear visual separation showing gemma dominates with linguistic prompts, while qwen performs better with minimal prompts + adversarial system.

---

### 2. **heatmap_qwen3_0_6b.png**
**What it shows:** Three individual heatmaps showing qwen's performance breakdown
- One heatmap for each user prompt style (minimal, casual, linguistic)

**Key patterns:**
- Minimal prompts: adversarial (53.7%) >> casual/analytical (35.2%)
- Casual prompts: analytical (50%) > adversarial (43.5%) > casual (34.3%)
- Linguistic prompts: casual (63.9%) ≈ adversarial (62.9%) >> analytical (47.2%)

**Insight:** Qwen shows instruction saturation with linguistic + analytical combination.

---

### 3. **heatmap_gemma3_1b.png**
**What it shows:** Three individual heatmaps showing gemma's performance breakdown
- One heatmap for each user prompt style (minimal, casual, linguistic)

**Key patterns:**
- Minimal prompts: analytical (57.4%) >> casual (35.1%) > adversarial (27.8%)
- Casual prompts: analytical (52.8%) > adversarial (39.8%) > casual (36.1%)
- Linguistic prompts: casual (83.3%) > adversarial (79.6%) > analytical (75.0%)

**Insight:** Gemma strongly prefers analytical system prompts for minimal/casual user prompts, but instruction saturation appears with linguistic prompts.

---

### 4. **heatmap_comparison_matrix.png**
**What it shows:** Performance gap between models (Gemma - Qwen)
- **Red region:** Qwen performs better
- **Blue region:** Gemma performs better
- **Intensity:** Size of performance gap

**Critical insights:**
- Minimal + adversarial: Red intensity (qwen +26.0 points) — strongest qwen advantage
- Minimal + analytical: Blue intensity (gemma +22.2 points) — strongest gemma advantage
- Linguistic + analytical: Blue intensity (gemma +27.8 points) — instruction saturation hurts qwen

**Usage:** Identify which configurations favor which model.

---

### 5. **line_system_prompt_effect.png**
**What it shows:** 3 line plots showing how system prompt style affects both models
- **Left panel:** Minimal user prompts
- **Center panel:** Casual user prompts
- **Right panel:** Linguistic user prompts

**Line interpretation:**
- Blue (°) = qwen3:0.6b
- Orange (□) = gemma3:1b
- Steep slopes = model is sensitive to system prompt changes
- Parallel lines = models respond similarly to system prompts
- Crossing lines = opposite preferences

**Key observation:** Lines cross most dramatically in the minimal prompts panel (opposite preferences), converge in casual panel, and diverge again with linguistic prompts.

---

### 6. **bar_user_prompt_effect.png**
**What it shows:** All 9 prompt combinations in a single bar chart
- **Grouping:** Three groups for each user prompt style (minimal, casual, linguistic)
- **Within each group:** 6 bars showing different system prompt × model combinations

**Color coding:**
- Dark blue: qwen3:0.6b
- Orange: gemma3:1b
- Within model: three shades for three system prompt styles

**Key insight:** Clear elevation from minimal→casual→linguistic, with gemma showing more dramatic improvements (48.3 points) vs qwen (28.7 points).

---

### 7. **performance_ranges.png**
**What it shows:** Performance range (min-max) for each model across all configurations
- **Error bars:** Show full range from worst to best configuration
- **Center point:** Mean performance
- **Color:** Blue = qwen, Orange = gemma

**Critical statistics:**
- **qwen range:** 35.19% to 63.89% (span: 28.7 points)
- **gemma range:** 27.78% to 83.33% (span: 55.5 points)
- **Interpretation:** Gemma is 1.93× more sensitive to prompt configuration

**Implication:** Prompt engineering is critical for gemma; qwen is more robust to poor prompts.

---

### 8. **radar_all_combinations.png**
**What it shows:** Radar/polar chart of all 9 prompt combinations
- **Categories (outer ring):** All 9 combinations (e.g., Min+Adv, Min+Cas, etc.)
- **Blue polygon:** qwen3:0.6b performance trace
- **Orange polygon:** gemma3:1b performance trace

**Visual interpretation:**
- Ragged/jagged polygon = inconsistent model performance
- Smooth polygon = consistent model performance
- Polygon area = overall performance envelope

**Key observation:** Gemma's polygon is much more "spiky" (especially in the linguistic region reaching 83%), while qwen's is more uniform.

---

### 9. **performance_deltas.png**
**What it shows:** Four panels showing performance improvements/degradations
- **Top-left:** qwen's system prompt effect on minimal user prompts
- **Top-right:** gemma's system prompt effect on minimal user prompts
- **Bottom-left:** qwen's user prompt improvement effect
- **Bottom-right:** gemma's user prompt improvement effect

**Color coding:**
- Green bars: positive impact
- Red bars: negative impact

**Key deltas:**
- qwen gains +18.5 from adversarial (minimal user)
- gemma gains +22.4 from analytical (minimal user)
- qwen improves +29.6 from minimal→linguistic user prompts
- gemma improves +48.3 from minimal→linguistic user prompts

---

## How to Interpret These Visualizations

### For Model Selection
1. **Use qwen3:0.6b if:** You have minimal prompts or expect efficiency to matter
2. **Use gemma3:1b if:** You can afford detailed prompts and want best accuracy

### For Prompt Design
1. **Minimal prompts:** Use adversarial system (qwen) or analytical system (gemma)
2. **Casual prompts:** Use analytical system (both models)
3. **Linguistic prompts:** Use casual system (both models—avoids saturation)

### For Expected Performance
1. **Best case:** gemma3:1b + linguistic user + casual system = **83.33%**
2. **Most robust:** qwen3:0.6b + adversarial system = stable 43-53% across user prompts
3. **Worst case:** gemma3:1b + minimal user + adversarial system = **27.78%**

### For Understanding Model Personalities
1. **qwen3:0.6b:** Efficiency-driven (likes adversarial), stable (28-point range)
2. **gemma3:1b:** Quality-driven (likes analytical), sensitive (56-point range)

---

## Technical Details

### Generation Script
All visualizations generated by: `generate_prompt_analysis_visualizations.py`

**Command to regenerate:**
```bash
cd /Volumes/2TB/repos/gol_eval
./bin/python3 generate_prompt_analysis_visualizations.py
```

### Libraries Used
- matplotlib: Plotting framework
- seaborn: Statistical visualization
- numpy: Numerical operations
- pandas: Data handling

### Image Quality
- DPI: 300 (print-ready)
- Format: PNG (transparent background)
- Total disk space: ~2.1 MB

---

## Integration with Main Report

These visualizations are embedded in: `PROMPT_ANALYSIS_REPORT.md`

View the main report for full context and interpretation of each visualization.

---

## Data Source

All data derived from 108 test cases per configuration:
- **Seed:** 42 (reproducible)
- **Temperature:** 0.1 (low randomness)
- **Thinking:** Disabled
- **Difficulties:** 1, 2, 3 (balanced)
- **Targets:** 0, 1, 2 (balanced)

Complete raw results available in: `results_qwen_gemma.txt`

