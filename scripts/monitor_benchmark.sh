#!/bin/bash
# Monitor benchmark progress

RESULTS_DIR="results/multi_model_20260117_125829"
LOG_FILE="$RESULTS_DIR/benchmark_run.log"

echo "=== Benchmark Progress Monitor ==="
echo "Started: $(date)"
echo ""

# Count completed tests
COMPLETED=$(find "$RESULTS_DIR" -name "*.json" | wc -l)
echo "Tests completed: $COMPLETED / 45"
echo ""

# Show last 30 lines of log
echo "=== Recent Log Entries ==="
tail -30 "$LOG_FILE"
echo ""

# Show current test files
echo "=== Test Files Created ==="
ls -lh "$RESULTS_DIR"/*.json 2>/dev/null | wc -l
echo ""

# Extract accuracies from completed tests
echo "=== Completed Test Accuracies ==="
for file in "$RESULTS_DIR"/*.json; do
    if [ -f "$file" ]; then
        basename=$(basename "$file" .json)
        accuracy=$(grep -oP "Avg Accuracy.*?:\s+\K[\d.]+%" "$file" | head -1 || echo "In Progress")
        echo "  $basename: $accuracy"
    fi
done
