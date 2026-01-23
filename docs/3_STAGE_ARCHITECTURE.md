# 3-Stage Architecture - Implementation Guide

This document describes the new 3-stage benchmark architecture that transforms the monolithic system into three independent, portable stages.

## Architecture Overview

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  1. GENERATE     │────▶│  2. EXECUTE      │────▶│  3. ANALYZE      │
│  Test Sets       │     │  On Models       │     │  Results         │
└──────────────────┘     └──────────────────┘     └──────────────────┘
   YAML configs            testsets.json.gz       results.json.gz
   ↓                       ↓                       ↓
   testset_xyz.json.gz     results_model_xyz...    reports/charts
```

## Key Benefits

✅ **Generate once, run many**: Test sets are reusable across models  
✅ **Portable execution**: Test runner works on any machine with model access  
✅ **Offline analysis**: No model dependencies for reporting  
✅ **Reproducible**: Same test set = identical conditions  
✅ **Version controlled**: Test sets and configs are tracked  
✅ **Compressed storage**: Efficient JSON.gz format  

## Stage 1: Test Set Generation

### Purpose
Create deterministic, reproducible test sets from declarative YAML configurations.

### Input: YAML Configuration
```yaml
# configs/testsets/ari_baseline_v1.yaml
metadata:
  name: "ari_baseline_v1"
  version: "1.0"
  schema_version: "1.0.0"
  description: "Core arithmetic reasoning baseline"
  task_type: "arithmetic"

task:
  type: "arithmetic"
  generation:
    seed: 42
    target_accuracies: [0, 1, 2]
    expressions_per_target: 12
    mode: "expression"

sampling:
  temperature: 0.1
  top_k: 40
  max_tokens: 512

execution:
  no_thinking: true
  timeout_seconds: 30
  prompt_language: "en"
```

### Usage
```bash
# Generate single test set
python scripts/generate_testset.py configs/testsets/ari_baseline_v1.yaml

# Generate all test sets
python scripts/generate_testset.py "configs/testsets/*.yaml" --validate

# Output: testsets/testset_ari_baseline_v1_20260122_143052.json.gz
```

### Output Format
```json
{
  "format_version": "1.0.0",
  "metadata": {
    "name": "ari_baseline_v1",
    "version": "1.0",
    "created_at": "2026-01-22T14:30:31Z",
    "config_hash": "84aac797cb5c978d",
    "task_type": "arithmetic"
  },
  "generation_params": { "seed": 42, ... },
  "sampling_params": { "temperature": 0.1, ... },
  "test_cases": [
    {
      "test_id": "ari_0000",
      "task_type": "arithmetic",
      "config_name": "minimal_analytical",
      "prompts": {
        "system": "...",
        "user": "...",
        "full": "..."
      },
      "task_params": {
        "expression": "-52 - -33 + 36 + -17",
        "expected_answer": 0,
        ...
      }
    }
  ]
}
```

## Stage 2: Test Execution

### Purpose  
Portable, dependency-minimal script to run test sets on models and save structured results.

### Features
- **Minimal dependencies**: Only standard library + model APIs
- **Provider support**: Ollama and HuggingFace
- **Error handling**: Timeout, retry, graceful failures
- **Progress tracking**: Real-time execution updates
- **Metadata capture**: Model info, execution environment

### Usage
```bash
# Run on Ollama model
python scripts/run_testset.py testsets/testset_ari_baseline_v1.json.gz \
    --model qwen3:0.6b \
    --provider ollama \
    --output-dir results/

# Run on HuggingFace model  
python scripts/run_testset.py testsets/testset_gol_v1.json.gz \
    --model microsoft/DialoGPT-medium \
    --provider huggingface \
    --output-dir results/
```

### Output Format
```json
{
  "format_version": "1.0.0",
  "metadata": {
    "result_id": "results_qwen3_0.6b_ari_baseline_v1_20260122_150132",
    "created_at": "2026-01-22T15:01:32Z",
    "hostname": "server-01.example.com"
  },
  "testset_metadata": {
    "testset_name": "ari_baseline_v1",
    "config_hash": "84aac797cb5c978d"
  },
  "model_info": {
    "model_name": "qwen3:0.6b",
    "provider": "ollama"
  },
  "results": [
    {
      "test_id": "ari_0000", 
      "status": "success",
      "input": { "user_prompt": "...", "task_params": {...} },
      "output": { "raw_response": "...", "parsed_answer": 0 },
      "evaluation": { "correct": true, "accuracy": 1.0 }
    }
  ],
  "summary_statistics": {
    "accuracy": 0.6296,
    "parse_error_rate": 0.1574
  }
}
```

## Stage 3: Analysis & Reporting

### Purpose
Process result files and generate comprehensive analysis reports and visualizations.

### Features
- **Multi-result analysis**: Compare across models and configurations
- **Rich reporting**: Markdown reports with detailed breakdowns  
- **Visualizations**: Accuracy charts, time analysis, error breakdowns
- **Error analysis**: Parse errors, type mismatches, performance issues
- **Export formats**: PNG charts, markdown reports, console summaries

### Usage
```bash
# Single model analysis
python scripts/analyze_results.py results/results_qwen3_*.json.gz

