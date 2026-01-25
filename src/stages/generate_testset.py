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
from src.engine.CellularAutomata1DEngine import CellularAutomata1DEngine, CellularAutomataTestGenerator
from src.core.TestGenerator import TestGenerator
from src.core.types import DifficultyLevel, BaseTestConfig, GameState
from src.benchmarks.gol_eval import format_grid
from src.utils.path_manager import get_path_manager, RunMetadata
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
    
    # Support both old format (target_accuracies) and new format (complexity + target_values)
    if 'complexity' in gen_params and 'target_values' in gen_params:
        # New format: separate complexity and target values
        complexity_levels = gen_params['complexity'] if isinstance(gen_params['complexity'], list) else [gen_params['complexity']]
        target_values = gen_params['target_values'] if isinstance(gen_params['target_values'], list) else [gen_params['target_values']]
    else:
        # Old format: target_accuracies maps to both
        target_values = gen_params.get('target_accuracies', [1])
        complexity_levels = [min(tv + 1, 5) for tv in target_values]  # Map to complexity 1-5
    
    test_id = 0
    for prompt_config in config['task']['prompt_configs']:
        for complexity in complexity_levels:
            for target_value in target_values:
                # Generate all expressions for this target at once
                expressions = generator.generate_expressions_for_target(
                    target=target_value,
                    complexity=complexity,
                    count=gen_params.get('expressions_per_target', gen_params.get('count', 10))
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
                        'complexity': complexity,
                        'target_value': target_value,
                        'expression': expression,
                        'expected_answer': target_value,  # The expression evaluates to this
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


def generate_c14_tests(config: Dict) -> List[Dict]:
    """Generate 1D Cellular Automata test cases."""
    tests = []
    gen_params = config['task']['generation']
    
    # Initialize components
    ca_engine = CellularAutomata1DEngine()
    ca_generator = CellularAutomataTestGenerator(seed=gen_params['seed'])
    prompt_engine = PromptEngine()
    
    test_id = 0
    for prompt_config in config['task']['prompt_configs']:
        for rule_number in gen_params['rule_numbers']:
            for i in range(gen_params.get('cases_per_rule', 5)):
                # Generate test case
                test_case_data = ca_generator.generate_test_case(
                    rule_number=rule_number,
                    width=gen_params.get('width', 16),
                    steps=gen_params.get('steps', 1),
                    boundary=gen_params.get('boundary_condition', 'wrap'),
                    initial_pattern=gen_params.get('initial_pattern', 'random'),
                    density=gen_params.get('density', 0.5)
                )
                
                # Create prompt context
                context = PromptContext(
                    task_type=TaskType.CELLULAR_AUTOMATA_1D,
                    language=Language(prompt_config.get('language', 'en')),
                    style=PromptStyle(prompt_config['user_style']),
                    system_style=SystemPromptStyle(prompt_config['system_style'])
                )
                
                # Prepare state strings
                alive_char = config['execution'].get('cell_markers', ['1', '0'])[0]
                dead_char = config['execution'].get('cell_markers', ['1', '0'])[1]
                state_str = ca_engine.state_to_string(test_case_data['initial_state'], alive_char, dead_char)
                expected_state_str = ca_engine.state_to_string(test_case_data['expected_states'][0], alive_char, dead_char)
                
                # Prepare rule table
                rule_table = ca_engine.format_rule_table(rule_number)
                
                # Boundary descriptions
                boundary_descriptions = {
                    'wrap': 'Periodic boundaries (edges wrap around)',
                    'dead': 'Fixed boundaries with dead cells (0)',
                    'alive': 'Fixed boundaries with alive cells (1)'
                }
                boundary_desc = boundary_descriptions.get(test_case_data['boundary'], '')
                
                # Generate examples for EXAMPLES prompt style
                examples_text = ""
                if prompt_config['user_style'] == 'examples':
                    # Generate 2 simple examples
                    example_cases = ca_generator.generate_batch(
                        rule_numbers=[rule_number],
                        width=8,  # Smaller width for examples
                        steps=1,
                        cases_per_rule=2,  # Generate 2 examples
                        boundary=test_case_data['boundary'],
                        initial_pattern='centered_single',
                        density=0.5
                    )
                    
                    for i, ex in enumerate(example_cases[:2], 1):
                        ex_initial = ' '.join(str(c) for c in ex['initial_state'])
                        ex_next = ' '.join(str(c) for c in ex['expected_states'][0])
                        examples_text += f"Example {i}:\nCurrent: {ex_initial}\nNext: {ex_next}\n\n"
                
                # Set all context variables
                context.set('rule_number', rule_number)
                context.set('state_str', state_str)
                context.set('rule_table', rule_table)
                context.set('boundary_description', boundary_desc)
                context.set('boundary_math', f"periodic" if test_case_data['boundary'] == 'wrap' else "fixed")
                context.set('example_output', f"{alive_char} {dead_char} {alive_char} ...")
                context.set('examples', examples_text.strip())
                
                # Generate prompts
                result = prompt_engine.generate(context)
                
                # Create test case
                test_case = {
                    'test_id': f"c14_{test_id:04d}",
                    'task_type': 'cellular_automata_1d',
                    'config_name': f"{prompt_config['user_style']}_{prompt_config['system_style']}",
                    'prompts': {
                        'system': result.system_prompt,
                        'user': result.user_prompt,
                        'full': f"{result.system_prompt}\n\n{result.user_prompt}"
                    },
                    'task_params': {
                        'rule_number': rule_number,
                        'initial_state': test_case_data['initial_state'],
                        'expected_next_state': test_case_data['expected_states'][0],
                        'width': test_case_data['width'],
                        'steps': test_case_data['steps'],
                        'boundary': test_case_data['boundary'],
                        'difficulty': test_case_data['difficulty'],
                        'rule_description': test_case_data['rule_description']
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


def generate_linda_tests(config: Dict) -> List[Dict]:
    """Generate Linda Conjunction Fallacy test cases with culture-language alignment."""
    tests = []
    gen_params = config['task']['generation']
    
    # Import Linda benchmark components
    from src.benchmarks.linda_eval import LindaBenchmark, PersonaTemplate
    
    # Get language and ensure culture alignment
    language = config['execution'].get('prompt_language', 'en')
    culture_filter = gen_params.get('culture_filter', None)
    
    # Map language to appropriate cultures to avoid mismatch (English prompt + Chinese name)
    language_culture_map = {
        'en': ['western', 'african', 'european'],  # English-speaking cultures
        'es': ['latin_american', 'european'],      # Spanish-speaking cultures
        'fr': ['european', 'african'],             # French-speaking cultures
        'de': ['european'],                        # German-speaking cultures
        'zh': ['east_asian'],                      # Chinese-speaking cultures
    }
    
    # Filter cultures based on language
    if culture_filter:
        # Validate culture is compatible with language
        compatible_cultures = language_culture_map.get(language, ['western'])
        if culture_filter not in compatible_cultures:
            print(f"Warning: Culture '{culture_filter}' may not align with language '{language}'. Using compatible culture.")
            culture_filter = compatible_cultures[0]
    else:
        # Use all cultures compatible with the language
        compatible_cultures = language_culture_map.get(language, ['western'])
        culture_filter = None  # Will use all compatible cultures
    
    # Initialize Linda benchmark
    linda_benchmark = LindaBenchmark(
        language=language,
        num_options=gen_params.get('num_options', 8),
        culture_filter=culture_filter
    )
    
    # Filter personas by language-compatible cultures if no specific filter
    if not culture_filter:
        compatible_cultures = language_culture_map.get(language, ['western'])
        linda_benchmark.persona_templates = [
            p for p in linda_benchmark.persona_templates 
            if p.culture in compatible_cultures
        ]
    
    if not linda_benchmark.persona_templates:
        raise ValueError(f"No personas available for language '{language}' and culture filter '{culture_filter}'")
    
    prompt_engine = PromptEngine()
    test_id = 0
    
    for prompt_config in config['task']['prompt_configs']:
        personas_per_config = gen_params.get('personas_per_config', 5)
        
        for persona_idx in range(personas_per_config):
            # Cycle through available personas
            persona = linda_benchmark.persona_templates[persona_idx % len(linda_benchmark.persona_templates)]
            
            # Generate test item using Linda's logic
            test_item = linda_benchmark.generate_test_item(persona)
            
            # Create prompt context
            context = PromptContext(
                task_type=TaskType.LINDA_FALLACY,
                language=Language(language),
                style=PromptStyle(prompt_config['user_style']),
                system_style=SystemPromptStyle(prompt_config['system_style'])
            )
            
            # Format persona description
            traits_str = ", ".join(persona.personality_traits)
            background_str = ". ".join(persona.background)
            activities_str = " and ".join(persona.activities)
            persona_description = f"{persona.name} is {persona.age} years old, {traits_str}. {background_str}. As a student, {activities_str}."
            
            # Set Linda-specific context variables
            context.set('persona_description', persona_description)
            context.set('ranked_items', '\n'.join(f"{i+1}. {item}" for i, item in enumerate(test_item.all_items)))
            context.set('num_options', len(test_item.all_items))
            
            # Generate prompts
            result = prompt_engine.generate(context)
            
            # Create test case
            test_case = {
                'test_id': f"linda_{test_id:04d}",
                'task_type': 'linda_fallacy',
                'config_name': prompt_config['name'],
                'prompts': {
                    'system': result.system_prompt,
                    'user': result.user_prompt,
                    'full': f"{result.system_prompt}\n\n{result.user_prompt}"
                },
                'task_params': {
                    'persona': {
                        'name': persona.name,
                        'age': persona.age,
                        'personality_traits': persona.personality_traits,
                        'background': persona.background,
                        'activities': persona.activities,
                        'culture': persona.culture
                    },
                    'test_item': {
                        'description': test_item.description,
                        'conjunction_item': test_item.conjunction_item,
                        'component_a': test_item.component_a,
                        'component_b': test_item.component_b,
                        'distractors': test_item.distractors,
                        'all_items': test_item.all_items
                    },
                    'expected_fallacy': True,  # We expect models to fall into conjunction fallacy
                    'num_options': len(test_item.all_items)
                },
                'prompt_metadata': {
                    'user_style': prompt_config['user_style'],
                    'system_style': prompt_config['system_style'],
                    'language': language,
                    'culture': persona.culture
                },
                'generation_metadata': {
                    'seed': gen_params['seed'],
                    'generator_version': "1.0.0",
                    'created_at': datetime.now().isoformat(),
                    'culture_filter': culture_filter,
                    'language_culture_aligned': True
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
    elif task_type == "cellular_automata_1d":
        test_cases = generate_c14_tests(config)
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
        elif task_type == "linda_fallacy":
            task_test_cases = generate_linda_tests(single_task_config)
        elif task_type == "cellular_automata_1d":
            task_test_cases = generate_c14_tests(single_task_config)
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
    
    # Use PathManager for organized file management
    path_mgr = get_path_manager()
    
    # Extract task types for filename
    task_types = testset['statistics']['task_types']
    base_name = config['metadata']['name']
    
    # Generate descriptive filepath
    filepath = path_mgr.get_testset_path(
        config_name=base_name,
        task_types=task_types,
        config_hash=config_hash,
        timestamp=timestamp
    )
    
    # Save compressed test set
    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(testset, f, indent=2)
    
    print(f"✓ Generated test set: {filepath}")
    print(f"  - {len(test_cases)} test cases (expected: {total_expected})")
    print(f"  - {prompt_configs} prompt configs")
    print(f"  - Task types: {', '.join(task_types)}")
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