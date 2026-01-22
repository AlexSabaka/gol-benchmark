# GoL Benchmark - 3-Stage Architecture Refactor

## Overview

Transform the benchmark into three independent stages with clean data handoffs:

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  1. GENERATE     │────▶│  2. EXECUTE      │────▶│  3. ANALYZE      │
│  Test Sets       │     │  On Models       │     │  Results         │
└──────────────────┘     └──────────────────┘     └──────────────────┘
   YAML configs            test_sets.json.gz       results.json.gz
   ↓                       ↓                       ↓
   testset_xyz.json.gz     results_model_xyz...    reports/charts
```

**Key Benefits:**
- ✅ Generate test sets once, run on many models
- ✅ Portable test runner (cloud VMs, different machines)
- ✅ Offline analysis (no model dependencies)
- ✅ Reproducible (same test set = identical conditions)
- ✅ Version control test sets (git track configs + test sets)

---

## Stage 1: Test Set Generation

### Purpose
Generate deterministic, reproducible test sets from declarative YAML configs.

### Input: YAML Configuration

**File:** `configs/testsets/ari_baseline_v1.yaml`

```yaml
# Test Set Configuration
metadata:
  name: "ari_baseline_v1"
  version: "1.0"
  description: "Core arithmetic reasoning baseline"
  created_by: "alex"
  created_at: "2026-01-22"

# Task configuration
task:
  type: "arithmetic"
  
  # Test generation params
  generation:
    seed: 42
    complexity_levels: [1, 3, 5]
    targets: [0, 1, 2]
    expressions_per_config: 12
    
  # Prompt configurations to test
  prompt_configs:
    - name: "minimal_analytical"
      user_style: "minimal"
      system_style: "analytical"
      language: "en"
      
    - name: "linguistic_casual"
      user_style: "linguistic"
      system_style: "casual"
      language: "en"
      
    - name: "minimal_adversarial"
      user_style: "minimal"
      system_style: "adversarial"
      language: "en"

# Sampling parameters (for model execution)
sampling:
  temperature: 0.1
  top_k: 40
  top_p: 0.9
  min_p: 0.05
  max_tokens: 512
  
# Execution hints (optional, for test runner)
execution:
  no_thinking: true
  timeout_seconds: 30
  retry_on_error: 3
```

**File:** `configs/testsets/gol_multilingual_v1.yaml`

```yaml
metadata:
  name: "gol_multilingual_v1"
  version: "1.0"
  description: "Game of Life multilingual test"
  
task:
  type: "game_of_life"
  
  generation:
    seed: 123
    difficulty_levels: ["easy", "medium", "hard"]
    patterns: ["blinker", "glider", "random"]
    grids_per_config: 10
    
  prompt_configs:
    - name: "linguistic_en"
      user_style: "linguistic"
      system_style: "analytical"
      language: "en"
      
    - name: "linguistic_es"
      user_style: "linguistic"
      system_style: "analytical"
      language: "es"
      
    - name: "linguistic_ua"
      user_style: "linguistic"
      system_style: "analytical"
      language: "ua"

sampling:
  temperature: 0.1
  max_tokens: 1024
  
execution:
  no_thinking: true
  cell_markers: ["1", "0"]
