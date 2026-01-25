"""
Centralized Path and File Management for GoL Benchmark Suite.

This module provides a unified interface for all file and directory operations,
ensuring consistent naming conventions.

All benchmark artifacts are saved to a single user-specified output directory:
    output_dir/
    ├── config_*.yaml          # YAML configs for test generation
    ├── testset_*.json.gz       # Generated test sets (compressed JSON)
    ├── results_*.json.gz       # Test execution results
    ├── report_*.md             # Analysis reports
    └── charts_*/               # Visualization directories
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
    
    All files are saved to a single output directory specified by the user.
    No subdirectories are created - all artifacts go to the root output directory.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize PathManager.
        
        Args:
            output_dir: Directory where all output files will be saved.
                       If None, uses current directory.
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
    
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
        parts = ["config", name]
        if task_types:
            tasks_str = "-".join(sorted(task_types))
            parts.append(tasks_str)
        parts.append(timestamp)
        
        filename = "_".join(parts) + ".yaml"
        filepath = self.output_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        return filepath
    
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
        filepath = self.output_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        return filepath
    
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
        
        parts = ["results", testset_name, model_str, timestamp]
        filename = "_".join(parts) + ".json.gz"
        
        filepath = self.output_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        return filepath
    
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
            Path to report file in output directory
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        filename = f"report_{report_name}_{timestamp}.{format}"
        filepath = self.output_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        return filepath
    
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
            Path to visualization directory in output directory
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        dirname = f"charts_{report_name}_{timestamp}"
        path = self.output_dir / dirname
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def save_run_metadata(self, metadata: RunMetadata) -> Path:
        """
        Save metadata for a benchmark run (disabled - no longer used).
        
        Returns path but doesn't save anything.
        """
        # Metadata saving disabled - all info is in result files
        return self.output_dir / f"metadata_{metadata.run_id}.json"
    
    def get_recent_runs(self, limit: int = 10) -> List[RunMetadata]:
        """
        Retrieve metadata for recent benchmark runs (disabled - no longer used).
        
        Returns empty list.
        """
        # Metadata tracking disabled
        return []
    
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


def get_path_manager(output_dir: Optional[Path] = None) -> PathManager:
    """
    Get the default PathManager instance.
    
    Args:
        output_dir: Override the output directory (for custom runs)
    
    Returns:
        PathManager instance
    """
    global _default_manager
    if _default_manager is None or output_dir is not None:
        _default_manager = PathManager(output_dir)
    return _default_manager
