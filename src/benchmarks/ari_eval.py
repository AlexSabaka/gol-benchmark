"""
Math Expression Generator for gol_eval benchmark
Generates expressions that evaluate to a given target value with varying complexity levels
Includes multilingual prompt templates similar to PROMPT_STYLES.py structure

DEPRECATED: This module is deprecated and will be removed in a future version.
Please use the plugin-based architecture instead:

    from src.plugins import PluginRegistry
    plugin = PluginRegistry.get('arithmetic')
    generator = plugin.get_generator()
    parser = plugin.get_parser()
    evaluator = plugin.get_evaluator()

Or use the 3-stage pipeline:
    python src/stages/generate_testset.py configs/testsets/ari_config.yaml
    python src/stages/run_testset.py testset_*.json.gz --model <model>
    python src/stages/analyze_results.py results_*.json.gz
"""

import warnings
warnings.warn(
    "src.benchmarks.ari_eval is deprecated. "
    "Use the plugin-based architecture (src.plugins.arithmetic) "
    "or the 3-stage pipeline (src.stages) instead.",
    DeprecationWarning,
    stacklevel=2
)

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import random
import re
from tabulate import tabulate
from typing import List, Literal, Optional, Tuple, Dict
from itertools import product, combinations_with_replacement
from tqdm import tqdm

import numpy as np

import argparse
import sys

from src.models.BaseModelInterface import BaseModelInterface, create_interface
from src.evaluation.TestEvaluator import TestEvaluator, TestResult
from src.engine.MathExpressionGenerator import MathExpressionGenerator
from src.core.PromptEngine import PromptEngine, Language, SystemPromptStyle

from src.core.types import AriTestConfig as TestConfig

def run_ari_tests(test_cases, model, config: TestConfig) -> Dict[str, Dict]:
    # Initialize components
    model_interface = create_interface(config)
    evaluator = TestEvaluator()
    
    # Preload models to reduce latency
    model_interface.preload_models()

    results = []
    t0 = datetime.now()
    with tqdm(enumerate(test_cases), desc=f"Model {model}", unit="test", total=len(test_cases), dynamic_ncols=True) as pbar:
        for i, test_case in pbar:
            try:
                response, stats = model_interface.query_model(model, test_case['prompt'], test_case['system'])

                # Parse and evaluate
                target = float(test_case['target'])
                predicted = parse_response(str(test_case['target']), response)
                
                # Display on pbar running correct and incorrect predictions count
                pbar.set_postfix_str(f"Correct {sum(1 for r in results if r['accuracy'] == 1.0)}/{len(test_cases)}")
                
                if predicted is None and config.verbose:
                    print(f"Query: {test_case['expression']}")
                    print(f"Predicted: {predicted}")
                    print(f"Ground Truth: {target}")
                    
                    print('Prompt:')
                    print(test_case['prompt'])
                    print('–'*80)
                    print('Response:')
                    print(response)
                    print('–'*80)

                result: TestResult = {
                    "accuracy": 1.0 if target == predicted else 0.0,
                    "correct_cells": 1 if target == predicted else 0,
                    "total_cells": 1,
                    "parse_error": predicted is None,
                    "cell_by_cell": [],
                    "raw_response": response,
                    "error_details": None
                }
                result['total_duration'] = stats['total_duration']
                result['load_duration'] = stats['load_duration']
                result['prompt_eval_count'] = stats['prompt_eval_count']
                result['prompt_eval_duration'] = stats['prompt_eval_duration']
                result['eval_count'] = stats['eval_count']
                result['eval_duration'] = stats['eval_duration']
                
                results.append(result)

            except Exception as e:
                print(f"Error in test {i+1} for model {model}: {e}")
                raise e
                results.append({
                    "accuracy": 0.0,
                    "correct_cells": 0,
                    "total_cells": 1,
                    "parse_error": True,
                    "cell_by_cell": [],
                    "raw_response": str(e),
                    "error_details": str(e)
                })

    t1 = datetime.now()
    duration = (t1 - t0).total_seconds()

    # Final evaluation for this model
    batch_eval = evaluator.evaluate_batch(results)
    
    if config.verbose:
        print(f"\nResults for {model}:")
        print(f"   Average Accuracy: {batch_eval['average_accuracy']:.2%}")
        print(f"   Normalized Accuracy: {batch_eval['normalized_accuracy']:.2%}")
        # print(f"   Std Accuracy: {batch_eval['std_accuracy']:.2%}")
        # print(f"   Median Accuracy: {batch_eval['median_accuracy']:.2%}")
        print(f"   Valid Tests: {batch_eval['valid_tests']}/{batch_eval['total_tests']}")
        print(f"   Parse Errors: {batch_eval['parse_errors']}")
        print(f"   Success Rate: {batch_eval['success_rate']:.2%}")
        print(f"   Total Duration: {duration:.2f} seconds")
        print(f"   Avg Duration: {duration / len(test_cases):.2f} seconds per test")

    return batch_eval

