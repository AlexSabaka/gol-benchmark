"""Web server configuration — single source of truth for runtime paths.

All mutable runtime artifacts (results, testsets, annotations, jobs, logs)
live under ``data_root`` (default ``<project>/data``). Override the root
with ``GOL_DATA_ROOT`` or individual subdirectories with their own env
vars if needed.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

# Project root (gol_eval/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _default_data_root() -> str:
    return os.environ.get("GOL_DATA_ROOT", str(PROJECT_ROOT / "data"))


@dataclass
class WebConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    # Umbrella directory for all runtime files. Override with GOL_DATA_ROOT.
    data_root: str = field(default_factory=_default_data_root)
    # Subdirs — populated in __post_init__ from data_root if left blank.
    testsets_dir: str = ""
    results_dir: str = ""
    annotations_dir: str = ""
    reports_dir: str = ""
    charts_dir: str = ""
    jobs_dir: str = ""
    partial_dir: str = ""
    logs_dir: str = ""
    log_file: str = ""
    # configs stays at repo root — it's user-authored, VCS-tracked.
    configs_dir: str = field(default_factory=lambda: str(PROJECT_ROOT / "configs"))
    debug: bool = False

    def __post_init__(self) -> None:
        root = Path(self.data_root)
        if not self.testsets_dir:
            self.testsets_dir = str(root / "testsets")
        if not self.results_dir:
            self.results_dir = str(root / "results")
        if not self.annotations_dir:
            self.annotations_dir = str(root / "annotations")
        if not self.reports_dir:
            self.reports_dir = str(root / "reports")
        if not self.charts_dir:
            self.charts_dir = str(Path(self.reports_dir) / "charts")
        if not self.jobs_dir:
            self.jobs_dir = str(root / "jobs")
        if not self.partial_dir:
            self.partial_dir = str(Path(self.jobs_dir) / "partial")
        if not self.logs_dir:
            self.logs_dir = str(root / "logs")
        if not self.log_file:
            self.log_file = os.environ.get(
                "GOL_LOG_FILE", str(Path(self.logs_dir) / "gol_eval.log")
            )

        for p in (
            self.testsets_dir,
            self.results_dir,
            self.annotations_dir,
            self.reports_dir,
            self.jobs_dir,
            self.partial_dir,
            self.logs_dir,
        ):
            Path(p).mkdir(parents=True, exist_ok=True)

    # ── Derived paths ─────────────────────────────────────────────────────────

    def annotation_path_for(self, result_filename: str) -> Path:
        """Return the annotation sidecar path for a given result filename.

        New layout: ``data/annotations/{result_stem}.json.gz`` — no
        ``_annotations`` suffix, the directory is the namespace.
        """
        name = Path(result_filename).name
        if name.endswith(".json.gz"):
            stem = name[: -len(".json.gz")]
        elif name.endswith(".json"):
            stem = name[: -len(".json")]
        else:
            stem = Path(name).stem
        return Path(self.annotations_dir) / f"{stem}.json.gz"

    def partial_path_for(self, job_id: str) -> Path:
        """Return the pause-checkpoint path for a given job id."""
        return Path(self.partial_dir) / f"{job_id}.json.gz"


# Singleton used across the app
web_config = WebConfig()
