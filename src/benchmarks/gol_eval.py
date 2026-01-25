#!/usr/bin/env python3
"""
Game of Life Test Framework for LLM Reasoning
Tests whether models can systematically apply Conway's Game of Life rules

DEPRECATED: This module is deprecated and will be removed in a future version.
Please use the plugin-based architecture instead:

    from src.plugins import PluginRegistry
    plugin = PluginRegistry.get('game_of_life')
    generator = plugin.get_generator()
    parser = plugin.get_parser()
    evaluator = plugin.get_evaluator()

Or use the 3-stage pipeline:
    python src/stages/generate_testset.py configs/testsets/gol_config.yaml
    python src/stages/run_testset.py testset_*.json.gz --model <model>
    python src/stages/analyze_results.py results_*.json.gz
"""

import warnings
warnings.warn(
    "src.benchmarks.gol_eval is deprecated. "
    "Use the plugin-based architecture (src.plugins.game_of_life) "
    "or the 3-stage pipeline (src.stages) instead.",
    DeprecationWarning,
    stacklevel=2
)

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import re
from tabulate import tabulate
from typing import Dict, List, Optional, Literal, Tuple, TypedDict
from tqdm import tqdm

import numpy as np

import argparse
import sys

from src.core.PromptEngine import PromptEngine, Language, SystemPromptStyle, create_gol_context
from src.utils.logger import logger
from src.core.types import DifficultyLevel, ParseError, GameOfLifeTestConfig as TestConfig

from src.engine.GameOfLifeEngine import GameOfLifeEngine
from src.models.BaseModelInterface import BaseModelInterface, create_interface
from src.evaluation.TestEvaluator import TestEvaluator
from src.core.TestGenerator import TestGenerator, EXAMPLE_PATTERNS

def format_examples(patterns, width, height, config: TestConfig):
    engine = GameOfLifeEngine()
    results = []
    np.random.shuffle(patterns)
    for ex in patterns[:config.examples_count]:
        start_row = np.random.randint(1, min(len(ex), height) + 1)
        start_col = np.random.randint(1, min(len(ex[0]), width) + 1)
        grid = [[0 for _ in range(width)] for _ in range(height)]
        for r in range(min(len(ex), height - start_row)):
            for c in range(min(len(ex[0]), width - start_col)):
                grid[start_row + r][start_col + c] = ex[r][c]

        neighbors = [
            [engine.count_neighbors(grid, i, j) for j,col in enumerate(row)] for i,row in enumerate(grid)
        ]
    
        results.append(
f"""{format_grid(grid, config.live_dead_cell_markers[0], config.live_dead_cell_markers[1])}

{format_grid(engine.next_state(grid), config.live_dead_cell_markers[0], config.live_dead_cell_markers[1])}""")

    if 'rules_math' in config.prompt_style:
        def format_single_example(res):
            res = res.replace(" ", " & ")
            subres = []
            for i in range(len(res) - 1):
                if res[i] == '\n' and res[i+1] != '\n' and i - 1 > 0 and res[i - 1] != '\n':
                    subres.append(" \\\\\n")
                elif res[i] == '\n' and res[i+1] == '\n':
                    subres.append("\n\\end{bmatrix} \\newlinen\ng{(1)} = \\begin{bmatrix}")
                else:
                    subres.append(res[i])
            else:
                subres.append(res[-1])
            res = ''.join(subres)
            return "g{(0)} = \\begin{bmatrix}\n" + res + "\n\\end{bmatrix}"
        
        return "\n\\\\\n\\rule{100pt}{0.4pt} \\\\\n".join([
            format_single_example(r) for r in results
        ])

    return "\n---\n".join(results)

