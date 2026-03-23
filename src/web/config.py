"""Web server configuration."""
from dataclasses import dataclass, field
from pathlib import Path

# Project root (gol_eval/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class WebConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    testsets_dir: str = field(default_factory=lambda: str(PROJECT_ROOT / "testsets"))
    results_dir: str = field(default_factory=lambda: str(PROJECT_ROOT / "results"))
    configs_dir: str = field(default_factory=lambda: str(PROJECT_ROOT / "configs"))
    reports_dir: str = field(default_factory=lambda: str(PROJECT_ROOT / "reports"))
    charts_dir: str = field(default_factory=lambda: str(PROJECT_ROOT / "reports" / "charts"))
    debug: bool = False


# Singleton used across the app
web_config = WebConfig()
