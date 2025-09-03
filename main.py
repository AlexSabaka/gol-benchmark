#!/usr/bin/env python3
"""
Game of Life Test Framework for LLM Reasoning
Tests whether models can systematically apply Conway's Game of Life rules
"""

import random
import json
import argparse
from typing import List, Tuple, Dict, Optional
import numpy as np
from dataclasses import dataclass
from enum import Enum
import ollama
import sys
from tabulate import tabulate

class DifficultyLevel(Enum):
    EASY = "3x3"
    MEDIUM = "5x5" 
    HARD = "8x8"
    NIGHTMARE = "10x10"
    
    @classmethod
    def from_string(cls, value: str):
        """Parse difficulty from string"""
        mapping = {
            "easy": cls.EASY,
            "medium": cls.MEDIUM,
            "hard": cls.HARD,
            "nightmare": cls.NIGHTMARE
        }
        return mapping.get(value.lower(), cls.EASY)

@dataclass
class TestConfig:
    """Configuration for the test run"""
    models: List[str]
    difficulty: DifficultyLevel
    batch_size: int
    temperature: float
    top_k: int
    min_k: int
    min_p: float
    verbose: bool
    seed: Optional[int] = None

@dataclass
class GameState:
    grid: List[List[int]]
    width: int
    height: int
    
    def __post_init__(self):
        self.width = len(self.grid[0]) if self.grid else 0
        self.height = len(self.grid)

class GameOfLifeEngine:
    """Core Game of Life logic - our ground truth"""
    
    @staticmethod
    def count_neighbors(grid: List[List[int]], row: int, col: int) -> int:
        """Count live neighbors for a cell"""
        count = 0
        height, width = len(grid), len(grid[0])
        
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:  # Skip the cell itself
                    continue
                    
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
                current_cell = grid[row][col]
                
                # Conway's Rules:
                # 1. Any live cell with 2-3 neighbors survives
                # 2. Any dead cell with exactly 3 neighbors becomes alive
                # 3. All other live cells die, all other dead cells stay dead
                
                if current_cell == 1:  # Live cell
                    new_grid[row][col] = 1 if neighbors in [2, 3] else 0
                else:  # Dead cell
                    new_grid[row][col] = 1 if neighbors == 3 else 0
        
        return new_grid