```

### Output: Test Set JSON

**File:** `testsets/testset_ari_baseline_v1_20260122_143052.json.gz`

```json
{
  "metadata": {
    "name": "ari_baseline_v1",
    "version": "1.0",
    "description": "Core arithmetic reasoning baseline",
    "created_by": "alex",
    "created_at": "2026-01-22T14:30:52Z",
    "generator_version": "gol_eval_v2.0",
    "config_file": "configs/testsets/ari_baseline_v1.yaml",
    "config_hash": "sha256:abc123..."
  },
  
  "generation_params": {
    "seed": 42,
    "task_type": "arithmetic",
    "complexity_levels": [1, 3, 5],
    "targets": [0, 1, 2],
    "expressions_per_config": 12
  },
  
  "sampling_params": {
    "temperature": 0.1,
    "top_k": 40,
    "top_p": 0.9,
    "min_p": 0.05,
    "max_tokens": 512
  },
  
  "execution_hints": {
    "no_thinking": true,
    "timeout_seconds": 30,
    "retry_on_error": 3
  },
  
  "test_cases": [
    {
      "test_id": "ari_baseline_v1_000",
      "prompt_config": "minimal_analytical",
      "task_params": {
        "complexity": 1,
        "target": 0,
        "expression": "5 - 5",
        "expected_answer": 0
      },
      "prompts": {
        "system_prompt": "You are an expert analytical engine...",
        "user_prompt": "5 - 5 =",
        "full_prompt": "<system>You are an expert...</system>\n<user>5 - 5 =</user>"
      },
      "metadata": {
        "difficulty": "easy",
        "language": "en",
        "user_style": "minimal",
        "system_style": "analytical"
      }
    },
    {
      "test_id": "ari_baseline_v1_001",
      "prompt_config": "minimal_analytical",
      "task_params": {
        "complexity": 1,
        "target": 1,
        "expression": "3 - 2",
        "expected_answer": 1
      },
      "prompts": {
        "system_prompt": "You are an expert analytical engine...",
        "user_prompt": "3 - 2 =",
        "full_prompt": "<system>You are an expert...</system>\n<user>3 - 2 =</user>"
      },
      "metadata": {
        "difficulty": "easy",
        "language": "en",
        "user_style": "minimal",
        "system_style": "analytical"
      }
    }
    // ... 106 more test cases
  ],
  
  "statistics": {
    "total_test_cases": 108,
    "prompt_configs": 3,
    "complexity_levels": 3,
    "targets": 3,
    "expressions_per_complexity_target": 12
  }
}
```

### Generator Script

**File:** `scripts/generate_testset.py`

```python
#!/usr/bin/env python3
"""
Generate test sets from YAML configuration files.

Usage:
    python scripts/generate_testset.py configs/testsets/ari_baseline_v1.yaml
    python scripts/generate_testset.py configs/testsets/*.yaml --output-dir testsets/
"""

import yaml
import json
import gzip
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Minimal imports - only generation dependencies
from src.core.PromptEngine import PromptEngine
from src.engine.MathExpressionGenerator import MathExpressionGenerator
from src.engine.GameOfLifeEngine import GameOfLifeEngine


