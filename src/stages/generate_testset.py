#!/usr/bin/env python3
"""
Generate test sets from YAML configuration files.

This script implements Stage 1 of the 3-stage benchmark architecture:
YAML Config → Test Set Generation → Compressed JSON.gz Test Set

Usage:
    python scripts/generate_testset.py configs/testsets/ari_baseline_v1.yaml
    python scripts/generate_testset.py configs/testsets/*.yaml --output-dir testsets/
"""

import yaml
import json
import gzip
import hashlib
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.PromptEngine import PromptEngine, Language, PromptStyle, SystemPromptStyle, TaskType, PromptContext
from src.engine.MathExpressionGenerator import MathExpressionGenerator
from src.engine.GameOfLifeEngine import GameOfLifeEngine
from src.core.TestGenerator import TestGenerator
from src.core.types import DifficultyLevel, BaseTestConfig, GameState
from src.benchmarks.gol_eval import format_grid
from dataclasses import dataclass

@dataclass 
class MinimalTestConfig(BaseTestConfig):
    """Minimal config for test generation"""
    models: List[str] = None  # Not needed for generation
    seed: int = 42
    known_patterns_dir: str = "data/conways_life/known_patterns"
    
    def __post_init__(self):
        # Set a dummy model list to satisfy BaseTestConfig
        if self.models is None:
            self.models = ["dummy"]
        super().__post_init__()


# Version for test set format compatibility
TESTSET_FORMAT_VERSION = "1.0.0"


