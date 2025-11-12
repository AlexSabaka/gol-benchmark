#!/usr/bin/env python3
"""
Game of Life Matrix Testing Framework
Runs parameter matrix tests for LLM reasoning evaluation
"""

import itertools
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from tabulate import tabulate
import argparse

from gol_eval import format_examples, format_grid, format_prompt, parse_response
import numpy as np

from src.PROMPT_STYLES import get_prompt_style
from src.utils.logger import logger
from src.types import DifficultyLevel, ParseError, TestConfig
from src.GameOfLifeEngine import GameOfLifeEngine
from src.BaseModelInterface import BaseModelInterface, create_interface
from src.TestEvaluator import TestEvaluator
from src.TestGenerator import TestGenerator, EXAMPLE_PATTERNS

@dataclass
class MatrixConfig:
    """Configuration for matrix testing"""
    # Base configuration (fixed across all tests)
    models: List[str]
    interface_type: str = 'ollama'
    batch_size: int = 10
    iterations: int = 1
    known_patterns_ratio: float = 1.0
    density: float = 0.3
    seed: Optional[int] = 42
    verbose: bool = False
    results_dir: str = 'matrix_results'
    
    # Parameter matrices (will be varied)
    live_dead_cell_markers: List[Tuple[str, str]] = None
    difficulties: List[str] = None
    temperatures: List[float] = None
    num_predicts: List[int] = None
    ctx_lens: List[int] = None
    prompt_languages: List[str] = None
    prompt_styles: List[str] = None
    no_think_options: List[bool] = None
    
    # Additional sampling parameters (usually fixed)
    top_k: int = 40
    min_k: int = 1
    min_p: float = 0.05