def load_config(config_path: str) -> Dict[str, Any]:
    """Load YAML config file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def compute_config_hash(config: Dict) -> str:
    """Compute SHA256 hash of config for versioning."""
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()


def generate_arithmetic_tests(config: Dict) -> List[Dict]:
    """Generate arithmetic test cases."""
    tests = []
    gen_params = config['task']['generation']
    
    generator = MathExpressionGenerator(seed=gen_params['seed'])
    prompt_engine = PromptEngine()
    
    test_id = 0
    for prompt_config in config['task']['prompt_configs']:
        for complexity in gen_params['complexity_levels']:
            for target in gen_params['targets']:
                expressions = generator.generate_expressions_for_target(
                    target=target,
                    complexity=complexity,
                    count=gen_params['expressions_per_config']
                )
                
                for expr in expressions:
                    # Generate prompts
                    system_prompt = prompt_engine.get_system_prompt(
                        prompt_config['system_style']
                    )
                    user_prompt = prompt_engine.format_arithmetic_prompt(
                        expression=expr,
                        style=prompt_config['user_style'],
                        language=prompt_config['language']
                    )
                    
                    test_case = {
                        "test_id": f"{config['metadata']['name']}_{test_id:03d}",
                        "prompt_config": prompt_config['name'],
                        "task_params": {
                            "complexity": complexity,
                            "target": target,
                            "expression": expr,
                            "expected_answer": target
                        },
                        "prompts": {
                            "system_prompt": system_prompt,
                            "user_prompt": user_prompt,
                            "full_prompt": f"{system_prompt}\n\n{user_prompt}"
                        },
                        "metadata": {
                            "difficulty": "easy" if complexity <= 2 else "hard",
                            "language": prompt_config['language'],
                            "user_style": prompt_config['user_style'],
                            "system_style": prompt_config['system_style']
                        }
                    }
                    tests.append(test_case)
                    test_id += 1
    
    return tests


def generate_gol_tests(config: Dict) -> List[Dict]:
    """Generate Game of Life test cases."""
    tests = []
    gen_params = config['task']['generation']
    
    gol_engine = GameOfLifeEngine()
    prompt_engine = PromptEngine()
    
    test_id = 0
    for prompt_config in config['task']['prompt_configs']:
        for difficulty in gen_params['difficulty_levels']:
            for pattern_type in gen_params['patterns']:
                for _ in range(gen_params['grids_per_config']):
                    # Generate grid
                    grid = gol_engine.generate_test_grid(
                        difficulty=difficulty,
                        pattern=pattern_type,
                        seed=gen_params['seed'] + test_id
                    )
                    next_grid = gol_engine.evolve(grid)
                    
                    # Generate prompts
                    system_prompt = prompt_engine.get_system_prompt(
                        prompt_config['system_style']
                    )
                    user_prompt = prompt_engine.format_gol_prompt(
                        grid=grid,
                        style=prompt_config['user_style'],
                        language=prompt_config['language']
                    )
                    
                    test_case = {
                        "test_id": f"{config['metadata']['name']}_{test_id:03d}",
                        "prompt_config": prompt_config['name'],
                        "task_params": {
                            "difficulty": difficulty,
                            "pattern_type": pattern_type,
                            "grid": grid.tolist(),
                            "expected_next_grid": next_grid.tolist()
                        },
                        "prompts": {
                            "system_prompt": system_prompt,
                            "user_prompt": user_prompt,
                            "full_prompt": f"{system_prompt}\n\n{user_prompt}"
                        },
                        "metadata": {
                            "difficulty": difficulty,
                            "language": prompt_config['language'],
                            "user_style": prompt_config['user_style'],
                            "system_style": prompt_config['system_style']
                        }
                    }
                    tests.append(test_case)
                    test_id += 1
    
    return tests


def generate_testset(config_path: str, output_dir: str = "testsets") -> str:
    """Generate test set from config file."""
    config = load_config(config_path)
    
    # Generate test cases based on task type
    task_type = config['task']['type']
    if task_type == "arithmetic":
        test_cases = generate_arithmetic_tests(config)
    elif task_type == "game_of_life":
        test_cases = generate_gol_tests(config)
    else:
        raise ValueError(f"Unknown task type: {task_type}")
    
    # Build output structure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    testset = {
        "metadata": {
            **config['metadata'],
            "created_at": datetime.now().isoformat(),
            "generator_version": "gol_eval_v2.0",
            "config_file": config_path,
            "config_hash": f"sha256:{compute_config_hash(config)}"
        },
        "generation_params": config['task']['generation'],
        "sampling_params": config.get('sampling', {}),
        "execution_hints": config.get('execution', {}),
        "test_cases": test_cases,
        "statistics": {
            "total_test_cases": len(test_cases),
            "prompt_configs": len(config['task']['prompt_configs']),
            # ... more stats
        }
    }
    
    # Save to gzipped JSON
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"testset_{config['metadata']['name']}_{timestamp}.json.gz"
    filepath = output_path / filename
    
    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(testset, f, indent=2)
    
    print(f"✓ Generated test set: {filepath}")
    print(f"  - {len(test_cases)} test cases")
    print(f"  - {testset['statistics']['prompt_configs']} prompt configs")
    
    return str(filepath)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test sets from YAML configs")
    parser.add_argument("config", help="Path to YAML config file or glob pattern")
    parser.add_argument("--output-dir", default="testsets", help="Output directory")
    
    args = parser.parse_args()
    
    # Handle glob patterns
    import glob
    config_files = glob.glob(args.config)
    
    if not config_files:
        print(f"Error: No config files found matching: {args.config}")
        exit(1)
    
    for config_file in config_files:
        generate_testset(config_file, args.output_dir)
```

---

## Stage 2: Test Execution

### Purpose
Portable, dependency-minimal script to run test sets on models and save results.

### Input: Test Set JSON.gz

From Stage 1 output.

### Output: Results JSON

**File:** `results/results_qwen3_0.6b_ari_baseline_v1_20260122_150132.json.gz`

```json
{
  "metadata": {
    "result_id": "results_qwen3_0.6b_ari_baseline_v1_20260122_150132",
    "created_at": "2026-01-22T15:01:32Z",
    "executor_version": "test_runner_v2.0",
    "hostname": "cloud-vm-01",
    "python_version": "3.11.5"
  },
  
  "testset_metadata": {
    "testset_file": "testsets/testset_ari_baseline_v1_20260122_143052.json.gz",
    "testset_name": "ari_baseline_v1",
    "testset_version": "1.0",
    "config_hash": "sha256:abc123..."
  },
  
  "model_info": {
    "model_name": "qwen3:0.6b",
    "model_provider": "ollama",
    "quantization": "Q4_K_M",
    "context_length": 2048,
    "version": "qwen3:0.6b-q4-k-m"
  },
  
  "execution_info": {
    "started_at": "2026-01-22T15:01:32Z",
    "completed_at": "2026-01-22T15:08:47Z",
    "duration_seconds": 435,
    "total_tests": 108,
    "successful_tests": 107,
    "failed_tests": 1,
    "average_time_per_test": 4.03
  },
  
  "results": [
    {
      "test_id": "ari_baseline_v1_000",
      "status": "success",
      "timing": {
        "started_at": "2026-01-22T15:01:32.123Z",
        "completed_at": "2026-01-22T15:01:36.456Z",
        "duration_seconds": 4.333
      },
      "input": {
        "system_prompt": "You are an expert analytical engine...",
        "user_prompt": "5 - 5 =",
        "sampling_params": {
          "temperature": 0.1,
          "top_k": 40,
          "max_tokens": 512
        }
      },
      "output": {
        "raw_response": "0",
        "tokens_generated": 1,
        "finish_reason": "stop"
      },
      "evaluation": {
        "expected_answer": 0,
        "parsed_answer": 0,
        "correct": true,
        "match_type": "exact"
      }
    },
    {
      "test_id": "ari_baseline_v1_001",
      "status": "success",
      "timing": {
        "started_at": "2026-01-22T15:01:36.500Z",
        "completed_at": "2026-01-22T15:01:40.123Z",
        "duration_seconds": 3.623
      },
      "input": {
        "system_prompt": "You are an expert analytical engine...",
        "user_prompt": "3 - 2 =",
        "sampling_params": {
          "temperature": 0.1,
          "top_k": 40,
          "max_tokens": 512
        }
      },
      "output": {
        "raw_response": "1",
        "tokens_generated": 1,
        "finish_reason": "stop"
      },
      "evaluation": {
        "expected_answer": 1,
        "parsed_answer": 1,
        "correct": true,
        "match_type": "exact"
      }
    }
    // ... 106 more results
  ],
  
  "summary_statistics": {
    "accuracy": 0.6296,
    "by_prompt_config": {
      "minimal_analytical": {
        "total": 36,
        "correct": 21,
        "accuracy": 0.5833
      },
      "linguistic_casual": {
        "total": 36,
        "correct": 28,
        "accuracy": 0.7778
      },
      "minimal_adversarial": {
        "total": 36,
        "correct": 19,
        "accuracy": 0.5278
      }
    },
    "by_complexity": {
      "1": {"total": 36, "correct": 31, "accuracy": 0.8611},
      "3": {"total": 36, "correct": 22, "accuracy": 0.6111},
      "5": {"total": 36, "correct": 15, "accuracy": 0.4167}
    }
  }
}
```

### Test Runner Script

**File:** `scripts/run_testset.py`

```python
#!/usr/bin/env python3
"""
Portable test runner - execute test sets on models.

