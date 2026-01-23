#!/usr/bin/env python3
"""
Test the updated benchmark TUI with 3-stage architecture.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli.benchmark_tui import execute_benchmark, _create_testset_config
from src.cli.benchmark_config import BenchmarkConfig, ModelSpec, PromptSpec, TestParams
from rich.console import Console

console = Console()

def test_3stage_tui_config():
    """Test that TUI can create proper 3-stage configs."""
    
    console.print("[bold cyan]Testing 3-Stage TUI Configuration[/bold cyan]")
    
    # Create a simple test config
    with tempfile.TemporaryDirectory() as temp_dir:
        config = BenchmarkConfig(
            name='test_3stage',
            description='Test 3-stage workflow',
            task_type='arithmetic',
            models=[
                ModelSpec(name='test-model', provider='ollama')
            ],
            prompts=PromptSpec(
                user_styles=['minimal'],
                system_styles=['casual']
            ),
            params=TestParams(
                batch_size=2,
                temperature=0.1,
                language='en',
                thinking_enabled=False
            ),
            output_dir=temp_dir,
            generate_charts=True
        )
        
        console.print(f"✓ Created test config: {config.name}")
        console.print(f"  Task: {config.task_type}")
        console.print(f"  Models: {len(config.models)}")
        console.print(f"  Batch size: {config.params.batch_size}")
        
        # Test YAML config generation
        try:
            yaml_path = _create_testset_config(config)
            console.print(f"✓ Generated YAML config: {yaml_path}")
            
            # Check that the file exists and has content
            yaml_file = Path(yaml_path)
            if yaml_file.exists() and yaml_file.stat().st_size > 0:
                console.print("✓ YAML config file is valid")
                
                # Show some content
                content = yaml_file.read_text()
                lines = content.split('\n')[:10]  # First 10 lines
                console.print("[dim]YAML content preview:[/dim]")
                for line in lines:
                    console.print(f"[dim]  {line}[/dim]")
                
                return True
            else:
                console.print("[red]✗ YAML config file is empty or missing[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Error creating YAML config: {e}[/red]")
            return False


def test_config_integration():
    """Test that the config integrates properly with stage scripts."""
    
    console.print("\n[bold cyan]Testing Config Integration[/bold cyan]")
    
    # Check that the stage scripts exist
    stage_scripts = [
        "src/stages/generate_testset.py",
        "src/stages/run_testset.py",
        "src/stages/analyze_results.py"
    ]
    
    for script_path in stage_scripts:
        script = Path(script_path)
        if script.exists():
            console.print(f"✓ Found {script_path}")
        else:
            console.print(f"[red]✗ Missing {script_path}[/red]")
            return False
    
    console.print("✓ All stage scripts are available")
    return True


if __name__ == '__main__':
    console.print("[bold]Testing 3-Stage TUI Integration[/bold]")
    console.print("=" * 50)
    
    success = True
    
    # Test 1: Config creation
    if not test_3stage_tui_config():
        success = False
    
    # Test 2: Script integration  
    if not test_config_integration():
        success = False
    
    # Summary
    console.print("\n" + "=" * 50)
    if success:
        console.print("[bold green]✅ All tests passed![/bold green]")
        console.print("\n[cyan]Ready to use the 3-stage TUI:[/cyan]")
        console.print("  python src/cli/benchmark_tui.py")
        console.print("\n[dim]The TUI will now use:")
        console.print("  Stage 1: Generate test sets")
        console.print("  Stage 2: Execute tests") 
        console.print("  Stage 3: Analyze results")
    else:
        console.print("[bold red]❌ Some tests failed[/bold red]")
        console.print("Please check the errors above.")
    
    sys.exit(0 if success else 1)