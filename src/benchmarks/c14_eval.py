"""
Cellular Automata 1D Benchmark (C14) for gol_eval
Tests LLM reasoning on Wolfram elementary cellular automata (Rules 0-255)
Validates evolution prediction accuracy with various rule complexities
"""
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from tabulate import tabulate
from typing import List, Dict, Any
from tqdm import tqdm

import argparse
import sys

from src.models.BaseModelInterface import create_interface
from src.evaluation.TestEvaluator import TestEvaluator, TestResult
from src.core.types import C14TestConfig as TestConfig
from src.core.PromptEngine import PromptEngine, Language, SystemPromptStyle
from src.engine.CellularAutomata1DEngine import CellularAutomata1DEngine, BoundaryCondition


def parse_evolution_response(response: str, expected_steps: int) -> List[str] | None:
    """
    Parse cellular automata evolution from model response.
    
    Handles formats:
    - Bracketed: [0,1,0,1,1]
    - Spaced: 0 1 0 1 1
    - Comma-separated: 0,1,0,1,1
    - Text mixed: "Step 3: [0,1,0,1,1]"
    
    Returns:
        List of state strings if parsed successfully, None otherwise
    """
    if not response:
        return None
    
    lines = response.strip().split('\n')
    states = []
    
    # Strategy 1: Look for bracketed sequences [0,1,0,...]
    bracket_pattern = r'\[([0-9,\s]+)\]'
    for line in lines:
        matches = re.findall(bracket_pattern, line)
        for match in matches:
            # Clean and normalize
            state = match.replace(' ', '').replace(',', '')
            if len(state) > 0 and all(c in '01' for c in state):
                states.append(state)
    
    if len(states) >= expected_steps:
        return states[:expected_steps]
    
    # Strategy 2: Look for space/comma-separated binary sequences
    for line in lines:
        # Remove common prefixes
        line = re.sub(r'^(Step\s+\d+[:.]?\s*|State\s+\d+[:.]?\s*|t=\d+[:.]?\s*)', '', line, flags=re.IGNORECASE)
        line = line.strip()
        
        # Try to extract binary sequence
        if ',' in line:
            parts = line.split(',')
        else:
            parts = line.split()
        
        # Filter to binary digits
        binary_parts = [p.strip() for p in parts if p.strip() in ['0', '1']]
        
        if len(binary_parts) > 3:  # Minimum reasonable width
            state = ''.join(binary_parts)
            states.append(state)
    
    if len(states) >= expected_steps:
        return states[:expected_steps]
    
    # Strategy 3: Look for continuous binary strings (01001101...)
    binary_pattern = r'\b([01]{4,})\b'
    for line in lines:
        matches = re.findall(binary_pattern, line)
        states.extend(matches)
    
    if len(states) >= expected_steps:
        return states[:expected_steps]
    
    return None if len(states) == 0 else states


