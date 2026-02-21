#!/usr/bin/env python3
"""
Benchmark Testing TUI - Terminal User Interface

Interactive terminal interface for configuring and running benchmark tests.
Uses questionary for simple, beautiful CLI prompts.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import sys
import questionary
from questionary import Style
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.path_manager import get_path_manager

@dataclass
class TaskConfiguration:
    """Configuration for a single task type in multi-task test set."""
    task_type: str  # 'ari', 'gol', 'c14', 'linda'
    task_name: str  # Display name
    batch_size: int
    prompts: 'PromptSpec'
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_tests(self) -> int:
        """Calculate total test cases for this task."""
        return self.batch_size * self.prompts.config_count()

@dataclass 
class MultiTaskConfig:
    """Configuration for multi-task test set generation."""
    name: str
    description: str
    tasks: List[TaskConfiguration]
    output_dir: str  # Directory where all files will be saved
    temperature: float = 0.1
    language: str = 'en'
    thinking_enabled: bool = False
    ollama_host: str = 'http://localhost:11434'
    
    @property
    def total_tests(self) -> int:
        return sum(task.total_tests for task in self.tasks)
    
    @property
    def total_task_types(self) -> int:
        return len(self.tasks)

from src.cli.benchmark_config import (
    BenchmarkConfig, ModelSpec, PromptSpec, TestParams
)
from src.utils.model_providers import ModelProviderManager, ModelInfo

# Setup Rich console
console = Console()

# Custom style for questionary
custom_style = Style([
    ('qmark', 'fg:#ff9142 bold'),
    ('question', 'fg:#ffffff bold'),
    ('answer', 'fg:#4ecdc4 bold'),
    ('pointer', 'fg:#ff9142 bold'),
    ('highlighted', 'fg:#ff9142 bold'),
    ('selected', 'fg:#4ecdc4'),
    ('separator', 'fg:#cc5de8'),
    ('instruction', 'fg:#858585'),
])


class BenchmarkTUI:
    """Terminal UI for benchmark configuration and execution."""
    
    def __init__(self):
        self.config: Optional[BenchmarkConfig] = None
        self.multi_task_config: Optional[MultiTaskConfig] = None
        self.generated_testset_path: Optional[str] = None
        self.ollama_host: str = "http://localhost:11434"
        self.provider_manager = ModelProviderManager()
        self.selected_provider: str = "ollama"
        self.available_providers: Dict[str, bool] = {}
        self._check_available_providers()
    
    def _check_available_providers(self):
        """Check which model providers are available."""
        for provider_name, provider in self.provider_manager.providers.items():
            is_available = provider.is_available()
            self.available_providers[provider_name] = is_available
    
    def display_header(self):
        """Display welcome header."""
        console.clear()
        title = Text("🚀 Benchmark Testing Automation", style="bold magenta")
        subtitle = Text("Terminal UI for configuring and running comprehensive LLM benchmarks", style="dim")
        console.print(Panel(f"{title}\n{subtitle}", expand=False))
    
    def main_menu(self) -> str:
        """Main menu selection."""
        self.display_header()
        
        choice = questionary.select(
            'What would you like to do?',
            choices=[
                'Start New Benchmark',
                'Quick Start (5 min test)',
                'Exit',
            ],
            style=custom_style
        ).ask()
        
        return choice
    
    def model_selection_for_execution(self) -> List[ModelSpec]:
        """Select models for executing the pre-generated test set (Step 3)."""
        provider = self._get_providers_to_use()
        if not provider:
            return []
        
        self.display_header()
        console.print(Panel(f"Step 3: Select Models for Execution ({provider})", style="bold"))
        
        # Get available models
        available_models = self._get_available_models_for_provider(provider)
        if not available_models:
            return []
        
        # Ask how to view models
        view_mode = self._show_model_grouping_options()
        
        console.print()  # Add spacing
        
        # Build choices based on view mode
        if view_mode == 'All Models (flat list)':
            choices = self._present_flat_models(available_models)
        elif view_mode == 'Grouped by Family':
            choices = self._present_grouped_models(available_models, group_by="family")
        elif view_mode == 'Grouped by Quantization':
            choices = self._present_grouped_models(available_models, group_by="quantization")
        elif view_mode == 'Grouped by Size':
            choices = self._present_grouped_models(available_models, group_by="size")
        elif view_mode == 'Filter & Select':
            return self._filter_and_select_models(available_models, provider)
        else:
            choices = self._present_flat_models(available_models)
        
        # Multi-select from choices
        selected_models_info = questionary.checkbox(
            'Select models to test (space to toggle, enter to confirm):',
            choices=choices,
            style=custom_style,
            validate=lambda x: len(x) > 0 or "Select at least one model"
        ).ask()
        
        if not selected_models_info:
            return []
        
        # Convert ModelInfo to ModelSpec
        selected_specs = []
        for model_info in selected_models_info:
            spec = ModelSpec(
                name=model_info.name,
                provider=provider,
                size_params=model_info.size_params,
                family=model_info.family,
                quantization=model_info.quantization,
                size_bytes=model_info.size_bytes,
                tags=[model_info.family] + ([model_info.quantization] if model_info.quantization else []),
            )
            selected_specs.append(spec)
        
        # Show summary
        console.print(f"\n✓ Selected {len(selected_specs)} models:")
        for spec in selected_specs:
            console.print(f"  • {spec.display_name}")
        
        return selected_specs
    
    def _get_providers_to_use(self) -> str:
        """Let user select which provider to use."""
        available = [name for name, avail in self.available_providers.items() if avail]
        
        if not available:
            console.print("[red]✗ No model providers available[/red]")
            console.print("  Please install Ollama: https://ollama.ai")
            return None
        
        if len(available) == 1:
            self.selected_provider = available[0]
            if self.selected_provider == "ollama":
                self._configure_ollama_host()
            return self.selected_provider
        
        self.display_header()
        console.print(Panel("Step 0: Select Model Provider", style="bold"))
        
        provider_choice = questionary.select(
            'Which model provider would you like to use?',
            choices=available,
            default=self.selected_provider if self.selected_provider in available else available[0],
            style=custom_style
        ).ask()
        
        self.selected_provider = provider_choice
        if provider_choice == "ollama":
            self._configure_ollama_host()
        return provider_choice
    
    def _configure_ollama_host(self):
        """Ask user for Ollama host URL (allows connecting to remote Ollama instances)."""
        host = questionary.text(
            'Ollama host URL:',
            default=self.ollama_host,
            style=custom_style
        ).ask()
        if host and host.strip():
            self.ollama_host = host.strip().rstrip('/')
            # Update provider manager and re-check availability
            self.provider_manager.set_ollama_host(self.ollama_host)
            self._check_available_providers()
    
    def _get_available_models_for_provider(self, provider: str) -> List[ModelInfo]:
        """Get available models from the selected provider."""
        models = self.provider_manager.list_models_by_provider(provider)
        
        if not models:
            console.print(f"[yellow]⚠️  No models found in {provider}[/yellow]")
            if provider == "ollama":
                console.print("  Pull some models first: [dim]ollama pull qwen3:0.6b[/dim]")
        
        return models
    
    def _show_model_grouping_options(self) -> str:
        """Let user choose how to view/filter models."""
        choice = questionary.select(
            'How would you like to view models?',
            choices=[
                'All Models (flat list)',
                'Grouped by Family',
                'Grouped by Quantization',
                'Grouped by Size',
                'Filter & Select',
            ],
            style=custom_style
        ).ask()
        
        return choice
    
    def _present_grouped_models(
        self,
        models: List[ModelInfo],
        group_by: str
    ) -> List[questionary.Choice]:
        """Present models grouped and return questionary choices."""
        grouped = self.provider_manager.group_models(models, group_by=group_by)
        
        choices = []
        for group_name, group_models in grouped.items():
            choices.append(questionary.Separator(f"─── {group_name} ───"))
            for model in group_models:
                choices.append(
                    questionary.Choice(
                        model.display_name,
                        value=model
                    )
                )
        
        return choices
    
    def _present_flat_models(self, models: List[ModelInfo]) -> List[questionary.Choice]:
        """Present all models in flat list."""
        choices = []
        for model in models:
            choices.append(
                questionary.Choice(
                    model.display_name,
                    value=model
                )
            )
        return choices
    
    def _filter_and_select_models(
        self,
        models: List[ModelInfo],
        provider: str
    ) -> List[ModelSpec]:
        """Advanced filtering options for model selection."""
        console.print("\n📋 Advanced Filtering Options\n")
        
        # Filter by family
        families = sorted(set(m.family for m in models))
        if families:
            selected_families = questionary.checkbox(
                'Filter by Model Family:',
                choices=families + ['All'],
                default=['All'],
                style=custom_style
            ).ask()
            
            if 'All' not in selected_families:
                models = [m for m in models if m.family in selected_families]
        
        # Filter by quantization
        quantizations = sorted(set(m.quantization for m in models if m.quantization))
        if quantizations:
            selected_quants = questionary.checkbox(
                'Filter by Quantization:',
                choices=quantizations + ['Full Precision', 'All'],
                default=['All'],
                style=custom_style
            ).ask()
            
            if 'All' not in selected_quants:
                filter_quants = [q for q in selected_quants if q != 'Full Precision']
                filter_full = 'Full Precision' in selected_quants
                models = [m for m in models if (m.quantization in filter_quants) or (filter_full and not m.quantization)]
        
        # Now show filtered models
        console.print(f"\n✓ {len(models)} models match filters\n")
        
        choices = self._present_flat_models(models)
        selected_models_info = questionary.checkbox(
            'Select models:',
            choices=choices,
            style=custom_style,
            validate=lambda x: len(x) > 0 or "Select at least one model"
        ).ask()
        
        if not selected_models_info:
            return []
        
        # Convert to ModelSpec
        selected_specs = []
        for model_info in selected_models_info:
            spec = ModelSpec(
                name=model_info.name,
                provider=provider,
                size_params=model_info.size_params,
                family=model_info.family,
                quantization=model_info.quantization,
                size_bytes=model_info.size_bytes,
                tags=[model_info.family] + ([model_info.quantization] if model_info.quantization else []),
            )
            selected_specs.append(spec)
        
        return selected_specs
    
    def multi_task_configuration(self) -> Optional[MultiTaskConfig]:
        """Configure multiple tasks for test set generation."""
        self.display_header()
        console.print(Panel("Step 1: Multi-Task Configuration", style="bold"))
        
        # Available task types
        available_tasks = [
            {'id': 'ari', 'name': 'ARI (Math Expressions)', 'description': 'Arithmetic expression evaluation'},
            {'id': 'gol', 'name': 'GoL (Game of Life)', 'description': 'Conway\'s Game of Life simulation'},
            {'id': 'c14', 'name': 'C14 (Cellular Automata)', 'description': 'General cellular automata'},
            {'id': 'shapes', 'name': 'Shapes (ASCII)', 'description': 'Visual spatial reasoning with ASCII shapes'},
            {'id': 'tracking', 'name': 'Tracking (Grape Test)', 'description': 'Object location tracking through action steps'},
            {'id': 'sally_anne', 'name': 'Sally-Anne (False Belief)', 'description': 'Theory of Mind false belief reasoning test'},
            {'id': 'linda', 'name': 'Linda (Pattern Recognition)', 'description': 'Statistical reasoning patterns'},
            {'id': 'grid_tasks', 'name': 'Grid Tasks (Table Reasoning)', 'description': 'Reading and reasoning about formatted tables with various data types'},
            {'id': 'carwash', 'name': 'Carwash Paradox', 'description': 'Walk or drive? Tests whether model tracks the goal of a trip'},
            {'id': 'inverted_cup', 'name': 'Inverted Cup', 'description': 'Sealed-top / open-bottom cup — how to use it? Tests spatial orientation reasoning'}
        ]
        
        # Select tasks to include
        selected_task_types = questionary.checkbox(
            'Select task types to include in test set:',
            choices=[questionary.Choice(
                f"{task['name']} - {task['description']}",
                value=task['id'],
                checked=(task['id'] == 'ari')  # Default to ARI
            ) for task in available_tasks],
            style=custom_style,
            validate=lambda x: len(x) > 0 or "Select at least one task type"
        ).ask()
        
        if not selected_task_types:
            return None
        
        # Configure each selected task
        task_configs = []
        
        # Ask if user wants to customize or use defaults
        customize = questionary.confirm(
            'Customize prompt styles and parameters? (No = use sensible defaults)',
            default=False,
            style=custom_style
        ).ask()
        
        for task_id in selected_task_types:
            task_info = next(t for t in available_tasks if t['id'] == task_id)
            if customize:
                task_config = self._configure_single_task(task_id, task_info['name'])
            else:
                task_config = self._configure_single_task_quick(task_id, task_info['name'])
            if task_config:
                task_configs.append(task_config)
        
        if not task_configs:
            return None
        
        # Global settings - simplified
        self.display_header()
        console.print(Panel("Global Settings", style="bold"))
        
        # Ask for advanced settings
        advanced = questionary.confirm(
            'Configure advanced settings? (No = use defaults: temp=0.1, lang=English, no thinking)',
            default=False,
            style=custom_style
        ).ask()
        
        if advanced:
            temperature = float(questionary.text(
                'Temperature (0.0-1.0):',
                default='0.1',
                validate=lambda x: x.replace('.', '', 1).isdigit() and 0 <= float(x) <= 1,
                style=custom_style
            ).ask())
            
            language = questionary.select(
                'Language:',
                choices=['English', 'Spanish', 'French', 'German', 'Chinese', 'Ukrainian'],
                default='English',
                style=custom_style
            ).ask()
            lang_map = {'English': 'en', 'Spanish': 'es', 'French': 'fr', 'German': 'de', 'Chinese': 'zh', 'Ukrainian': 'uk'}
            language = lang_map[language]
            
            thinking = questionary.confirm(
                'Enable thinking/reasoning mode?',
                default=False,
                style=custom_style
            ).ask()
        else:
            temperature = 0.1
            language = 'en'
            thinking = False
        
        # Test set name
        name = questionary.text(
            'Test set name (optional):',
            default=f"multi_task_{'-'.join(selected_task_types)}",
            style=custom_style
        ).ask()
        
        # Output directory - ask early since it's needed for all stages
        output_dir = questionary.text(
            'Output directory (all files will be saved here):',
            default='results/runs',
            style=custom_style
        ).ask()
        
        description = f"Multi-task: {', '.join([t.task_name for t in task_configs])}"
        
        return MultiTaskConfig(
            name=name,
            description=description,
            tasks=task_configs,
            output_dir=output_dir,
            temperature=temperature,
            language=language,
            thinking_enabled=thinking
        )
    
    def _configure_single_task_quick(self, task_id: str, task_name: str) -> Optional[TaskConfiguration]:
        """Quick configuration with defaults."""
        # Default batch size
        batch_size = 30
        
        # Default prompts: minimal + analytical
        prompts = PromptSpec(user_styles=['minimal'], system_styles=['analytical'])
        
        # Default task-specific parameters
        parameters = {}
        if task_id == 'ari':
            parameters = {'complexity': [2], 'target_values': [1, 2, 3], 'mode': 'expression'}
        elif task_id == 'gol':
            parameters = {'difficulty': 'EASY', 'density': 0.3}
        elif task_id == 'c14':
            parameters = {'rule_numbers': [90], 'width': 16, 'steps': 1, 'boundary_condition': 'wrap'}
        elif task_id == 'shapes':
            parameters = {'width_range': (3, 15), 'height_range': (2, 5), 'symbols': ['*', '#'], 'spacing': [' '], 'coordinate_labels': True, 'filled': [True, False], 'question_type': 'dimensions'}
        elif task_id == 'tracking':
            parameters = {'objects': ['grape', 'marble', 'keys'], 'containers': ['cup', 'bowl', 'mug'], 'distractor_count': [0, 1, 2], 'post_inversion_moves': [0, 1, 2]}
        elif task_id == 'sally_anne':
            parameters = {'use_random_pairs': True, 'objects': ['marble', 'ball', 'toy'], 'containers': [('basket', 'box'), ('drawer', 'cupboard')], 'distractor_count': 0, 'leave_activities': ['goes for a walk', 'goes outside', 'leaves the room'], 'include_observer': False}
        elif task_id == 'carwash':
            parameters = {
                'distances': ['50m', '100m', '200m', 'corner', '2min_walk'],
                'count': 50,
            }
        elif task_id == 'inverted_cup':
            parameters = {
                'description_styles': [
                    'sealed_top_open_bottom', 'lid_top_hole_bottom', 'upside_down_explicit',
                    'rim_at_bottom', 'inverted_normal', 'mouth_down', 'closed_on_top'
                ],
                'count': 50,
            }
        elif task_id == 'linda':
            parameters = {'num_options': 8, 'personas_per_config': 5}
        elif task_id == 'grid_tasks':
            parameters = {
                'min_rows': 2,
                'max_rows': 10,
                'min_cols': 2,
                'max_cols': 6,
                'data_types': ['sales', 'hr', 'grades'],
                'question_types': ['cell_lookup', 'row_sum', 'column_count', 'max_min'],
                'table_style': 'unicode',
                'numeric_tolerance': 0.1
            }
        
        return TaskConfiguration(
            task_type=task_id,
            task_name=task_name,
            batch_size=batch_size,
            prompts=prompts,
            parameters=parameters
        )
    
    def _configure_single_task(self, task_id: str, task_name: str) -> Optional[TaskConfiguration]:
        """Configure a single task type."""
        self.display_header()
        console.print(Panel(f"Configure: {task_name}", style="bold yellow"))
        
        # Batch size for this task
        batch_size = questionary.text(
            f'Number of {task_name} test cases:',
            default='50',
            validate=lambda x: x.isdigit() and int(x) > 0,
            style=custom_style
        ).ask()
        batch_size = int(batch_size)
        
        # Prompt configuration for this task
        console.print(f"\n[cyan]Prompt Configuration for {task_name}[/cyan]")
        prompts = self._configure_task_prompts()
        
        # Task-specific parameters
        parameters = self._configure_task_specific_params(task_id)
        
        return TaskConfiguration(
            task_type=task_id,
            task_name=task_name,
            batch_size=batch_size,
            prompts=prompts,
            parameters=parameters
        )
    
    def _configure_task_prompts(self) -> PromptSpec:
        """Configure prompts for a single task."""
        # Available prompt styles
        user_style_choices = ['minimal', 'casual', 'linguistic', 'examples', 'rules_math']
        system_style_choices = ['analytical', 'casual', 'adversarial', 'none']
        
        # User prompt styles
        user_styles = questionary.checkbox(
            'User Prompt Styles:',
            choices=[
                questionary.Choice(style, checked=(style in ['minimal', 'casual']))
                for style in user_style_choices
            ],
            style=custom_style
        ).ask()
        
        # System prompt styles
        system_styles = questionary.checkbox(
            'System Prompt Styles:',
            choices=[
                questionary.Choice(style, checked=(style in ['analytical']))
                for style in system_style_choices
            ],
            style=custom_style
        ).ask()
        
        # Validate selections
        if not user_styles:
            user_styles = ['minimal']
        if not system_styles:
            system_styles = ['analytical']
        
        console.print(f"  → {len(user_styles) * len(system_styles)} prompt combinations")
        
        return PromptSpec(user_styles=user_styles, system_styles=system_styles)
    
    def _configure_task_specific_params(self, task_type: str) -> Dict[str, Any]:
        """Configure task-specific parameters."""
        config = {}
        
        if task_type == 'ari':
            # ARI-specific config
            console.print("\n[cyan]Complexity:[/cyan] How deeply nested the expression can be (1-5)")
            console.print("[cyan]Target Values:[/cyan] What number(s) the expression should evaluate to\n")
            
            complexity = questionary.checkbox(
                'Complexity Levels (1=simple, 5=deeply nested):',
                choices=[
                    questionary.Choice('1', checked=False),
                    questionary.Choice('2', checked=True),
                    questionary.Choice('3', checked=False),
                    questionary.Choice('4', checked=False),
                    questionary.Choice('5', checked=False),
                ],
                style=custom_style
            ).ask()
            config['complexity'] = [int(c) for c in (complexity or ['2'])]
            
            target_values_input = questionary.text(
                'Target Values (comma-separated numbers, e.g., "0,1,2,5,10"):',
                default='1,2,3',
                style=custom_style
            ).ask()
            config['target_values'] = [int(v.strip()) for v in target_values_input.split(',')]
            
            mode = questionary.select(
                'Expression Mode:',
                choices=['expression', 'equation'],
                default='expression',
                style=custom_style
            ).ask()
            config['mode'] = mode
            
        elif task_type == 'gol':
            # GoL-specific config
            difficulty = questionary.select(
                'Difficulty Level:',
                choices=[
                    questionary.Choice('EASY (3x3 grid)', value='EASY'),
                    questionary.Choice('MEDIUM (5x5 grid)', value='MEDIUM'),
                    questionary.Choice('HARD (8x8 grid)', value='HARD'),
                ],
                default='EASY',
                style=custom_style
            ).ask()
            config['difficulty'] = difficulty
            
            density = questionary.text(
                'Grid density (0.0-1.0):',
                default='0.3',
                validate=lambda x: x.replace('.', '', 1).isdigit() and 0 <= float(x) <= 1,
                style=custom_style
            ).ask()
            config['density'] = float(density)
            
        elif task_type in ('c14'):
            # C14-specific config
            difficulties = questionary.checkbox(
                'Difficulty Levels:',
                choices=[
                    questionary.Choice('1', checked=True),
                    questionary.Choice('2'),
                    questionary.Choice('3'),
                ],
                style=custom_style
            ).ask()
            config['difficulties'] = [int(d) for d in (difficulties or ['1'])]
            
        elif task_type == 'linda':
            # Linda Conjunction Fallacy specific configuration
            console.print("\n🧠 [bold blue]Configuring Linda Conjunction Fallacy Task[/bold blue]")
            
            # Number of ranking options
            num_options = questionary.select(
                'Number of ranking options:',
                choices=[
                    questionary.Choice(title='Six options', value='6'),
                    questionary.Choice(title='Eight options (recommended)', value='8'),
                    questionary.Choice(title='Ten options', value='10'),
                    questionary.Choice(title='Twelve options', value='12'),
                ],
                default='8',
                style=custom_style
            ).ask()
            config['num_options'] = int(num_options)
            
            # Culture filter
            culture_filter = questionary.select(
                'Cultural focus (personas will be filtered by language compatibility):',
                choices=[
                    questionary.Choice(title='All compatible cultures (recommended)', value=None),
                    questionary.Choice(title='Western cultures', value='western'),
                    questionary.Choice(title='East Asian cultures', value='east_asian'),
                    questionary.Choice(title='South Asian cultures', value='south_asian'),
                    questionary.Choice(title='African cultures', value='african'),
                    questionary.Choice(title='Middle Eastern cultures', value='middle_eastern'),
                    questionary.Choice(title='Latin American cultures', value='latin_american'),
                    questionary.Choice(title='European cultures', value='european'),
                ],
                default=None,
                style=custom_style
            ).ask()
            if culture_filter:
                config['culture_filter'] = culture_filter
            
            # Personas per prompt configuration
            personas_per_config = questionary.text(
                'Number of personas per prompt configuration:',
                default='5',
                validate=lambda x: x.isdigit() and int(x) > 0,
                style=custom_style
            ).ask()
            config['personas_per_config'] = int(personas_per_config)
        
        elif task_type == 'shapes':
            # ASCII Shapes specific configuration
            console.print("\n🔲 [bold blue]Configuring ASCII Shapes Task[/bold blue]")
            
            # Width range
            width_min = questionary.text(
                'Minimum width:',
                default='3',
                validate=lambda x: x.isdigit() and int(x) > 0,
                style=custom_style
            ).ask()
            width_max = questionary.text(
                'Maximum width:',
                default='20',
                validate=lambda x: x.isdigit() and int(x) >= int(width_min),
                style=custom_style
            ).ask()
            config['width_range'] = (int(width_min), int(width_max))
            
            # Height range
            height_min = questionary.text(
                'Minimum height:',
                default='2',
                validate=lambda x: x.isdigit() and int(x) > 0,
                style=custom_style
            ).ask()
            height_max = questionary.text(
                'Maximum height:',
                default='7',
                validate=lambda x: x.isdigit() and int(x) >= int(height_min),
                style=custom_style
            ).ask()
            config['height_range'] = (int(height_min), int(height_max))
            
            # Symbols
            symbols_input = questionary.text(
                'Symbols to use (space-separated, e.g., "* # X █ 🟦"):',
                default='* # X █',
                style=custom_style
            ).ask()
            config['symbols'] = symbols_input.split()
            
            # Spacing
            spacing_input = questionary.select(
                'Spacing between symbols:',
                choices=[
                    questionary.Choice(title='Space (default)', value=' '),
                    questionary.Choice(title='None (compact)', value=''),
                    questionary.Choice(title='Underscore', value='_'),
                ],
                default=' ',
                style=custom_style
            ).ask()
            config['spacing'] = [spacing_input]
            
            # Coordinate labels
            coordinate_labels = questionary.confirm(
                'Include coordinate labels (numbered axes)?',
                default=True,
                style=custom_style
            ).ask()
            config['coordinate_labels'] = coordinate_labels
            
            # Filled options
            filled_options = questionary.checkbox(
                'Shape fill options:',
                choices=[
                    questionary.Choice(title='Filled (solid)', value='filled', checked=True),
                    questionary.Choice(title='Hollow (border only)', value='hollow', checked=True),
                ],
                style=custom_style,
                validate=lambda x: len(x) > 0 or "Select at least one fill option"
            ).ask()
            config['filled'] = [opt == 'filled' for opt in filled_options]
            
            # Question type
            question_type = questionary.select(
                'Question type to test:',
                choices=[
                    questionary.Choice(title='Dimensions (What is the width and height?)', value='dimensions'),
                    questionary.Choice(title='Count (How many symbols?)', value='count'),
                    questionary.Choice(title='Position (Is there a symbol at x,y?)', value='position'),
                ],
                default='dimensions',
                style=custom_style
            ).ask()
            config['question_type'] = question_type
        
        elif task_type == 'tracking':
            # Object Tracking (Grape Test) specific configuration
            console.print("\n🍇 [bold blue]Configuring Object Tracking (Grape Test) Task[/bold blue]")
            console.print("[dim]Tests LLM's ability to track objects through inversions and movements[/dim]\n")
            
            # Objects to track
            console.print("[cyan]Objects:[/cyan] Items to be tracked through the scenario")
            objects_input = questionary.text(
                'Objects to track (comma-separated):',
                default='grape, marble, keys, coin, ring',
                style=custom_style
            ).ask()
            config['objects'] = [obj.strip() for obj in objects_input.split(',')]
            
            # Containers
            console.print("\n[cyan]Containers:[/cyan] What holds the objects initially")
            containers_input = questionary.text(
                'Containers (comma-separated):',
                default='cup, bowl, mug, bucket, box',
                style=custom_style
            ).ask()
            config['containers'] = [cont.strip() for cont in containers_input.split(',')]
            
            # Distractor counts
            console.print("\n[cyan]Distractors:[/cyan] Irrelevant actions that increase difficulty")
            distractor_options = questionary.checkbox(
                'Number of distractor actions:',
                choices=[
                    questionary.Choice(title='0 distractors (easiest)', value='0', checked=True),
                    questionary.Choice(title='1 distractor', value='1', checked=True),
                    questionary.Choice(title='2 distractors', value='2', checked=True),
                    questionary.Choice(title='3 distractors', value='3', checked=False),
                    questionary.Choice(title='4+ distractors (nightmare)', value='4', checked=False),
                ],
                style=custom_style,
                validate=lambda x: len(x) > 0 or "Select at least one distractor count"
            ).ask()
            config['distractor_count'] = [int(d) for d in distractor_options]
            
            # Post-inversion moves
            console.print("\n[cyan]Post-Inversion Moves:[/cyan] Container movements after the object falls out")
            console.print("[dim]This is the critical test: does the model know the object stays behind?[/dim]")
            post_inv_options = questionary.checkbox(
                'Number of container moves after inversion:',
                choices=[
                    questionary.Choice(title='0 moves (container stays)', value='0', checked=True),
                    questionary.Choice(title='1 move', value='1', checked=True),
                    questionary.Choice(title='2 moves', value='2', checked=True),
                    questionary.Choice(title='3+ moves', value='3', checked=False),
                ],
                style=custom_style,
                validate=lambda x: len(x) > 0 or "Select at least one post-inversion move count"
            ).ask()
            config['post_inversion_moves'] = [int(m) for m in post_inv_options]
            
            # Optional: Advanced settings
            advanced = questionary.confirm(
                '\nConfigure advanced settings? (locations, distractor types)',
                default=False,
                style=custom_style
            ).ask()
            
            if advanced:
                # Initial locations
                console.print("\n[cyan]Initial Locations:[/cyan] Where objects are initially placed")
                locations_input = questionary.text(
                    'Initial locations (comma-separated):',
                    default='counter, table, shelf, desk, dresser, nightstand',
                    style=custom_style
                ).ask()
                config['location_initial'] = [loc.strip() for loc in locations_input.split(',')]
                
                # Distractor types
                console.print("\n[cyan]Distractor Types:[/cyan] Categories of irrelevant actions")
                distractor_types = questionary.checkbox(
                    'Distractor action types:',
                    choices=[
                        questionary.Choice(title='Irrelevant (unrelated actions)', value='irrelevant', checked=True),
                        questionary.Choice(title='Spatial (location-based)', value='spatial', checked=True),
                        questionary.Choice(title='Temporal (time-based)', value='temporal', checked=True),
                    ],
                    style=custom_style
                ).ask()
                if distractor_types:
                    config['distractor_types'] = distractor_types
            
            console.print(f"\n[green]✓ Configuration complete![/green]")
            console.print(f"  Objects: {len(config['objects'])} types")
            console.print(f"  Containers: {len(config['containers'])} types")
            console.print(f"  Distractor levels: {config['distractor_count']}")
            console.print(f"  Post-inversion moves: {config['post_inversion_moves']}")
        
        elif task_type == 'sally_anne':
            # Sally-Anne False Belief Test specific configuration
            console.print("\n🧠 [bold blue]Configuring Sally-Anne False Belief Test Task[/bold blue]")
            console.print("[dim]Tests Theory of Mind: understanding that others can hold false beliefs[/dim]\n")
            
            # Subject pairs configuration
            console.print("[cyan]Subject Pairs:[/cyan] Characters in the scenario")
            use_random = questionary.confirm(
                'Use random name pairs? (Names library generates diverse names with proper pronouns)',
                default=True,
                style=custom_style
            ).ask()
            
            if use_random:
                config['use_random_pairs'] = True
                console.print("[green]✓ Will use random names from 'names' library[/green]")
            else:
                config['use_random_pairs'] = False
                console.print("\n[yellow]Manual subject pairs format: name1,gender1,name2,gender2[/yellow]")
                console.print("[dim]Gender options: male, female (for proper pronoun usage)[/dim]")
                pairs_input = questionary.text(
                    'Subject pairs (semicolon-separated, e.g., "Sally,female,Anne,female;Alice,female,Bob,male"):',
                    default='Sally,female,Anne,female',
                    style=custom_style
                ).ask()
                
                # Parse subject pairs
                pairs = []
                for pair_str in pairs_input.split(';'):
                    parts = [p.strip() for p in pair_str.split(',')]
                    if len(parts) == 4:
                        pairs.append(tuple(parts))
                config['subject_pairs'] = pairs
                console.print(f"[green]✓ Configured {len(pairs)} subject pair(s)[/green]")
            
            # Objects to be moved
            console.print("\n[cyan]Objects:[/cyan] Items to be moved in the scenario")
            objects_input = questionary.text(
                'Objects (comma-separated):',
                default='marble, ball, toy, book, keys',
                style=custom_style
            ).ask()
            config['objects'] = [obj.strip() for obj in objects_input.split(',')]
            
            # Container pairs
            console.print("\n[cyan]Container Pairs:[/cyan] (initial_container, moved_container)")
            console.print("[dim]Format: basket:box means object starts in basket, moves to box[/dim]")
            containers_input = questionary.text(
                'Container pairs (semicolon-separated, e.g., "basket:box;drawer:cupboard"):',
                default='basket:box;drawer:cupboard;bag:pocket',
                style=custom_style
            ).ask()
            
            # Parse container pairs
            container_pairs = []
            for pair_str in containers_input.split(';'):
                parts = [p.strip() for p in pair_str.split(':')]
                if len(parts) == 2:
                    container_pairs.append(tuple(parts))
            config['containers'] = container_pairs
            
            # Leave activities (what Subject A does when leaving)
            console.print("\n[cyan]Leave Activities:[/cyan] What Subject A does when leaving the scene")
            activities_input = questionary.text(
                'Leave activities (comma-separated):',
                default='goes for a walk, goes outside, leaves the room, goes to the kitchen',
                style=custom_style
            ).ask()
            config['leave_activities'] = [act.strip() for act in activities_input.split(',')]
            
            # Distractor count
            console.print("\n[cyan]Distractors:[/cyan] Additional scene elements (increases difficulty)")
            distractor_count = questionary.select(
                'Number of distractor elements:',
                choices=[
                    questionary.Choice(title='0 distractors (clean scenario)', value='0'),
                    questionary.Choice(title='1 distractor', value='1'),
                    questionary.Choice(title='2 distractors', value='2'),
                    questionary.Choice(title='3 distractors', value='3'),
                ],
                default='0',
                style=custom_style
            ).ask()
            config['distractor_count'] = int(distractor_count)
            
            # Observer variant
            console.print("\n[cyan]Observer Variant:[/cyan] Include third-person witness?")
            include_observer = questionary.confirm(
                'Include an observer who watches both placement and transfer?',
                default=False,
                style=custom_style
            ).ask()
            config['include_observer'] = include_observer
            
            console.print(f"\n[green]✓ Configuration complete![/green]")
            console.print(f"  Subject pairs: {'Random (names library)' if config.get('use_random_pairs') else f"{len(config.get('subject_pairs', []))} defined"}")
            console.print(f"  Objects: {len(config['objects'])} types")
            console.print(f"  Container pairs: {len(config['containers'])}")
            console.print(f"  Leave activities: {len(config['leave_activities'])}")
            console.print(f"  Distractors: {config['distractor_count']}")
            console.print(f"  Observer: {'Yes' if config['include_observer'] else 'No'}")
        
        elif task_type == 'grid_tasks':
            # Grid Tasks (Table Reasoning) specific configuration
            console.print("\n📊 [bold blue]Configuring Grid Tasks (Table Reasoning)[/bold blue]")
            console.print("[dim]Tests ability to read and reason about formatted tables with various data types[/dim]\n")
            
            # Table size ranges
            console.print("[cyan]Table Size Ranges:[/cyan]")
            min_rows = questionary.text(
                'Minimum rows:',
                default='2',
                validate=lambda x: x.isdigit() and int(x) >= 1,
                style=custom_style
            ).ask()
            max_rows = questionary.text(
                'Maximum rows:',
                default='10',
                validate=lambda x: x.isdigit() and int(x) >= int(min_rows),
                style=custom_style
            ).ask()
            config['min_rows'] = int(min_rows)
            config['max_rows'] = int(max_rows)
            
            min_cols = questionary.text(
                'Minimum columns:',
                default='2',
                validate=lambda x: x.isdigit() and int(x) >= 1,
                style=custom_style
            ).ask()
            max_cols = questionary.text(
                'Maximum columns:',
                default='6',
                validate=lambda x: x.isdigit() and int(x) >= int(min_cols),
                style=custom_style
            ).ask()
            config['min_cols'] = int(min_cols)
            config['max_cols'] = int(max_cols)
            
            # Data types
            console.print("\n[cyan]Data Types:[/cyan] Types of fake data to generate")
            data_types = questionary.checkbox(
                'Select data types:',
                choices=[
                    questionary.Choice(title='Sales Reports (products, regions, revenues)', value='sales', checked=True),
                    questionary.Choice(title='HR Data (employees, departments, salaries)', value='hr', checked=True),
                    questionary.Choice(title='Student Grades (students, subjects, scores)', value='grades', checked=True),
                    questionary.Choice(title='Inventory (items, quantities, prices)', value='inventory', checked=False),
                ],
                style=custom_style,
                validate=lambda x: len(x) > 0 or "Select at least one data type"
            ).ask()
            config['data_types'] = data_types
            
            # Question types
            console.print("\n[cyan]Question Types:[/cyan] Types of questions to ask about the data")
            question_types = questionary.checkbox(
                'Select question types:',
                choices=[
                    questionary.Choice(title='Cell Lookup (What is X\'s Y?)', value='cell_lookup', checked=True),
                    questionary.Choice(title='Row Sum (What is the total?)', value='row_sum', checked=True),
                    questionary.Choice(title='Column Count (How many X?)', value='column_count', checked=True),
                    questionary.Choice(title='Filter Count (How many X > Y?)', value='filter_count', checked=False),
                    questionary.Choice(title='Max/Min (Who has highest/lowest?)', value='max_min', checked=True),
                ],
                style=custom_style,
                validate=lambda x: len(x) > 0 or "Select at least one question type"
            ).ask()
            config['question_types'] = question_types
            
            # Table style
            console.print("\n[cyan]Table Style:[/cyan] Visual formatting for tables")
            table_style = questionary.select(
                'Table rendering style:',
                choices=[
                    questionary.Choice(title='Unicode Box Drawing (╔═╗ - default)', value='unicode'),
                    questionary.Choice(title='Unicode Single Line (┌─┐)', value='unicode_single'),
                    questionary.Choice(title='ASCII MySQL Style (+--+)', value='mysql'),
                    questionary.Choice(title='GitHub Markdown (|---|)', value='gfm'),
                    questionary.Choice(title='Compact (minimal borders)', value='compact'),
                    questionary.Choice(title='Plain (no borders)', value='plain'),
                ],
                default='unicode',
                style=custom_style
            ).ask()
            config['table_style'] = table_style
            
            # Numeric tolerance
            console.print("\n[cyan]Numeric Tolerance:[/cyan] Acceptable difference for numeric answers")
            numeric_tolerance = questionary.text(
                'Numeric tolerance (e.g., 0.1 for ±0.1 difference):',
                default='0.1',
                validate=lambda x: x.replace('.', '', 1).isdigit() and float(x) >= 0,
                style=custom_style
            ).ask()
            config['numeric_tolerance'] = float(numeric_tolerance)
            
            console.print(f"\n[green]✓ Configuration complete![/green]")
            console.print(f"  Table size: {config['min_rows']}-{config['max_rows']} rows, {config['min_cols']}-{config['max_cols']} cols")
            console.print(f"  Data types: {', '.join(config['data_types'])}")
            console.print(f"  Question types: {', '.join(config['question_types'])}")
            console.print(f"  Table style: {config['table_style']}")
            console.print(f"  Numeric tolerance: ±{config['numeric_tolerance']}")
        
        return config
    
    def generate_test_set(self, multi_task_config: MultiTaskConfig) -> Optional[str]:
        """Generate multi-task test set (Stage 1)."""
        self.display_header()
        console.print(Panel("Step 2: Generate Test Set (Stage 1)", style="bold green"))
        
        # Show summary
        summary_table = Table(title="Test Set Summary", show_header=True)
        summary_table.add_column("Task Type", style="cyan")
        summary_table.add_column("Test Cases", style="green")
        summary_table.add_column("Prompt Configs", style="yellow")
        summary_table.add_column("Total", style="magenta")
        
        for task in multi_task_config.tasks:
            summary_table.add_row(
                task.task_name,
                str(task.batch_size),
                str(task.prompts.config_count()),
                str(task.total_tests)
            )
        
        summary_table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            "",
            f"[bold]{multi_task_config.total_tests}[/bold]"
        )
        
        console.print(summary_table)
        console.print(f"\n[cyan]Test Set: {multi_task_config.name}[/cyan]")
        console.print(f"[dim]{multi_task_config.description}[/dim]")
        
        if not questionary.confirm(
            'Generate this test set?',
            default=True,
            style=custom_style
        ).ask():
            return None
        
        # Create YAML config for multi-task test set
        yaml_config_path = self._create_multi_task_yaml_config(multi_task_config)
        console.print(f"\n[cyan]→ Generated YAML config: {yaml_config_path}[/cyan]")
        
        # Generate test set using Stage 1
        console.print("[cyan]→ Generating test set...[/cyan]")
        
        import subprocess
        import sys
        
        generate_cmd = [
            sys.executable, "src/stages/generate_testset.py",
            yaml_config_path,
            "--output-dir", multi_task_config.output_dir,
            "--validate"
        ]
        
        result = subprocess.run(generate_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[red]✗ Test set generation failed: {result.stderr}[/red]")
            return None
        
        # Extract testset path from output
        testset_path = _extract_testset_path(result.stdout)
        if not testset_path:
            console.print("[red]✗ Could not find generated test set path[/red]")
            return None
        
        console.print(f"[green]✓ Test set generated: {testset_path}[/green]")
        return testset_path
    
    def execution_configuration(self) -> dict:
        """Configure execution and output options (Step 4)."""
        self.display_header()
        console.print(Panel("Step 4: Execution Configuration", style="bold"))
        
        # Generate charts
        generate_charts = questionary.confirm(
            'Generate analysis and visualizations after execution?',
            default=True,
            style=custom_style
        ).ask()
        
        # Verbosity
        verbosity = questionary.select(
            'Verbosity level:',
            choices=['quiet', 'normal', 'verbose'],
            default='normal',
            style=custom_style
        ).ask()
        
        return {
            'generate_charts': generate_charts,
            'verbosity': verbosity,
        }
    
    def task_specific_config(self, task_type: str) -> Dict:
        """Configure task-specific parameters."""
        self.display_header()
        console.print(Panel(f"Step 5: Configure {task_type.upper()} Parameters", style="bold"))
        
        config = {}
        
        if task_type == 'ari':
            # ARI-specific config
            difficulties = questionary.checkbox(
                'Difficulty Levels:',
                choices=[
                    questionary.Choice('1', checked=True),
                    questionary.Choice('2'),
                    questionary.Choice('3'),
                ],
                style=custom_style
            ).ask()
            config['difficulties'] = [int(d) for d in (difficulties or ['1'])]
            
            mode = questionary.select(
                'Expression Mode:',
                choices=['expression', 'equation'],
                default='expression',
                style=custom_style
            ).ask()
            config['mode'] = mode
            
            random_target = questionary.confirm(
                'Random target values?',
                default=False,
                style=custom_style
            ).ask()
            config['random_target'] = random_target
            
            # Target values input
            if not random_target:
                target_values_input = questionary.text(
                    'Target values (comma-separated, e.g., "10,20,50"):',
                    default='10,20,50',
                    style=custom_style
                ).ask()
                try:
                    config['target_values'] = [int(v.strip()) for v in target_values_input.split(',')]
                except ValueError:
                    console.print("[yellow]Invalid target values, using defaults[/yellow]")
                    config['target_values'] = [10, 20, 50]
            else:
                config['target_values'] = []  # Empty list signals random generation
        
        elif task_type == 'gol':
            # GoL-specific config
            difficulty = questionary.select(
                'Difficulty Level:',
                choices=[
                    questionary.Choice('EASY (3x3 grid)', value='EASY'),
                    questionary.Choice('MEDIUM (5x5 grid)', value='MEDIUM'),
                    questionary.Choice('HARD (8x8 grid)', value='HARD'),
                    questionary.Choice('NIGHTMARE (10x10 grid)', value='NIGHTMARE'),
                ],
                default='EASY',
                style=custom_style
            ).ask()
            config['difficulty'] = difficulty
            
            density = questionary.text(
                'Grid density (0.0-1.0):',
                default='0.3',
                validate=lambda x: x.replace('.', '', 1).isdigit() and 0 <= float(x) <= 1,
                style=custom_style
            ).ask()
            config['density'] = float(density)
            
            iterations = questionary.text(
                'Iterations:',
                default='1',
                validate=lambda x: x.isdigit() and int(x) > 0,
                style=custom_style
            ).ask()
            config['iterations'] = int(iterations)
        
        elif task_type == 'c14':
            # C14 (1D Cellular Automata) specific config
            console.print("\n🔢 [bold blue]Configuring 1D Cellular Automata (Wolfram Rules)[/bold blue]")
            
            # Rule difficulty selection
            rule_choice = questionary.select(
                'Select rule difficulty:',
                choices=[
                    questionary.Choice(title='Easy (trivial rules: 0, 51, 204, 255)', value='easy'),
                    questionary.Choice(title='Medium (fractal rules: 90, 150, 184)', value='medium'),
                    questionary.Choice(title='Hard (chaotic rules: 30, 110, 45)', value='hard'),
                    questionary.Choice(title='Custom rule numbers', value='custom'),
                ],
                default='medium',
                style=custom_style
            ).ask()
            
            if rule_choice == 'custom':
                rules_input = questionary.text(
                    'Enter rule numbers (0-255, comma-separated):',
                    default='30,90,110',
                    style=custom_style
                ).ask()
                config['rule_numbers'] = [int(r.strip()) for r in rules_input.split(',')]
            else:
                rule_map = {
                    'easy': [0, 51, 204, 255],
                    'medium': [90, 150, 184],
                    'hard': [30, 110, 45]
                }
                config['rule_numbers'] = rule_map[rule_choice]
            
            # Width configuration
            width = questionary.text(
                'Grid width (number of cells):',
                default='16',
                validate=lambda x: x.isdigit() and int(x) >= 3,
                style=custom_style
            ).ask()
            config['width'] = int(width)
            
            # Steps
            steps = questionary.text(
                'Number of steps to predict:',
                default='1',
                validate=lambda x: x.isdigit() and int(x) > 0,
                style=custom_style
            ).ask()
            config['steps'] = int(steps)
            
            # Boundary condition
            boundary = questionary.select(
                'Boundary condition:',
                choices=[
                    questionary.Choice(title='Wrap (periodic)', value='wrap'),
                    questionary.Choice(title='Dead (fixed 0s at edges)', value='dead'),
                    questionary.Choice(title='Alive (fixed 1s at edges)', value='alive'),
                ],
                default='wrap',
                style=custom_style
            ).ask()
            config['boundary_condition'] = boundary
            
            # Initial pattern
            initial_pattern = questionary.select(
                'Initial state pattern:',
                choices=['random', 'centered_single', 'centered_pair', 'centered_triplet'],
                default='random',
                style=custom_style
            ).ask()
            config['initial_pattern'] = initial_pattern
            
            if initial_pattern == 'random':
                density = questionary.text(
                    'Random density (0.0-1.0):',
                    default='0.5',
                    validate=lambda x: x.replace('.', '', 1).isdigit() and 0 <= float(x) <= 1,
                    style=custom_style
                ).ask()
                config['density'] = float(density)
        
        elif task_type == 'linda':
            # Linda Conjunction Fallacy configuration
            console.print("\n🧠 [bold blue]Configuring Linda Conjunction Fallacy Task[/bold blue]")
            
            # Number of ranking options
            num_options = questionary.select(
                'Number of ranking options:',
                choices=[
                    questionary.Choice(title='Six options', value=6),
                    questionary.Choice(title='Eight options (recommended)', value=8),
                    questionary.Choice(title='Ten options', value=10),
                    questionary.Choice(title='Twelve options', value=12),
                ],
                default=8,
                style=custom_style
            ).ask()
            config['num_options'] = num_options
            
            # Culture filter
            culture_filter = questionary.select(
                'Cultural focus:',
                choices=[
                    questionary.Choice(title='All compatible cultures (recommended)', value=None),
                    questionary.Choice(title='Western cultures', value='western'),
                    questionary.Choice(title='East Asian cultures', value='east_asian'),
                    questionary.Choice(title='South Asian cultures', value='south_asian'),
                    questionary.Choice(title='African cultures', value='african'),
                    questionary.Choice(title='Middle Eastern cultures', value='middle_eastern'),
                    questionary.Choice(title='Latin American cultures', value='latin_american'),
                    questionary.Choice(title='European cultures', value='european'),
                ],
                default=None,
                style=custom_style
            ).ask()
            if culture_filter:
                config['culture_filter'] = culture_filter
            
            # Personas per prompt configuration
            personas_per_config = questionary.text(
                'Number of personas per prompt configuration:',
                default='5',
                validate=lambda x: x.isdigit() and int(x) > 0,
                style=custom_style
            ).ask()
            config['personas_per_config'] = int(personas_per_config)
        
        return config
    
    def output_configuration(self) -> dict:
        """Configure reporting options."""
        self.display_header()
        console.print(Panel("Step 6: Reporting Configuration", style="bold"))
        
        # Generate charts
        generate_charts = questionary.confirm(
            'Generate visualizations?',
            default=True,
            style=custom_style
        ).ask()
        
        # Report formats - use questionary.Choice with checked parameter
        report_format_choices = ['markdown', 'html', 'json']
        report_formats = questionary.checkbox(
            'Report formats:',
            choices=[
                questionary.Choice(fmt, checked=(fmt in ['markdown', 'json']))
                for fmt in report_format_choices
            ],
            style=custom_style
        ).ask()
        
        # Validate selections
        if not report_formats:
            report_formats = ['markdown', 'json']
        
        # Verbosity
        verbosity = questionary.select(
            'Verbosity level:',
            choices=['quiet', 'normal', 'verbose', 'debug'],
            default='normal',
            style=custom_style
        ).ask()
        
        return {
            'generate_charts': generate_charts,
            'report_formats': report_formats,
            'verbosity': verbosity,
        }
    
    def execution_confirmation_screen(self, config: BenchmarkConfig, multi_task_config: MultiTaskConfig) -> bool:
        """Final confirmation before executing tests on pre-generated test set."""
        self.display_header()
        console.print(Panel("Review Execution Configuration", style="bold green"))
        
        # Create detailed summary table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="green")
        
        table.add_row("Test Set", multi_task_config.name)
        table.add_row("Description", multi_task_config.description or "N/A")
        table.add_row("Task Types", f"{multi_task_config.total_task_types} types")
        
        # List tasks
        for task in multi_task_config.tasks:
            table.add_row("  •", f"{task.task_name}: {task.total_tests} tests")
        
        table.add_row("Total Tests", str(multi_task_config.total_tests))
        table.add_row("Test Set File", Path(self.generated_testset_path).name if self.generated_testset_path else "N/A")
        table.add_row("", "")  # Spacer
        
        # Model information
        table.add_row("Provider", config.models[0].provider if config.models else "N/A")
        table.add_row("Models", f"{len(config.models)} selected")
        
        # List models
        for model in config.models[:3]:  # Show first 3
            table.add_row("  •", model.display_name)
        if len(config.models) > 3:
            table.add_row("  •", f"... and {len(config.models) - 3} more")
        
        table.add_row("Output Dir", config.output_dir)
        table.add_row("Analysis", "Enabled" if config.generate_charts else "Disabled")
        
        # Estimate execution time
        estimated_minutes = len(config.models) * multi_task_config.total_tests * 0.5  # Rough estimate
        table.add_row("Est. Runtime", f"{estimated_minutes:.0f} minutes")
        
        console.print(table)
        console.print()
        
        confirm = questionary.confirm(
            '⚙️  Execute tests on pre-generated test set?',
            default=True,
            style=custom_style
        ).ask()
        
        return confirm
    
    def create_new_benchmark(self) -> Optional[BenchmarkConfig]:
        """Guided setup for new 3-stage benchmark workflow."""
        
        # Step 1: Multi-Task Configuration
        multi_task_config = self.multi_task_configuration()
        if not multi_task_config:
            console.print("[red]No tasks configured. Aborting.[/red]")
            return None
        
        # Step 2: Generate Test Set (Stage 1)
        testset_path = self.generate_test_set(multi_task_config)
        if not testset_path:
            console.print("[red]Test set generation failed. Aborting.[/red]")
            return None
        
        # Store the generated test set path
        self.multi_task_config = multi_task_config
        self.generated_testset_path = testset_path
        
        # Step 3: Model Selection  
        models = self.model_selection_for_execution()
        if not models:
            console.print("[red]No models selected. Aborting.[/red]")
            return None
        
        # Step 4: Execution Configuration
        exec_config = self.execution_configuration()
        
        # Create a BenchmarkConfig for execution (backward compatibility)
        # This is mainly used for the execution phase
        config = BenchmarkConfig(
            name=multi_task_config.name,
            description=multi_task_config.description,
            models=models,
            prompts=PromptSpec(user_styles=['multi'], system_styles=['task']),  # Placeholder
            params=TestParams(
                batch_size=multi_task_config.total_tests,
                temperature=multi_task_config.temperature,
                language=multi_task_config.language,
                thinking_enabled=multi_task_config.thinking_enabled
            ),
            output_dir=multi_task_config.output_dir,
            generate_charts=exec_config['generate_charts'],
            report_formats=['markdown', 'json'],
            verbosity=exec_config['verbosity'],
            ollama_host=self.ollama_host,
        )
        
        # Store multi-task info in config
        config.task_type = 'multi-task'
        config.task_config = {'testset_path': testset_path}
        
        # Store for later use
        self.config = config
        return config
    
    def quick_start_benchmark(self) -> Optional[BenchmarkConfig]:
        """Quick 5-minute benchmark with sensible defaults."""
        self.display_header()
        console.print(Panel("⚡ Quick Start (5 min test)", style="bold cyan"))
        console.print("[dim]Pre-configured test: Arithmetic task, 2 models, minimal settings[/dim]\n")
        
        # Ask for output directory first
        output_dir = questionary.text(
            'Output directory (all files will be saved here):',
            default='results/runs',
            style=custom_style
        ).ask()
        
        # Auto-configure: Arithmetic task with minimal settings
        from src.core.PromptEngine import PromptStyle, SystemPromptStyle
        
        # Default prompt config
        prompts = PromptSpec(
            user_styles=['minimal'],
            system_styles=['analytical']
        )
        
        # Default task config
        task_config = TaskConfiguration(
            task_type='ari',
            task_name='ARI (Math Expressions)',
            batch_size=20,  # Small batch for quick testing
            prompts=prompts,
            parameters={'difficulties': [2], 'mode': 'expression'}
        )
        
        # Create multi-task config
        multi_task_config = MultiTaskConfig(
            name=f"quick_test_{questionary.text('Test name suffix (optional):', default='', style=custom_style).ask() or 'auto'}",
            description="Quick 5-minute benchmark test",
            tasks=[task_config],
            temperature=0.1,
            language='en',
            thinking_enabled=False,
            output_dir=output_dir
        )
        
        # Generate test set
        console.print("\n[cyan]→ Generating test set...[/cyan]")
        testset_path = self.generate_test_set(multi_task_config)
        if not testset_path:
            console.print("[red]Test set generation failed.[/red]")
            return None
        
        # Store paths
        self.multi_task_config = multi_task_config
        self.generated_testset_path = testset_path
        
        # Model selection - suggest 2 fast models
        console.print("\n[cyan]Select 2 models for quick testing:[/cyan]")
        models = self.model_selection_for_execution()
        if not models:
            console.print("[red]No models selected.[/red]")
            return None
        
        # Auto-configure execution
        exec_config = {
            'output_dir': 'results/runs',
            'generate_charts': True,
            'verbosity': 'normal'
        }
        
        # Create config
        config = BenchmarkConfig(
            name=multi_task_config.name,
            description=multi_task_config.description,
            models=models,
            prompts=prompts,
            params=TestParams(
                batch_size=20,
                temperature=0.1,
                language='en',
                thinking_enabled=False
            ),
            output_dir=output_dir,
            generate_charts=True,
            report_formats=['markdown', 'json'],
            verbosity='normal',
            ollama_host=self.ollama_host,
        )
        
        config.task_type = 'multi-task'
        config.task_config = {'testset_path': testset_path}
        
        self.config = config
        return config

    def _create_multi_task_yaml_config(self, multi_task_config: MultiTaskConfig) -> str:
        """Create YAML config for multi-task test set generation."""
        import yaml
        from datetime import datetime
        
        # Build YAML config structure for multi-task
        yaml_config = {
            'metadata': {
                'name': f"multi_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'version': '1.0',
                'schema_version': '1.0.0',
                'description': multi_task_config.description,
                'created_by': 'benchmark_tui',
                'task_type': 'multi-task'
            },
            'tasks': [],  # Multiple tasks
            'sampling': {
                'temperature': multi_task_config.temperature,
                'top_k': 40,
                'max_tokens': 2048
            },
            'execution': {
                'no_thinking': not multi_task_config.thinking_enabled,
                'timeout_seconds': 30,
                'prompt_language': multi_task_config.language
            }
        }
        
        # Map TUI task types to stage script task types
        task_type_mapping = {
            'ari': 'arithmetic',
            'gol': 'game_of_life', 
            'c14': 'cellular_automata_1d',
            'shapes': 'ascii_shapes',
            'tracking': 'object_tracking',
            'sally_anne': 'sally_anne',
            'linda': 'linda_fallacy',
            'grid_tasks': 'grid_tasks',
            'carwash': 'carwash',
            'inverted_cup': 'inverted_cup'
        }
        
        # Add each task configuration
        for task_config in multi_task_config.tasks:
            mapped_task_type = task_type_mapping.get(task_config.task_type, task_config.task_type)
            
            task_yaml = {
                'type': mapped_task_type,
                'generation': {
                    'seed': 42,
                },
                'prompt_configs': []
            }
            
            # Add task-specific generation params
            if mapped_task_type == 'arithmetic':
                # Support both old and new format
                if 'complexity' in task_config.parameters and 'target_values' in task_config.parameters:
                    # New format
                    task_yaml['generation'].update({
                        'complexity': task_config.parameters.get('complexity', [2]),
                        'target_values': task_config.parameters.get('target_values', [1, 2, 3]),
                        'count': task_config.batch_size,
                        'mode': task_config.parameters.get('mode', 'expression')
                    })
                else:
                    # Old format (backward compatibility)
                    task_yaml['generation'].update({
                        'target_accuracies': task_config.parameters.get('difficulties', [0, 1, 2]),
                        'expressions_per_target': task_config.batch_size,
                        'mode': task_config.parameters.get('mode', 'expression')
                    })
            elif mapped_task_type == 'game_of_life':
                task_yaml['generation'].update({
                    'difficulty_levels': [task_config.parameters.get('difficulty', 'EASY')],
                    'grids_per_difficulty': task_config.batch_size,
                    'density': task_config.parameters.get('density', 0.3),
                    'known_patterns_ratio': 0.3
                })
                yaml_config['execution']['cell_markers'] = ['1', '0']
            elif mapped_task_type == 'cellular_automata_1d':
                task_yaml['generation'].update({
                    'rule_numbers': task_config.parameters.get('rule_numbers', [90]),
                    'width': task_config.parameters.get('width', 16),
                    'steps': task_config.parameters.get('steps', 1),
                    'boundary_condition': task_config.parameters.get('boundary_condition', 'wrap'),
                    'initial_pattern': task_config.parameters.get('initial_pattern', 'random'),
                    'density': task_config.parameters.get('density', 0.5),
                    'cases_per_rule': task_config.batch_size
                })
                yaml_config['execution']['cell_markers'] = ['1', '0']
            elif mapped_task_type == 'ascii_shapes':
                task_yaml['generation'].update({
                    'width_range': list(task_config.parameters.get('width_range', (3, 20))),
                    'height_range': list(task_config.parameters.get('height_range', (2, 7))),
                    'symbols': task_config.parameters.get('symbols', ['*', '#', 'X', '█']),
                    'spacing': task_config.parameters.get('spacing', [' ']),
                    'coordinate_labels': task_config.parameters.get('coordinate_labels', True),
                    'filled': task_config.parameters.get('filled', [True, False]),
                    'question_type': task_config.parameters.get('question_type', 'dimensions'),
                    'cases_per_config': task_config.batch_size
                })
            elif mapped_task_type == 'object_tracking':
                task_yaml['generation'].update({
                    'count': task_config.batch_size,
                    'object': task_config.parameters.get('objects', ['grape', 'marble', 'keys']),
                    'container': task_config.parameters.get('containers', ['cup', 'bowl', 'mug']),
                    'distractor_count': task_config.parameters.get('distractor_count', [0, 1, 2]),
                    'post_inversion_moves': task_config.parameters.get('post_inversion_moves', [0, 1, 2])
                })
                # Add optional advanced parameters if provided
                if 'location_initial' in task_config.parameters:
                    task_yaml['generation']['location_initial'] = task_config.parameters['location_initial']
                if 'distractor_types' in task_config.parameters:
                    task_yaml['generation']['distractor_types'] = task_config.parameters['distractor_types']
            elif mapped_task_type == 'sally_anne':
                task_yaml['generation'].update({
                    'cases_per_config': task_config.batch_size,
                    'objects': task_config.parameters.get('objects', ['marble', 'ball', 'toy']),
                    'containers': task_config.parameters.get('containers', [('basket', 'box'), ('drawer', 'cupboard')]),
                    'distractor_count': task_config.parameters.get('distractor_count', 0),
                    'leave_activities': task_config.parameters.get('leave_activities', ['goes for a walk', 'goes outside']),
                    'include_observer': task_config.parameters.get('include_observer', False)
                })
                # Handle subject pairs (random vs specific)
                if task_config.parameters.get('use_random_pairs', True):
                    task_yaml['generation']['subject_pairs'] = []  # Empty list signals random generation
                elif 'subject_pairs' in task_config.parameters:
                    task_yaml['generation']['subject_pairs'] = task_config.parameters['subject_pairs']
            elif mapped_task_type == 'linda_fallacy':
                task_yaml['generation'].update({
                    'num_options': task_config.parameters.get('num_options', 8),
                    'personas_per_config': task_config.batch_size,
                    'culture_filter': task_config.parameters.get('culture_filter', []),
                    'ranking_mode': task_config.parameters.get('ranking_mode', 'probability')
                })
            elif mapped_task_type == 'grid_tasks':
                task_yaml['generation'].update({
                    'min_rows': task_config.parameters.get('min_rows', 2),
                    'max_rows': task_config.parameters.get('max_rows', 20),
                    'min_cols': task_config.parameters.get('min_cols', 2),
                    'max_cols': task_config.parameters.get('max_cols', 10),
                    'data_types': task_config.parameters.get('data_types', ['sales', 'hr', 'grades']),
                    'question_types': task_config.parameters.get('question_types', ['cell_lookup', 'row_sum', 'column_count']),
                    'table_style': task_config.parameters.get('table_style', 'unicode'),
                    'cases_per_config': task_config.batch_size,
                    'numeric_tolerance': task_config.parameters.get('numeric_tolerance', 0.1)
                })
            elif mapped_task_type == 'carwash':
                task_yaml['generation'].update({
                    'distances': task_config.parameters.get(
                        'distances', ['50m', '100m', '200m', 'corner', '2min_walk']
                    ),
                    'count': task_config.batch_size,
                })
            elif mapped_task_type == 'inverted_cup':
                task_yaml['generation'].update({
                    'description_styles': task_config.parameters.get(
                        'description_styles',
                        ['sealed_top_open_bottom', 'lid_top_hole_bottom', 'upside_down_explicit',
                         'rim_at_bottom', 'inverted_normal', 'mouth_down', 'closed_on_top']
                    ),
                    'count': task_config.batch_size,
                })
            
            # Add prompt configurations for this task
            for user_style in task_config.prompts.user_styles:
                for system_style in task_config.prompts.system_styles:
                    prompt_config = {
                        'name': f"{task_config.task_type}_{user_style}_{system_style}",
                        'user_style': user_style,
                        'system_style': system_style
                    }
                    if mapped_task_type == 'game_of_life':
                        prompt_config['language'] = multi_task_config.language
                    task_yaml['prompt_configs'].append(prompt_config)
            
            yaml_config['tasks'].append(task_yaml)
        
        # Save YAML config using PathManager to output directory
        path_mgr = get_path_manager(output_dir=Path(multi_task_config.output_dir))
        
        # Extract task types for filename
        task_types = [t['type'] for t in yaml_config['tasks']]
        
        config_path = path_mgr.get_testset_config_path(
            name=yaml_config['metadata']['name'],
            task_types=task_types
        )
        
        with open(config_path, 'w') as f:
            yaml.dump(yaml_config, f, default_flow_style=False, sort_keys=False)
        
        return str(config_path)


def execute_benchmark(config: BenchmarkConfig) -> bool:
    """Execute benchmark using pre-generated test set (3-stage architecture)."""
    import subprocess
    import sys
    import json
    from datetime import datetime
    
    try:
        console.print("\n" + "=" * 80)
        console.print("[bold cyan]Benchmark Execution[/bold cyan]")
        console.print("=" * 80)
        console.print()
        
        # Create output directory
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓ Output directory: {config.output_dir}[/green]")
        
        # Get the pre-generated test set path
        testset_path = config.task_config.get('testset_path') if hasattr(config, 'task_config') else None
        if not testset_path:
            console.print("[red]✗ No pre-generated test set found![/red]")
            return False
        
        console.print(f"[cyan]✓ Test set: {Path(testset_path).name}[/cyan]")
        console.print(f"[cyan]✓ Models: {len(config.models)} selected[/cyan]")
        for model in config.models:
            console.print(f"  • {model.display_name}")
        console.print()
        
        # Single confirmation
        if not questionary.confirm(
            '🚀 Start execution?',
            default=True,
            style=custom_style
        ).ask():
            console.print("[yellow]Execution cancelled.[/yellow]")
            return False
            
        # =======================================================================
        # STAGE 2: EXECUTE TESTS ON PRE-GENERATED TEST SET
        # =======================================================================
        
        console.print("\n[bold cyan]STAGE 2: Test Execution[/bold cyan]")
        console.print("─" * 40)
        
        all_results = []
        total_models = len(config.models)
        
        for model_idx, model_spec in enumerate(config.models, 1):
            console.print(f"\n[cyan][{model_idx}/{total_models}] Executing on {model_spec.display_name}[/cyan]")
            
            # Run test set on this model
            run_cmd = [
                sys.executable, "src/stages/run_testset.py",
                testset_path,
                "--model", model_spec.name,
                "--provider", model_spec.provider,
                "--output-dir", config.output_dir
            ]
            
            if model_spec.quantization:
                run_cmd.extend(["--quantization", model_spec.quantization])
            
            if model_spec.provider == "ollama":
                ollama_host = getattr(config, 'ollama_host', 'http://localhost:11434')
                if ollama_host != 'http://localhost:11434':
                    run_cmd.extend(["--ollama-host", ollama_host])
            
            try:
                result = subprocess.run(
                    run_cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600  # 1 hour timeout per model
                )
                
                if result.returncode == 0:
                    # Extract result file path
                    result_path = _extract_result_path(result.stdout)
                    console.print(f"[green]✓ {model_spec.display_name} completed[/green]")
                    all_results.append({
                        'model': model_spec.display_name,
                        'result_file': result_path
                    })
                else:
                    console.print(f"[yellow]⚠️  {model_spec.display_name} completed with errors[/yellow]")
                    console.print(f"[dim]{result.stderr}[/dim]")
            
            except subprocess.TimeoutExpired:
                console.print(f"[red]✗ {model_spec.display_name} timed out after 1 hour[/red]")
            except Exception as e:
                console.print(f"[red]✗ Error running {model_spec.display_name}: {e}[/red]")
        
        # =======================================================================
        # STAGE 3: ANALYSIS & REPORTING
        # =======================================================================
        
        if all_results and config.generate_charts:
            console.print("\n[bold cyan]STAGE 3: Analysis & Reporting[/bold cyan]")
            console.print("─" * 40)
            
            # Collect all result files
            result_files = [r['result_file'] for r in all_results if r['result_file']]
            
            if result_files:
                console.print("[cyan]→ Analyzing results...[/cyan]")
                
                # Generate analysis report
                report_path = f"{config.output_dir}/benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                html_report_path = report_path.replace('.md', '.html')
                chart_dir = f"{config.output_dir}/charts"
                
                analyze_cmd = [
                    sys.executable, "src/stages/analyze_results.py"
                ] + result_files + [
                    "--output", report_path,
                    "--visualize",
                    "--output-dir", chart_dir
                ]
                
                # Add --comparison flag for multi-model analysis
                if len(result_files) > 1:
                    analyze_cmd.append("--comparison")
                
                try:
                    result = subprocess.run(analyze_cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        console.print(f"[green]✓ Markdown report: {report_path}[/green]")
                        console.print(f"[green]✓ HTML report with charts: {html_report_path}[/green]")
                        console.print(f"[green]✓ Visualizations: {chart_dir}[/green]")
                    else:
                        console.print(f"[yellow]⚠️  Analysis completed with warnings[/yellow]")
                        if result.stderr:
                            console.print(f"[dim]{result.stderr[:500]}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]⚠️  Could not generate analysis: {e}[/yellow]")
            
            # Save execution summary
            summary_file = Path(config.output_dir) / f"execution_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            summary_data = {
                'workflow': '3-stage-pre-generated',
                'test_set_file': testset_path,
                'models': [m.display_name for m in config.models],
                'completed_models': len(all_results),
                'output_directory': config.output_dir,
                'results': all_results
            }
            summary_file.write_text(json.dumps(summary_data, indent=2))
            console.print(f"\n[green]✓ Execution summary saved to: {summary_file}[/green]")
            
            console.print(f"\n[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]")
            console.print("[green]✓ Multi-task benchmark execution completed![/green]")
            console.print(f"[cyan]Results saved to: {config.output_dir}[/cyan]")
            
            return True
        else:
            console.print("[yellow]Benchmark cancelled.[/yellow]")
            return False

    except Exception as e:
        console.print(f"[red]✗ Error during benchmark execution: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False



def _extract_testset_path(output: str) -> str:
    """Extract testset file path from generate_testset.py output."""
    import re
    
    match = re.search(r'✓ Generated test set: (.+\.json\.gz)', output)
    if match:
        return match.group(1)
    return None


def _extract_result_path(output: str) -> str:
    """Extract result file path from run_testset.py output."""
    import re
    
    match = re.search(r'✓ Results saved: (.+\.json\.gz)', output)
    if match:
        return match.group(1)
    return None

def main():
    """Main TUI entry point."""
    tui = BenchmarkTUI()
    
    while True:
        choice = tui.main_menu()
        
        if choice == 'Start New Benchmark':
            config = tui.create_new_benchmark()
            if config:
                if execute_benchmark(config):
                    break
        
        elif choice == 'Quick Start (5 min test)':
            config = tui.quick_start_benchmark()
            if config:
                if execute_benchmark(config):
                    break
        
        elif choice == 'Exit':
            console.print("[yellow]Goodbye![/yellow]")
            break


if __name__ == "__main__":
    main()
