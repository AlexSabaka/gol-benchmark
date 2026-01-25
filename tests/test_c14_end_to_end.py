"""
End-to-End Test for C14 (1D Cellular Automata) Benchmark
Tests the complete 3-stage pipeline: Generate → Run → Analyze

This validates:
1. Test set generation from YAML config
2. Model execution and parsing
3. Result analysis and reporting
"""
import json
import gzip
import tempfile
import shutil
from pathlib import Path
import subprocess
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_c14_end_to_end():
    """
    Complete end-to-end test of C14 benchmark pipeline.
    Tests all 3 stages with a minimal configuration.
    """
    print("="*80)
    print("C14 CELLULAR AUTOMATA END-TO-END TEST")
    print("="*80)
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        testset_dir = tmpdir_path / "testsets"
        results_dir = tmpdir_path / "results"
        reports_dir = tmpdir_path / "reports"
        
        testset_dir.mkdir()
        results_dir.mkdir()
        reports_dir.mkdir()
        
        # ========================================================================
        # STAGE 1: Generate Test Set
        # ========================================================================
        print("\n" + "─"*80)
        print("STAGE 1: Generating C14 Test Set")
        print("─"*80)
        
        config_yaml = """
metadata:
  name: "c14_e2e_test_v1"
  version: "1.0"
  schema_version: "1.0.0"
  description: "End-to-end test for C14 benchmark"
  created_by: "test_c14_end_to_end.py"
  task_type: "multi-task"

tasks:
  - type: "cellular_automata_1d"
    generation:
      seed: 42
      rule_numbers: [30, 90]
      width: 12
      steps: 3
      cases_per_rule: 3
      boundary_condition: "wrap"
      density: 0.3
    prompt_configs:
      - name: "minimal_analytical"
        user_style: "minimal"
        system_style: "analytical"

sampling:
  temperature: 0.1
  max_tokens: 512

execution:
  no_thinking: true
"""
        
        config_path = tmpdir_path / "c14_test_config.yaml"
        with open(config_path, 'w') as f:
            f.write(config_yaml)
        
        # Run Stage 1
        cmd = [
            sys.executable, 
            str(project_root / "src" / "stages" / "generate_testset.py"),
            str(config_path),
            "--output-dir", str(testset_dir)
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode != 0:
            print("❌ STAGE 1 FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
        
        print("✅ Stage 1 completed successfully")
        
        # Find generated test set (may be in project testsets/ dir, not tmpdir)
        testset_files = list(testset_dir.glob("testset_*.json.gz"))
        if not testset_files:
            # Try parent directory (testsets/ might be nested)
            testset_files = list(tmpdir_path.glob("**/testset_*.json.gz"))
        if not testset_files:
            # Try project testsets directory
            project_testsets = project_root / "testsets"
            testset_files = sorted(project_testsets.glob("testset_c14_e2e_*.json.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if not testset_files:
            print("❌ No test set file generated")
            print(f"   Searched in: {testset_dir}")
            print(f"   Also searched recursively in: {tmpdir_path}")
            print(f"   Also searched in: {project_root / 'testsets'}")
            # List what files were created
            all_files = list(tmpdir_path.rglob("*"))
            print(f"   Files in tmpdir: {[str(f.relative_to(tmpdir_path)) for f in all_files if f.is_file()]}")
            return False
        
        testset_path = testset_files[0]
        print(f"📦 Generated test set: {testset_path.name}")
        
        # Validate test set structure
        with gzip.open(testset_path, 'rt') as f:
            testset_data = json.load(f)
        
        assert 'metadata' in testset_data, "Missing metadata in test set"
        assert 'test_cases' in testset_data, "Missing test_cases in test set"
        assert len(testset_data['test_cases']) == 6, f"Expected 6 test cases (2 rules × 3 cases), got {len(testset_data['test_cases'])}"
        
        # Validate C14 test case structure
        for tc in testset_data['test_cases']:
            assert 'task_type' in tc, "Missing task_type"
            assert tc['task_type'] == 'cellular_automata_1d', f"Wrong task type: {tc['task_type']}"
            assert 'task_params' in tc, "Missing task_params"
            
            # Check task_params has required fields
            params = tc['task_params']
            assert 'rule_number' in params, "Missing rule_number in task_params"
            assert 'initial_state' in params, "Missing initial_state in task_params"
            assert 'expected_next_state' in params, "Missing expected_next_state in task_params"
            
            # Check prompts
            assert 'prompts' in tc, "Missing prompts"
            assert 'user' in tc['prompts'] or 'full' in tc['prompts'], "Missing user prompt"
            assert 'system' in tc['prompts'], "Missing system prompt"
        
        print(f"✅ Test set validated: {len(testset_data['test_cases'])} test cases")
        
        # Check for diversity (different initial states)
        initial_states = [str(tc['task_params']['initial_state']) for tc in testset_data['test_cases']]
        unique_states = len(set(initial_states))
        print(f"   Diversity check: {unique_states}/{len(initial_states)} unique initial states")
        
        if unique_states == 1:
            print("   ⚠️  WARNING: All initial states are identical (diversity issue)")
        else:
            print(f"   ✅ Good diversity: {unique_states} unique states")
        
        # ========================================================================
        # STAGE 2: Execute on Model
        # ========================================================================
        print("\n" + "─"*80)
        print("STAGE 2: Executing Test Set on Model")
        print("─"*80)
        
        # Check if Ollama is available
        try:
            subprocess.run(['ollama', 'list'], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            print("⚠️  Ollama not available - skipping Stage 2 & 3")
            print("✅ Stage 1 validation passed - partial success")
            return True
        
        # Use lightweight model for testing
        test_model = "qwen3:0.6b"
        
        cmd = [
            sys.executable,
            str(project_root / "src" / "stages" / "run_testset.py"),
            str(testset_path),
            "--model", test_model,
            "--provider", "ollama",
            "--output-dir", str(results_dir)
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print("❌ STAGE 2 FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
        
        print("✅ Stage 2 completed successfully")
        
        # Find results file
        result_files = list(results_dir.glob("results_*.json.gz"))
        if not result_files:
            print("❌ No results file generated")
            return False
        
        results_path = result_files[0]
        print(f"📊 Generated results: {results_path.name}")
        
        # Validate results structure
        with gzip.open(results_path, 'rt') as f:
            results_data = json.load(f)
        
        assert 'metadata' in results_data, "Missing metadata in results"
        assert 'evaluations' in results_data, "Missing evaluations in results"
        assert len(results_data['evaluations']) == 6, f"Expected 6 evaluations, got {len(results_data['evaluations'])}"
        
        # Analyze results
        total_tests = len(results_data['evaluations'])
        parse_errors = sum(1 for e in results_data['evaluations'] if e.get('parse_error', False))
        correct = sum(1 for e in results_data['evaluations'] if e.get('accuracy', 0) == 1.0)
        avg_accuracy = sum(e.get('accuracy', 0) for e in results_data['evaluations']) / total_tests
        
        print(f"   Total tests: {total_tests}")
        print(f"   Parse errors: {parse_errors}/{total_tests} ({parse_errors/total_tests*100:.1f}%)")
        print(f"   Correct predictions: {correct}/{total_tests} ({correct/total_tests*100:.1f}%)")
        print(f"   Average accuracy: {avg_accuracy:.2%}")
        
        if parse_errors == total_tests:
            print("   ⚠️  All tests had parse errors - check parsing logic")
        elif parse_errors > total_tests * 0.5:
            print("   ⚠️  High parse error rate - may need parser improvements")
        else:
            print("   ✅ Acceptable parse error rate")
        
        # ========================================================================
        # STAGE 3: Analyze Results
        # ========================================================================
        print("\n" + "─"*80)
        print("STAGE 3: Analyzing Results")
        print("─"*80)
        
        report_path = reports_dir / "c14_test_report.md"
        
        cmd = [
            sys.executable,
            str(project_root / "src" / "stages" / "analyze_results.py"),
            str(results_path),
            "--output", str(report_path),
            "--output-dir", str(reports_dir)
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print("❌ STAGE 3 FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
        
        print("✅ Stage 3 completed successfully")
        
        # Validate report was created
        if not report_path.exists():
            print("❌ Report file not created")
            return False
        
        report_size = report_path.stat().st_size
        print(f"📄 Generated report: {report_path.name} ({report_size} bytes)")
        
        # Check report content
        with open(report_path, 'r') as f:
            report_content = f.read()
        
        # Basic validation
        assert len(report_content) > 0, "Empty report"
        assert test_model in report_content, f"Model {test_model} not mentioned in report"
        
        print("   ✅ Report validated")
        
        # ========================================================================
        # FINAL SUMMARY
        # ========================================================================
        print("\n" + "="*80)
        print("END-TO-END TEST SUMMARY")
        print("="*80)
        print("✅ Stage 1: Test set generation - PASSED")
        print("✅ Stage 2: Model execution - PASSED")
        print("✅ Stage 3: Result analysis - PASSED")
        print("="*80)
        print(f"📊 Final Statistics:")
        print(f"   Test Cases: {total_tests}")
        print(f"   Accuracy: {avg_accuracy:.2%}")
        print(f"   Parse Errors: {parse_errors}/{total_tests}")
        print(f"   Unique Initial States: {unique_states}/{len(initial_states)}")
        print("="*80)
        print("✅ C14 END-TO-END TEST PASSED")
        print("="*80)
        
        return True


if __name__ == "__main__":
    try:
        success = test_c14_end_to_end()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
