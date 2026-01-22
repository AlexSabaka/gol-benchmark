#!/bin/bash
# Multi-Model GoL Benchmark Campaign - January 2026
# Tests 5 models across 3x3 prompt matrix (9 configs each = 45 total runs)

set -e  # Exit on error

# Activate virtual environment
source bin/activate

# Configuration
DIFFICULTY="medium"
BATCH_SIZE=20
SEED=42
TEMPERATURE=0.25
CTX_LEN=4096
NUM_PREDICT=2048
TOP_K=40
MIN_K=1
MIN_P=0.05
KNOWN_PATTERNS_RATIO=1.0
DENSITY=0.50
MARKERS="1,0"
LANGUAGE="en"

# Output directory with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_DIR="results/multi_model_${TIMESTAMP}"
mkdir -p "$RESULTS_DIR"

# Models to test
MODELS=(
    "gemma3:4b"
    "qwen3:1.7b"
    "llama3.2_3b_122824_uncensored.Q8_0-1739364637622:latest"
    "hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q4_K_M"
    "gemma3:12b"
)

# Prompt styles to test
USER_STYLES=("minimal" "casual" "linguistic")
SYSTEM_STYLES=("analytical" "casual" "adversarial")

# Log file
LOG_FILE="$RESULTS_DIR/benchmark_run.log"
echo "Multi-Model GoL Benchmark Campaign Started: $(date)" | tee "$LOG_FILE"
echo "Testing ${#MODELS[@]} models with ${#USER_STYLES[@]}x${#SYSTEM_STYLES[@]} = $((${#USER_STYLES[@]} * ${#SYSTEM_STYLES[@]})) configurations each" | tee -a "$LOG_FILE"
echo "=" | tee -a "$LOG_FILE"

# Test each model
for model in "${MODELS[@]}"; do
    echo "" | tee -a "$LOG_FILE"
    echo "🔬 Testing model: $model" | tee -a "$LOG_FILE"
    echo "Started: $(date)" | tee -a "$LOG_FILE"
    
    MODEL_SAFE_NAME=$(echo "$model" | sed 's/[^a-zA-Z0-9]/_/g')
    
    # Test each prompt combination
    for user_style in "${USER_STYLES[@]}"; do
        for system_style in "${SYSTEM_STYLES[@]}"; do
            CONFIG_NAME="${user_style}_${system_style}"
            RESULT_FILE="$RESULTS_DIR/${MODEL_SAFE_NAME}_${CONFIG_NAME}.json"
            
            echo "  → Config: $CONFIG_NAME" | tee -a "$LOG_FILE"
            
            # Run benchmark
            python -m src.benchmarks.gol_eval \
                --model "$model" \
                --difficulty "$DIFFICULTY" \
                --batch-size "$BATCH_SIZE" \
                --seed "$SEED" \
                --temperature "$TEMPERATURE" \
                --ctx-len "$CTX_LEN" \
                --num-predict "$NUM_PREDICT" \
                --top-k "$TOP_K" \
                --min-k "$MIN_K" \
                --min-p "$MIN_P" \
                --known-patterns-ratio "$KNOWN_PATTERNS_RATIO" \
                --density "$DENSITY" \
                --live-dead-cell-markers "$MARKERS" \
                --no-think \
                --prompt-language "$LANGUAGE" \
                --prompt-style "$user_style" \
                --system-prompt-style "$system_style" \
                > "$RESULT_FILE" 2>&1
            
            # Extract accuracy from output
            ACCURACY=$(grep -oP "Avg Accuracy.*?:\s+\K[\d.]+%" "$RESULT_FILE" | head -1 || echo "N/A")
            echo "    ✓ Accuracy: $ACCURACY" | tee -a "$LOG_FILE"
        done
    done
    
    echo "  Completed: $(date)" | tee -a "$LOG_FILE"
done

echo "" | tee -a "$LOG_FILE"
echo "=" | tee -a "$LOG_FILE"
echo "🎉 All benchmark tests completed: $(date)" | tee -a "$LOG_FILE"
echo "Results saved to: $RESULTS_DIR" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Next steps:" | tee -a "$LOG_FILE"
echo "1. Run aggregation: python -m src.visualization.analyze_multi_model_results $RESULTS_DIR" | tee -a "$LOG_FILE"
echo "2. Generate visualizations: python -m src.visualization.generate_prompt_benchmark_visualizations $RESULTS_DIR" | tee -a "$LOG_FILE"