class TestGenerator:
    """Generates diverse Game of Life test cases"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
    
    @staticmethod
    def generate_random_grid(width: int, height: int, density: float = 0.3) -> List[List[int]]:
        """Generate random initial state with given density"""
        return [[1 if random.random() < density else 0 for _ in range(width)] 
                for _ in range(height)]
    
    @staticmethod
    def generate_known_patterns(pattern_type: str = "blinker") -> List[List[int]]:
        """Generate known patterns for targeted testing"""
        patterns = {
            "blinker": [[0,1,0],[0,1,0],[0,1,0]],
            "block": [[1,1],[1,1]],
            "glider": [[0,1,0],[0,0,1],[1,1,1]],
            "empty": [[0,0,0],[0,0,0],[0,0,0]],
            "toad": [[0,1,1,1],[1,1,1,0]],
            "beacon": [[1,1,0,0],[1,1,0,0],[0,0,1,1],[0,0,1,1]]
        }
        return patterns.get(pattern_type, patterns["blinker"])
    
    def create_test_batch(self, difficulty: DifficultyLevel, batch_size: int = 10) -> List[GameState]:
        """Create a batch of test cases"""
        size_map = {
            DifficultyLevel.EASY: (3, 3),
            DifficultyLevel.MEDIUM: (5, 5), 
            DifficultyLevel.HARD: (8, 8),
            DifficultyLevel.NIGHTMARE: (10, 10)
        }
        
        width, height = size_map[difficulty]
        tests = []
        
        # Mix of random and known patterns
        pattern_names = ["blinker", "block", "glider", "empty", "toad", "beacon"]
        
        for i in range(batch_size):
            if i < batch_size // 3:  # 1/3 known patterns
                pattern_name = random.choice(pattern_names)
                base_grid = self.generate_known_patterns(pattern_name)
                
                # Resize/pad pattern to fit target size
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
            
            tests.append(GameState(grid, width, height))
        
        return tests

class OllamaInterface:
    """Interface for communicating with Ollama using the official package"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.client = ollama.Client()
        
        # Check if model exists
        try:
            self.client.list()  # This will fail if ollama isn't running
        except Exception as e:
            print(f"❌ Error connecting to Ollama: {e}")
            print("Make sure Ollama is running: ollama serve")
            sys.exit(1)
    
    def format_prompt(self, grid: List[List[int]], prompt_style: str = "systematic") -> str:
        """Format grid into a clear prompt with different styles"""
        grid_str = "\n".join([" ".join(map(str, row)) for row in grid])
        
        if prompt_style == "systematic":
            prompt = f"""You are applying Conway's Game of Life rules. Here are the EXACT rules:

1. Any live cell (1) with 2 or 3 live neighbors survives to the next generation
2. Any dead cell (0) with exactly 3 live neighbors becomes alive  
3. All other live cells die (become 0)
4. All other dead cells stay dead (remain 0)

For each cell, count its 8 adjacent neighbors (including diagonally adjacent).

Current state:
{grid_str}

Apply the rules systematically to EVERY cell and give me the next state.
Respond with ONLY the grid numbers, one row per line, numbers separated by spaces.

Next state:"""
        
        elif prompt_style == "casual":
            prompt = f"""Here's a Game of Life grid. You know the rules - live cells need 2-3 neighbors to survive, dead cells need exactly 3 to come alive.

Current:
{grid_str}

What's next?"""
        
        else:  # minimal
            prompt = f"""Game of Life next state:
{grid_str}

Next:"""
        
        return prompt
    
    def query_model(self, model: str, prompt: str) -> str:
        """Send prompt to Ollama and get response"""
        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                options={
                    'temperature': self.config.temperature,
                    'top_k': self.config.top_k,
                    'min_k': self.config.min_k,
                    'min_p': self.config.min_p,
                    'num_predict': 100,  # Limit response length
                }
            )
            return response['response']
        except Exception as e:
            print(f"❌ Error querying model {model}: {e}")
            return ""
    
    def parse_response(self, response: str, expected_shape: Tuple[int, int]) -> Optional[List[List[int]]]:
        """Parse model response back into grid format with better error handling"""
        try:
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            
            # Find lines that look like grid rows - be more flexible
            grid_lines = []
            for line in lines:
                # Clean up the line - remove extra chars
                clean_line = ''.join(c if c in '01 \t' else ' ' for c in line)
                numbers = clean_line.split()
                
                # Check if this line has the right number of 0s and 1s
                if len(numbers) == expected_shape[1] and all(n in ['0', '1'] for n in numbers):
                    grid_lines.append(numbers)
            
            # Take the first valid grid we find
            if len(grid_lines) >= expected_shape[0]:
                grid = []
                for i in range(expected_shape[0]):
                    row = [int(x) for x in grid_lines[i]]
                    grid.append(row)
                return grid
            
            return None
            
        except Exception as e:
            if self.config.verbose:
                print(f"❌ Parse error: {e}")
                print(f"Response was: '{response}'")
            return None