class MatrixTester:
    """Handles matrix testing execution and results management"""
    
    def __init__(self, config: MatrixConfig):
        self.config = config
        self.results = []
        self.start_time = None
        self.results_file = None
        
    def generate_test_combinations(self) -> List[Dict[str, Any]]:
        """Generate all parameter combinations for testing"""
        combinations = list(itertools.product(
            self.config.live_dead_cell_markers,
            self.config.difficulties,
            self.config.temperatures,
            self.config.num_predicts,
            self.config.ctx_lens,
            self.config.prompt_languages,
            self.config.prompt_styles,
            self.config.no_think_options
        ))
        
        test_configs = []
        for combo in combinations:
            (markers, difficulty, temp, num_pred, ctx_len, 
             prompt_lang, prompt_style, no_think) = combo
            
            test_config = {
                'live_dead_cell_markers': markers,
                'difficulty': difficulty,
                'temperature': temp,
                'num_predict': num_pred,
                'ctx_len': ctx_len,
                'prompt_language': prompt_lang,
                'prompt_style': prompt_style,
                'no_think': no_think
            }
            test_configs.append(test_config)
        
        return test_configs
    
    def create_test_config(self, params: Dict[str, Any]) -> TestConfig:
        """Create a TestConfig object from parameter dictionary"""
        return TestConfig(
            models=self.config.models,
            interface_type=self.config.interface_type,
            difficulty=DifficultyLevel.from_string(params['difficulty']),
            batch_size=self.config.batch_size,
            density=self.config.density,
            known_patterns_ratio=self.config.known_patterns_ratio,
            iterations=self.config.iterations,
            temperature=params['temperature'],
            no_think=params['no_think'],
            ctx_len=params['ctx_len'],
            num_predict=params['num_predict'],
            top_k=self.config.top_k,
            min_k=self.config.min_k,
            min_p=self.config.min_p,
            verbose=self.config.verbose,
            seed=self.config.seed,
            prompt_style=params['prompt_style'],
            live_dead_cell_markers=params['live_dead_cell_markers'],
            prompt_language=params['prompt_language'],
            results_dir=self.config.results_dir
        )
    
    def run_matrix_test(self) -> List[Dict[str, Any]]:
        """Execute the complete matrix test"""
        self.start_time = datetime.now()
        test_combinations = self.generate_test_combinations()
        
        print(f"🚀 Starting Matrix Test Run")
        print(f"📊 Total combinations: {len(test_combinations)}")
        print(f"🤖 Models: {', '.join(self.config.models)}")
        print(f"⏰ Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Results directory: {self.config.results_dir}")
        print("=" * 80)
        
        # Setup results file
        self.setup_results_file()
        
        all_tests = []
        test_id = 1
        for params in test_combinations:
            test_config = self.create_test_config(params)
            # Generate test cases for this config
            generator = TestGenerator(test_config)
            test_cases = generator.create_test_batch(
                test_config.difficulty,
                test_config.batch_size,
                test_config.density,
                test_config.known_patterns_ratio
            )
            # Store with metadata
            for test_case in test_cases:
                all_tests.append({
                    'test_id': test_id,
                    'params': params.copy(),
                    'test_case': test_case,
                    'config': test_config  # we’ll need this per-test for prompt formatting etc.
                })
            test_id += 1  # Note: this is per-test-case now, not per-param-combo

        print(f"🧪 Total individual test cases to run: {len(all_tests)}")

        # 🔄 RUN: Group by model → run ALL test cases for each model in one go
        model_results_dict = {model: {} for model in self.config.models}  # Final results per model

        for model_name in self.config.models:
            print(f"\n🧠 MODEL BATCH: {model_name}")
            print(f"   Running {len(all_tests)} test cases...")

            # Create interface ONCE per model
            # ⚠️ We need to create a dummy config to init the interface — we’ll override per-test later
            dummy_config = self.create_test_config(test_combinations[0])
            dummy_config.models = [model_name]  # Override to single model
            model_interface = create_interface(dummy_config)
            model_interface.preload_models()  # Preload once per model

            evaluator = TestEvaluator()
            engine = GameOfLifeEngine()

            all_results_for_model = []

            # Run all test cases for this model
            for i, test_data in enumerate(all_tests):
                params = test_data['params']
                test_case = test_data['test_case']
                per_test_config = test_data['config']  # Already has model list — but we’re forcing single model

                # Override config to use current model (just in case)
                per_test_config.models = [model_name]

                logger.debug(f"Test {i+1}/{len(all_tests)} for model {model_name}")

                try:
                    # Get ground truth
                    ground_truth = [test_case.grid, engine.next_state(test_case.grid)]
                    ground_truth.append(engine.next_state(ground_truth[-1]))

                    examples = "" if per_test_config.prompt_style not in ["examples", "example_rules_math"] else format_examples(EXAMPLE_PATTERNS, test_case.width, test_case.height, per_test_config)

                    # Query model
                    prompt = format_prompt(
                        test_case.grid,
                        per_test_config.prompt_style,
                        per_test_config.prompt_language,
                        examples=examples,
                        live_cell_mark=per_test_config.live_dead_cell_markers[0],
                        dead_cell_mark=per_test_config.live_dead_cell_markers[1]
                    )
                    response = model_interface.query_model(model_name, prompt)

                    # Parse and evaluate
                    predicted = parse_response(
                        prompt,
                        response,
                        ground_truth[1],
                        live_cell_mark=per_test_config.live_dead_cell_markers[0],
                        dead_cell_mark=per_test_config.live_dead_cell_markers[1]
                    )

                    if predicted is not None:
                        logger.info(f"Predicted:\n{format_grid(predicted, per_test_config.live_dead_cell_markers[0], per_test_config.live_dead_cell_markers[1])}")
                        logger.info(f"Ground Truth:\n{format_grid(ground_truth[1], per_test_config.live_dead_cell_markers[0], per_test_config.live_dead_cell_markers[1])}")
                        if per_test_config.verbose:
                            logger.info(f"Prompt:\n---\n{prompt}\n---\nResponse:\n{response}\n---")

                    result = evaluator.compare_grids(predicted, ground_truth[1])
                    result["raw_response"] = response
                    result["test_id"] = test_data['test_id']
                    result["params"] = params

                    all_results_for_model.append(result)

                except Exception as e:
                    logger.error(f"Error in test {i+1} for model {model_name}: {e}", exc_info=True)
                    all_results_for_model.append({
                        "accuracy": 0.0,
                        "correct_cells": 0,
                        "total_cells": test_case.width * test_case.height,
                        "parse_error": True,
                        "cell_by_cell": [],
                        "raw_response": str(e),
                        "error_details": str(e),
                        "test_id": test_data['test_id'],
                        "params": params
                    })

            # After running ALL test cases for this model → evaluate batch
            batch_eval = evaluator.evaluate_batch(all_results_for_model)
            model_results_dict[model_name] = batch_eval

            # Save per-model incremental results
            model_result_entry = {
                'model_name': model_name,
                'timestamp': datetime.now().isoformat(),
                'parameters_tested': len(test_combinations),
                'total_test_cases': len(all_results_for_model),
                'batch_eval': batch_eval,
                'detailed_results': all_results_for_model  # optional — can be huge
            }

            # Save to incremental file
            incremental_file = self.results_file.with_name(self.results_file.stem + '_per_model.jsonl')
            with open(incremental_file, 'a') as f:
                json.dump(model_result_entry, f)
                f.write('\n')

            print(f"✅ Model {model_name} done. Avg Accuracy: {batch_eval['average_accuracy']:.2%}")

        # 🧾 FINALIZE: Assemble final results in original format
        # We’ll create one “test” per parameter combination, with all model results attached
        self.results = []
        for i, params in enumerate(test_combinations, 1):
            # For each param combo, gather results from all models
            model_results_for_combo = {}
            for model_name in self.config.models:
                # Filter results for this param combo
                combo_results = [
                    res for res in model_results_dict[model_name].get('detailed_results', [])
                    if res.get('params') == params
                ]
                if combo_results:
                    # Re-evaluate just this subset
                    subset_eval = evaluator.evaluate_batch(combo_results)
                    model_results_for_combo[model_name] = subset_eval
                else:
                    model_results_for_combo[model_name] = {"error": "No results for this combo"}

            test_result = {
                'test_id': i,
                'timestamp': datetime.now().isoformat(),
                'parameters': params,
                'model_results': model_results_for_combo
            }
            self.results.append(test_result)
            self.save_incremental_result(test_result)

        # Save final consolidated results
        self.save_final_results()
        self.print_final_summary()

        return self.results
    
    def setup_results_file(self):
        """Setup results directory and file"""
        results_dir = Path(self.config.results_dir)
        results_dir.mkdir(exist_ok=True)
        
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        models_str = "_".join(
            "".join(c if c.isalnum() or c in ('-', '_', '.') else '_' for c in model)
            for model in self.config.models
        )
        
        self.results_file = results_dir / f"matrix_{models_str}_{timestamp}.json"
    
    def save_incremental_result(self, result: Dict[str, Any]):
        """Save individual test result incrementally"""
        incremental_file = self.results_file.with_suffix('.incremental.jsonl')
        with open(incremental_file, 'a') as f:
            json.dump(result, f)
            f.write('\n')
    
    def save_final_results(self):
        """Save final consolidated results"""
        final_results = {
            'config': asdict(self.config),
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'total_tests': len(self.results),
            'results': self.results
        }
        
        with open(self.results_file, 'w') as f:
            json.dump(final_results, f, indent=2)
        
        print(f"💾 Results saved to: {self.results_file}")
    
    def print_test_config(self, params: Dict[str, Any]):
        """Print current test configuration"""
        markers_display = f"{params['live_dead_cell_markers'][0]}/{params['live_dead_cell_markers'][1]}"
        print(f"   Markers: {markers_display} | "
              f"Difficulty: {params['difficulty']} | "
              f"Temp: {params['temperature']} | "
              f"Thinking: {'No' if params['no_think'] else 'Yes'}")
        print(f"   Style: {params['prompt_style']} | "
              f"Lang: {params['prompt_language']} | "
              f"Ctx: {params['ctx_len']} | "
              f"Predict: {params['num_predict']}")
    
    def print_test_summary(self, model_results: Dict[str, Dict]):
        """Print brief summary of test results"""
        if not model_results:
            print("   ❌ No results")
            return
        
        best_model = max(
            model_results.items(),
            key=lambda x: x[1].get('normalized_accuracy', 0)
        )
        
        print(f"   🏆 Best: {best_model[0]} "
              f"({best_model[1].get('normalized_accuracy', 0):.1%})")
    
    def print_final_summary(self):
        """Print final summary of all tests"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print(f"\n{'=' * 80}")
        print(f"🏁 MATRIX TEST COMPLETE")
        print(f"⏰ Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"📊 Total Tests: {len(self.results)}")
        
        # Find best overall configuration
        successful_results = [r for r in self.results if 'model_results' in r and r['model_results']]
        if successful_results:
            best_result = max(
                successful_results,
                key=lambda x: max(
                    (model_data.get('normalized_accuracy', 0) 
                     for model_data in x['model_results'].values()),
                    default=0
                )
            )
            
            best_model_name = max(
                best_result['model_results'].items(),
                key=lambda x: x[1].get('normalized_accuracy', 0)
            )[0]
            
            best_score = best_result['model_results'][best_model_name].get('normalized_accuracy', 0)
            
            print(f"🥇 Best Overall: {best_model_name} ({best_score:.1%})")
            print(f"🔧 Best Config: {best_result['parameters']}")
        
        print(f"💾 Results: {self.results_file}")
        print(f"{'=' * 80}")

def create_analysis_report(results_file: str):
    """Create a detailed analysis report from matrix results"""
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    results = data['results']
    successful_results = [r for r in results if 'model_results' in r and r['model_results']]
    
    if not successful_results:
        print("No successful results to analyze")
        return
    
    # Analyze by parameter
    print(f"\n📈 PARAMETER ANALYSIS")
    print("=" * 50)
    
    parameters_to_analyze = [
        'difficulty', 'temperature', 'prompt_style', 'no_think',
        'live_dead_cell_markers', 'prompt_language', 'ctx_len', 'num_predict'
    ]
    
    for param in parameters_to_analyze:
        param_results = {}
        
        for result in successful_results:
            param_value = str(result['parameters'][param])
            if param_value not in param_results:
                param_results[param_value] = []
            
            # Get best model score for this test
            best_score = max(
                model_data.get('normalized_accuracy', 0)
                for model_data in result['model_results'].values()
            )
            param_results[param_value].append(best_score)
        
        # Calculate averages
        param_averages = {
            value: sum(scores) / len(scores)
            for value, scores in param_results.items()
        }
        
        print(f"\n{param.upper()}:")
        for value, avg_score in sorted(param_averages.items(), key=lambda x: x[1], reverse=True):
            count = len(param_results[value])
            print(f"  {value}: {avg_score:.1%} (n={count})")

def setup_argparser() -> argparse.ArgumentParser:
    """Setup command line argument parser for matrix testing"""
    parser = argparse.ArgumentParser(
        description="Game of Life Matrix Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        '--model', '-m', type=str, nargs='+', required=True,
        help='Models to test (e.g., qwen3:0.6b qwen3:1.7b)'
    )
    
    # Test configuration
    parser.add_argument(
        '--batch-size', '-b', type=int, default=10,
        help='Batch size for each test (default: 10)'
    )
    
    parser.add_argument(
        '--seed', '-s', type=int, default=42,
        help='Random seed (default: 42)'
    )
    
    # Parameter matrices (optional - defaults will be used if not specified)
    parser.add_argument(
        '--difficulty', type=str, nargs='+',
        choices=['easy', 'medium', 'hard', 'nightmare'],
        help='Difficulty levels to test'
    )
    
    parser.add_argument(
        '--temperature', type=float, nargs='+',
        help='Temperature values to test'
    )
    
    parser.add_argument(
        '--prompt-style', type=str, nargs='+',
        choices=['linguistic', 'example_rules_math', 'examples', 'casual', 'minimal'],
        help='Prompt styles to test'
    )
    
    parser.add_argument(
        '--prompt-language', type=str, nargs='+',
        choices=['en', 'fr', 'es', 'de', 'zh', 'ua'],
        help='Languages to test'
    )
    
    parser.add_argument(
        '--ctx-len', type=int, nargs='+',
        help='Context lengths to test'
    )
    
    parser.add_argument(
        '--num-predict', type=int, nargs='+',
        help='Num predict values to test'
    )
    
    # Output configuration
    parser.add_argument(
        '--results-dir', type=str, default='matrix_results',
        help='Results directory (default: matrix_results)'
    )
    
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Verbose output'
    )
    
    # Analysis mode
    parser.add_argument(
        '--analyze', type=str,
        help='Analyze existing results file instead of running tests'
    )
    
    return parser

def main():
    """Main entry point for matrix testing"""
    parser = setup_argparser()
    args = parser.parse_args()
    
    # Analysis mode
    if args.analyze:
        create_analysis_report(args.analyze)
        return
    
    # Create matrix configuration
    config = MatrixConfig(
        models=args.models,
        batch_size=args.batch_size,
        seed=args.seed,
        verbose=args.verbose,
        results_dir=args.results_dir
    )
    
    # Override defaults with command line arguments
    if args.difficulties:
        config.difficulties = args.difficulties
    if args.temperatures:
        config.temperatures = args.temperatures
    if args.prompt_styles:
        config.prompt_styles = args.prompt_styles
    if args.prompt_languages:
        config.prompt_languages = args.prompt_languages
    if args.ctx_lens:
        config.ctx_lens = args.ctx_lens
    if args.num_predicts:
        config.num_predicts = args.num_predicts
    
    # Run matrix test
    tester = MatrixTester(config)
    tester.run_matrix_test()

if __name__ == "__main__":
    main()