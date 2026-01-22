#!/usr/bin/env python3
"""
Benchmark Runner - Main Orchestrator

Coordinates the entire benchmark workflow: TUI -> Config -> Execute -> Visualize -> Report
"""

import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Optional

from src.cli.benchmark_tui import BenchmarkTUI
from src.cli.benchmark_config import BenchmarkConfig, ConfigManager
from src.cli.test_executor import TestExecutor
from src.visualization.visualization_engine import VisualizationEngine


class BenchmarkRunner:
    """Main orchestrator for the benchmark workflow."""
    
    def __init__(self):
        self.tui = BenchmarkTUI()
        self.config_manager = ConfigManager()
        self.current_config: Optional[BenchmarkConfig] = None
        self.executor: Optional[TestExecutor] = None
        self.visualizer: Optional[VisualizationEngine] = None
    
    def _print_header(self):
        """Display welcome header."""
        print("\n" + "="*70)
        print("  🚀 BENCHMARK AUTOMATION SYSTEM")
        print("  Interactive Testing & Visualization Pipeline")
        print("="*70 + "\n")
    
    def _print_footer(self, elapsed_seconds: float):
        """Display completion footer."""
        hours, remainder = divmod(int(elapsed_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        time_str = ""
        if hours > 0:
            time_str += f"{hours}h "
        if minutes > 0:
            time_str += f"{minutes}m "
        time_str += f"{seconds}s"
        
        print("\n" + "="*70)
        print("  ✅ BENCHMARK COMPLETE")
        print(f"  Total Time: {time_str}")
        print("="*70 + "\n")
    
    def workflow_create_new(self):
        """Workflow: Create new benchmark configuration."""
        print("\n📋 CREATING NEW BENCHMARK\n")
        
        # Get config from TUI
        config = self.tui.create_new_benchmark()
        
        if not config:
            print("❌ Benchmark creation cancelled\n")
            return False
        
        self.current_config = config
        
        # Validate config
        is_valid, errors = config.validate()
        if not is_valid:
            print("\n❌ Configuration validation failed:")
            for error in errors:
                print(f"  • {error}")
            return False
        
        # Save config
        config_path = self.config_manager.save_to_yaml(config)
        print(f"\n✓ Saved configuration: {config_path}\n")
        
        return True
    
    def workflow_load_config(self):
        """Workflow: Load existing configuration."""
        saved_configs = self.config_manager.list_saved_configs()
        
        if not saved_configs:
            print("\n❌ No saved configurations found\n")
            return False
        
        print("\n📂 SAVED CONFIGURATIONS:\n")
        for i, config_path in enumerate(saved_configs, 1):
            print(f"  {i}. {config_path.stem}")
        
        # Simple menu
        choice = input("\nEnter configuration number (or 0 to cancel): ").strip()
        
        try:
            choice_num = int(choice)
            if choice_num == 0:
                return False
            if 1 <= choice_num <= len(saved_configs):
                config = self.config_manager.load_from_yaml(saved_configs[choice_num - 1])
                self.current_config = config
                print(f"\n✓ Loaded: {config.name}\n")
                return True
        except (ValueError, IndexError):
            pass
        
        print("\n❌ Invalid selection\n")
        return False
    
    def workflow_execute_tests(self) -> bool:
        """Workflow: Execute all configured tests."""
        if not self.current_config:
            print("\n❌ No configuration loaded\n")
            return False
        
        print("\n🧪 EXECUTING TESTS\n")
        
        # Create executor
        self.executor = TestExecutor(self.current_config)
        
        total_tests = self.current_config.total_test_count()
        print(f"Total tests to run: {total_tests}")
        print(f"Estimated time: ~{self.current_config.estimated_duration_minutes():.0f} minutes\n")
        
        # Ask for confirmation
        confirm = input("Proceed with testing? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Testing cancelled\n")
            return False
        
        print()
        
        # Run all tests
        start_time = datetime.now()
        results = self.executor.run_all_tests()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if not results:
            print("\n❌ No tests completed successfully\n")
            return False
        
        # Save results
        results_file = self.executor.save_results()
        
        # Print summary
        summary = self.executor.generate_summary()
        print(f"\n{'='*70}")
        print(f"  ✅ TESTS COMPLETED")
        print(f"{'='*70}")
        print(f"  Tests completed: {len(results)}/{total_tests}")
        print(f"  Mean accuracy: {summary.get('mean_accuracy', 0):.2f}%")
        print(f"  Best: {summary.get('best_model', ('N/A', 0))[0]} ({summary.get('best_model', ('N/A', 0))[1]:.2f}%)")
        print(f"  Worst: {summary.get('worst_model', ('N/A', 0))[0]} ({summary.get('worst_model', ('N/A', 0))[1]:.2f}%)")
        print(f"  Time: {elapsed/60:.1f} minutes")
        print(f"{'='*70}\n")
        
        return True
    
    def workflow_generate_charts(self) -> bool:
        """Workflow: Generate visualizations from results."""
        if not self.current_config or not self.executor:
            print("\n❌ No test results available\n")
            return False
        
        print("\n📊 GENERATING VISUALIZATIONS\n")
        
        # Create visualizer
        self.visualizer = VisualizationEngine(self.current_config.output_dir)
        
        # Generate all charts
        results_file = Path(self.current_config.output_dir) / "results.json"
        charts = self.visualizer.generate_all_charts(results_file)
        
        if not charts:
            print("\n⚠️  No charts generated\n")
            return False
        
        # Generate HTML index
        html_index = self.visualizer.generate_html_index()
        
        print(f"\n✓ Generated {len(charts)} charts")
        print(f"✓ HTML index: {html_index}\n")
        
        return True
    
    def workflow_generate_report(self) -> bool:
        """Workflow: Generate markdown report."""
        if not self.current_config or not self.executor:
            print("\n❌ No test results available\n")
            return False
        
        print("\n📄 GENERATING REPORT\n")
        
        summary = self.executor.generate_summary()
        results_file = Path(self.current_config.output_dir) / "results.json"
        
        # Build report
        report = f"""# Benchmark Report

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Configuration

- **Name:** {self.current_config.name}
- **Models:** {len(self.current_config.models)} models
- **Prompt Configurations:** {self.current_config.prompts.config_count()}
- **Task Types:** {', '.join(self.current_config.params.task_types)}
- **Difficulties:** {', '.join(map(str, self.current_config.params.difficulties))}

## Results Summary

- **Total Tests Run:** {summary.get('total_tests', 0)}
- **Mean Accuracy:** {summary.get('mean_accuracy', 0):.2f}%
- **Best Model:** {summary.get('best_model', ('N/A', 0))[0]} ({summary.get('best_model', ('N/A', 0))[1]:.2f}%)
- **Worst Model:** {summary.get('worst_model', ('N/A', 0))[0]} ({summary.get('worst_model', ('N/A', 0))[1]:.2f}%)
- **Range:** {summary.get('max_accuracy', 0) - summary.get('min_accuracy', 0):.2f}%

## Output

- **Results:** {results_file}
- **Charts:** {self.current_config.output_dir}/charts/
- **HTML Index:** {self.current_config.output_dir}/index.html

---

*Generated by Benchmark Automation System*
"""
        
        # Save report
        report_file = Path(self.current_config.output_dir) / "report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"✓ Report saved: {report_file}\n")
        
        return True
    
    def run_interactive_session(self):
        """Run the interactive benchmark session."""
        self._print_header()
        
        start_time = datetime.now()
        
        while True:
            print("\n📍 MAIN MENU\n")
            print("1. Create new benchmark")
            print("2. Load saved configuration")
            print("3. Run tests")
            print("4. Generate charts")
            print("5. Generate report")
            print("6. View results directory")
            print("7. Exit")
            
            choice = input("\nSelect option (1-7): ").strip()
            
            if choice == "1":
                if self.workflow_create_new():
                    continue
            
            elif choice == "2":
                if self.workflow_load_config():
                    continue
            
            elif choice == "3":
                if self.workflow_execute_tests():
                    continue
            
            elif choice == "4":
                if self.workflow_generate_charts():
                    continue
            
            elif choice == "5":
                if self.workflow_generate_report():
                    continue
            
            elif choice == "6":
                if self.current_config:
                    output_dir = Path(self.current_config.output_dir)
                    print(f"\n📂 Results: {output_dir}")
                    print(f"   Files: {len(list(output_dir.glob('*')))}\n")
                else:
                    print("\n❌ No configuration loaded\n")
            
            elif choice == "7":
                print("\n👋 Exiting...\n")
                break
            
            else:
                print("\n❌ Invalid option\n")
        
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > 60:
            self._print_footer(elapsed)


def main():
    """Entry point."""
    try:
        runner = BenchmarkRunner()
        runner.run_interactive_session()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
