#!/usr/bin/env python3
"""
Portable test runner - execute test sets on models.

This script implements Stage 2 of the 3-stage benchmark architecture:
Test Set JSON.gz → Query Models → Results JSON.gz

ZERO DEPENDENCIES except standard library + model API!
This script should run anywhere with just Python + ollama/transformers.

Usage:
    # Run on Ollama model
    python scripts/run_testset.py testsets/testset_ari_baseline_v1.json.gz \\
        --model qwen3:0.6b --provider ollama --output-dir results/

    # Run on HuggingFace model  
    python scripts/run_testset.py testsets/testset_gol_v1.json.gz \\
        --model microsoft/DialoGPT-medium --provider huggingface --output-dir results/
"""

import json
import gzip
import time
import socket
import sys
import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Version for results format compatibility
RESULTS_FORMAT_VERSION = "1.0.0"


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
    
    def query(self, prompt: str, params: Dict) -> Dict[str, Any]:
        """Query Ollama model."""
        import urllib.request
        import urllib.parse
        
        # Prepare request data
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": params.get("temperature", 0.1),
                "top_k": params.get("top_k", 40),
                "top_p": params.get("top_p", 0.9),
                "min_p": params.get("min_p", 0.05),
                "num_predict": params.get("max_tokens", 2048),
            }
        }
        
        # Add system prompt if available
        if "system_prompt" in params:
            data["system"] = params["system_prompt"]
        
        # Make request
        start_time = time.time()
        try:
            request_data = json.dumps(data).encode('utf-8')
            request = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(request, timeout=params.get("timeout_seconds", 30)) as response:
                result = json.loads(response.read().decode('utf-8'))
                
            end_time = time.time()
            
            return {
                "response": result.get("response", ""),
                "tokens_generated": result.get("eval_count", 0),
                "duration": end_time - start_time,
                "model_info": {
                    "name": self.model_name,
                    "provider": "ollama"
                }
            }
        
        except Exception as e:
            end_time = time.time()
            return {
                "error": str(e),
                "duration": end_time - start_time,
                "model_info": {
                    "name": self.model_name,
                    "provider": "ollama"
                }
            }


class HuggingFaceInterface(ModelInterface):
    """Minimal HuggingFace interface."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        
        # Import transformers (optional dependency)
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
        except ImportError:
            raise ImportError("HuggingFace interface requires 'transformers' and 'torch' packages")
    
    def query(self, prompt: str, params: Dict) -> Dict[str, Any]:
        """Query HuggingFace model."""
        import torch
        
        start_time = time.time()
        try:
            # Combine system + user prompt
            if "system_prompt" in params:
                full_prompt = f"{params['system_prompt']}\\n\\n{prompt}"
            else:
                full_prompt = prompt
                
            # Tokenize
            inputs = self.tokenizer(full_prompt, return_tensors="pt")
            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=params.get("max_tokens", 2048),
                    temperature=params.get("temperature", 0.1),
                    top_k=params.get("top_k", 40),
                    top_p=params.get("top_p", 0.9),
                    do_sample=params.get("temperature", 0.1) > 0,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response (only new tokens)
            response_tokens = outputs[0][inputs["input_ids"].shape[1]:]
            response = self.tokenizer.decode(response_tokens, skip_special_tokens=True)
            
            end_time = time.time()
            
            return {
                "response": response.strip(),
                "tokens_generated": len(response_tokens),
                "duration": end_time - start_time,
                "model_info": {
                    "name": self.model_name,
                    "provider": "huggingface"
                }
            }
            
        except Exception as e:
            end_time = time.time()
            return {
                "error": str(e),
                "duration": end_time - start_time,
                "model_info": {
                    "name": self.model_name,
                    "provider": "huggingface"
                }
            }


# ============================================================================
# TEST EXECUTION ENGINE
# ============================================================================

def load_testset(filepath: str) -> Dict:
    """Load test set from gzipped JSON."""
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        return json.load(f)


def save_results(results: Dict, output_dir: str, filename: str) -> str:
    """Save results to gzipped JSON."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filepath = output_path / filename
    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    return str(filepath)