ZERO DEPENDENCIES except standard library + model API!
This script should run anywhere with just Python + ollama/transformers.

Usage:
    # Run on Ollama model
    python scripts/run_testset.py \
        testsets/testset_ari_baseline_v1.json.gz \
        --model qwen3:0.6b \
        --provider ollama \
        --output-dir results/

    # Run on HuggingFace model  
    python scripts/run_testset.py \
        testsets/testset_gol_v1.json.gz \
        --model meta-llama/Llama-3.2-3B-Instruct \
        --provider huggingface \
        --output-dir results/
"""

import json
import gzip
import time
import socket
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys


# ============================================================================
# MODEL INTERFACES (minimal implementations)
# ============================================================================

class ModelInterface:
    """Abstract base for model interfaces."""
    
    def query(self, prompt: str, params: Dict) -> Dict[str, Any]:
        """Query model and return response."""
        raise NotImplementedError


class OllamaInterface(ModelInterface):
    """Minimal Ollama interface."""
    
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        
        # Check if requests is available
        try:
            import requests
            self.requests = requests
        except ImportError:
            print("ERROR: 'requests' library required for Ollama")
            print("Install: pip install requests")
            sys.exit(1)
    
    def query(self, prompt: str, params: Dict) -> Dict[str, Any]:
        """Query Ollama model."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": params.get("temperature", 0.1),
                "top_k": params.get("top_k", 40),
                "top_p": params.get("top_p", 0.9),
                "num_predict": params.get("max_tokens", 512)
            }
        }
        
        response = self.requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        return {
            "raw_response": result["response"],
            "tokens_generated": result.get("eval_count", 0),
            "finish_reason": "stop"
        }