def load_config(config_path: str) -> Dict[str, Any]:
    """Load YAML config file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def compute_config_hash(config: Dict) -> str:
    """Compute SHA256 hash of config for versioning."""
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]  # Short hash for readability


def generate_arithmetic_tests(config: Dict) -> List[Dict]:
    """Generate arithmetic test cases."""
    tests = []
    gen_params = config['task']['generation']
    
    generator = MathExpressionGenerator(seed=gen_params['seed'])
    prompt_engine = PromptEngine()
    
    test_id = 0
    for prompt_config in config['task']['prompt_configs']:
        for target_accuracy in gen_params['target_accuracies']:
            # Generate all expressions for this target at once
            expressions = generator.generate_expressions_for_target(
                target=target_accuracy,
                complexity=target_accuracy + 1,  # Map to complexity level
                count=gen_params['expressions_per_target']
            )
            
            for i, expression in enumerate(expressions):
                
                # Create prompt context
                context = PromptContext(
                    task_type=TaskType.MATH_EXPRESSION,
                    language=Language(config['execution'].get('prompt_language', 'en')),
                    style=PromptStyle(prompt_config['user_style']),
                    system_style=SystemPromptStyle(prompt_config['system_style'])
                )
                
                # Set expression context
                context.set('expression', expression)
                context.set('variables', {})
                
                # Generate prompts
                result = prompt_engine.generate(context)
                
                # Create test case
                test_case = {
                    'test_id': f"ari_{test_id:04d}",
                    'task_type': 'arithmetic',
                    'config_name': prompt_config['name'],
                    'prompts': {
                        'system': result.system_prompt,
                        'user': result.user_prompt,
                        'full': f"{result.system_prompt}\n\n{result.user_prompt}"
                    },
                    'task_params': {
                        'target_accuracy': target_accuracy,
                        'difficulty': target_accuracy + 1,
                        'expression': expression,
                        'expected_answer': target_accuracy,  # The expression evaluates to this
                        'variables': {},
                        'mode': gen_params.get('mode', 'expression')
                    },
                    'prompt_metadata': {
                        'user_style': prompt_config['user_style'],
                        'system_style': prompt_config['system_style'],
                        'language': config['execution'].get('prompt_language', 'en')
                    },
                    'generation_metadata': {
                        'seed': gen_params['seed'],
                        'generator_version': "1.0.0",
                        'created_at': datetime.now().isoformat()
                    }
                }
                
                tests.append(test_case)
                test_id += 1
    
    return tests


def generate_gol_tests(config: Dict) -> List[Dict]:
    """Generate Game of Life test cases."""
    tests = []
    gen_params = config['task']['generation']
    
    # Initialize components
    gol_engine = GameOfLifeEngine()
    
    # Create minimal config for TestGenerator
    test_config = MinimalTestConfig(seed=gen_params['seed'])
    test_generator = TestGenerator(test_config)
    
    prompt_engine = PromptEngine()
    
    test_id = 0
    for prompt_config in config['task']['prompt_configs']:
        for difficulty_str in gen_params['difficulty_levels']:
            try:
                difficulty = DifficultyLevel[difficulty_str]  # Use bracket notation for enum access
            except KeyError:
                # Fallback to from_string if available
                difficulty = DifficultyLevel.from_string(difficulty_str.lower())
            
            for i in range(gen_params['grids_per_difficulty']):
                # Generate test batch (just take first one for simplicity)
                test_batch = test_generator.create_test_batch(
                    difficulty=difficulty,
                    batch_size=1,
                    density=gen_params.get('density', 0.5),
                    known_patterns_ratio=gen_params.get('known_patterns_ratio', 0.3)
                )
                
                game_state = test_batch[0]
                initial_grid = game_state.grid
                
                # Compute next state
                next_state = gol_engine.next_state(initial_grid)
                
                # Create prompt context
                context = PromptContext(
                    task_type=TaskType.GAME_OF_LIFE,
                    language=Language(prompt_config.get('language', 'en')),
                    style=PromptStyle(prompt_config['user_style']),
                    system_style=SystemPromptStyle(prompt_config['system_style'])
                )
                
                # Set grid context
                live_cell = config['execution'].get('cell_markers', ['1', '0'])[0]
                dead_cell = config['execution'].get('cell_markers', ['1', '0'])[1]
                grid_str = format_grid(initial_grid, live_cell, dead_cell)
                
                context.set('initial_grid', initial_grid)
                context.set('live_cell', live_cell)
                context.set('dead_cell', dead_cell)
                context.set('grid_str', grid_str)
                context.set('l', live_cell)  # Also set short aliases used in templates
                context.set('d', dead_cell)
                
                # Generate prompts
                result = prompt_engine.generate(context)
                
                # Create test case
                test_case = {
                    'test_id': f"gol_{test_id:04d}",
                    'task_type': 'game_of_life',
                    'config_name': prompt_config['name'],
                    'prompts': {
                        'system': result.system_prompt,
                        'user': result.user_prompt,
                        'full': f"{result.system_prompt}\n\n{result.user_prompt}"
                    },
                    'task_params': {
                        'difficulty': difficulty_str,
                        'initial_grid': initial_grid,
                        'expected_next_state': next_state,
                        'live_cell': live_cell,
                        'dead_cell': dead_cell,
                        'density': gen_params.get('density', 0.5),
                        'known_pattern': None  # Could be enhanced to track pattern name
                    },
                    'prompt_metadata': {
                        'user_style': prompt_config['user_style'],
                        'system_style': prompt_config['system_style'],
                        'language': prompt_config.get('language', 'en')
                    },
                    'generation_metadata': {
                        'seed': gen_params['seed'],
                        'generator_version': "1.0.0",
                        'created_at': datetime.now().isoformat()
                    }
                }
                
                tests.append(test_case)
                test_id += 1
    
    return tests


def generate_testset(config_path: str, output_dir: str = "testsets") -> str:
    """Generate test set from config file (supports both single-task and multi-task configs)."""
    print(f"Loading config: {config_path}")
    config = load_config(config_path)
    
    # Check if this is a multi-task config
    if 'tasks' in config:
        return generate_multi_task_testset(config, config_path, output_dir)
    
    # Legacy single-task config handling
    return generate_single_task_testset(config, config_path, output_dir)


def generate_single_task_testset(config: Dict, config_path: str, output_dir: str) -> str:
    """Generate test set for single-task config (legacy format)."""
    # Validate config
    required_fields = ['metadata', 'task', 'sampling', 'execution']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    # Generate test cases based on task type
    task_type = config['task']['type']
    print(f"Generating test cases for task type: {task_type}")
    
    if task_type == "arithmetic":
        test_cases = generate_arithmetic_tests(config)
    elif task_type == "game_of_life":
        test_cases = generate_gol_tests(config)
    else:
        raise ValueError(f"Unknown task type: {task_type}")
    
    return _finalize_testset(config, config_path, output_dir, test_cases, task_type)


def generate_multi_task_testset(config: Dict, config_path: str, output_dir: str) -> str:
    """Generate test set for multi-task config."""
    # Validate config
    required_fields = ['metadata', 'tasks', 'sampling', 'execution']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    print(f"Generating multi-task test set with {len(config['tasks'])} task types")
    
    all_test_cases = []
    test_id_counter = 0
    
    # Process each task
    for task_idx, task_config in enumerate(config['tasks']):
        task_type = task_config['type']
        print(f"  [{task_idx + 1}/{len(config['tasks'])}] Generating {task_type} tests...")
        
        # Create a single-task config for this task
        single_task_config = {
            'metadata': config['metadata'],
            'task': task_config,
            'sampling': config['sampling'],
            'execution': config['execution']
        }
        
        # Generate tests for this task type
        if task_type == "arithmetic":
            task_test_cases = generate_arithmetic_tests(single_task_config)
        elif task_type == "game_of_life":
            task_test_cases = generate_gol_tests(single_task_config)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
        
        # Update test IDs to be unique across all tasks
        for test_case in task_test_cases:
            test_case['test_id'] = f"multi_{test_id_counter:04d}_{task_type}"
            test_id_counter += 1
        
        all_test_cases.extend(task_test_cases)
        print(f"    ✓ Generated {len(task_test_cases)} {task_type} test cases")
    
    return _finalize_testset(config, config_path, output_dir, all_test_cases, "multi-task")


def _finalize_testset(config: Dict, config_path: str, output_dir: str, test_cases: List[Dict], task_type: str) -> str:
    """Finalize and save test set."""
    # Compute statistics
    if 'tasks' in config:  # Multi-task
        prompt_configs = sum(len(task['prompt_configs']) for task in config['tasks'])
        total_expected = len(test_cases)  # For multi-task, just use actual count
    else:  # Single task
        prompt_configs = len(config['task']['prompt_configs'])
        if task_type == "arithmetic":
            targets = len(config['task']['generation']['target_accuracies'])
            per_target = config['task']['generation']['expressions_per_target']
            total_expected = prompt_configs * targets * per_target
        elif task_type == "game_of_life":
            difficulties = len(config['task']['generation']['difficulty_levels'])
            per_difficulty = config['task']['generation']['grids_per_difficulty']
            total_expected = prompt_configs * difficulties * per_difficulty
        else:
            total_expected = len(test_cases)
    
    # Build output structure with versioning
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_hash = compute_config_hash(config)
    
    testset = {
        "format_version": TESTSET_FORMAT_VERSION,
        "metadata": {
            "name": config['metadata']['name'],
            "version": config['metadata']['version'],
            "schema_version": config['metadata']['schema_version'],
            "description": config['metadata']['description'],
            "created_by": config['metadata']['created_by'],
            "task_type": config['metadata']['task_type'],
            "created_at": datetime.now().isoformat(),
            "config_file": os.path.basename(config_path),
            "config_hash": config_hash,
            "generator_version": "1.0.0"
        },
        
        "generation_params": config.get('tasks', [config.get('task', {})]),  # Support both formats
        "sampling_params": config['sampling'],
        "execution_params": config['execution'],
        
        "test_cases": test_cases,
        
        "statistics": {
            "total_test_cases": len(test_cases),
            "prompt_configurations": prompt_configs,
            "task_types": [task_type] if task_type != "multi-task" else [t['type'] for t in config.get('tasks', [])],
            "expected_count": total_expected
        }
    }
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate output filename 
    base_name = config['metadata']['name']
    filename = f"testset_{base_name}_{timestamp}.json.gz"
    filepath = Path(output_dir) / filename
    
    # Save compressed test set
    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(testset, f, indent=2)
    
    print(f"✓ Generated test set: {filepath}")
    print(f"  - {len(test_cases)} test cases (expected: {total_expected})")
    print(f"  - {prompt_configs} prompt configs")
    print(f"  - Task type: {task_type}")
    print(f"  - Config hash: {config_hash}")
    print(f"  - Format version: {TESTSET_FORMAT_VERSION}")
    
    return str(filepath)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test sets from YAML configs")
    parser.add_argument("config", help="Path to YAML config file or glob pattern")
    parser.add_argument("--output-dir", default="testsets", help="Output directory")
    parser.add_argument("--validate", action="store_true", help="Validate test set after generation")
    
    args = parser.parse_args()
    
    # Handle glob patterns
    import glob
    config_files = glob.glob(args.config)
    
    if not config_files:
        print(f"Error: No config files found matching: {args.config}")
        sys.exit(1)
    
    successful = 0
    failed = 0
    
    for config_file in config_files:
        try:
            output_path = generate_testset(config_file, args.output_dir)
            
            # Optional validation
            if args.validate:
                print(f"Validating {output_path}...")
                with gzip.open(output_path, 'rt', encoding='utf-8') as f:
                    testset = json.load(f)
                    assert testset['format_version'] == TESTSET_FORMAT_VERSION
                    assert len(testset['test_cases']) > 0
                    print("✓ Validation passed")
            
            successful += 1
            
        except Exception as e:
            print(f"✗ Failed to generate test set from {config_file}: {e}")
            failed += 1
    
    print(f"\nSummary: {successful} successful, {failed} failed")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()