# GoL Procedural Benchmark

A procedural benchmark suite for testing multilingual LLM reasoning capabilities across tasks requiring step-by-step logic and systematic rule application.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## What Is This?

GoL Benchmark is a **pet project evolved to experimental playground** for stress-testing how well language models handle **structured reasoning tasks** across different:

- **Languages** (English, Spanish, French, German, Chinese, Ukrainian)
- **Prompt styles** (linguistic, casual, minimal, examples-based)
- **Representations** (numeric `1/0` vs emoji `🟩/🟥` and etc)
- **Complexity levels** (from easy to nightmare mode)

Think of it as a systematic benchmark for LLMs to expose their reasoning gaps, biases, and quirks.

---

## What Gets Tested?

### 1. **Game of Life (GoL)** 🕹️

Conway's cellular automaton rules — can models predict the next grid state?

### 2. **Arithmetic Expression Evaluation (Ari)** 🧮

Math expression parsing and solving with varying complexity levels.

### 3. **Linda Conjunction Fallacy** 🧠

Classic Tversky & Kahneman cognitive bias test — do models fall for probabilistic reasoning traps?

### 4. **Cellular Automata (C14)** 🔄

Pattern evolution testing (similar to GoL but configurable rules).

### 5. **Math Equation Generation (MEG)** 📐

Procedural equation generation for benchmarking symbolic reasoning.

---

## Quick Start

### Prerequisites

- **Python 3.8+**
- **[Ollama](https://ollama.ai/)** (for running local LLMs)

### Installation

```bash
# Clone the repo
git clone https://github.com/AlexSabaka/gol-benchmark.git
cd gol-benchmark

# Install dependencies
pip install -r requirements.txt

# Make sure Ollama is running
ollama serve
```

### Run Your First Benchmark

```bash
# Game of Life - Easy difficulty with qwen3
python gol_eval.py --difficulty medium --temperature 0.25 --ctx-len 4096 --num-predict 2048 --top-k 40 --min-k 1 --min-p 0.05 --prompt-style linguistic --live-dead-cell-markers 1,0 --prompt-language en --model qwen3:0.6b gemma3:1b --batch-size=20 --seed=42 --known-patterns-ratio=1.0 --density=.50 --no-think

# Arithmetic expressions with multiple models
python ari_eval.py --model qwen3:0.6b llama3.2:3b --difficulty 3 --batch-size 10

# Linda fallacy test in Spanish
python linda_eval.py --models llama3.2:3b --language es --trials 10
```

---

## Key Findings (So Far)

### The Emoji Catastrophe 🟩🟥

**Using emoji markers (`🟩/🟥`) instead of numeric (`1/0`) causes complete failure:**

| Model | Numeric (1/0) | Emoji (🟩/🟥) |
|-------|---------------|----------------|
| qwen3:0.6b | 61.67% | **0.00%** |
| gemma3:1b | 66.11% | **0.00%** |


### Prompt Style Impact

- **Examples-based prompts** work best for GoL (66% accuracy)
- **Minimal prompts** show surprising resilience (56-60% accuracy)
- **"Thinking" mode** (chain-of-thought) often hurts performance on structured tasks

---

## Configuration Options

### Global Parameters

```bash
python gol_eval.py --help
python ari_eval.py --help
python с14_eval.py --help
python linda_eval.py --help

# TODO: Add concrete usage examples
```

---

## Contributing

This is a **personal experiment**, but if you're curious and want to:

- Add new benchmark tasks
- Test more models
- Improve prompt engineering
- Fix bugs or add features

**Pull requests are welcomed!**

---

## Roadmap

- [ ] More languages (Japanese, Arabic, Hindi)
- [ ] Cross-lingual transfer tests
- [ ] Add visual result dashboards
- [ ] OpenAI API integration for testing closed models (GPT-4, Claude, Gemini)
- [ ] Document failure modes systematically
- [ ] Add statistical significance testing

---

## License

See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Anthropic AI team
- Conway's Game of Life rules
- The Ollama team for making local LLM testing accessible
- And every model that crashed hilariously on emoji grids