class HuggingFaceInterface(ModelInterface):
    """Minimal HuggingFace interface."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            self.torch = torch
            self.AutoTokenizer = AutoTokenizer
            self.AutoModelForCausalLM = AutoModelForCausalLM
        except ImportError:
            print("ERROR: 'transformers' and 'torch' required for HuggingFace")
            print("Install: pip install transformers torch")
            sys.exit(1)
        
        # Load model
        self.tokenizer = self.AutoTokenizer.from_pretrained(model_name)
        self.model = self.AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=self.torch.float16,
            device_map="auto"
        )
    
    def query(self, prompt: str, params: Dict) -> Dict[str, Any]:
        """Query HuggingFace model."""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=params.get("max_tokens", 512),
            temperature=params.get("temperature", 0.1),
            top_k=params.get("top_k", 40),
            top_p=params.get("top_p", 0.9),
            do_sample=True
        )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return {
            "raw_response": response,
            "tokens_generated": len(outputs[0]) - len(inputs.input_ids[0]),
            "finish_reason": "stop"
        }


# ============================================================================
# TEST EXECUTION ENGINE
# ============================================================================

def load_testset(filepath: str) -> Dict:
    """Load test set from gzipped JSON."""
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        return json.load(f)


def save_results(results: Dict, output_dir: str, filename: str):
    """Save results to gzipped JSON."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filepath = output_path / filename
    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    return str(filepath)


def parse_answer(response: str, task_type: str) -> Any:
    """Extract answer from model response."""
    # Simple parsing - can be enhanced
    response = response.strip()
    
    if task_type == "arithmetic":
        # Try to extract number
        import re
        numbers = re.findall(r'-?\d+\.?\d*', response)
        if numbers:
            try:
                return int(float(numbers[-1]))  # Last number in response
            except ValueError:
                return None
    
    elif task_type == "game_of_life":
        # Try to parse grid
        lines = response.strip().split('\n')
        grid = []
        for line in lines:
            row = [int(c) for c in line.split() if c in ('0', '1')]
            if row:
                grid.append(row)
        return grid if grid else None
    
    return None


def evaluate_result(parsed_answer: Any, expected_answer: Any, task_type: str) -> Dict:
    """Evaluate if answer is correct."""
    if parsed_answer is None:
        return {
            "correct": False,
            "match_type": "parse_error",
            "expected_answer": expected_answer,
            "parsed_answer": None
        }
    
    if task_type == "arithmetic":
        correct = (parsed_answer == expected_answer)
        return {
            "correct": correct,
            "match_type": "exact" if correct else "mismatch",
            "expected_answer": expected_answer,
            "parsed_answer": parsed_answer
        }
    
    elif task_type == "game_of_life":
        # Grid comparison
        if not isinstance(parsed_answer, list) or not isinstance(expected_answer, list):
            return {
                "correct": False,
                "match_type": "type_error",
                "expected_answer": expected_answer,
                "parsed_answer": parsed_answer
            }
        
        correct = (parsed_answer == expected_answer)
        return {
            "correct": correct,
            "match_type": "exact" if correct else "mismatch",
            "expected_answer": expected_answer,
            "parsed_answer": parsed_answer
        }
    
    return {"correct": False, "match_type": "unknown"}


