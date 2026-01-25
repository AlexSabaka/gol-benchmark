"""
Centralized Path and File Management for GoL Benchmark Suite.

This module provides a unified interface for all file and directory operations,
ensuring consistent naming conventions, organized directory structure, and 
better traceability of test runs.

Directory Structure:
    workspace/
    ├── configs/
    │   └── testsets/           # YAML configs for test generation
    ├── testsets/              # Generated test sets (compressed JSON)
    ├── results/               # Test execution results
    │   ├── runs/              # Individual test runs
    │   └── reports/           # Analysis reports and visualizations
    └── .benchmark_metadata/   # Internal metadata for tracking runs
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import json
import hashlib
from dataclasses import dataclass, asdict


@dataclass
class RunMetadata:
    """Metadata for a benchmark run."""
    run_id: str
    timestamp: str
    models: List[str]
    task_types: List[str]
    testset_path: str
    description: str
    config_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PathManager:
    """
    Centralized manager for all file paths and directory operations.
    
    Provides consistent naming, automatic directory creation, and metadata tracking.
    """
    
    # Root directories (relative to project root)
    CONFIGS_DIR = Path("configs")
    TESTSETS_DIR = Path("testsets")
    RESULTS_DIR = Path("results")
    METADATA_DIR = Path(".benchmark_metadata")
    
    # Subdirectories
    CONFIG_TESTSETS_DIR = CONFIGS_DIR / "testsets"
    RESULTS_RUNS_DIR = RESULTS_DIR / "runs"
    RESULTS_REPORTS_DIR = RESULTS_DIR / "reports"
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """
        Initialize PathManager.
        
        Args:
            workspace_root: Root directory of the workspace. If None, uses current directory.
        """
        self.root = Path(workspace_root) if workspace_root else Path.cwd()
        self._ensure_directory_structure()
    
    def _ensure_directory_structure(self):
        """Create the standard directory structure if it doesn't exist."""
        directories = [
            self.CONFIGS_DIR,
            self.CONFIG_TESTSETS_DIR,
            self.TESTSETS_DIR,
            self.RESULTS_DIR,
            self.RESULTS_RUNS_DIR,
            self.RESULTS_REPORTS_DIR,
            self.METADATA_DIR,
        ]
        
        for directory in directories:
            (self.root / directory).mkdir(parents=True, exist_ok=True)
    
    def get_testset_config_path(
        self,
        name: str,
        task_types: Optional[List[str]] = None,
        timestamp: Optional[str] = None
    ) -> Path:
        """
        Generate path for a test set configuration YAML file.
        
        Args:
            name: Base name for the config
            task_types: List of task types included (e.g., ['arithmetic', 'game_of_life'])
            timestamp: Optional timestamp (auto-generated if None)
        
        Returns:
            Path to config file with descriptive name
        
        Example:
            get_testset_config_path("baseline", ["ari", "gol"])
            -> configs/testsets/baseline_ari-gol_20260123_143000.yaml
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Build descriptive filename
        parts = [name]
        if task_types:
            tasks_str = "-".join(sorted(task_types))
            parts.append(tasks_str)
        parts.append(timestamp)
        
        filename = "_".join(parts) + ".yaml"
        return self.root / self.CONFIG_TESTSETS_DIR / filename
    
    def get_testset_path(
        self,
        config_name: str,
        task_types: Optional[List[str]] = None,
        config_hash: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> Path:
        """
        Generate path for a generated test set (compressed JSON).
        
        Args:
            config_name: Name from the config metadata
            task_types: List of task types
            config_hash: Short hash of config for uniqueness
            timestamp: Optional timestamp
        
        Returns:
            Path to test set file
        
        Example:
            get_testset_path("baseline", ["ari", "gol"], "a3f5c2")
            -> testsets/baseline_ari-gol_a3f5c2_20260123_143000.json.gz
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        parts = ["testset", config_name]
        if task_types:
            tasks_str = "-".join(sorted(task_types))
            parts.append(tasks_str)
        if config_hash:
            parts.append(config_hash[:8])
        parts.append(timestamp)
        
        filename = "_".join(parts) + ".json.gz"
        return self.root / self.TESTSETS_DIR / filename
    
    def get_results_path(
        self,
        models: List[str],
        testset_name: str,
        run_id: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> Path:
        """
        Generate path for test execution results.
        
        Args:
            models: List of model names tested
            testset_name: Name of the test set used
            run_id: Unique run identifier (auto-generated if None)
            timestamp: Optional timestamp
        
        Returns:
            Path to results file
        
        Example:
            get_results_path(["qwen3_0.6b", "gemma3_1b"], "baseline_ari-gol")
            -> results/runs/baseline_ari-gol_qwen3-gemma3_run_abc123_20260123_143000.json.gz
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if run_id is None:
            run_id = self._generate_run_id()
        
        # Simplified model names
        model_str = "-".join([self._simplify_model_name(m) for m in models])
        
        parts = [testset_name, model_str, f"run_{run_id}", timestamp]
        filename = "_".join(parts) + ".json.gz"
        
        return self.root / self.RESULTS_RUNS_DIR / filename
    
    def get_report_path(
        self,
        report_name: str,
        format: str = "md",
        timestamp: Optional[str] = None
    ) -> Path:
        """
        Generate path for analysis reports.
        
        Args:
            report_name: Descriptive name for the report
            format: Report format (md, html, json)
            timestamp: Optional timestamp
        
        Returns:
            Path to report file
        
        Example:
            get_report_path("multi_model_comparison")
            -> results/reports/multi_model_comparison_20260123_143000.md
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        filename = f"{report_name}_{timestamp}.{format}"
        return self.root / self.RESULTS_REPORTS_DIR / filename
    
    def get_visualization_dir(
        self,
        report_name: str,
        timestamp: Optional[str] = None
    ) -> Path:
        """
        Generate directory for report visualizations.
        
        Args:
            report_name: Name matching the associated report
            timestamp: Optional timestamp
        
        Returns:
            Path to visualization directory
        
        Example:
            get_visualization_dir("multi_model_comparison")
            -> results/reports/multi_model_comparison_20260123_143000_charts/
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        dirname = f"{report_name}_{timestamp}_charts"
        path = self.root / self.RESULTS_REPORTS_DIR / dirname
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def save_run_metadata(self, metadata: RunMetadata) -> Path:
        """
        Save metadata for a benchmark run.
        
        Args:
            metadata: Run metadata to save
        
        Returns:
            Path to saved metadata file
        """
        filename = f"run_{metadata.run_id}.json"
        filepath = self.root / self.METADATA_DIR / filename
        
        with open(filepath, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        return filepath
    
    def get_recent_runs(self, limit: int = 10) -> List[RunMetadata]:
        """
        Retrieve metadata for recent benchmark runs.
        
        Args:
            limit: Maximum number of runs to return
        
        Returns:
            List of RunMetadata objects, sorted by timestamp (newest first)
        """
        metadata_files = sorted(
            (self.root / self.METADATA_DIR).glob("run_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]
        
        runs = []
        for filepath in metadata_files:
            try:
                with open(filepath) as f:
                    data = json.load(f)
                runs.append(RunMetadata(**data))
            except Exception:
                continue
        
        return runs
    
    @staticmethod
    def _generate_run_id() -> str:
        """Generate a short unique run ID."""
        timestamp = datetime.now().isoformat()
        hash_obj = hashlib.md5(timestamp.encode())
        return hash_obj.hexdigest()[:6]
    
    @staticmethod
    def _simplify_model_name(model: str) -> str:
        """
        Simplify model name for use in filenames.
        
        Examples:
            "qwen3:0.6b" -> "qwen3-0.6b"
            "gemma3:1b" -> "gemma3-1b"
            "llama-3.1-8b-instruct" -> "llama-3.1-8b"
        """
        # Replace colons with hyphens
        simplified = model.replace(":", "-").replace("/", "-")
        
        # Remove common suffixes
        for suffix in ["-instruct", "-chat", "-base"]:
            if simplified.lower().endswith(suffix):
                simplified = simplified[:-len(suffix)]
        
        return simplified
    
    def cleanup_old_files(
        self,
        directory: Path,
        days: int = 30,
        pattern: str = "*",
        dry_run: bool = True
    ) -> List[Path]:
        """
        Clean up old files from a directory.
        
        Args:
            directory: Directory to clean
            days: Delete files older than this many days
            pattern: Glob pattern for files to consider
            dry_run: If True, only report what would be deleted
        
        Returns:
            List of files that were (or would be) deleted
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(days=days)
        old_files = []
        
        for filepath in (self.root / directory).glob(pattern):
            if filepath.is_file():
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                if mtime < cutoff_time:
                    old_files.append(filepath)
                    if not dry_run:
                        filepath.unlink()
        
        return old_files


# Global instance for convenience
_default_manager = None


def get_path_manager(workspace_root: Optional[Path] = None) -> PathManager:
    """
    Get the default PathManager instance.
    
    Args:
        workspace_root: Override the workspace root (for testing)
    
    Returns:
        PathManager instance
    """
    global _default_manager
    if _default_manager is None or workspace_root is not None:
        _default_manager = PathManager(workspace_root)
    return _default_manager
