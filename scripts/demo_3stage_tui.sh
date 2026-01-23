#!/bin/bash
set -e

echo "🚀 Demo: 3-Stage Benchmark TUI Integration"
echo "============================================"
echo

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "❌ Ollama is not running. Please start it with: ollama serve"
    exit 1
fi

echo "✅ Ollama is running"

# Check if qwen3:0.6b is available
if ! ollama list | grep -q "qwen3"; then
    echo "⚠️  qwen3:0.6b not found. Pulling model..."
    ollama pull qwen3:0.6b
fi

echo "✅ Model qwen3:0.6b is available"
echo

# Create a simple config for demo
echo "📝 Creating demo config..."

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DEMO_DIR="results/tui_demo_$TIMESTAMP"
mkdir -p "$DEMO_DIR"

# Demo: Use the TUI programmatically through Python
echo "🎯 Starting TUI Demo..."
echo

python3 -c "
import sys
sys.path.append('.')

from src.cli.benchmark_tui import BenchmarkTUI
from src.cli.benchmark_config import BenchmarkConfig, ModelSpec, PromptSpec, TestParams
from datetime import datetime

# Create a simple config for demo
config = BenchmarkConfig(
    name='tui_3stage_demo',
    description='Demo of 3-stage TUI workflow',
    task_type='arithmetic',
    models=[
        ModelSpec(name='qwen3:0.6b', provider='ollama', display_name='Qwen3 0.6B')
    ],
    prompts=PromptSpec(
        user_styles=['minimal'],
        system_styles=['casual']
    ),
    params=TestParams(
        batch_size=5,
        temperature=0.1,
        language='en',
        thinking_enabled=False
    ),
    output_dir='$DEMO_DIR',
    generate_charts=True
)

print('Demo config created:')
print(f'  Task: {config.task_type}')
print(f'  Models: {len(config.models)}')
print(f'  Output: {config.output_dir}')
print(f'  Total tests: {config.total_test_count()}')
print()

# Test the 3-stage execution
from src.cli.benchmark_tui import execute_benchmark, console
console.print('[bold cyan]Testing 3-Stage Architecture...[/bold cyan]')
"

echo
echo "✅ Demo TUI configuration complete!"
echo "📊 Results will be saved to: $DEMO_DIR"
echo
echo "🔗 Next steps:"
echo "  1. Run: python src/cli/benchmark_tui.py"
echo "  2. Choose 'Start New Benchmark'"
echo "  3. Select Arithmetic task"
echo "  4. Choose qwen3:0.6b model"
echo "  5. Watch the 3-stage execution!"
echo
echo "💡 The new workflow:"
echo "  Stage 1: Generate test set (YAML → JSON.gz)"
echo "  Stage 2: Execute tests (portable runner)"
echo "  Stage 3: Analyze results (markdown + charts)"
echo