def parse_answer(response: str, task_type: str) -> Any:
    """Extract answer from model response using proven parsing strategies from ari_eval.py"""
    if not response:
        return None
        
    response = response.strip()
    
    if task_type == "arithmetic":
        # Use the exact parsing logic from ari_eval.py that we know works
        return parse_arithmetic_response("", response)  # target not used in our enhanced version
    
    elif task_type == "game_of_life":
        # Enhanced Game of Life parsing (keep existing logic but simplified)
        lines = response.split('\n')
        
        # Strategy 1: Look from end for rectangular patterns
        for start_idx in range(len(lines) - 3 + 1, -1, -1):  # Assume 3x3 minimum
            candidate_lines = lines[start_idx:start_idx + 10]  # Check up to 10x10
            
            # Try different grid sizes
            for grid_size in range(3, min(11, len(candidate_lines) + 1)):
                grid_lines = candidate_lines[:grid_size]
                grid = []
                
                for line in grid_lines:
                    # Extract 0s and 1s from line
                    digits = re.findall(r'[01]', line)
                    if len(digits) == grid_size:  # Must be square
                        grid.append([int(d) for d in digits])
                    else:
                        break
                
                if len(grid) == grid_size:
                    return grid
        
        # Strategy 2: Extract any rectangular pattern of 0s and 1s
        all_digits = re.findall(r'[01]', response)
        if len(all_digits) >= 9:  # At least 3x3
            # Try different square sizes
            for grid_size in [3, 4, 5, 6, 7, 8, 9, 10]:
                total_cells = grid_size * grid_size
                if len(all_digits) >= total_cells:
                    try:
                        grid_digits = all_digits[:total_cells]  # Take first set
                        grid = []
                        for i in range(grid_size):
                            row_start = i * grid_size
                            row_end = row_start + grid_size
                            row = [int(d) for d in grid_digits[row_start:row_end]]
                            grid.append(row)
                        return grid
                    except:
                        continue
        
        return None
    
    return None


def parse_arithmetic_response(target: str, response: str) -> float:
    """
    Enhanced parsing with multiple fallback strategies for arithmetic expressions.
    This is the enhanced version from ari_eval.py with LaTeX boxed pattern support.
    
    Strategy 0: Handle JSON escaping first
    Strategy 1: LaTeX boxed pattern (\\boxed{number})  
    Strategy 2: Look for keywords + extract numbers
    Strategy 3: Find "= number" patterns  
    Strategy 4: Extract last number in response
    Strategy 5: Find number after specific keywords
    Strategy 6: Regex-based number extraction
    """
    if not response:
        return None
        
    response = str(response).strip()
    
    # Strategy 0: Handle JSON escaping (\\boxed becomes \boxed)
    # This is crucial for multi-task results where responses are JSON-escaped
    import json
    try:
        # Try to unescape JSON if it looks like it's escaped
        if '\\\\boxed' in response or '\\\\[' in response:
            response = json.loads(f'"{response}"')
    except:
        pass  # If JSON unescaping fails, use original response
    
    # Strategy 1: LaTeX boxed pattern - PRIORITY PATTERN
    # Look for \boxed{number} patterns (most common in math responses)
    boxed_patterns = [
        r'\\boxed\{([+-]?(?:[0-9]*[.])?[0-9]+)\}',  # \boxed{123}
        r'\\boxed\{\s*([+-]?(?:[0-9]*[.])?[0-9]+)\s*\}',  # \boxed{ 123 }
        r'boxed\{([+-]?(?:[0-9]*[.])?[0-9]+)\}',   # boxed{123} (no backslash)
    ]
    
    for pattern in boxed_patterns:
        matches = re.findall(pattern, response)
        if matches:
            try:
                return float(matches[-1])  # Take the last boxed answer
            except:
                continue
    
    # Strategy 2: Original keyword-based approach (enhanced)
    match_words = [
        'final result', 'result', 'final answer', 'answer', 'response', 
        'therefore', '\\boxed', 'equals', '=', target,
        'final result:', 'answer:', 'result:', 'solution:'
    ]
    
    response_lines = response.lower().splitlines()
    response_lines.reverse()
    
    for i, line in enumerate(response_lines):
        if any(word in line for word in match_words):
            # Look for number in this line and following lines
            for j in range(i, min(i + 3, len(response_lines))):  # Check up to 3 lines
                current_line = response_lines[j]
                
                # Try to extract number from line with target
                if target in current_line:
                    parts = current_line.split('=')
                    if len(parts) > 1:
                        number_match = re.search(r'[+-]?([0-9]*[.])?[0-9]+', parts[-1].strip())
                        if number_match:
                            try:
                                return float(number_match.group())
                            except:
                                continue
                
                # Extract any number from the line
                number_match = re.search(r'[+-]?([0-9]*[.])?[0-9]+', current_line)
                if number_match:
                    try:
                        return float(number_match.group())
                    except:
                        continue
    
    # Strategy 3: Look for "= number" patterns in original response
    equals_pattern = r'=\s*([+-]?(?:[0-9]*[.])?[0-9]+)(?:\s|$)'
    equals_matches = re.findall(equals_pattern, response)
    if equals_matches:
        try:
            return float(equals_matches[-1])  # Take the last match
        except:
            pass
    
    # Strategy 4: Find the last number in the response
    all_numbers = re.findall(r'[+-]?(?:[0-9]*[.])?[0-9]+', response)
    if all_numbers:
        # Try numbers from the end
        for num_str in reversed(all_numbers):
            try:
                return float(num_str)
            except:
                continue
    
    # Strategy 5: Look for specific answer patterns
    answer_patterns = [
        r'answer[:\s]+([+-]?(?:[0-9]*[.])?[0-9]+)',
        r'result[:\s]+([+-]?(?:[0-9]*[.])?[0-9]+)',
        r'solution[:\s]+([+-]?(?:[0-9]*[.])?[0-9]+)',
        r'final[:\s]+([+-]?(?:[0-9]*[.])?[0-9]+)'
    ]
    
    response_lower = response.lower()
    for pattern in answer_patterns:
        matches = re.findall(pattern, response_lower)
        if matches:
            try:
                return float(matches[-1])
            except:
                continue
    
    # Strategy 6: Extract number from mathematical expressions
    # Look for standalone numbers that might be results
    lines = response.strip().split('\n')
    for line in reversed(lines):  # Start from the end
        line = line.strip()
        if line and re.match(r'^[+-]?(?:[0-9]*[.])?[0-9]+$', line):
            try:
                return float(line)
            except:
                continue
    
    return None


