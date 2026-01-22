#!/usr/bin/env python3
"""
Benchmark Testing TUI - Terminal User Interface

Interactive terminal interface for configuring and running benchmark tests.
Uses questionary for simple, beautiful CLI prompts.
"""

from typing import List, Optional, Dict
from pathlib import Path
import questionary
from questionary import Style
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from benchmark_config import (
    BenchmarkConfig, ModelSpec, PromptSpec, TestParams, 
    ConfigManager, PRESET_CONFIGS
)
from model_providers import ModelProviderManager, ModelInfo

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
    
    def model_selection(self) -> List[ModelSpec]:
        """Multi-select models to test with provider support."""
        provider = self._get_providers_to_use()
        if not provider:
            return []
        
        self.display_header()
        console.print(Panel(f"Step 1: Select Models ({provider})", style="bold"))
        
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
            'Select models (space to toggle, enter to confirm):',
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
    
    def task_selection(self) -> str:
        """Select which benchmark task to run."""
        self.display_header()
        console.print(Panel("Step 2: Select Task Type", style="bold"))
        
        task = questionary.select(
            'Which task would you like to benchmark?',
            choices=[
                questionary.Choice('ARI (Math Expressions)', value='ari'),
                questionary.Choice('GoL (Game of Life)', value='gol'),
                questionary.Choice('C14 (Cellular Automata)', value='c14'),
                questionary.Choice('Linda (Pattern Recognition)', value='linda'),
            ],
            style=custom_style
        ).ask()
        
        return task
    
    def prompt_configuration(self) -> PromptSpec:
        """Configure prompt styles."""
        self.display_header()
        console.print(Panel("Step 3: Configure Prompts", style="bold"))
        
        # Available prompt styles
        user_style_choices = ['minimal', 'casual', 'linguistic', 'examples', 'rules_math']
        system_style_choices = ['analytical', 'casual', 'adversarial', 'none']
        
        # User prompt styles - use questionary.Choice with checked parameter
        user_styles = questionary.checkbox(
            'User Prompt Styles:',
            choices=[
                questionary.Choice(style, checked=(style in ['minimal', 'casual', 'linguistic']))
                for style in user_style_choices
            ],
            style=custom_style
        ).ask()
        
        # System prompt styles
        system_styles = questionary.checkbox(
            'System Prompt Styles:',
            choices=[
                questionary.Choice(style, checked=(style in ['analytical', 'casual']))
                for style in system_style_choices
            ],
            style=custom_style
        ).ask()
        
        # Validate selections
        if not user_styles:
            user_styles = ['minimal', 'casual', 'linguistic']
        if not system_styles:
            system_styles = ['analytical', 'casual']
        
        # Show matrix
        config_count = len(user_styles) * len(system_styles)
        console.print(f"\n✓ Total configurations: {config_count}")
        console.print(f"  User styles: {', '.join(user_styles)}")
        console.print(f"  System styles: {', '.join(system_styles)}")
        
        return PromptSpec(user_styles=user_styles, system_styles=system_styles)
    
    def test_parameters(self) -> TestParams:
        """Configure test execution parameters."""
        self.display_header()
        console.print(Panel("Step 4: Test Parameters", style="bold"))
        
        # Batch size
        batch_size = questionary.text(
            'Batch size:',
            default='12',
            validate=lambda x: x.isdigit() and int(x) > 0,
            style=custom_style
        ).ask()
        batch_size = int(batch_size)
        
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
        
        return TestParams(
            batch_size=batch_size,
            temperature=temperature,
            language=language,
            thinking_enabled=thinking,
        )
    
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
            # Linda-specific config
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
    
    def confirmation_screen(self, config: BenchmarkConfig) -> bool:
        """Final confirmation before running tests."""
        self.display_header()
        console.print(Panel("Review Configuration", style="bold green"))
        
        # Create detailed summary table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="green")
        
        table.add_row("Name", config.name)
        table.add_row("Provider", config.models[0].provider if config.models else "N/A")
        table.add_row("Models", f"{len(config.models)} selected")
        
        # List models
        for model in config.models[:3]:  # Show first 3
            table.add_row("  •", model.display_name)
        if len(config.models) > 3:
            table.add_row("  •", f"... and {len(config.models) - 3} more")
        
        # Task information
        if hasattr(config, 'task_type'):
            table.add_row("Task Type", config.task_type.upper())
        
        table.add_row("Prompt Configs", str(config.prompts.config_count()))
        table.add_row("Batch Size", str(config.params.batch_size))
        table.add_row("Temperature", f"{config.params.temperature:.2f}")
        table.add_row("Total Tests", str(config.total_test_count()))
        table.add_row("Estimated Time", f"{config.estimated_duration_minutes():.0f} minutes")
        table.add_row("Output Dir", config.output_dir)
        
        console.print(table)
        console.print()
        
        confirm = questionary.confirm(
            '🚀 Ready to start testing?',
            default=True,
            style=custom_style
        ).ask()
        
        return confirm
    
    def create_new_benchmark(self) -> Optional[BenchmarkConfig]:
        """Guided setup for new benchmark."""
        # Step 1: Models
        models = self.model_selection()
        if not models:
            console.print("[red]No models selected. Aborting.[/red]")
            return None
        
        # Step 2: Task Selection
        task_type = self.task_selection()
        if not task_type:
            console.print("[red]No task selected. Aborting.[/red]")
            return None
        
        # Step 3: Prompts
        prompts = self.prompt_configuration()
        
        # Step 4: Task-specific configuration
        task_config = self.task_specific_config(task_type)
        
        # Step 5: Test parameters
        params = self.test_parameters()
        
        # Step 6: Output configuration
        output_config = self.output_configuration()
        
        # Create config
        config = BenchmarkConfig(
            name=questionary.text(
                'Benchmark name:',
                default=f'{task_type.upper()} Benchmark',
                style=custom_style
            ).ask(),
            description=questionary.text(
                'Description (optional):',
                default='',
                style=custom_style
            ).ask(),
            models=models,
            prompts=prompts,
            params=params,
            output_dir=output_config['output_dir'],
            generate_charts=output_config['generate_charts'],
            report_formats=output_config['report_formats'],
            verbosity=output_config['verbosity'],
        )
        
        # Store task type in config metadata
        config.task_type = task_type
        config.task_config = task_config
        
        # Confirmation
        if self.confirmation_screen(config):
            self.config = config
            return config
        
        return None