class TestEvaluator:
    """Evaluates model performance on Game of Life tests"""
    
    @staticmethod
    def compare_grids(predicted: Optional[List[List[int]]], actual: List[List[int]]) -> Dict:
        """Compare predicted vs actual grid"""
        if predicted is None or len(predicted) != len(actual):
            return {
                "accuracy": 0.0,
                "correct_cells": 0,
                "total_cells": len(actual) * len(actual[0]),
                "parse_error": True,
                "cell_by_cell": []
            }
        
        total_cells = len(actual) * len(actual[0])
        correct_cells = 0
        cell_by_cell = []
        
        for i in range(len(actual)):
            for j in range(len(actual[0])):
                if i < len(predicted) and j < len(predicted[i]):
                    is_correct = predicted[i][j] == actual[i][j]
                    if is_correct:
                        correct_cells += 1
                    cell_by_cell.append({
                        'pos': (i, j),
                        'predicted': predicted[i][j],
                        'actual': actual[i][j],
                        'correct': is_correct
                    })
        
        return {
            "accuracy": correct_cells / total_cells,
            "correct_cells": correct_cells,
            "total_cells": total_cells,
            "parse_error": False,
            "cell_by_cell": cell_by_cell
        }
    
    @staticmethod
    def evaluate_batch(results: List[Dict]) -> Dict:
        """Evaluate a batch of test results"""
        if not results:
            return {"error": "No results to evaluate"}
        
        valid_results = [r for r in results if not r.get("parse_error", False)]
        parse_errors = [r for r in results if r.get("parse_error", False)]
        
        if not valid_results:
            return {
                "average_accuracy": 0.0,
                "valid_tests": 0,
                "parse_errors": len(parse_errors),
                "total_tests": len(results),
                "success_rate": 0.0,
                "accuracy_distribution": []
            }
        
        accuracies = [r["accuracy"] for r in valid_results]
        
        return {
            "average_accuracy": sum(accuracies) / len(accuracies),
            "median_accuracy": sorted(accuracies)[len(accuracies) // 2],
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
            "valid_tests": len(valid_results),
            "parse_errors": len(parse_errors),
            "total_tests": len(results),
            "success_rate": len(valid_results) / len(results),
            "accuracy_distribution": accuracies,
            "perfect_scores": len([a for a in accuracies if a == 1.0])
        }

def run_game_of_life_test(config: TestConfig):
    """Main function to run the Game of Life test"""
    
    print(f"🎮 Game of Life LLM Reasoning Test")
    print(f"{'='*50}")
    print(f"Models: {', '.join(config.models)}")
    print(f"Difficulty: {config.difficulty.value}")
    print(f"Batch size: {config.batch_size}")
    print(f"Temperature: {config.temperature}")
    print(f"Top-k: {config.top_k}, Min-k: {config.min_k}, Min-p: {config.min_p}")
    if config.seed:
        print(f"Seed: {config.seed}")
    print(f"{'='*50}")
    
    # Initialize components
    generator = TestGenerator(config.seed)
    ollama_interface = OllamaInterface(config)
    evaluator = TestEvaluator()
    engine = GameOfLifeEngine()
    
    # Generate test cases (same for all models)
    test_cases = generator.create_test_batch(config.difficulty, config.batch_size)
    
    # Store results for each model
    model_results = {}
    
    # Run tests for each model
    for model in config.models:
        print(f"\n🚀 Testing model: {model}")
        results = []
        
        for i, test_case in enumerate(test_cases):
            if config.verbose:
                print(f"\n🧪 Test {i+1}/{config.batch_size}")
                print("Current state:")
                for row in test_case.grid:
                    print(" ".join(map(str, row)))
            
            # Get ground truth
            ground_truth = engine.next_state(test_case.grid)
            
            if config.verbose:
                print("Expected next state:")
                for row in ground_truth:
                    print(" ".join(map(str, row)))
            
            # Query model with systematic prompting
            prompt = ollama_interface.format_prompt(test_case.grid, "systematic")
            response = ollama_interface.query_model(model, prompt)
            
            if config.verbose:
                print(f"Model response: {response}")
            
            # Parse and evaluate
            predicted = ollama_interface.parse_response(response, (test_case.height, test_case.width))
            result = evaluator.compare_grids(predicted, ground_truth)
            
            if config.verbose:
                if predicted:
                    print("Model predicted:")
                    for row in predicted:
                        print(" ".join(map(str, row)))
                    print(f"✅ Accuracy: {result['accuracy']:.2%}")
                else:
                    print("❌ Failed to parse model response")
            
            results.append(result)
        
        # Final evaluation for this model
        batch_eval = evaluator.evaluate_batch(results)
        model_results[model] = batch_eval
        
        print(f"\n📊 Results for {model}:")
        print(f"   Average Accuracy: {batch_eval['average_accuracy']:.2%}")
        print(f"   Valid Tests: {batch_eval['valid_tests']}/{batch_eval['total_tests']}")
        print(f"   Parse Errors: {batch_eval['parse_errors']}")
    
    # Display comparison table
    print(f"\n{'='*80}")
    print("🏆 MODEL COMPARISON TABLE")
    print(f"{'='*80}")
    
    # Prepare table data
    table_data = []
    headers = ["Model", "Avg Accuracy", "Valid Tests", "Parse Errors", "Success Rate", "Perfect Scores"]
    
    for model, results in model_results.items():
        row = [
            model,
            f"{results['average_accuracy']:.2%}",
            f"{results['valid_tests']}/{results['total_tests']}",
            results['parse_errors'],
            f"{results['success_rate']:.2%}",
            results.get('perfect_scores', 0)
        ]
        table_data.append(row)
    
    # Sort by average accuracy (descending)
    table_data.sort(key=lambda x: float(x[1].rstrip('%')), reverse=True)
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Detailed analysis
    print(f"\n{'='*80}")
    print("🧠 DETAILED ANALYSIS")
    print(f"{'='*80}")
    
    best_model = max(model_results.items(), key=lambda x: x[1]['average_accuracy'])
    print(f"🥇 Best Performing Model: {best_model[0]} ({best_model[1]['average_accuracy']:.2%})")
    
    if best_model[1]['average_accuracy'] > 0.8:
        print("   Analysis: Strong systematic reasoning detected!")
    elif best_model[1]['average_accuracy'] > 0.5:
        print("   Analysis: Partial reasoning - might be pattern matching")
    else:
        print("   Analysis: Likely pattern matching or random guessing")
    
    return model_results

def setup_argparser():
    """Set up command line argument parser"""
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
    
    # Model configuration (now accepts multiple models)
    parser.add_argument('--model', '-m', type=str, nargs='+', default=['qwen3:0.6b'],
                       help='Ollama models to test (default: qwen3:0.6b)')
    
    # Test configuration
    parser.add_argument('--difficulty', '-d', type=str, default='easy',
                       choices=['easy', 'medium', 'hard', 'nightmare'],
                       help='Test difficulty level (default: easy)')
    
    parser.add_argument('--batch-size', '-b', type=int, default=5,
                       help='Number of tests to run (default: 5)')
    
    parser.add_argument('--seed', '-s', type=int,
                       help='Random seed for reproducible tests')
    
    # Sampling parameters
    parser.add_argument('--temperature', '-t', type=float, default=0.1,
                       help='Temperature for sampling (default: 0.1)')
    
    parser.add_argument('--top-k', type=int, default=40,
                       help='Top-k for sampling (default: 40)')
    
    parser.add_argument('--min-k', type=int, default=1,
                       help='Min-k for sampling (default: 1)')
    
    parser.add_argument('--min-p', type=float, default=0.05,
                       help='Min-p for sampling (default: 0.05)')
    
    # Output configuration
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output showing each test')
    
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output, just final results')
    
    return parser

def main():
    """Main entry point"""
    parser = setup_argparser()
    args = parser.parse_args()
    
    # Create config
    config = TestConfig(
        models=args.model,
        difficulty=DifficultyLevel.from_string(args.difficulty),
        batch_size=args.batch_size,
        temperature=args.temperature,
        top_k=args.top_k,
        min_k=args.min_k,
        min_p=args.min_p,
        verbose=args.verbose and not args.quiet,
        seed=args.seed
    )
    
    try:
        model_results = run_game_of_life_test(config)
        
        # Exit with non-zero if all models failed completely
        all_failed = all(results.get('success_rate', 0) == 0 
                        for results in model_results.values())
        if all_failed:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()