def parse_response(target: str, response: str) -> float:
    """
    Enhanced parsing with multiple fallback strategies for arithmetic expressions.
    
    Strategy 1: Look for keywords + extract numbers
    Strategy 2: Find "= number" patterns
    Strategy 3: Extract last number in response
    Strategy 4: Find number after specific keywords
    Strategy 5: Regex-based number extraction
    """
    if not response:
        return None
        
    response = str(response).strip()
    
    # Strategy 1: Original keyword-based approach (enhanced)
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
    
    # Strategy 2: Look for "= number" patterns in original response
    equals_pattern = r'=\s*([+-]?(?:[0-9]*[.])?[0-9]+)(?:\s|$)'
    equals_matches = re.findall(equals_pattern, response)
    if equals_matches:
        try:
            return float(equals_matches[-1])  # Take the last match
        except:
            pass
    
    # Strategy 3: Find the last number in the response
    all_numbers = re.findall(r'[+-]?(?:[0-9]*[.])?[0-9]+', response)
    if all_numbers:
        # Try numbers from the end
        for num_str in reversed(all_numbers):
            try:
                return float(num_str)
            except:
                continue
    
    # Strategy 4: Look for specific answer patterns
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
    
    # Strategy 5: Extract number from mathematical expressions
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

def setup_argparser() -> argparse.ArgumentParser:
    """Set up command line argument parser with enhanced help"""
    parser = argparse.ArgumentParser(
        description="Ari Test Framework for LLM Reasoning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ari_eval.py --model qwen3:0.6b --difficulty 1 --batch-size 5
  python ari_eval.py --model llama3.2:3b phi3:3.8b --difficulty 5 --temperature 0.1
  python ari_eval.py --model qwen3:0.6b llama3.2:3b --batch-size 10 --seed 42 --verbose
        """
    )

    # Model configuration
    parser.add_argument(
        '--model', '-m', type=str, nargs='+',
        default=['qwen3:0.6b'],
        help='Ollama models to test (default: qwen3:0.6b)'
    )

    # Test configuration
    parser.add_argument(
        '--difficulty', '-d', type=int, nargs='+', default=[3],
        help='Test difficulties level, sets maximum expression tree depth (default: 3)'
    )
    
    parser.add_argument(
        "--mode", type=str, default="expression", choices=["expression", "equation"],
        help="Mode of test case generation: 'expression' for expressions, 'equation' for equations (default: expression)"
    )
    
    parser.add_argument(
        "--variables", type=str, nargs='+', default=['x'],
        help="Variables to use in expressions (default: ['x'])"
    )

    parser.add_argument(
        '--target', type=int, nargs='+', default=[3],
        help='Test target values (default: 3)'
    )

    parser.add_argument(
        '--rand-target', action='store_true',
        help='Use random target values'
    )

    parser.add_argument(
        '--batch-size', '-b', type=int, default=5,
        help='Number of tests to run (default: 5)'
    )

    parser.add_argument(
        '--seed', '-s', type=int,
        help='Random seed for reproducible tests'
    )

    # Sampling parameters
    parser.add_argument(
        '--temperature', '-t', type=float, default=0.1,
        help='Temperature for sampling (default: 0.1)'
    )

    parser.add_argument(
        '--no-think', action='store_true',
        help='Disable "thinking" step'
    )

    parser.add_argument(
        '--ctx-len', '-c', type=int, default=2048,
        help='Context length (default: 2048)'
    )

    parser.add_argument(
        '--num-predict', '-n', type=int, default=1024,
        help='Number of tokens to predict (default: 1024)'
    )

    parser.add_argument(
        '--top-k', type=int, default=40,
        help='Top-k for sampling (default: 40)'
    )

    parser.add_argument(
        '--min-k', type=int, default=1,
        help='Min-k for sampling (default: 1)'
    )

    parser.add_argument(
        '--min-p', type=float, default=0.05,
        help='Min-p for sampling (default: 0.05)'
    )

    # Prompt style
    parser.add_argument(
        '--prompt-style', type=str, default='linguistic',
        choices=['linguistic', 'casual', 'minimal', 'examples', 'rules_math'],
        help='Prompt style to use (default: linguistic)'
    )

    parser.add_argument(
        '--system-prompt-style', type=str, default='analytical',
        choices=['analytical', 'casual', 'adversarial', 'none'],
        help='System prompt style to use (default: analytical)'
    )

    parser.add_argument(
        '--examples-count', type=int, default=10,
        help='Examples count in prompt (default: 10)'
    )

    parser.add_argument(
        '--prompt-language', type=str, default='en',
        choices=['en', 'fr', 'es', 'de', 'zh', 'ua'],
        help='Language for the prompt (default: en)'
    )

    # Output configuration
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Verbose output showing each test'
    )

    parser.add_argument(
        '--quiet', '-q', action='store_true',
        help='Minimal output, just final results'
    )

    parser.add_argument(
        '--results-dir', type=str, default='results',
        help='Directory to save results (default: results)'
    )

    return parser

def display_results(model_results: Dict[str, Dict], config: TestConfig) -> None:
    """Display results in a user-friendly format"""

    print(f"\n{'='*80}")
    print(f"🏁 FINAL RESULTS FOR TEST RUN CONFIGURATION")
    print(f"Models: {', '.join(config.models)}")
    print(f"Thinking: {'Disabled' if config.no_think else 'Enabled / Auto'}")
    print(f"Target: {', '.join(map(str, config.target_values))}")
    print(f"Difficulty: {', '.join(map(str, config.difficulties))}")
    print(f"Batch Size: {config.batch_size}")
    print(f"Temperature: {config.temperature}")
    print(f"Prompt Style: {config.prompt_style}")
    print(f"System Prompt Style: {config.system_prompt_style}")
    print(f"Prompt Language: {config.prompt_language}")
    print(f"{'='*80}")

    # Prepare table data
    table_data = []
    headers = [
        # "Model", "Avg Accuracy", "Mean Accuracy", "Median Accuracy", "Norm Accuracy",
        "Model", "Avg Accuracy", "Norm Accuracy",
        "Valid Tests", "Parse Errors", "Success Rate", "Perfect Scores", "Top Errors"
    ]

    for model, results in model_results.items():
        row = [
            model,
            f"{results['average_accuracy']:.2%}",
            # f"{results['mean_accuracy']:.2%}",
            # f"{results['median_accuracy']:.2%}",
            f"{results['normalized_accuracy']:.2%}",
            f"{results['valid_tests']}/{results['total_tests']}",
            results['parse_errors'],
            f"{results['success_rate']:.2%}",
            results.get('perfect_scores', 0),
            ""
        ]
        table_data.append(row)

    # Sort by normalized accuracy (descending)
    table_data.sort(key=lambda x: float(x[2].rstrip('%')), reverse=True)

    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Find best model by normalized accuracy
    best_model = max(
        model_results.items(),
        key=lambda x: x[1]['normalized_accuracy']
    )

    print(f"🥇 Best Performing Model: {best_model[0]} ({best_model[1]['normalized_accuracy']:.2%})")

def generate_target_test_cases(config: TestConfig, generator: MathExpressionGenerator) -> List[Dict]:
    prompt_engine = PromptEngine()
    
    # Map string system prompt style to enum
    system_style_map = {
        'analytical': SystemPromptStyle.ANALYTICAL,
        'casual': SystemPromptStyle.CASUAL,
        'adversarial': SystemPromptStyle.ADVERSARIAL,
        'none': SystemPromptStyle.NONE,
    }
    system_prompt_style = system_style_map.get(config.system_prompt_style, SystemPromptStyle.ANALYTICAL)
    
    # Map string language to enum
    language_map = {
        'en': Language.EN,
        'fr': Language.FR,
        'es': Language.ES,
        'de': Language.DE,
        'zh': Language.ZH,
        'ua': Language.UA,
    }
    prompt_language = language_map.get(config.prompt_language, Language.EN)
    
    test_cases = []
    for target in config.target_values:
        for complexity in config.difficulties:
            print(f"Complexity {complexity} expressions that equal {target}:")
            
            test_case = generator.generate_test_case(target, complexity, count=config.batch_size, language=config.prompt_language, style=config.prompt_style)

            for e, p in zip(test_case['items'], test_case['prompts']):
                test_cases.append({
                    "complexity": test_case["complexity"],
                    "language": test_case["language"],
                    "style": test_case["style"],
                    "target": test_case["target"],
                    "expression": e,
                    "prompt": p,
                    "system": prompt_engine.get_system_prompt_by_enum(system_prompt_style, prompt_language),
                })
    return test_cases

def generate_random_target_test_cases(config: TestConfig, generator: MathExpressionGenerator) -> List[Dict]:
    prompt_engine = PromptEngine()
    
    # Map string system prompt style to enum
    system_style_map = {
        'analytical': SystemPromptStyle.ANALYTICAL,
        'casual': SystemPromptStyle.CASUAL,
        'adversarial': SystemPromptStyle.ADVERSARIAL,
        'none': SystemPromptStyle.NONE,
    }
    system_prompt_style = system_style_map.get(config.system_prompt_style, SystemPromptStyle.ANALYTICAL)
    
    test_cases = []
    for complexity in config.difficulties:
        target = random.randint(-100, 100)

        print(f"Complexity {complexity} expressions that equal {target}:")
        
        test_case = generator.generate_test_case(target, complexity, count=config.batch_size, language=config.prompt_language, style=config.prompt_style)
        
        for e, p in zip(test_case['expressions'], test_case['prompts']):
            test_cases.append({
                "complexity": test_case["complexity"],
                "language": test_case["language"],
                "style": test_case["style"],
                "target": test_case["target"],
                "expression": e,
                "prompt": p,
                "system": prompt_engine.get_system_prompt_by_enum(system_prompt_style),
            })
    return test_cases

def main() -> None:
    """Main entry point with enhanced error handling"""
    try:
        parser = setup_argparser()
        args = parser.parse_args()

        # Create config with validation
        config = TestConfig(
            models=args.model,
            difficulties=args.difficulty,
            target_values=args.target,
            random_target=args.rand_target,
            batch_size=args.batch_size,
            temperature=args.temperature,
            no_think=args.no_think,
            ctx_len=args.ctx_len,
            num_predict=args.num_predict,
            top_k=args.top_k,
            min_k=args.min_k,
            min_p=args.min_p,
            verbose=args.verbose and not args.quiet,
            seed=args.seed,
            prompt_style=args.prompt_style,
            system_prompt_style=args.system_prompt_style,
            examples_count=args.examples_count,
            prompt_language=args.prompt_language,
            results_dir=args.results_dir
        )

        generator = MathExpressionGenerator(seed=config.seed)
        
        # Test generating expressions for target value 2 with different complexities
        print("=== Math Expression Generator Test ===")
        print()
        
        test_cases = generate_random_target_test_cases(config, generator) if config.random_target else generate_target_test_cases(config, generator)

        if config.verbose:
            print(f"\nGenerated {len(test_cases)} test cases:")
            # Print system prompt and user prompt generated formats
            print("System and User Prompts:")
            print(test_cases[0]['system'])
            print('–'*80)
            print(test_cases[0]['prompt'])
            print('–'*80)
            for i, tc in enumerate(test_cases):
                print(f"Test Case {i+1}:")
                print(f"  Target: {tc['target']}, Evaluates to: {eval(tc['expression'])}")
                print(f"  Expression: {tc['expression']}")
                print(f"{'-'*40}")

        model_results = {}
        for model in config.models:
            # Run tests
            model_results[model] = run_ari_tests(test_cases, model, config)

        # Display results
        display_results(model_results, config)


    except KeyboardInterrupt:
        print("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        raise e
        sys.exit(1)

if __name__ == "__main__":
    main()