def run_testset(
    testset_path: str,
    model_name: str,
    provider: str,
    output_dir: str,
    **kwargs
) -> str:
    """Execute test set and save results."""
    
    # Load test set
    print(f"Loading test set: {testset_path}")
    testset = load_testset(testset_path)
    
    # Initialize model interface
    print(f"Initializing {provider} interface for {model_name}")
    if provider == "ollama":
        interface = OllamaInterface(model_name)
    elif provider == "huggingface":
        interface = HuggingFaceInterface(model_name)
    else:
        raise ValueError(f"Unknown provider: {provider}")
    
    # Prepare results structure
    start_time = datetime.now()
    results = {
        "metadata": {
            "result_id": f"results_{model_name.replace('/', '_')}_{testset['metadata']['name']}_{start_time.strftime('%Y%m%d_%H%M%S')}",
            "created_at": start_time.isoformat(),
            "executor_version": "test_runner_v2.0",
            "hostname": socket.gethostname(),
            "python_version": sys.version
        },
        "testset_metadata": {
            "testset_file": testset_path,
            "testset_name": testset['metadata']['name'],
            "testset_version": testset['metadata']['version'],
            "config_hash": testset['metadata']['config_hash']
        },
        "model_info": {
            "model_name": model_name,
            "model_provider": provider,
            "quantization": kwargs.get("quantization", "unknown"),
            "context_length": kwargs.get("context_length", "unknown")
        },
        "execution_info": {
            "started_at": start_time.isoformat(),
            "total_tests": len(testset['test_cases'])
        },
        "results": []
    }
    
    # Run tests
    successful = 0
    failed = 0
    task_type = testset['generation_params'].get('task_type', 
                                                   testset['metadata']['name'].split('_')[0])
    
    print(f"\nRunning {len(testset['test_cases'])} tests...")
    for i, test_case in enumerate(testset['test_cases']):
        test_id = test_case['test_id']
        print(f"  [{i+1}/{len(testset['test_cases'])}] {test_id}... ", end='', flush=True)
        
        test_start = datetime.now()
        
        try:
            # Query model
            prompt = test_case['prompts']['full_prompt']
            sampling_params = testset['sampling_params']
            
            output = interface.query(prompt, sampling_params)
            
            # Parse and evaluate
            expected = test_case['task_params'].get('expected_answer',
                                                     test_case['task_params'].get('expected_next_grid'))
            parsed = parse_answer(output['raw_response'], task_type)
            evaluation = evaluate_result(parsed, expected, task_type)
            
            test_result = {
                "test_id": test_id,
                "status": "success",
                "timing": {
                    "started_at": test_start.isoformat(),
                    "completed_at": datetime.now().isoformat(),
                    "duration_seconds": (datetime.now() - test_start).total_seconds()
                },
                "input": {
                    "system_prompt": test_case['prompts']['system_prompt'],
                    "user_prompt": test_case['prompts']['user_prompt'],
                    "sampling_params": sampling_params
                },
                "output": output,
                "evaluation": evaluation
            }
            
            results["results"].append(test_result)
            successful += 1
            print("✓" if evaluation['correct'] else "✗")
            
        except Exception as e:
            test_result = {
                "test_id": test_id,
                "status": "error",
                "timing": {
                    "started_at": test_start.isoformat(),
                    "completed_at": datetime.now().isoformat(),
                    "duration_seconds": (datetime.now() - test_start).total_seconds()
                },
                "error": str(e)
            }
            results["results"].append(test_result)
            failed += 1
            print("ERROR")
    
    # Finalize results
    end_time = datetime.now()
    results["execution_info"].update({
        "completed_at": end_time.isoformat(),
        "duration_seconds": (end_time - start_time).total_seconds(),
        "successful_tests": successful,
        "failed_tests": failed,
        "average_time_per_test": (end_time - start_time).total_seconds() / len(testset['test_cases'])
    })
    
    # Compute summary statistics
    correct_count = sum(1 for r in results["results"] 
                       if r.get("evaluation", {}).get("correct", False))
    results["summary_statistics"] = {
        "accuracy": correct_count / len(results["results"]) if results["results"] else 0
    }
    
    # Save results
    filename = f"{results['metadata']['result_id']}.json.gz"
    output_path = save_results(results, output_dir, filename)
    
    print(f"\n✓ Results saved: {output_path}")
    print(f"  - Accuracy: {results['summary_statistics']['accuracy']:.2%}")
    print(f"  - Duration: {results['execution_info']['duration_seconds']:.1f}s")
    
    return output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run test set on model")
    parser.add_argument("testset", help="Path to test set JSON.gz file")
    parser.add_argument("--model", required=True, help="Model name")
    parser.add_argument("--provider", required=True, choices=["ollama", "huggingface"],
                       help="Model provider")
    parser.add_argument("--output-dir", default="results", help="Output directory")
    parser.add_argument("--quantization", help="Quantization format (for metadata)")
    parser.add_argument("--context-length", type=int, help="Context length (for metadata)")
    
    args = parser.parse_args()
    
    run_testset(
        testset_path=args.testset,
        model_name=args.model,
        provider=args.provider,
        output_dir=args.output_dir,
        quantization=args.quantization,
        context_length=args.context_length
    )
```

---

## Stage 3: Analysis & Reporting

### Purpose
Process result files and generate comprehensive analysis reports.

### Input: Results JSON.gz files

From Stage 2 output (one or more).

### Output: Reports & Visualizations

- Markdown reports
- HTML dashboards
- PNG/SVG charts
- Comparison tables

### Analyzer Script

**File:** `scripts/analyze_results.py`

```python
#!/usr/bin/env python3
"""
Analyze test results and generate reports.

Usage:
    # Single model analysis
    python scripts/analyze_results.py results/results_qwen3_*.json.gz

    # Multi-model comparison
    python scripts/analyze_results.py results/results_*.json.gz \
        --comparison \
        --output reports/comparison_2026-01-22.md

    # Generate visualizations
    python scripts/analyze_results.py results/*.json.gz \
        --visualize \
        --output-dir reports/charts/
"""