def execute_benchmark(config: BenchmarkConfig) -> bool:
    """Execute benchmark with the given configuration."""
    import subprocess
    import sys
    import json
    from datetime import datetime
    
    try:
        console.print("\n" + "=" * 80)
        console.print("[bold cyan]Starting Benchmark Execution[/bold cyan]")
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
        
        # Display execution summary
        summary_table = Table(title="Benchmark Summary", show_header=True)
        summary_table.add_column("Parameter", style="cyan")
        summary_table.add_column("Value", style="green")
        
        task_type = config.task_type.upper() if hasattr(config, 'task_type') else "N/A"
        summary_table.add_row("Task", task_type)
        summary_table.add_row("Models", str(len(config.models)))
        summary_table.add_row("Prompt Configs", str(config.prompts.config_count()))
        summary_table.add_row("Total Tests", str(config.total_test_count()))
        summary_table.add_row("Estimated Time", f"{config.estimated_duration_minutes():.0f} minutes")
        summary_table.add_row("Output Directory", config.output_dir)
        
        console.print(summary_table)
        console.print()
        
        # Show start confirmation
        if questionary.confirm(
            'Start execution now?',
            default=True,
            style=custom_style
        ).ask():
            console.print("\n[cyan]Executing benchmark...[/cyan]")
            console.print("[dim]This may take a while depending on the number of tests.[/dim]")
            console.print()
            
            # Map task types to scripts
            task_script_map = {
                'ari': 'ari_eval.py',
                'gol': 'gol_eval.py',
                'c14': 'c14_eval.py',
                'linda': 'linda_eval.py',
            }
            
            task_type_lower = task_type.lower() if task_type != "N/A" else None
            script = task_script_map.get(task_type_lower)
            
            if not script:
                console.print(f"[red]✗ Unknown task type: {task_type}[/red]")
                return False
            
            # Execute for each prompt combination (USER style x SYSTEM style)
            # All models are passed together
            prompt_combos = list(zip(config.prompts.user_styles, config.prompts.system_styles))
            total_combos = len(prompt_combos)
            all_results = []
            
            for combo_idx, (user_style, system_style) in enumerate(prompt_combos, 1):
                console.print(f"\n[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]")
                console.print(f"[bold cyan][{combo_idx}/{total_combos}] Prompt Config: {user_style} (user) × {system_style} (system)[/bold cyan]")
                console.print(f"[cyan]Models: {', '.join([m.display_name for m in config.models])}[/cyan]")
                console.print(f"[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]\n")
                
                # Build command arguments
                cmd = [sys.executable, script]
                
                # Add all models at once
                model_names = [m.name for m in config.models]
                cmd.extend(['--model'] + model_names)
                
                cmd.extend(['--batch-size', str(config.params.batch_size)])
                cmd.extend(['--temperature', str(config.params.temperature)])
                cmd.extend(['--prompt-language', config.params.language])
                cmd.extend(['--prompt-style', user_style])
                cmd.extend(['--system-prompt-style', system_style])
                cmd.extend(['--results-dir', config.output_dir])
                
                # Add task-specific configuration
                if hasattr(config, 'task_config') and config.task_config:
                    task_cfg = config.task_config
                    
                    if task_type_lower == 'ari':
                        if 'target_values' in task_cfg and task_cfg['target_values']:
                            cmd.extend(['--target'] + [str(v) for v in task_cfg['target_values']])
                        if 'mode' in task_cfg:
                            cmd.extend(['--mode', task_cfg['mode']])
                        if 'difficulties' in task_cfg:
                            cmd.extend(['--difficulty'] + [str(d) for d in task_cfg['difficulties']])
                    
                    elif task_type_lower == 'gol':
                        if 'difficulties' in task_cfg:
                            pass  # Would need GoL-specific args
                    
                    elif task_type_lower in ('c14', 'linda'):
                        if 'difficulties' in task_cfg:
                            cmd.extend(['--difficulty'] + [str(d) for d in task_cfg['difficulties']])
                
                # Execute the script
                console.print(f"[dim]Command: {' '.join(cmd)}[/dim]\n")
                
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=3600  # 1 hour timeout per prompt combo
                    )
                    
                    # Save stdout to results file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    result_file = Path(config.output_dir) / f"results_{user_style}_{system_style}_{timestamp}.txt"
                    result_file.write_text(result.stdout)
                    
                    # Also save stderr if there are errors
                    if result.stderr:
                        error_file = Path(config.output_dir) / f"errors_{user_style}_{system_style}_{timestamp}.txt"
                        error_file.write_text(result.stderr)
                    
                    # Print output
                    console.print(result.stdout)
                    
                    if result.returncode != 0:
                        console.print(f"[yellow]⚠️  Prompt config {user_style}/{system_style} completed with exit code {result.returncode}[/yellow]")
                    else:
                        console.print(f"[green]✓ Prompt config {user_style}/{system_style} completed successfully[/green]")
                        all_results.append({
                            'combo_idx': combo_idx,
                            'user_style': user_style,
                            'system_style': system_style,
                            'models': len(config.models),
                            'result_file': str(result_file)
                        })
                
                except subprocess.TimeoutExpired:
                    console.print(f"[red]✗ Prompt config {user_style}/{system_style} timed out after 1 hour[/red]")
                except Exception as e:
                    console.print(f"[red]✗ Error running {user_style}/{system_style}: {e}[/red]")
            
            # Save execution summary
            summary_file = Path(config.output_dir) / f"execution_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            summary_data = {
                'task_type': task_type_lower,
                'models': [m.display_name for m in config.models],
                'prompt_configs': total_combos,
                'completed_configs': len(all_results),
                'output_directory': config.output_dir,
                'results': all_results
            }
            summary_file.write_text(json.dumps(summary_data, indent=2))
            console.print(f"\n[green]✓ Execution summary saved to: {summary_file}[/green]")
            
            # Generate charts if enabled
            if config.generate_charts:
                console.print("\n[cyan]Generating visualizations...[/cyan]")
                try:
                    _generate_benchmark_charts(config.output_dir, task_type_lower)
                    console.print("[green]✓ Charts generated successfully[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠️  Could not generate charts: {e}[/yellow]")
            
            console.print(f"\n[cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/cyan]")
            console.print("[green]✓ Benchmark execution completed![/green]")
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
