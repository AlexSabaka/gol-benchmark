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
    temperature: float = 0.1
    language: str = 'en'
    thinking_enabled: bool = False
    
    @property
    def total_tests(self) -> int:
        return sum(task.total_tests for task in self.tasks)
    
    @property
    def total_task_types(self) -> int:
        return len(self.tasks)

from src.cli.benchmark_config import (
    BenchmarkConfig, ModelSpec, PromptSpec, TestParams,
    ConfigManager, PRESET_CONFIGS
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
                'Load Previous Configuration',
                'Use Preset Configuration',
                'View Recent Results',
                'Exit',
            ],
            style=custom_style
        ).ask()
        
        return choice
    
    def preset_selection(self) -> Optional[BenchmarkConfig]:
        """Select and load a preset configuration."""
        self.display_header()
        
        presets = list(PRESET_CONFIGS.keys()) + ['Back to Main Menu']
        
        choice = questionary.select(
            'Choose a preset configuration:',
            choices=presets,
            style=custom_style
        ).ask()
        
        if choice == 'Back to Main Menu' or choice is None:
            return None
        
        self.config = PRESET_CONFIGS[choice]
        self._show_config_summary()
        return self.config
    
    def _show_config_summary(self):
        """Display a summary of current configuration."""
        if not self.config:
            return
        
        table = Table(title="Configuration Summary", show_header=True)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Name", self.config.name)
        table.add_row("Description", self.config.description)
        table.add_row("Models", str(len(self.config.models)))
        table.add_row("Prompt Configs", str(self.config.prompts.config_count()))
        table.add_row("Total Tests", str(self.config.total_test_count()))
        table.add_row("Est. Duration", f"{self.config.estimated_duration_minutes():.0f} min")
        
        console.print(table)
    
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
        return provider_choice
    
    def _get_available_models_for_provider(self, provider: str) -> List[ModelInfo]:
        """Get available models from the selected provider."""
        models = self.provider_manager.list_models_by_provider(provider)
        
        if not models:
            console.print(f"[yellow]⚠️  No models found in {provider}[/yellow]")
            if provider == "ollama":
                console.print("  Pull some models first: [dim]ollama pull qwen:0.5b[/dim]")
        
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
            {'id': 'linda', 'name': 'Linda (Pattern Recognition)', 'description': 'Statistical reasoning patterns'}
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
        for task_id in selected_task_types:
            task_info = next(t for t in available_tasks if t['id'] == task_id)
            task_config = self._configure_single_task(task_id, task_info['name'])
            if task_config:
                task_configs.append(task_config)
        
        if not task_configs:
            return None
        
        # Global settings
        self.display_header()
        console.print(Panel("Global Test Set Configuration", style="bold"))
        
        # Temperature
        temperature = questionary.text(
            'Temperature (0.0-1.0):',
            default='0.1',
            validate=lambda x: x.replace('.', '', 1).isdigit() and 0 <= float(x) <= 1,
            style=custom_style
        ).ask()
        temperature = float(temperature)
        
        # Language
        language = questionary.select(
            'Language:',
            choices=['English', 'Spanish', 'French', 'German', 'Chinese', 'Ukrainian'],
            default='English',
            style=custom_style
        ).ask()
        lang_map = {'English': 'en', 'Spanish': 'es', 'French': 'fr', 'German': 'de', 'Chinese': 'zh', 'Ukrainian': 'uk'}
        language = lang_map[language]
        
        # Thinking mode
        thinking = questionary.confirm(
            'Enable thinking/reasoning mode?',
            default=False,
            style=custom_style
        ).ask()
        
        # Test set name and description
        name = questionary.text(
            'Test set name:',
            default=f"Multi-Task-{'-'.join(selected_task_types)}",
            style=custom_style
        ).ask()
        
        description = questionary.text(
            'Test set description (optional):',
            default=f"Multi-task test set with {len(task_configs)} task types",
            style=custom_style
        ).ask()
        
        return MultiTaskConfig(
            name=name,
            description=description,
            tasks=task_configs,
            temperature=temperature,
            language=language,
            thinking_enabled=thinking
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
        
        # Output directory
        output_dir = questionary.text(
            'Output directory:',
            default='results_multi_task',
            style=custom_style
        ).ask()
        
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
            'output_dir': output_dir,
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
        """Configure output and reporting options."""
        self.display_header()
        console.print(Panel("Step 6: Output Configuration", style="bold"))
        
        # Output directory
        output_dir = questionary.text(
            'Output directory:',
            default='results_run_auto',
            style=custom_style
        ).ask()
        
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
            'output_dir': output_dir,
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
            output_dir=exec_config['output_dir'],
            generate_charts=exec_config['generate_charts'],
            report_formats=['markdown', 'json'],
            verbosity=exec_config['verbosity'],
        )
        
        # Store multi-task info in config
        config.task_type = 'multi-task'
        config.task_config = {'testset_path': testset_path}
        
        # Final confirmation
        if self.execution_confirmation_screen(config, multi_task_config):
            self.config = config
            return config
        
        return None

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
            'c14': 'c14',
            'linda': 'linda_fallacy'
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
            elif mapped_task_type == 'c14':
                task_yaml['generation'].update({
                    'difficulty_levels': task_config.parameters.get('difficulties', [1]),
                    'cases_per_difficulty': task_config.batch_size
                })
            elif mapped_task_type == 'linda_fallacy':
                task_yaml['generation'].update({
                    'num_options': task_config.parameters.get('num_options', 8),
                    'personas_per_config': task_config.batch_size,
                    'culture_filter': task_config.parameters.get('culture_filter', []),
                    'ranking_mode': task_config.parameters.get('ranking_mode', 'probability')
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
        
        # Save YAML config
        config_dir = Path("configs/testsets")
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_path = config_dir / f"{yaml_config['metadata']['name']}.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(yaml_config, f, default_flow_style=False, sort_keys=False)
        
        return str(config_path)


def execute_benchmark(config: BenchmarkConfig) -> bool:
    """Execute benchmark using pre-generated test set (3-stage architecture)."""
    import subprocess
    import sys
    import json
    import yaml
    from datetime import datetime
    
    try:
        console.print("\n" + "=" * 80)
        console.print("[bold cyan]Starting Benchmark Execution on Pre-Generated Test Set[/bold cyan]")
        console.print("=" * 80)
        console.print()
        
        # Save configuration first
        config_path = ConfigManager.save_to_yaml(config)
        console.print(f"[green]✓ Configuration saved to: {config_path}[/green]")
        
        # Create output directory
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Save config to output directory as well
        ConfigManager.save_to_json(config)
        console.print(f"[green]✓ Output directory created: {config.output_dir}[/green]")
        
        # Get the pre-generated test set path
        testset_path = config.task_config.get('testset_path') if hasattr(config, 'task_config') else None
        if not testset_path:
            console.print("[red]✗ No pre-generated test set found. This shouldn't happen![/red]")
            return False
        
        console.print(f"[cyan]✓ Using pre-generated test set: {Path(testset_path).name}[/cyan]")
        
        # Display execution summary
        summary_table = Table(title="Execution Summary", show_header=True)
        summary_table.add_column("Parameter", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Test Set", Path(testset_path).name)
        summary_table.add_row("Models", str(len(config.models)))
        summary_table.add_row("Output Directory", config.output_dir)
        summary_table.add_row("Analysis", "Enabled" if config.generate_charts else "Disabled")
        
        console.print(summary_table)
        console.print()
        
        # Show start confirmation
        if questionary.confirm(
            'Execute tests now?',
            default=True,
            style=custom_style
        ).ask():
            
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
                    chart_dir = f"{config.output_dir}/charts"
                    
                    analyze_cmd = [
                        sys.executable, "src/stages/analyze_results.py"
                    ] + result_files + [
                        "--output", report_path,
                        "--visualize",
                        "--output-dir", chart_dir
                    ]
                    
                    try:
                        result = subprocess.run(analyze_cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            console.print(f"[green]✓ Analysis report generated: {report_path}[/green]")
                            console.print(f"[green]✓ Visualizations saved to: {chart_dir}[/green]")
                        else:
                            console.print(f"[yellow]⚠️  Analysis completed with warnings[/yellow]")
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


def _generate_benchmark_charts(output_dir: str, task_type: str) -> None:
    """Generate visualization charts for benchmark results."""
    import re
    from pathlib import Path
    
    results_dir = Path(output_dir)
    result_files = sorted(results_dir.glob("results_*.txt"))
    
    if not result_files:
        console.print("[yellow]No result files found for chart generation[/yellow]")
        return
    
    # Parse results and create simple text-based summary
    all_data = {}
    
    for result_file in result_files:
        content = result_file.read_text()
        
        # Extract model names and accuracies from tabulate output
        # Look for lines like: "model_name    | 85.50% | 82.30% | ..."
        lines = content.split('\n')
        for line in lines:
            if '|' in line and '%' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3 and parts[0] and not parts[0].startswith('─'):
                    model_name = parts[0]
                    try:
                        accuracy_str = parts[1].replace('%', '')
                        accuracy = float(accuracy_str)
                        if model_name not in all_data:
                            all_data[model_name] = []
                        all_data[model_name].append(accuracy)
                    except (ValueError, IndexError):
                        pass
    
    # Create summary chart file
    if all_data:
        chart_file = results_dir / f"accuracy_summary_{Path.cwd().name}.txt"
        chart_content = _create_ascii_chart(all_data)
        chart_file.write_text(chart_content)
        console.print(f"[green]✓ Chart saved to: {chart_file}[/green]")


def _create_ascii_chart(data: dict) -> str:
    """Create a simple ASCII bar chart from accuracy data."""
    if not data:
        return "No data to display"
    
    # Calculate averages
    avg_data = {model: sum(values) / len(values) for model, values in data.items()}
    
    # Sort by average accuracy
    sorted_data = sorted(avg_data.items(), key=lambda x: x[1], reverse=True)
    
    max_model_len = max(len(model) for model in avg_data.keys())
    max_accuracy = max(avg_data.values())
    
    chart = "╔════════════════════════════════════════════╗\n"
    chart += "║       Model Accuracy Summary               ║\n"
    chart += "╚════════════════════════════════════════════╝\n\n"
    
    for model, accuracy in sorted_data:
        bar_length = int((accuracy / 100) * 40)
        bar = "█" * bar_length + "░" * (40 - bar_length)
        chart += f"{model:<{max_model_len}} │{bar}│ {accuracy:6.2f}%\n"
    
    return chart


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
        
        elif choice == 'Use Preset Configuration':
            config = tui.preset_selection()
            if config:
                if questionary.confirm('Use this configuration?', style=custom_style).ask():
                    console.print("\n[green]✓ Configuration selected![/green]")
                    if execute_benchmark(config):
                        break
        
        elif choice == 'Load Previous Configuration':
            saved = ConfigManager.list_saved_configs()
            if not saved:
                console.print("[yellow]No saved configurations found.[/yellow]")
                continue
            
            choice_file = questionary.select(
                'Select configuration:',
                choices=[f.name for f in saved],
                style=custom_style
            ).ask()
            
            if choice_file:
                config = ConfigManager.load_from_yaml(
                    ConfigManager.CONFIG_DIR / choice_file
                )
                console.print(f"\n[green]✓ Loaded: {config.name}[/green]")
                if execute_benchmark(config):
                    break
        
        elif choice == 'View Recent Results':
            results_dir = Path("results")
            if not results_dir.exists():
                console.print("[yellow]No results directory found.[/yellow]")
                continue
            
            # List recent result files
            result_files = sorted(results_dir.glob("*.json"), reverse=True)[:10]
            if not result_files:
                console.print("[yellow]No result files found.[/yellow]")
                continue
            
            console.print("\n[cyan]Recent Results:[/cyan]")
            for i, f in enumerate(result_files, 1):
                size_kb = f.stat().st_size / 1024
                console.print(f"  {i}. {f.name} ({size_kb:.1f} KB)")
        
        elif choice == 'Exit':
            console.print("[yellow]Goodbye![/yellow]")
            break


if __name__ == "__main__":
    main()