import json
import gzip
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


def load_result_file(filepath: str) -> Dict:
    """Load result JSON.gz file."""
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        return json.load(f)


def extract_dataframe(result: Dict) -> pd.DataFrame:
    """Convert result to pandas DataFrame for analysis."""
    rows = []
    for test_result in result['results']:
        if test_result['status'] != 'success':
            continue
        
        row = {
            'test_id': test_result['test_id'],
            'model': result['model_info']['model_name'],
            'provider': result['model_info']['model_provider'],
            'correct': test_result['evaluation']['correct'],
            'duration': test_result['timing']['duration_seconds'],
        }
        
        # Add metadata if available
        # This requires accessing original test case metadata
        # For now, parse from test_id
        
        rows.append(row)
    
    return pd.DataFrame(rows)


def generate_markdown_report(results: List[Dict], output_path: str):
    """Generate comprehensive markdown report."""
    
    report = []
    report.append("# Benchmark Analysis Report\n")
    report.append(f"Generated: {pd.Timestamp.now()}\n\n")
    
    # Summary table
    report.append("## Summary\n\n")
    report.append("| Model | Provider | Tests | Accuracy | Avg Time | Duration |\n")
    report.append("|-------|----------|-------|----------|----------|----------|\n")
    
    for result in results:
        model = result['model_info']['model_name']
        provider = result['model_info']['model_provider']
        tests = result['execution_info']['total_tests']
        accuracy = result['summary_statistics']['accuracy']
        avg_time = result['execution_info']['average_time_per_test']
        duration = result['execution_info']['duration_seconds']
        
        report.append(f"| {model} | {provider} | {tests} | {accuracy:.2%} | "
                     f"{avg_time:.2f}s | {duration:.1f}s |\n")
    
    report.append("\n")
    
    # Detailed analysis per model
    for result in results:
        report.append(f"## {result['model_info']['model_name']}\n\n")
        report.append(f"**Provider:** {result['model_info']['model_provider']}  \n")
        report.append(f"**Overall Accuracy:** {result['summary_statistics']['accuracy']:.2%}\n\n")
        
        # Breakdown by prompt config (if available in summary stats)
        if 'by_prompt_config' in result['summary_statistics']:
            report.append("### By Prompt Configuration\n\n")
            report.append("| Config | Tests | Correct | Accuracy |\n")
            report.append("|--------|-------|---------|----------|\n")
            
            for config, stats in result['summary_statistics']['by_prompt_config'].items():
                report.append(f"| {config} | {stats['total']} | {stats['correct']} | "
                             f"{stats['accuracy']:.2%} |\n")
            report.append("\n")
    
    # Save report
    with open(output_path, 'w') as f:
        f.writelines(report)
    
    print(f"✓ Report saved: {output_path}")


