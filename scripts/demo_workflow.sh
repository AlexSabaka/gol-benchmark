#!/bin/bash
# Complete 3-Stage Architecture Workflow Demo
# 
# This script demonstrates the full 3-stage benchmark pipeline:
# Stage 1: Test Set Generation
# Stage 2: Test Execution  
# Stage 3: Analysis & Reporting

set -e  # Exit on any error

echo "=================================================="
echo "GoL Benchmark - 3-Stage Architecture Demo"
echo "=================================================="
echo

# ============================================================================
# STAGE 1: GENERATE TEST SETS
# ============================================================================

echo "STAGE 1: Test Set Generation"
echo "----------------------------"

# Generate core baseline test sets
echo "→ Generating arithmetic baseline test set..."
python src/stages/generate_testset.py configs/testsets/ari_baseline_v1.yaml --validate

echo "→ Generating Game of Life multilingual test set..."
python src/stages/generate_testset.py configs/testsets/gol_multilingual_v1.yaml --validate

echo "→ Generated test sets:"
ls -la testsets/testset_*$(date +%Y%m%d)*.json.gz | tail -2

echo
echo "✓ Stage 1 Complete: Test sets generated with versioning"
echo

# ============================================================================
# STAGE 2: EXECUTE TESTS
# ============================================================================

echo "STAGE 2: Test Execution"
echo "-----------------------"

# Get the latest arithmetic test set
ARI_TESTSET=$(ls testsets/testset_ari_baseline_v1_*.json.gz | tail -1)
echo "→ Using arithmetic test set: $(basename $ARI_TESTSET)"

# Run on small model for demo
echo "→ Running tests on qwen3:0.6b (arithmetic)..."
python src/stages/run_testset.py "$ARI_TESTSET" \
    --model qwen3:0.6b \
    --provider ollama \
    --output-dir results/ | tail -5

echo
echo "✓ Stage 2 Complete: Test execution with portable runner"
echo

# ============================================================================
# STAGE 3: ANALYSIS & REPORTING
# ============================================================================

echo "STAGE 3: Analysis & Reporting"
echo "-----------------------------"

# Get all qwen3 results for this session
echo "→ Analyzing all qwen3:0.6b results..."
python src/stages/analyze_results.py "results/results_qwen3_0.6b_*$(date +%Y%m%d)*.json.gz" \
    --output "reports/demo_analysis_$(date +%Y%m%d_%H%M%S).md" \
    --visualize \
    --output-dir "reports/charts_demo"

echo
echo "✓ Stage 3 Complete: Analysis report and visualizations generated"
echo

# ============================================================================
# SUMMARY
# ============================================================================

echo
echo "=================================================="
echo "WORKFLOW DEMO COMPLETE"
echo "=================================================="
echo
echo "Generated files:"
echo "----------------"
echo "Test Sets:"
ls testsets/testset_*$(date +%Y%m%d)*.json.gz | sed 's/^/  /'

echo
echo "Results:"
ls results/results_*$(date +%Y%m%d)*.json.gz | head -3 | sed 's/^/  /'
if [ $(ls results/results_*$(date +%Y%m%d)*.json.gz | wc -l) -gt 3 ]; then
    echo "  ... and $(( $(ls results/results_*$(date +%Y%m%d)*.json.gz | wc -l) - 3 )) more"
fi

echo
echo "Reports:"
ls reports/demo_analysis_*.md 2>/dev/null | tail -1 | sed 's/^/  /' || echo "  (none generated in this run)"

echo
echo "Visualizations:" 
ls reports/charts_demo/*.png 2>/dev/null | sed 's/^/  /' || echo "  (none generated in this run)"

echo
echo "Key Benefits Demonstrated:"
echo "-------------------------"
echo "✓ Reproducible test sets with version tracking"
echo "✓ Portable test execution (works on any machine with model access)"
echo "✓ Offline analysis and reporting (no model dependencies)"
echo "✓ Compressed data formats for efficient storage"
echo "✓ Complete separation of concerns across 3 stages"
echo
echo "Next Steps:"
echo "----------"
echo "1. Create more test set configurations for different scenarios"
echo "2. Run tests on multiple models in parallel"
echo "3. Generate comparative analysis reports"
echo "4. Integrate with CI/CD for automated benchmarking"
echo