def evaluate_result(parsed_answer: Any, expected_answer: Any, task_type: str) -> Dict:
    """Evaluate if answer is correct."""
    if parsed_answer is None:
        return {
            "correct": False,
            "match_type": "parse_error",
            "accuracy": 0.0,
            "error": "Failed to parse response"
        }
    
    if task_type == "arithmetic":
        # Numeric comparison with tolerance
        try:
            expected = float(expected_answer)
            actual = float(parsed_answer)
            correct = abs(expected - actual) < 0.001
            
            return {
                "correct": correct,
                "match_type": "exact" if correct else "numeric_mismatch",
                "accuracy": 1.0 if correct else 0.0,
                "expected": expected,
                "actual": actual
            }
        except (ValueError, TypeError):
            return {
                "correct": False,
                "match_type": "type_error",
                "accuracy": 0.0,
                "expected": expected_answer,
                "actual": parsed_answer
            }
    
    elif task_type == "game_of_life":
        # Grid comparison
        if not isinstance(parsed_answer, list) or not isinstance(expected_answer, list):
            return {
                "correct": False,
                "match_type": "type_error",
                "accuracy": 0.0
            }
        
        # Compare dimensions
        if len(parsed_answer) != len(expected_answer):
            return {
                "correct": False,
                "match_type": "dimension_mismatch",
                "accuracy": 0.0,
                "expected_dims": (len(expected_answer), len(expected_answer[0]) if expected_answer else 0),
                "actual_dims": (len(parsed_answer), len(parsed_answer[0]) if parsed_answer else 0)
            }
        
        # Cell-by-cell comparison
        total_cells = 0
        correct_cells = 0
        
        for i, (expected_row, actual_row) in enumerate(zip(expected_answer, parsed_answer)):
            if len(expected_row) != len(actual_row):
                return {
                    "correct": False,
                    "match_type": "row_length_mismatch",
                    "accuracy": 0.0,
                    "error_row": i
                }
            
            for expected_cell, actual_cell in zip(expected_row, actual_row):
                total_cells += 1
                if expected_cell == actual_cell:
                    correct_cells += 1
        
        accuracy = correct_cells / total_cells if total_cells > 0 else 0.0
        perfect_match = correct_cells == total_cells
        
        return {
            "correct": perfect_match,
            "match_type": "perfect" if perfect_match else "partial",
            "accuracy": accuracy,
            "correct_cells": correct_cells,
            "total_cells": total_cells
        }
    
    return {"correct": False, "match_type": "unknown", "accuracy": 0.0}


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
    
    # Validate format version compatibility
    if testset.get("format_version") != "1.0.0":
        print(f"Warning: Test set format version {testset.get('format_version')} may not be fully compatible")
    
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
        "format_version": RESULTS_FORMAT_VERSION,
        "metadata": {
            "result_id": f"results_{model_name.replace(':', '_').replace('/', '_')}_{testset['metadata']['name']}_{start_time.strftime('%Y%m%d_%H%M%S')}",
            "created_at": start_time.isoformat(),
            "hostname": socket.gethostname(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "runner_version": "1.0.0"
        },
        
        "testset_metadata": {
            "testset_file": os.path.basename(testset_path),
            "testset_name": testset['metadata']['name'],
            "testset_version": testset['metadata']['version'],
            "config_hash": testset['metadata']['config_hash'],
            "task_type": testset['metadata']['task_type']
        },
        
        "model_info": {
            "model_name": model_name,
            "provider": provider,
            "quantization": kwargs.get("quantization"),
            "context_length": kwargs.get("context_length")
        },
        
        "execution_info": {
            "started_at": start_time.isoformat(),
            "sampling_params": testset.get("sampling_params", {}),
            "execution_hints": testset.get("execution_hints", {})
        },
        
        "results": []
    }
    
    # Run tests
    successful = 0
    failed = 0
    task_type = testset['metadata']['task_type']
    total_tests = len(testset['test_cases'])
    
    print(f"\\nRunning {total_tests} tests...")
    
    for i, test_case in enumerate(testset['test_cases']):
        test_id = test_case['test_id']
        
        # Progress indicator
        if i % 10 == 0 or i == total_tests - 1:
            print(f"Progress: {i+1}/{total_tests} ({(i+1)/total_tests*100:.1f}%)")
        
        # Prepare query parameters
        query_params = testset.get("sampling_params", {}).copy()
        query_params.update(testset.get("execution_hints", {}))
        
        # Add system prompt if available
        if test_case['prompts'].get('system'):
            query_params['system_prompt'] = test_case['prompts']['system']
        
        # Query model
        test_start = time.time()
        response_data = interface.query(test_case['prompts']['user'], query_params)
        test_end = time.time()
        
        # Process response
        if "error" in response_data:
            result = {
                "test_id": test_id,
                "status": "error",
                "error": response_data["error"],
                "duration": response_data["duration"],
                "input": {
                    "user_prompt": test_case['prompts']['user'],
                    "system_prompt": test_case['prompts'].get('system'),
                    "task_params": test_case['task_params']
                }
            }
            failed += 1
            
        else:
            # Parse and evaluate response
            raw_response = response_data["response"]
            
            # Get task type from individual test case (for multi-task support)
            individual_task_type = test_case.get('task_type', task_type)
            
            parsed_answer = parse_answer(raw_response, individual_task_type)
            expected_answer = test_case['task_params'].get('expected_answer') or test_case['task_params'].get('expected_next_state')
            
            evaluation = evaluate_result(parsed_answer, expected_answer, individual_task_type)
            
            result = {
                "test_id": test_id,
                "status": "success",
                "input": {
                    "user_prompt": test_case['prompts']['user'],
                    "system_prompt": test_case['prompts'].get('system'),
                    "task_params": test_case['task_params']
                },
                "output": {
                    "raw_response": raw_response,
                    "parsed_answer": parsed_answer,
                    "tokens_generated": response_data.get("tokens_generated", 0)
                },
                "evaluation": evaluation,
                "duration": response_data["duration"]
            }
            successful += 1
        
        results["results"].append(result)
    
    # Finalize results
    end_time = datetime.now()
    results["execution_info"].update({
        "completed_at": end_time.isoformat(),
        "duration_seconds": (end_time - start_time).total_seconds(),
        "successful_tests": successful,
        "failed_tests": failed,
        "average_time_per_test": (end_time - start_time).total_seconds() / total_tests
    })
    
    # Compute summary statistics
    if successful > 0:
        correct_count = sum(1 for r in results["results"] 
                           if r.get("evaluation", {}).get("correct", False))
        accuracy = correct_count / successful
        
        # Task-specific stats
        if task_type == "arithmetic":
            parse_errors = sum(1 for r in results["results"]
                              if r.get("evaluation", {}).get("match_type") == "parse_error")
        elif task_type == "game_of_life":
            total_cell_accuracy = []
            for r in results["results"]:
                if r.get("evaluation", {}).get("accuracy") is not None:
                    total_cell_accuracy.append(r["evaluation"]["accuracy"])
            avg_cell_accuracy = sum(total_cell_accuracy) / len(total_cell_accuracy) if total_cell_accuracy else 0.0
        
        results["summary_statistics"] = {
            "accuracy": accuracy,
            "correct_responses": correct_count,
            "total_responses": successful,
            "parse_error_rate": sum(1 for r in results["results"] 
                                   if r.get("evaluation", {}).get("match_type") == "parse_error") / successful,
        }
        
        if task_type == "game_of_life" and 'avg_cell_accuracy' in locals():
            results["summary_statistics"]["average_cell_accuracy"] = avg_cell_accuracy
            
    else:
        results["summary_statistics"] = {"accuracy": 0.0}
    
    # Save results
    filename = f"{results['metadata']['result_id']}.json.gz"
    output_path = save_results(results, output_dir, filename)
    
    print(f"\\n✓ Results saved: {output_path}")
    print(f"  - Accuracy: {results['summary_statistics']['accuracy']:.2%}")
    print(f"  - Duration: {results['execution_info']['duration_seconds']:.1f}s")
    print(f"  - Successful: {successful}/{total_tests}")
    
    return output_path


def main():
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
    
    try:
        run_testset(
            testset_path=args.testset,
            model_name=args.model,
            provider=args.provider,
            output_dir=args.output_dir,
            quantization=args.quantization,
            context_length=args.context_length
        )
    except Exception as e:
        print(f"✗ Error running test set: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()