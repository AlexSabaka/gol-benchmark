#!/usr/bin/env python3
"""
Benchmark Test Executor

Handles running evaluation scripts and collecting results.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import re
from benchmark_config import BenchmarkConfig, ModelSpec


@dataclass
class TestResult:
    """Single test result."""
    model: str
    user_prompt: str
    system_prompt: str
    task_type: str
    difficulty: int
    accuracy: float
    success_rate: float
    parse_errors: int
    perfect_scores: int


class TestExecutor:
    """Executes benchmark tests and collects results."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / "execution.log"
    
    def _log(self, message: str, level: str = "INFO"):
        """Log message to file and optionally console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {level}: {message}"
        
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
        
        if self.config.verbosity in ["verbose", "debug"]:
            print(log_msg)
    
    def _build_ari_eval_command(
        self,
        model: str,
        user_prompt: str,
        system_prompt: str,
        difficulty: int,
    ) -> List[str]:
        """Build command for ari_eval.py."""
        cmd = [
            "python", "ari_eval.py",
            "--model", model,
            "--prompt-style", user_prompt,
            "--system-prompt-style", system_prompt.upper(),
            "--difficulty", str(difficulty),
            "--batch-size", str(self.config.params.batch_size),
            "--temperature", str(self.config.params.temperature),
            "--prompt-language", self.config.params.language,
            "--seed", str(self.config.params.seed),
        ]
        
        if self.config.params.thinking_enabled:
            cmd.append("--thinking")
        
        return cmd
    
    def _build_gol_eval_command(
        self,
        model: str,
        user_prompt: str,
        system_prompt: str,
        difficulty: int,
    ) -> List[str]:
        """Build command for gol_eval.py."""
        cmd = [
            "python", "gol_eval.py",
            "--model", model,
            "--prompt-style", user_prompt,
            "--system-prompt-style", system_prompt.upper(),
            "--difficulty", str(difficulty),
            "--batch-size", str(self.config.params.batch_size),
            "--temperature", str(self.config.params.temperature),
            "--prompt-language", self.config.params.language,
            "--seed", str(self.config.params.seed),
        ]
        
        if self.config.params.thinking_enabled:
            cmd.append("--thinking")
        
        return cmd
    
    def _parse_eval_output(self, output: str) -> Optional[Dict]:
        """Parse output from eval scripts to extract results."""
        # Look for the final results table
        accuracy_pattern = r'\|\s*([^|]+?)\s*\|\s*([\d.]+)%\s*\|'
        matches = re.findall(accuracy_pattern, output)
        
        if not matches:
            self._log(f"Could not parse accuracy from output", "WARNING")
            return None
        
        # Extract average accuracy from last match
        try:
            accuracy = float(matches[-1][1])
            return {"accuracy": accuracy}
        except (ValueError, IndexError):
            self._log(f"Error parsing accuracy value", "ERROR")
            return None
    
    def run_test(
        self,
        model: str,
        user_prompt: str,
        system_prompt: str,
        task_type: str,
        difficulty: int,
    ) -> Optional[TestResult]:
        """
        Run a single test configuration.
        
        Returns TestResult on success, None on failure.
        """
        self._log(f"Running: {model} | {user_prompt}+{system_prompt} | {task_type} d{difficulty}")
        
        # Build command based on task type
        if task_type == "MEG":
            cmd = self._build_ari_eval_command(model, user_prompt, system_prompt, difficulty)
        elif task_type == "GoL":
            cmd = self._build_gol_eval_command(model, user_prompt, system_prompt, difficulty)
        else:
            self._log(f"Unsupported task type: {task_type}", "WARNING")
            return None
        
        try:
            # Execute command with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per test
            )
            
            if result.returncode != 0:
                self._log(f"Test failed with return code {result.returncode}", "ERROR")
                if result.stderr:
                    self._log(f"Error: {result.stderr[:200]}", "ERROR")
                return None
            
            # Parse output
            parsed = self._parse_eval_output(result.stdout)
            if not parsed:
                return None
            
            # Create result
            test_result = TestResult(
                model=model,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                task_type=task_type,
                difficulty=difficulty,
                accuracy=parsed.get("accuracy", 0.0),
                success_rate=100.0,
                parse_errors=0,
                perfect_scores=0,
            )
            
            self._log(f"✓ Completed: {test_result.accuracy:.2f}%")
            return test_result
        
        except subprocess.TimeoutExpired:
            self._log(f"Test timed out (>5 minutes)", "ERROR")
            return None
        except Exception as e:
            self._log(f"Exception during test: {str(e)}", "ERROR")
            return None
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all configured tests."""
        total_tests = self.config.total_test_count()
        current_test = 0
        
        self._log(f"Starting benchmark: {self.config.name}")
        self._log(f"Total tests: {total_tests}")
        
        for model_spec in self.config.models:
            for user_prompt, system_prompt in self.config.prompts.get_combinations():
                for task_type in self.config.params.task_types:
                    for difficulty in self.config.params.difficulties:
                        current_test += 1
                        
                        print(f"\n[{current_test}/{total_tests}] Running test...")
                        
                        result = self.run_test(
                            model=model_spec.name,
                            user_prompt=user_prompt,
                            system_prompt=system_prompt,
                            task_type=task_type,
                            difficulty=difficulty,
                        )
                        
                        if result:
                            self.results.append(result)
                            print(f"✓ {model_spec.name}: {result.accuracy:.2f}%")
                        else:
                            print(f"✗ Test failed")
        
        self._log(f"Completed {len(self.results)} tests")
        return self.results
    
    def save_results(self) -> Path:
        """Save results to JSON file."""
        results_file = self.output_dir / "results.json"
        
        results_data = [asdict(r) for r in self.results]
        
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        self._log(f"Saved {len(self.results)} results to {results_file}")
        return results_file
    
    def generate_summary(self) -> Dict:
        """Generate summary statistics."""
        if not self.results:
            return {}
        
        accuracies = [r.accuracy for r in self.results]
        
        summary = {
            "total_tests": len(self.results),
            "mean_accuracy": sum(accuracies) / len(accuracies),
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
            "best_model": max(
                [(r.model, r.accuracy) for r in self.results],
                key=lambda x: x[1]
            ),
            "worst_model": min(
                [(r.model, r.accuracy) for r in self.results],
                key=lambda x: x[1]
            ),
        }
        
        return summary


if __name__ == "__main__":
    # Example
    from benchmark_config import PRESET_CONFIGS
    
    config = PRESET_CONFIGS["quick_test"]
    executor = TestExecutor(config)
    
    print(f"Configured to run {config.total_test_count()} tests")
    print(f"Output directory: {executor.output_dir}")
