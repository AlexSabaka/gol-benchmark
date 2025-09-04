#!/usr/bin/env python3
"""
Game of Life Test Framework for LLM Reasoning
Tests whether models can systematically apply Conway's Game of Life rules
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from tabulate import tabulate
from typing import List, Tuple, Dict, Optional, Literal, TypedDict
from tqdm import tqdm

import argparse
import json
import logging
import numpy as np
import ollama
import random
import sys

from src.PROMPT_STYLES import get_prompt_style

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_of_life_eval.log'),
        # logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DifficultyLevel(Enum):
    """Game difficulty levels with associated grid sizes"""
    EASY = (3, 3)
    MEDIUM = (5, 5)
    HARD = (8, 8)
    NIGHTMARE = (10, 10)

    @classmethod
    def from_string(cls, value: str) -> 'DifficultyLevel':
        """Parse difficulty from string with error handling"""
        mapping = {
            "easy": cls.EASY,
            "medium": cls.MEDIUM,
            "hard": cls.HARD,
            "nightmare": cls.NIGHTMARE
        }
        try:
            return mapping[value.lower()]
        except KeyError:
            logger.warning(f"Unknown difficulty '{value}', defaulting to EASY")
            return cls.EASY

class ParseError(Exception):
    """Custom exception for response parsing failures"""
    def __init__(self, message: str, response: str):
        self.response = response
        super().__init__(message)

class TestResult(TypedDict):
    """Type definition for test results"""
    accuracy: float
    correct_cells: int
    total_cells: int
    parse_error: bool
    cell_by_cell: List[Dict]
    raw_response: str
    error_details: Optional[str]

@dataclass
class TestConfig:
    """Configuration for the test run with validation"""
    models: List[str]
    difficulty: DifficultyLevel
    batch_size: int = 10
    temperature: float = 0.1
    no_think: Optional[bool] = None
    ctx_len: int = 2048
    num_predict: int = 1024
    top_k: int = 40
    min_k: int = 1
    min_p: float = 0.05
    verbose: bool = False
    seed: Optional[int] = None
    prompt_style: Literal["systematic", "casual", "minimal"] = "systematic"
    prompt_language: Literal["en", "fr", "es", "de", "zh", "ua"] = "en"
    log_dir: str = "logs"

    def __post_init__(self):
        """Validate configuration values"""
        if self.batch_size < 1:
            raise ValueError("Batch size must be at least 1")
        if not (0 <= self.temperature <= 2):
            raise ValueError("Temperature must be between 0 and 2")
        if self.top_k < 1:
            raise ValueError("Top-k must be at least 1")

        # Create log directory if it doesn't exist
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

@dataclass
class GameState:
    """Represents a Game of Life grid state with validation"""
    grid: List[List[int]]
    width: int = field(init=False)
    height: int = field(init=False)

    def __post_init__(self):
        """Validate and set dimensions"""
        if not self.grid or not all(self.grid):
            raise ValueError("Grid cannot be empty")

        self.height = len(self.grid)
        self.width = len(self.grid[0]) if self.height > 0 else 0

        # Validate all rows have same width
        if any(len(row) != self.width for row in self.grid):
            raise ValueError("All grid rows must have the same width")

        # Validate cell values
        if any(cell not in (0, 1) for row in self.grid for cell in row):
            raise ValueError("Grid cells must be 0 or 1")

class GameOfLifeEngine:
    """Core Game of Life logic with optimized neighbor counting"""

    @staticmethod
    def count_neighbors(grid: List[List[int]], row: int, col: int) -> int:
        """Count live neighbors for a cell with bounds checking"""
        count = 0
        height, width = len(grid), len(grid[0])
        directions = [(-1,-1), (-1,0), (-1,1),
                      (0,-1),          (0,1),
                      (1,-1),  (1,0), (1,1)]

        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            if 0 <= nr < height and 0 <= nc < width:
                count += grid[nr][nc]

        return count

    @staticmethod
    def next_state(grid: List[List[int]]) -> List[List[int]]:
        """Apply Game of Life rules to get next state"""
        height, width = len(grid), len(grid[0])
        new_grid = [[0 for _ in range(width)] for _ in range(height)]

        for row in range(height):
            for col in range(width):
                neighbors = GameOfLifeEngine.count_neighbors(grid, row, col)
                current = grid[row][col]

                # Conway's Rules implementation
                if current:
                    new_grid[row][col] = 1 if neighbors in (2, 3) else 0
                else:
                    new_grid[row][col] = 1 if neighbors == 3 else 0

        return new_grid

class TestGenerator:
    """Generates diverse Game of Life test cases with better pattern handling"""

    KNOWN_PATTERNS = {
        "blinker": [[0,1,0],[0,1,0],[0,1,0]],
        "block": [[1,1],[1,1]],
        "glider": [[0,1,0],[0,0,1],[1,1,1]],
        "empty": [[0,0,0],[0,0,0],[0,0,0]],
        "toad": [[0,1,1,1],[1,1,1,0]],
        "beacon": [[1,1,0,0],[1,1,0,0],[0,0,1,1],[0,0,1,1]]
    }

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    @staticmethod
    def generate_random_grid(width: int, height: int, density: float = 0.3) -> List[List[int]]:
        """Generate random initial state with given density"""
        if not (0 <= density <= 1):
            raise ValueError("Density must be between 0 and 1")

        return [[1 if random.random() < density else 0
                for _ in range(width)]
                for _ in range(height)]

    @staticmethod
    def generate_known_patterns(pattern_type: str) -> List[List[int]]:
        """Generate known patterns for targeted testing"""
        try:
            return TestGenerator.KNOWN_PATTERNS[pattern_type]
        except KeyError:
            logger.warning(f"Unknown pattern '{pattern_type}', defaulting to blinker")
            return TestGenerator.KNOWN_PATTERNS["blinker"]

    def create_test_batch(self, difficulty: DifficultyLevel, batch_size: int = 10) -> List[GameState]:
        """Create a batch of test cases with better pattern distribution"""
        width, height = difficulty.value
        tests = []
        pattern_names = list(TestGenerator.KNOWN_PATTERNS.keys())

        for i in range(batch_size):
            if i < batch_size // 3:  # 1/3 known patterns
                pattern_name = random.choice(pattern_names)
                base_grid = self.generate_known_patterns(pattern_name)

                # Create properly sized grid
                grid = [[0 for _ in range(width)] for _ in range(height)]

                # Center the pattern
                start_row = max(0, (height - len(base_grid)) // 2)
                start_col = max(0, (width - len(base_grid[0])) // 2)

                for r in range(min(len(base_grid), height - start_row)):
                    for c in range(min(len(base_grid[0]), width - start_col)):
                        grid[start_row + r][start_col + c] = base_grid[r][c]

            else:  # 2/3 random
                density = random.uniform(0.2, 0.5)
                grid = self.generate_random_grid(width, height, density)

            tests.append(GameState(grid))

        return tests

class OllamaInterface:
    """Enhanced interface for communicating with Ollama with better error handling"""

    def __init__(self, config: TestConfig):
        self.config = config
        self.client = ollama.Client()

        # Test connection
        try:
            self.client.list()
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise RuntimeError("Ollama server not running. Start with 'ollama serve'") from e

    def format_prompt(self, grid: List[List[int]], prompt_style: str = "systematic", prompt_language: str = "en") -> str:
        """Format grid into a clear prompt with validation"""
        
        grid_str = "\n".join([" ".join(map(str, row)) for row in grid])
        return get_prompt_style(prompt_language, prompt_style).format(grid_str=grid_str)

    def query_model(self, model: str, prompt: str) -> str:
        """Send prompt to Ollama with comprehensive error handling"""
        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                # think=not self.config.no_think if self.config.no_think is not None else None,
                options={
                    'temperature': self.config.temperature,
                    'top_k': self.config.top_k,
                    'min_k': self.config.min_k,
                    'min_p': self.config.min_p,
                    'num_ctx': self.config.ctx_len,
                    'num_predict': self.config.num_predict,
                }
            )
            return response['response'].strip()

        except ollama.ResponseError as e:
            error_msg = f"Ollama API error for model {model}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error querying model {model}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def parse_response(self, response: str, expected_shape: Tuple[int, int]) -> Optional[List[List[int]]]:
        """
        Robust response parsing with multiple fallback strategies.
        Returns parsed grid or None if parsing fails.
        """
        if not response:
            logger.warning("Empty response from model")
            return None

        try:
            # Strategy 1: Look for grid-like patterns in the response
            lines = [line.strip() for line in response.split('\n') if line.strip()]

            # Try to find the most grid-like section
            grid_candidates = []
            current_candidate = []

            for line in lines:
                # Clean line - keep only digits and spaces
                clean_line = ''.join(c for c in line if c in '01 \t')
                if not clean_line:
                    continue

                # Split into potential numbers
                parts = clean_line.split()
                if not parts:
                    continue

                # Check if this looks like a grid row
                if all(p in ('0', '1') for p in parts):
                    if len(parts) == expected_shape[1]:
                        current_candidate.append(parts)
                    else:
                        # If we were building a candidate but this line doesn't match,
                        # save the candidate if it's not empty
                        if current_candidate:
                            grid_candidates.append(current_candidate)
                            current_candidate = []
                else:
                    if current_candidate:
                        grid_candidates.append(current_candidate)
                        current_candidate = []

            # Add the last candidate if it exists
            if current_candidate:
                grid_candidates.append(current_candidate)

            # Find the best candidate (closest to expected shape)
            best_candidate = None
            best_score = -1

            for candidate in grid_candidates:
                if len(candidate) != expected_shape[0]:
                    continue

                # Check if all rows have correct length
                if all(len(row) == expected_shape[1] for row in candidate):
                    return [[int(cell) for cell in row] for row in candidate]

                # If not perfect, score by how close it is
                score = sum(1 for row in candidate if len(row) == expected_shape[1])
                if score > best_score:
                    best_score = score
                    best_candidate = candidate

            # If we found a partial match, try to use it
            if best_candidate and best_score >= expected_shape[0] * 0.7:  # At least 70% match
                # Pad or truncate rows to match expected width
                grid = []
                for row in best_candidate:
                    if len(row) > expected_shape[1]:
                        new_row = row[:expected_shape[1]]
                    else:
                        new_row = row + ['0'] * (expected_shape[1] - len(row))
                    grid.append([int(cell) for cell in new_row])
                return grid

            # Strategy 2: Look for JSON-like structures
            try:
                # Try to parse as JSON if it looks like JSON
                if ('{' in response and '}' in response) or ('[' in response and ']' in response):
                    data = json.loads(response)
                    if isinstance(data, list) and len(data) == expected_shape[0]:
                        grid = []
                        for row in data:
                            if isinstance(row, list) and len(row) == expected_shape[1]:
                                grid.append([int(cell) for cell in row])
                            else:
                                break
                        else:
                            if len(grid) == expected_shape[0]:
                                return grid
            except json.JSONDecodeError:
                pass

            # Strategy 3: Try to extract numbers from anywhere in the response
            all_numbers = []
            for c in response:
                if c in '01':
                    all_numbers.append(int(c))

            if len(all_numbers) >= expected_shape[0] * expected_shape[1]:
                try:
                    grid = []
                    for i in range(expected_shape[0]):
                        start = i * expected_shape[1]
                        end = start + expected_shape[1]
                        grid.append(all_numbers[start:end])
                    return grid
                except IndexError:
                    pass

            # If we get here, parsing failed
            logger.warning(
                f"Failed to parse response for {expected_shape} grid. Response: {response[:200]}..."
            )
            return None

        except Exception as e:
            logger.error(f"Parse error for response: {response[:200]}...", exc_info=True)
            return None

class TestEvaluator:
    """Evaluates model performance"""

    @staticmethod
    def compare_grids(predicted: Optional[List[List[int]]], actual: List[List[int]]) -> TestResult:
        """Compare predicted vs actual grid with detailed error tracking"""
        result: TestResult = {
            "accuracy": 0.0,
            "correct_cells": 0,
            "total_cells": len(actual) * len(actual[0]),
            "parse_error": predicted is None,
            "cell_by_cell": [],
            "raw_response": "",
            "error_details": None
        }

        if predicted is None:
            result["error_details"] = "Failed to parse model response"
            return result

        if len(predicted) != len(actual):
            result["error_details"] = f"Grid height mismatch: expected {len(actual)}, got {len(predicted)}"
            result["parse_error"] = True
            return result

        if any(len(p_row) != len(a_row) for p_row, a_row in zip(predicted, actual)):
            result["error_details"] = "Grid width mismatch between rows"
            result["parse_error"] = True
            return result

        total_cells = len(actual) * len(actual[0])
        correct_cells = 0

        for i in range(len(actual)):
            for j in range(len(actual[0])):
                predicted_val = predicted[i][j]
                actual_val = actual[i][j]
                is_correct = predicted_val == actual_val

                if is_correct:
                    correct_cells += 1

                result["cell_by_cell"].append({
                    'pos': (i, j),
                    'predicted': predicted_val,
                    'actual': actual_val,
                    'correct': is_correct
                })

        result.update({
            "accuracy": correct_cells / total_cells,
            "correct_cells": correct_cells,
            "total_cells": total_cells,
            "parse_error": False
        })

        return result

    @staticmethod
    def evaluate_batch(results: List[TestResult]) -> Dict:
        """Evaluate a batch of test results with enhanced metrics"""
        if not results:
            return {"error": "No results to evaluate"}

        valid_results = [r for r in results if not r.get("parse_error", False)]
        parse_errors = [r for r in results if r.get("parse_error", False)]

        if not valid_results:
            error_details = "\n".join(
                f"Test {i}: {r.get('error_details', 'Unknown error')}"
                for i, r in enumerate(parse_errors)
            )
            logger.error(f"All tests failed to parse:\n{error_details}")
            return {
                "average_accuracy": 0.0,
                "normalized_accuracy": 0.0,
                "valid_tests": 0,
                "parse_errors": len(parse_errors),
                "total_tests": len(results),
                "success_rate": 0.0,
                "error_details": error_details
            }

        accuracies = [r["accuracy"] for r in valid_results]
        total_accuracy = sum(accuracies)
        normalized_accuracy = total_accuracy / len(results)

        # Calculate error patterns
        error_patterns = {}
        for r in parse_errors:
            error = r.get("error_details", "Unknown error")
            error_patterns[error] = error_patterns.get(error, 0) + 1

        return {
            "average_accuracy": sum(accuracies) / len(accuracies),
            # "std_accuracy": np.nanstd(accuracies) if len(accuracies) > 1 else 0.0,
            # "median_accuracy": np.nanmedian(accuracies) if len(accuracies) > 0 else 0.0,
            "normalized_accuracy": normalized_accuracy,
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
            "valid_tests": len(valid_results),
            "parse_errors": len(parse_errors),
            "total_tests": len(results),
            "success_rate": len(valid_results) / len(results),
            "accuracy_distribution": accuracies,
            "perfect_scores": len([a for a in accuracies if a == 1.0]),
            "error_patterns": error_patterns,
            "most_common_errors": sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:3]
        }

def run_game_of_life_test(config: TestConfig) -> Dict[str, Dict]:
    """Main function to run the Game of Life test with enhanced logging"""
    logger.info(f"Starting Game of Life LLM Reasoning Test")
    logger.info(f"Models: {', '.join(config.models)}")
    logger.info(f"Difficulty: {config.difficulty.name} ({config.difficulty.value})")
    logger.info(f"Batch size: {config.batch_size}")

    # Initialize components
    generator = TestGenerator(config.seed)
    ollama_interface = OllamaInterface(config)
    evaluator = TestEvaluator()
    engine = GameOfLifeEngine()

    # Generate test cases
    test_cases = generator.create_test_batch(config.difficulty, config.batch_size)

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
                ground_truth = engine.next_state(test_case.grid)

                # Query model
                prompt = ollama_interface.format_prompt(
                    test_case.grid,
                    config.prompt_style
                )
                response = ollama_interface.query_model(model, prompt)

                # Parse and evaluate
                predicted = ollama_interface.parse_response(
                    response,
                    (test_case.height, test_case.width)
                )

                result = evaluator.compare_grids(predicted, ground_truth)
                result["raw_response"] = response  # Store raw response for debugging

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
  python game_of_life_test.py --model qwen3:0.6b --difficulty easy --batch-size 5
  python game_of_life_test.py --model llama3.2:3b phi3:3.8b --difficulty hard --temperature 0.1
  python game_of_life_test.py --model qwen3:0.6b llama3.2:3b --batch-size 10 --seed 42 --verbose
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
        '--difficulty', '-d', type=str, default='easy',
        choices=['easy', 'medium', 'hard', 'nightmare'],
        help='Test difficulty level (default: easy)'
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
        '--prompt-style', type=str, default='systematic',
        choices=['systematic', 'casual', 'minimal'],
        help='Prompt style to use (default: systematic)'
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
        '--log-dir', type=str, default='logs',
        help='Directory to store log files (default: logs)'
    )

    return parser

def display_results(model_results: Dict[str, Dict], config: TestConfig) -> None:
    """Display results in a user-friendly format"""

    print(f"\n{'='*80}")
    print("🏆 MODEL COMPARISON TABLE")
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

    # Detailed analysis
    print(f"\n{'='*80}")
    print("🧠 DETAILED ANALYSIS")
    print(f"{'='*80}")

    # Find best model by normalized accuracy
    best_model = max(
        model_results.items(),
        key=lambda x: x[1]['normalized_accuracy']
    )

    print(f"🥇 Best Performing Model: {best_model[0]} ({best_model[1]['normalized_accuracy']:.2%})")

    accuracy = best_model[1]['normalized_accuracy']
    if accuracy > 0.8:
        print("   Analysis: Strong systematic reasoning detected!")
    elif accuracy > 0.5:
        print("   Analysis: Partial reasoning - might be pattern matching")
    else:
        print("   Analysis: Likely pattern matching or random guessing")

    # Show error patterns if any model had parse errors
    has_parse_errors = any(
        results['parse_errors'] > 0
        for results in model_results.values()
    )

    if has_parse_errors:
        print(f"\n{'='*80}")
        print("🔍 PARSE ERROR ANALYSIS")
        print(f"{'='*80}")

        for model, results in model_results.items():
            if results.get('parse_errors', 0) > 0:
                print(f"\nModel: {model}")
                print(f"Parse errors: {results['parse_errors']}/{results['total_tests']}")
                print("Common error patterns:")
                for error, count in results.get("most_common_errors", []):
                    print(f"  - {error} ({count} times)")

def main() -> None:
    """Main entry point with enhanced error handling"""
    try:
        parser = setup_argparser()
        args = parser.parse_args()

        # Create config with validation
        config = TestConfig(
            models=args.model,
            difficulty=DifficultyLevel.from_string(args.difficulty),
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
            prompt_language=args.prompt_language,
            log_dir=args.log_dir
        )

        # Run tests
        model_results = run_game_of_life_test(config)

        # Display results
        display_results(model_results, config)

        # Exit with non-zero if all models failed completely
        all_failed = all(
            results.get('success_rate', 0) == 0
            for results in model_results.values()
        )

        if all_failed:
            logger.error("All models failed completely")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.error("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