def generate_visualizations(results: List[Dict], output_dir: str):
    """Generate visualization charts."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Extract data
    dfs = [extract_dataframe(r) for r in results]
    df = pd.concat(dfs, ignore_index=True)
    
    # 1. Accuracy comparison bar chart
    plt.figure(figsize=(10, 6))
    accuracy_by_model = df.groupby('model')['correct'].mean()
    accuracy_by_model.plot(kind='bar')
    plt.title('Model Accuracy Comparison')
    plt.ylabel('Accuracy')
    plt.xlabel('Model')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_path / 'accuracy_comparison.png', dpi=300)
    plt.close()
    
    # 2. Duration distribution
    plt.figure(figsize=(10, 6))
    for model in df['model'].unique():
        model_df = df[df['model'] == model]
        plt.hist(model_df['duration'], alpha=0.5, label=model, bins=20)
    plt.title('Response Time Distribution')
    plt.xlabel('Duration (seconds)')
    plt.ylabel('Count')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path / 'duration_distribution.png', dpi=300)
    plt.close()
    
    print(f"✓ Visualizations saved to: {output_dir}")


def analyze_results(result_files: List[str], **kwargs):
    """Main analysis function."""
    
    # Load all results
    print(f"Loading {len(result_files)} result files...")
    results = [load_result_file(f) for f in result_files]
    
    # Generate markdown report
    if kwargs.get('output'):
        generate_markdown_report(results, kwargs['output'])
    
    # Generate visualizations
    if kwargs.get('visualize'):
        generate_visualizations(results, kwargs.get('output_dir', 'reports/charts'))


if __name__ == "__main__":
    import argparse
    import glob
    
    parser = argparse.ArgumentParser(description="Analyze benchmark results")
    parser.add_argument("results", nargs='+', help="Result files (supports glob patterns)")
    parser.add_argument("--output", help="Output markdown report path")
    parser.add_argument("--visualize", action='store_true', help="Generate visualizations")
    parser.add_argument("--output-dir", default="reports/charts", help="Visualization output dir")
    parser.add_argument("--comparison", action='store_true', help="Generate comparison report")
    
    args = parser.parse_args()
    
    # Expand glob patterns
    result_files = []
    for pattern in args.results:
        result_files.extend(glob.glob(pattern))
    
    if not result_files:
        print("Error: No result files found")
        exit(1)
    
    analyze_results(
        result_files,
        output=args.output,
        visualize=args.visualize,
        output_dir=args.output_dir,
        comparison=args.comparison
    )
```

---

## Complete Workflow Example

```bash
# ============================================================================
# STAGE 1: Generate Test Sets
# ============================================================================

# Create test set configurations
mkdir -p configs/testsets

# Generate core baseline test set
python scripts/generate_testset.py configs/testsets/ari_baseline_v1.yaml

# Generate multilingual test set
python scripts/generate_testset.py configs/testsets/gol_multilingual_v1.yaml

# Output:
#   testsets/testset_ari_baseline_v1_20260122_143052.json.gz
#   testsets/testset_gol_multilingual_v1_20260122_143105.json.gz


# ============================================================================
# STAGE 2: Execute Tests
# ============================================================================

# Run on local Ollama models
python scripts/run_testset.py \
    testsets/testset_ari_baseline_v1_20260122_143052.json.gz \
    --model qwen3:0.6b \
    --provider ollama \
    --output-dir results/

python scripts/run_testset.py \
    testsets/testset_ari_baseline_v1_20260122_143052.json.gz \
    --model gemma3:1b \
    --provider ollama \
    --output-dir results/

# Copy test set to cloud VM
scp testsets/testset_ari_baseline_v1_20260122_143052.json.gz user@cloud-vm:/tmp/
scp scripts/run_testset.py user@cloud-vm:/tmp/

# Run on cloud VM
ssh user@cloud-vm
cd /tmp
python run_testset.py \
    testset_ari_baseline_v1_20260122_143052.json.gz \
    --model llama3.2:3b \
    --provider ollama \
    --output-dir ./results/

# Download results
scp user@cloud-vm:/tmp/results/*.json.gz results/


# ============================================================================
# STAGE 3: Analyze Results
# ============================================================================

# Generate single model report
python scripts/analyze_results.py \
    results/results_qwen3_0.6b_*.json.gz \
    --output reports/qwen3_analysis.md \
    --visualize

# Generate comparison report
python scripts/analyze_results.py \
    results/results_*_ari_baseline_v1_*.json.gz \
    --comparison \
    --output reports/ari_baseline_comparison_2026-01-22.md \
    --visualize \
    --output-dir reports/charts/ari_baseline/

# Output:
#   reports/ari_baseline_comparison_2026-01-22.md
#   reports/charts/ari_baseline/accuracy_comparison.png
#   reports/charts/ari_baseline/duration_distribution.png
```

---

## Benefits of This Architecture

### ✅ Separation of Concerns
- Test generation doesn't need model access
- Test execution doesn't need prompt engineering
- Analysis doesn't need models or generation logic

### ✅ Reproducibility
- Test sets are versioned and immutable
- Same test set = identical conditions
- Config hash ensures test set integrity

### ✅ Portability
- `run_testset.py` is standalone (copy to any machine)
- No complex dependencies
- Works with cloud VMs, different environments

### ✅ Flexibility
- Generate test sets once, run on many models
- Mix and match different test sets
- Combine results from different runs

### ✅ Efficiency
- No regeneration overhead
- Parallel execution possible (multiple VMs)
- Offline analysis (no model needed)

### ✅ Version Control
- Test sets can be git-tracked
- Config files are human-readable YAML
- Results are compressed but inspectable

---

## Next Steps for Implementation

1. **Phase 1:** Implement Stage 1 (test generation)
2. **Phase 2:** Implement Stage 2 (test runner)
3. **Phase 3:** Implement Stage 3 (analysis)
4. **Phase 4:** Create example configs and documentation
5. **Phase 5:** Integrate with existing benchmarks

Would you like me to start implementing any of these stages?