def format_prompt(grid: List[List[int]], config: TestConfig, examples: str = '') -> Tuple[str, str]:
    """Format grid into a clear prompt using PromptEngine"""
    grid_str = format_grid(grid, config.live_dead_cell_markers[0], config.live_dead_cell_markers[1])
    
    engine = PromptEngine()
    
    # Map language string to enum
    language_map = {
        'en': Language.EN,
        'fr': Language.FR,
        'es': Language.ES,
        'de': Language.DE,
        'zh': Language.ZH,
        'ua': Language.UA,
    }
    prompt_language = language_map.get(config.prompt_language, Language.EN)
    
    # Map system style string to enum
    system_style_map = {
        'analytical': SystemPromptStyle.ANALYTICAL,
        'casual': SystemPromptStyle.CASUAL,
        'adversarial': SystemPromptStyle.ADVERSARIAL,
        'none': SystemPromptStyle.NONE,
    }
    system_prompt_style = system_style_map.get(config.system_prompt_style, SystemPromptStyle.ANALYTICAL)
    
    # Create Game of Life context
    context = create_gol_context(
        grid_str=grid_str,
        prompt_style=config.prompt_style,
        language=prompt_language
    )
    
    # Generate prompt
    result = engine.generate(context)
    
    # Replace placeholders with actual markers
    user_prompt = result.user_prompt.format(
        l=config.live_dead_cell_markers[0],
        d=config.live_dead_cell_markers[1],
        w=len(grid[0]),
        h=len(grid),
        examples=examples
    )
    
    system_prompt = engine.get_system_prompt(system_prompt_style)
    
    return user_prompt, system_prompt