# Multi-model comparison report
python scripts/analyze_results.py results/results_*.json.gz \
    --output reports/comparison_2026-01-22.md

# Generate visualizations  
python scripts/analyze_results.py results/*.json.gz \
    --visualize \
    --output-dir reports/charts/
```

### Output Examples
- **Markdown Report**: `reports/comparison_2026-01-22.md` with performance tables, error analysis, sample results
- **Visualizations**: `reports/charts/accuracy_comparison.png`, `accuracy_vs_time.png`, `accuracy_vs_errors.png`
- **Console Summary**: Quick accuracy and error rate overview

## Complete Workflow

### Example Session
```bash
# Stage 1: Generate test sets
python scripts/generate_testset.py "configs/testsets/*.yaml"

# Stage 2: Run tests on multiple models  
python scripts/run_testset.py testsets/testset_ari_*.json.gz --model qwen3:0.6b --provider ollama
python scripts/run_testset.py testsets/testset_ari_*.json.gz --model gemma3:1b --provider ollama

# Stage 3: Analyze results
python scripts/analyze_results.py "results/results_*_ari_*.json.gz" \
    --output reports/ari_comparison.md \
    --visualize
```

### Demo Script
```bash
# Run complete workflow demonstration
./scripts/demo_workflow.sh
```

## Migration from Monolithic Architecture

### Before (Monolithic)
```bash
python gol_eval.py --model qwen3:0.6b --difficulty medium --batch-size 20
# → Generates tests, runs model, saves CSV, all in one execution
```

### After (3-Stage)  
```bash
# 1. Generate reusable test set
python scripts/generate_testset.py configs/testsets/gol_medium_v1.yaml

# 2. Run on any model (reusable test set)
python scripts/run_testset.py testsets/testset_gol_medium_v1.json.gz --model qwen3:0.6b

# 3. Analyze offline (no model needed)
python scripts/analyze_results.py results/results_*.json.gz --visualize
```

## Data Versioning & Compatibility

### Version Tracking
- **Format versions**: Test sets and results include format version for compatibility
- **Config hashing**: SHA256 hash ensures test set integrity  
- **Schema versioning**: Backward compatibility through version checks
- **Metadata capture**: Full provenance from config to analysis

### File Naming Convention
- Test sets: `testset_{name}_{timestamp}.json.gz`
- Results: `results_{model}_{testset_name}_{timestamp}.json.gz`  
- Reports: `{analysis_type}_{date}.md`

## Advanced Usage

### Custom Test Set Configurations
Create new YAML configs for specific scenarios:
- Multi-language testing
- Complexity variations  
- Prompt style matrices
- Domain-specific evaluations

### Parallel Execution
```bash
# Run multiple models in parallel
python scripts/run_testset.py testsets/test.json.gz --model qwen3:0.6b &
python scripts/run_testset.py testsets/test.json.gz --model gemma3:1b &
wait

# Analyze combined results
python scripts/analyze_results.py results/results_*_test_*.json.gz --comparison
```

### Cloud Deployment
```bash
# Copy test set to cloud VM
scp testsets/testset_ari_v1.json.gz cloud-vm:/tmp/
scp scripts/run_testset.py cloud-vm:/tmp/

# Run on cloud (minimal dependencies)
ssh cloud-vm "cd /tmp && python run_testset.py testset_ari_v1.json.gz --model llama2:7b --provider ollama"

# Download results for local analysis
scp cloud-vm:/tmp/results/*.json.gz results/
```

## Configuration Reference

### YAML Schema
- **metadata**: Name, version, description, task type
- **task**: Task-specific generation parameters  
- **sampling**: Model sampling parameters (temperature, top_k, etc.)
- **execution**: Runtime hints (timeouts, language, special flags)

### Supported Tasks
- **arithmetic**: Mathematical expression evaluation
- **game_of_life**: Conway's cellular automaton prediction
- **linda_fallacy**: Cognitive bias testing (future)
- **cellular_automata**: Configurable rule-based patterns (future)

### Model Providers
- **Ollama**: Local model server (`--provider ollama`)
- **HuggingFace**: Transformers library (`--provider huggingface`)
- **Future**: OpenAI API, Anthropic API, custom endpoints

## Implementation Status

### ✅ Completed
- [x] Stage 1: Test set generation with YAML configs
- [x] Stage 2: Portable test runner with Ollama/HuggingFace support  
- [x] Stage 3: Analysis engine with reports and visualizations
- [x] JSON.gz compressed data formats with versioning
- [x] Arithmetic task support with expression generation
- [x] Game of Life task support (basic, needs prompt tuning)
- [x] Complete workflow demonstration script

### 🔄 In Progress
- [ ] Prompt engineering optimization for GoL parsing
- [ ] Additional task types (Linda fallacy, cellular automata)
- [ ] Enhanced visualization options

### 📋 Future Enhancements
- [ ] OpenAI/Anthropic API providers
- [ ] Multi-language test set validation
- [ ] Statistical significance testing
- [ ] A/B test framework for prompt optimization
- [ ] Web dashboard for result exploration
- [ ] CI/CD integration for continuous benchmarking

---

For questions about implementation or usage, see the main project documentation or create an issue.