def run_c14_tests(test_cases: List[Dict], model: str, config: TestConfig) -> Dict[str, Any]:
    """Run C14 cellular automata tests on specified model"""
    model_interface = create_interface(config)
    evaluator = TestEvaluator()
    
    # Preload models to reduce latency
    model_interface.preload_models()

    results = []
    t0 = datetime.now()
    
    with tqdm(enumerate(test_cases), desc=f"Model {model}", unit="test", total=len(test_cases), dynamic_ncols=True) as pbar:
        for i, test_case in pbar:
            try:
                response, stats = model_interface.query_model(
                    model, 
                    test_case['prompt'], 
                    test_case['system']
                )

                # Parse evolution sequence
                expected_states = test_case['expected_states']
                expected_steps = len(expected_states)
                parsed_states = parse_evolution_response(response, expected_steps)
                
                # Evaluate accuracy
                if parsed_states is None:
                    accuracy = 0.0
                    correct_steps = 0
                    parse_error = True
                else:
                    # Compare each step
                    correct_steps = sum(
                        1 for pred, exp in zip(parsed_states, expected_states) 
                        if pred == exp
                    )
                    accuracy = correct_steps / len(expected_states) if expected_states else 0.0
                    parse_error = False
                
                result: TestResult = {
                    "accuracy": accuracy,
                    "correct_cells": correct_steps,
                    "total_cells": len(expected_states),
                    "parse_error": parse_error,
                    "cell_by_cell": [],
                    "raw_response": response,
                    "error_details": None,
                    "total_duration": stats.get('total_duration', 0),
                    "load_duration": stats.get('load_duration', 0),
                    "prompt_eval_count": stats.get('prompt_eval_count', 0),
                    "prompt_eval_duration": stats.get('prompt_eval_duration', 0),
                    "eval_count": stats.get('eval_count', 0),
                    "eval_duration": stats.get('eval_duration', 0),
                }
                
                results.append(result)
                
                # Update progress bar with running accuracy
                avg_acc = sum(r['accuracy'] for r in results) / len(results)
                pbar.set_postfix_str(f"Acc: {avg_acc:.1%}, Parse Errors: {sum(1 for r in results if r['parse_error'])}")

            except Exception as e:
                print(f"\nError in test {i+1} for model {model}: {e}")
                if config.verbose:
                    import traceback
                    traceback.print_exc()
                
                results.append({
                    "accuracy": 0.0,
                    "correct_cells": 0,
                    "total_cells": len(test_case.get('expected_states', [])),
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
        print(f"   Valid Tests: {batch_eval['valid_tests']}/{batch_eval['total_tests']}")
        print(f"   Parse Errors: {batch_eval['parse_errors']}")
        print(f"   Success Rate: {batch_eval['success_rate']:.2%}")
        print(f"   Total Duration: {duration:.2f} seconds")
        print(f"   Avg Duration: {duration / len(test_cases):.2f} seconds per test")

    return batch_eval


def generate_test_cases(config: TestConfig) -> List[Dict]:
    """Generate C14 test cases based on configuration"""
    engine = CellularAutomata1DEngine(seed=config.seed)
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
    
    # Map string boundary condition to enum
    boundary_map = {
        'wrap': BoundaryCondition.WRAP,
        'dead': BoundaryCondition.DEAD,
        'alive': BoundaryCondition.ALIVE,
    }
    boundary_condition = boundary_map.get(
        config.boundary_condition if hasattr(config, 'boundary_condition') else 'wrap',
        BoundaryCondition.WRAP
    )
    
    test_cases = []
    
    # Generate test cases for each rule number
    for rule_number in config.rule_numbers:
        for _ in range(config.cases_per_rule):
            # Generate test case using engine
            test_case = engine.generate_test_case(
                rule_number=rule_number,
                width=config.width,
                steps=config.steps,
                boundary_condition=boundary_condition,
                language=config.prompt_language,
                style=config.prompt_style
            )
            
            # Use PromptEngine to generate prompts
            from src.core.PromptEngine import create_c14_context
            context = create_c14_context(
                language=prompt_language.value,
                style=config.prompt_style,
                rule_number=test_case['rule_number'],
                initial_state=test_case['initial_state'],
                steps=test_case['steps'],
                boundary_condition=test_case['boundary_condition']
            )
            
            result = prompt_engine.generate(context)
            
            test_cases.append({
                "rule_number": test_case['rule_number'],
                "initial_state": test_case['initial_state'],
                "steps": test_case['steps'],
                "expected_states": test_case['evolution'],
                "boundary_condition": test_case['boundary_condition'],
                "language": config.prompt_language,
                "style": config.prompt_style,
                "prompt": result.user_prompt,
                "system": prompt_engine.get_system_prompt_by_enum(system_prompt_style, prompt_language),
            })
    
    return test_cases


def setup_argparser() -> argparse.ArgumentParser:
    """Set up command line argument parser"""
    parser = argparse.ArgumentParser(
        description="C14 Cellular Automata Test Framework for LLM Reasoning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python c14_eval.py --model qwen3:0.6b --rules 30 110 --batch-size 5
  python c14_eval.py --model llama3.2:3b --rules 90 150 --width 16 --steps 5
  python c14_eval.py --model qwen3:0.6b --rules 30 --boundary wrap dead --verbose
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
        '--rules', '-r', type=int, nargs='+', 
        default=[30],
        help='Wolfram rule numbers to test (0-255, default: 30)'
    )

    parser.add_argument(
        '--width', '-w', type=int, default=16,
        help='Width of cellular automata grid (default: 16)'
    )

    parser.add_argument(
        '--steps', type=int, default=3,
        help='Number of evolution steps (default: 3)'
    )

    parser.add_argument(
        '--cases-per-rule', type=int, default=5,
        help='Number of test cases per rule (default: 5)'
    )

    parser.add_argument(
        '--boundary', '-b', type=str, nargs='+',
        default=['wrap'],
        choices=['wrap', 'dead', 'alive'],
        help='Boundary conditions to test (default: wrap)'
    )

    parser.add_argument(
        '--density', type=float, default=0.3,
        help='Initial state density (default: 0.3)'
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

    # Prompt style
    parser.add_argument(
        '--prompt-style', type=str, default='linguistic',
        choices=['linguistic', 'casual', 'minimal', 'examples'],
        help='Prompt style to use (default: linguistic)'
    )

    parser.add_argument(
        '--system-prompt-style', type=str, default='analytical',
        choices=['analytical', 'casual', 'adversarial', 'none'],
        help='System prompt style to use (default: analytical)'
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
    print(f"🏁 C14 CELLULAR AUTOMATA TEST RESULTS")
    print(f"Models: {', '.join(config.models)}")
    print(f"Rules: {', '.join(map(str, config.rule_numbers))}")
    print(f"Grid Width: {config.width}")
    print(f"Evolution Steps: {config.steps}")
    print(f"Cases per Rule: {config.cases_per_rule}")
    print(f"Boundary Condition: {config.boundary_condition if hasattr(config, 'boundary_condition') else 'wrap'}")
    print(f"Temperature: {config.temperature}")
    print(f"Prompt Style: {config.prompt_style}")
    print(f"{'='*80}")

    # Prepare table data
    table_data = []
    headers = [
        "Model", "Avg Accuracy", "Norm Accuracy",
        "Valid Tests", "Parse Errors", "Success Rate"
    ]

    for model, results in model_results.items():
        row = [
            model,
            f"{results['average_accuracy']:.2%}",
            f"{results['normalized_accuracy']:.2%}",
            f"{results['valid_tests']}/{results['total_tests']}",
            results['parse_errors'],
            f"{results['success_rate']:.2%}",
        ]
        table_data.append(row)

    # Sort by normalized accuracy (descending)
    table_data.sort(key=lambda x: float(x[2].rstrip('%')), reverse=True)

    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Find best model
    if model_results:
        best_model = max(
            model_results.items(),
            key=lambda x: x[1]['normalized_accuracy']
        )
        print(f"\n🥇 Best Performing Model: {best_model[0]} ({best_model[1]['normalized_accuracy']:.2%})")


def save_results(model_results: Dict[str, Dict], config: TestConfig, test_cases: List[Dict]) -> Path:
    """Save results to JSON file"""
    results_dir = Path(config.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"c14_results_{timestamp}.json"
    filepath = results_dir / filename
    
    output = {
        "config": {
            "models": config.models,
            "rule_numbers": config.rule_numbers,
            "width": config.width,
            "steps": config.steps,
            "cases_per_rule": config.cases_per_rule,
            "temperature": config.temperature,
            "prompt_style": config.prompt_style,
            "prompt_language": config.prompt_language,
        },
        "model_results": model_results,
        "test_cases_count": len(test_cases),
        "timestamp": timestamp,
    }
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Results saved to: {filepath}")
    return filepath


def main() -> None:
    """Main entry point"""
    try:
        parser = setup_argparser()
        args = parser.parse_args()

        # Validate rule numbers
        invalid_rules = [r for r in args.rules if r < 0 or r > 255]
        if invalid_rules:
            print(f"❌ Error: Invalid rule numbers {invalid_rules}. Must be 0-255.")
            sys.exit(1)

        # Create config
        config = TestConfig(
            models=args.model,
            rule_numbers=args.rules,
            width=args.width,
            steps=args.steps,
            cases_per_rule=args.cases_per_rule,
            boundary_condition=args.boundary[0],  # Use first boundary for now
            density=args.density,
            temperature=args.temperature,
            no_think=args.no_think,
            ctx_len=args.ctx_len,
            num_predict=args.num_predict,
            verbose=args.verbose and not args.quiet,
            seed=args.seed,
            prompt_style=args.prompt_style,
            system_prompt_style=args.system_prompt_style,
            prompt_language=args.prompt_language,
            results_dir=args.results_dir
        )

        # Generate test cases
        print("🔄 Generating C14 test cases...")
        test_cases = generate_test_cases(config)
        print(f"✅ Generated {len(test_cases)} test cases")

        # Run tests on each model
        model_results = {}
        for model in config.models:
            model_results[model] = run_c14_tests(test_cases, model, config)

        # Display and save results
        display_results(model_results, config)
        save_results(model_results, config, test_cases)

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