def find_json_key_with_shape(data: dict, expected_shape: List[List[int]]) -> Optional[List[List[int]]]:
    """Recursively search for a key in a nested dict that matches the expected grid shape"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                result = find_json_key_with_shape(value, expected_shape)
                if result is not None:
                    return result
    elif isinstance(data, list):
        for item in data:
            result = find_json_key_with_shape(item, expected_shape)
            if result is not None:
                return result
    return None

def format_grid(g: List[List[int]], live_cell_mark: str = '1', dead_cell_mark: str = '0') -> str:
    """Format grid into string representation"""
    return "\n".join([" ".join(map(str, row)) for row in g]).replace('1', live_cell_mark).replace('0', dead_cell_mark)

def parse_response(prompt: str, response: str, expected_shape: List[List[int]], live_cell_mark: str = '1', dead_cell_mark: str = '0') -> Optional[List[List[int]]]:
    """
    Enhanced Game of Life response parsing with multiple fallback strategies.
    
    Strategy 1: Original grid pattern matching (enhanced)
    Strategy 2: Look for clearly marked grids
    Strategy 3: Parse any rectangular pattern of 0s and 1s
    """
    if not response:
        logger.warning("Empty response from model")
        return None
    
    expected_rows = len(expected_shape)
    expected_cols = len(expected_shape[0]) if expected_shape else 0
    
    try:
        lines = response.strip().split('\n')
        
        # Strategy 1: Enhanced original approach - look from end
        for start_idx in range(len(lines) - expected_rows + 1, -1, -1):
            candidate_lines = lines[start_idx:start_idx + expected_rows]
            if len(candidate_lines) != expected_rows:
                continue

            grid = []
            for line in candidate_lines:
                # Clean the line - remove all non-marker characters except spaces
                cleaned_line = ''
                for char in line.strip():
                    if char in (live_cell_mark, dead_cell_mark, ' ', '\t'):
                        cleaned_line += char
                    elif char.isdigit():  # Convert any digit to appropriate marker
                        cleaned_line += live_cell_mark if char != '0' else dead_cell_mark
                
                # Normalize whitespace and convert markers
                cleaned_line = re.sub(r'\s+', ' ', cleaned_line.strip())
                cleaned_line = cleaned_line.replace(live_cell_mark, '1').replace(dead_cell_mark, '0')
                
                # Extract row
                row = []
                for char in cleaned_line.split():
                    if char in ('0', '1'):
                        row.append(int(char))
                
                if len(row) != expected_cols:
                    break
                
                grid.append(row)
                
                if len(grid) == expected_rows:
                    logger.info(f"Successfully parsed grid using Strategy 1")
                    return grid
        
        # Strategy 2: Look for clearly marked grid sections
        grid_markers = ['next:', 'result:', 'grid:', 'state:', 'generation:']
        for marker in grid_markers:
            marker_idx = -1
            for i, line in enumerate(lines):
                if marker in line.lower():
                    marker_idx = i
                    break
            
            if marker_idx >= 0:
                # Try to parse grid starting from marker line
                for start_idx in range(marker_idx, min(marker_idx + 3, len(lines) - expected_rows + 1)):
                    candidate_lines = lines[start_idx:start_idx + expected_rows]
                    
                    grid = []
                    for line in candidate_lines:
                        # Extract 0s and 1s from line
                        digits = re.findall(r'[01]', line)
                        if len(digits) == expected_cols:
                            grid.append([int(d) for d in digits])
                        else:
                            break
                    
                    if len(grid) == expected_rows:
                        logger.info(f"Successfully parsed grid using Strategy 2 (marker: {marker})")
                        return grid
        
        # Strategy 3: Find any rectangular pattern of 0s and 1s
        for start_idx in range(len(lines) - expected_rows + 1):
            candidate_lines = lines[start_idx:start_idx + expected_rows]
            
            grid = []
            for line in candidate_lines:
                # Extract all 0s and 1s
                digits = re.findall(r'[01]', line)
                if len(digits) >= expected_cols:
                    # Take first expected_cols digits
                    grid.append([int(d) for d in digits[:expected_cols]])
                else:
                    break
            
            if len(grid) == expected_rows:
                # Verify this looks like a reasonable grid
                total_cells = expected_rows * expected_cols
                ones_count = sum(sum(row) for row in grid)
                if 0 <= ones_count <= total_cells:  # Basic sanity check
                    logger.info(f"Successfully parsed grid using Strategy 3")
                    return grid
        
        # Strategy 4: Last resort - try to extract any numbers and arrange them
        all_digits = re.findall(r'[01]', response)
        if len(all_digits) >= expected_rows * expected_cols:
            # Take the first or last set of digits that matches our grid size
            start_positions = [0, len(all_digits) - expected_rows * expected_cols]
            
            for start_pos in start_positions:
                try:
                    grid_digits = all_digits[start_pos:start_pos + expected_rows * expected_cols]
                    grid = []
                    for i in range(expected_rows):
                        row_start = i * expected_cols
                        row_end = row_start + expected_cols
                        row = [int(d) for d in grid_digits[row_start:row_end]]
                        grid.append(row)
                    
                    logger.info(f"Successfully parsed grid using Strategy 4")
                    return grid
                except:
                    continue
        
        logger.warning(
            f"All parsing strategies failed.\nExpected: {expected_rows}x{expected_cols}\nPrompt:\n---\n{prompt}\n---\nResponse:\n{response}\n---"
        )
        return None

    except Exception as e:
        logger.error(f"Failed to parse response for {expected_rows}x{expected_cols} grid.\nPrompt:\n---\n{prompt}\n---\nResponse:\n{response}\n---", exc_info=True)
        return None

def run_game_of_life_test(config: TestConfig) -> Dict[str, Dict]:
    """Main function to run the Game of Life test with enhanced logging"""
    logger.info(f"Starting Game of Life LLM Reasoning Test")
    logger.info(f"Models: {', '.join(config.models)}")
    logger.info(f"Difficulty: {config.difficulty.name} ({config.difficulty.value})")
    logger.info(f"Batch size: {config.batch_size}")

    # Initialize components
    generator = TestGenerator(config)
    model_interface = create_interface(config)
    evaluator = TestEvaluator()
    engine = GameOfLifeEngine()
    
    # Preload models to reduce latency
    model_interface.preload_models()

    # Generate test cases
    test_cases = generator.create_test_batch(config.difficulty, config.batch_size, config.density, config.known_patterns_ratio)

    # Store results for each model
    model_results = {}

    # Run tests for each model
    for model in config.models:
        logger.info(f"\nTesting model: {model}")
        results = []

        t0 = datetime.now()
        logger.info(f"Test start time: {t0.strftime('%Y-%m-%d %H:%M:%S')}")
        for i, test_case in tqdm(enumerate(test_cases), desc=f"Model {model}", unit="test", total=config.batch_size, dynamic_ncols=True):
            logger.debug(f"Test {i+1}/{config.batch_size}")

            try:
                # Get ground truth
                ground_truth = [test_case.grid, engine.next_state(test_case.grid)]
                ground_truth.append(engine.next_state(ground_truth[-1]))

                examples = format_examples(EXAMPLE_PATTERNS, test_case.width, test_case.height, config) if "example" in config.prompt_style else ""

                # Query model
                prompt, system = format_prompt(test_case.grid, config, examples)
                response, stats = model_interface.query_model(model, prompt, system)

                # Parse and evaluate
                predicted = parse_response(
                    prompt,
                    response,
                    ground_truth[1],
                    live_cell_mark=config.live_dead_cell_markers[0],
                    dead_cell_mark=config.live_dead_cell_markers[1]
                )
                
                if predicted is not None:
                    logger.info(f"Query:\n{format_grid(ground_truth[0], config.live_dead_cell_markers[0], config.live_dead_cell_markers[1])}")
                    logger.info(f"Predicted:\n{format_grid(predicted, config.live_dead_cell_markers[0], config.live_dead_cell_markers[1])}")
                    logger.info(f"Ground Truth:\n{format_grid(ground_truth[1], config.live_dead_cell_markers[0], config.live_dead_cell_markers[1])}")
                    if config.verbose:
                        logger.info(f"System:\n---\n{system}\n---\nPrompt:\n---\n{prompt}\n---\nResponse:\n{response}\n---")

                result = evaluator.compare_grids(predicted, ground_truth[1])
                result['raw_response'] = response
                result['total_duration'] = stats['total_duration']
                result['load_duration'] = stats['load_duration']
                result['prompt_eval_count'] = stats['prompt_eval_count']
                result['prompt_eval_duration'] = stats['prompt_eval_duration']
                result['eval_count'] = stats['eval_count']
                result['eval_duration'] = stats['eval_duration']
                
                results.append(result)

            except Exception as e:
                logger.error(f"Error in test {i+1} for model {model}: {e}", exc_info=True)
                results.append({
                    "accuracy": 0.0,
                    "correct_cells": 0,
                    "total_cells": test_case.width * test_case.height,
                    "parse_error": True,
                    "cell_by_cell": [],
                    "raw_response": str(e),
                    "error_details": str(e)
                })
        t1 = datetime.now()
        duration = (t1 - t0).total_seconds()

        logger.info(f"Test end time: {t1.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Total duration for model {model}: {duration:.2f} seconds")
        logger.info(f"Avg Duration: {duration / config.batch_size:.2f} seconds per test")

        # Final evaluation for this model
        batch_eval = evaluator.evaluate_batch(results)
        model_results[model] = batch_eval

        logger.info(f"Results for {model}:")
        logger.info(f"Average Accuracy: {batch_eval['average_accuracy']:.2%}")
        logger.info(f"Normalized Accuracy: {batch_eval['normalized_accuracy']:.2%}")
        # logger.info(f"Std Accuracy: {batch_eval['std_accuracy']:.2%}")
        # logger.info(f"Median Accuracy: {batch_eval['median_accuracy']:.2%}")
        logger.info(f"Valid Tests: {batch_eval['valid_tests']}/{batch_eval['total_tests']}")
        logger.info(f"Parse Errors: {batch_eval['parse_errors']}")
        
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
            print(f"   Avg Duration: {duration / config.batch_size:.2f} seconds per test")

        # Log error patterns if any
        if batch_eval.get("most_common_errors"):
            logger.warning("Most common parse errors:")
            for error, count in batch_eval["most_common_errors"]:
                logger.warning(f"  - {error} ({count} times)")

    return model_results

def setup_argparser() -> argparse.ArgumentParser:
    """Set up command line argument parser with enhanced help"""
    parser = argparse.ArgumentParser(
        description="Game of Life Test Framework for LLM Reasoning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gol_eval.py --model qwen3:0.6b --difficulty easy --batch-size 5
  python gol_eval.py --model llama3.2:3b phi3:3.8b --difficulty hard --temperature 0.1
  python gol_eval.py --model qwen3:0.6b llama3.2:3b --batch-size 10 --seed 42 --verbose
        """
    )

    # Interface configuration
    parser.add_argument(
        '--model-interface', '-i', type=str, default='ollama',
        choices=['ollama', 'huggingface'],
        help='Model interface to use (default: ollama)'
    )

    # Model configuration
    parser.add_argument(
        '--model', '-m', type=str, nargs='+',
        default=['qwen3:0.6b'],
        help='Ollama models to test (default: qwen3:0.6b)'
    )

    # Test configuration
    parser.add_argument(
        '--difficulty', '-d', type=str, default='easy',
        choices=['easy', 'medium', 'hard', 'nightmare'],
        help='Test difficulty level (default: easy)'
    )

    parser.add_argument(
        '--batch-size', '-b', type=int, default=5,
        help='Number of tests to run (default: 5)'
    )
    
    parser.add_argument(
        '--iterations', '-it', type=int, default=1,
        help='Number of iterations to run each test (default: 1)'
    )
    
    parser.add_argument(
        '--known-patterns-ratio', type=float, default=0.3,
        help='Ratio of known patterns in test batch (default: 0.3)'
    )
    
    parser.add_argument(
        '--known-patterns-dir', type=str, default=None,
        help='Directory containing known pattern files (.rle, .cells) for targeted testing'
    )
    
    parser.add_argument(
        '--density', type=float, default=0.3,
        help='Density of live cells in random grids (0 to 1, default: 0.3)'
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
        choices=['linguistic', 'casual', 'minimal', 'examples_linguistic', 'examples', 'example_rules_math', 'rules_math'],
        help='Prompt style to use (default: linguistic)'
    )

    parser.add_argument(
        '--system-prompt-style', type=str, default='analytical',
        choices=['analytical', 'casual', 'adversarial'],
        help='System prompt style to use (default: analytical)'
    )

    parser.add_argument(
        '--examples-count', type=int, default=10,
        help='Examples count in prompt (default: 10)'
    )

    parser.add_argument(
        '--live-dead-cell-markers', type=str, default='1,0',
        help='Markers for live and dead cells, comma-separated (default: 1,0)'
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
    print(f"Difficulty: {config.difficulty.name} ({config.difficulty.value})")
    print(f"Batch Size: {config.batch_size}")
    print(f"Iterations per Test: {config.iterations}")
    print(f"Known Patterns Ratio: {config.known_patterns_ratio}")
    print(f"Density: {config.density}")
    print(f"Temperature: {config.temperature}")
    print(f"Prompt Style: {config.prompt_style}")
    print(f"Prompt Language: {config.prompt_language}")
    print(f"Live/Dead Cell Markers: {config.live_dead_cell_markers[0]}/{config.live_dead_cell_markers[1]}")
    print(f"{'='*80}")

    # Prepare table data
    table_data = []
    headers = [
        # "Model", "Avg Accuracy", "Mean Accuracy", "Median Accuracy", "Norm Accuracy",
        "Model", "Avg Accuracy", "Norm Accuracy",
        "Valid Tests", "Parse Errors", "Success Rate", "Perfect Scores", "Top Errors"
    ]

    for model, results in model_results.items():
        top_errors = ", ".join(
            f"{err[:20]} ({cnt})"
            for err, cnt in results.get("most_common_errors", [])[:2]
        ) if results.get("most_common_errors") else "None"

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
            top_errors
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

def save_results(model_results: Dict[str, Dict], config: TestConfig) -> None:
    """Save results to a log file with timestamp"""

    # Format file name with config details and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_names = "_".join(
        "".join(c if c.isalnum() or c in ('-', '_', '.') else '_' for c in model)
        for model in config.models
    )
    other_details = f"{config.difficulty.name}_bs{config.batch_size}_temp{config.temperature}"
    filename = f"{model_names}_{other_details}_{timestamp}.csv"
    filepath = Path(config.results_dir) / filename
    
    # Write results to CSV
    with open(filepath, 'w') as f:
        headers = [
            "Model",
            "Avg Accuracy",
            "Norm Accuracy",
            "Valid Tests",
            "Parse Errors",
            "Success Rate",
            "Perfect Scores",
            "Total Duration",
            "Avg Duration",
            "Top Errors"
        ]
        f.write(",".join(headers) + "\n")

        for model, results in model_results.items():
            top_errors = ", ".join(
                f"{err[:20]} ({cnt})"
                for err, cnt in results.get("most_common_errors", [])[:2]
            ) if results.get("most_common_errors") else "None"
            
            row = [
                model,
                f"{results['average_accuracy']:.4f}",
                f"{results['normalized_accuracy']:.4f}",
                f"{results['valid_tests']}/{results['total_tests']}",
                str(results['parse_errors']),
                f"{results['success_rate']:.4f}",
                str(results.get('perfect_scores', 0)),
                str(results.get('total_duration', 'N/A')),
                str(results.get('avg_duration', 'N/A')),
                top_errors,
            ]
            f.write(",".join(row) + "\n")

def main() -> None:
    """Main entry point with enhanced error handling"""
    try:
        parser = setup_argparser()
        args = parser.parse_args()

        # Create config with validation
        config = TestConfig(
            models=args.model,
            interface_type=args.model_interface,
            difficulty=DifficultyLevel.from_string(args.difficulty),
            batch_size=args.batch_size,
            density=args.density,
            known_patterns_ratio=args.known_patterns_ratio,
            known_patterns_dir=args.known_patterns_dir,
            iterations=args.iterations,
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
            live_dead_cell_markers=tuple(map(str.strip, args.live_dead_cell_markers.split(','))),
            prompt_language=args.prompt_language,
            results_dir=args.results_dir
        )

        # Run tests
        model_results = run_game_of_life_test(config)

        # Display results
        display_results(model_results, config)
        
        # Save results
        save_results(model_results, config)

    except KeyboardInterrupt:
        logger.error("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
