#!/usr/bin/env python3
"""
Benchmark Configuration Management

Handles configuration structures, validation, and persistence for benchmark testing.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set
from pathlib import Path
from datetime import datetime
import json
import yaml


@dataclass
class ModelSpec:
    """Represents a model to test."""
    name: str
    provider: str = "ollama"  # "ollama", "huggingface", etc.
    size_params: Optional[str] = None  # "1.5B", "0.6B", etc.
    family: Optional[str] = None  # "qwen", "gemma", "acemathf", etc.
    quantization: Optional[str] = None  # "F16", "Q4_K_M", etc.
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)  # ["quantized", "math", "reasoning"]
    
    def __hash__(self):
        return hash((self.name, self.provider))
    
    def __eq__(self, other):
        return isinstance(other, ModelSpec) and self.name == other.name and self.provider == other.provider
    
    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        q_str = f" [{self.quantization}]" if self.quantization else ""
        size_str = f" • {self.size_params}" if self.size_params else ""
        return f"{self.name}{size_str}{q_str}"


@dataclass
class PromptSpec:
    """Represents prompt configuration."""
    user_styles: List[str] = field(default_factory=lambda: ["minimal", "casual", "linguistic"])
    system_styles: List[str] = field(default_factory=lambda: ["analytical", "casual", "adversarial"])
    
    def config_count(self) -> int:
        """Returns total number of configurations."""
        return len(self.user_styles) * len(self.system_styles)
    
    def get_combinations(self) -> List[tuple]:
        """Returns all (user, system) combinations."""
        return [(u, s) for u in self.user_styles for s in self.system_styles]


@dataclass
class TestParams:
    """Represents test execution parameters."""
    difficulties: List[int] = field(default_factory=lambda: [1, 2, 3])
    batch_size: int = 12
    temperature: float = 0.1
    task_types: List[str] = field(default_factory=lambda: ["MEG"])  # MEG, GoL, Ari, Linda, C14
    language: str = "en"  # en, es, fr, de, zh, uk
    thinking_enabled: bool = False
    seed: int = 42
    max_tests_per_model: Optional[int] = None  # None = unlimited


@dataclass
class BenchmarkConfig:
    """Complete benchmark configuration."""
    name: str
    description: str = ""
    models: List[ModelSpec] = field(default_factory=list)
    prompts: PromptSpec = field(default_factory=PromptSpec)
    params: TestParams = field(default_factory=TestParams)
    output_dir: str = ""
    save_config: bool = True
    generate_charts: bool = True
    report_formats: List[str] = field(default_factory=lambda: ["markdown", "json"])
    ollama_host: str = "http://localhost:11434"
    verbosity: str = "normal"  # quiet, normal, verbose, debug
    timestamp: str = ""
    task_type: str = "gol"  # gol, ari, c14, linda
    task_config: Dict = field(default_factory=dict)  # Task-specific configuration
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not self.output_dir:
            self.output_dir = f"results_run_{self.timestamp}"
    
    def total_test_count(self) -> int:
        """Calculates total number of test cases."""
        if not self.models:
            return 0
        configs_per_model = self.prompts.config_count()
        tests_per_config = len(self.params.difficulties) * len(self.params.task_types)
        total = len(self.models) * configs_per_model * tests_per_config
        
        if self.params.max_tests_per_model:
            total = min(total, len(self.models) * self.params.max_tests_per_model)
        
        return total
    
    def estimated_duration_minutes(self, minutes_per_model: float = 20.0) -> float:
        """Estimates total runtime in minutes."""
        return len(self.models) * minutes_per_model
    
    def validate(self) -> tuple[bool, List[str]]:
        """Validates configuration, returns (is_valid, error_messages)."""
        errors = []
        
        if not self.name:
            errors.append("Benchmark name cannot be empty")
        
        if not self.models:
            errors.append("No models selected")
        
        if self.prompts.config_count() == 0:
            errors.append("No prompt configurations selected")
        
        if self.batch_size < 1:
            errors.append("Batch size must be positive")
        
        if not (0 <= self.temperature <= 1):
            errors.append("Temperature must be between 0 and 1")
        
        if not self.params.difficulties:
            errors.append("Must select at least one difficulty level")
        
        if not self.params.task_types:
            errors.append("Must select at least one task type")
        
        if self.params.language not in ["en", "es", "fr", "de", "zh", "uk"]:
            errors.append(f"Invalid language: {self.params.language}")
        
        return len(errors) == 0, errors


class ConfigManager:
    """Manages saving/loading benchmark configurations."""
    
    CONFIG_DIR = Path("benchmark_configs")
    
    @classmethod
    def ensure_dir(cls):
        """Ensures config directory exists."""
        cls.CONFIG_DIR.mkdir(exist_ok=True)
    
    @classmethod
    def save_to_yaml(cls, config: BenchmarkConfig, filepath: Optional[Path] = None) -> Path:
        """Saves configuration to YAML file."""
        cls.ensure_dir()
        
        if filepath is None:
            filepath = cls.CONFIG_DIR / f"config_{config.timestamp}.yaml"
        
        config_dict = asdict(config)
        # Convert ModelSpec objects to dicts
        config_dict['models'] = [asdict(m) for m in config.models]
        config_dict['prompts'] = asdict(config.prompts)
        config_dict['params'] = asdict(config.params)
        
        with open(filepath, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
        
        return filepath
    
    @classmethod
    def load_from_yaml(cls, filepath: Path) -> BenchmarkConfig:
        """Loads configuration from YAML file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        # Reconstruct objects
        models = [ModelSpec(**m) for m in data['models']]
        prompts = PromptSpec(**data['prompts'])
        params = TestParams(**data['params'])
        
        return BenchmarkConfig(
            name=data['name'],
            description=data.get('description', ''),
            models=models,
            prompts=prompts,
            params=params,
            output_dir=data['output_dir'],
            save_config=data.get('save_config', True),
            generate_charts=data.get('generate_charts', True),
            report_formats=data.get('report_formats', ['markdown', 'json']),
            verbosity=data.get('verbosity', 'normal'),
            timestamp=data['timestamp'],
        )
    
    @classmethod
    def save_to_json(cls, config: BenchmarkConfig, filepath: Optional[Path] = None) -> Path:
        """Saves configuration to JSON file."""
        if filepath is None:
            filepath = Path(config.output_dir) / "config.json"
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = asdict(config)
        # Convert ModelSpec objects to dicts
        config_dict['models'] = [asdict(m) for m in config.models]
        config_dict['prompts'] = asdict(config.prompts)
        config_dict['params'] = asdict(config.params)
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        return filepath
    
    @classmethod
    def list_saved_configs(cls) -> List[Path]:
        """Lists all saved configuration files."""
        cls.ensure_dir()
        return sorted(cls.CONFIG_DIR.glob("config_*.yaml"), reverse=True)


# Preset configurations for quick starts
PRESET_CONFIGS = {
    "quick_test": BenchmarkConfig(
        name="Quick Test",
        description="Fast test with 3 models and minimal configs",
        models=[
            ModelSpec("qwen3:0.6b", "0.6B", "qwen"),
            ModelSpec("gemma3:1b", "1B", "gemma"),
            ModelSpec("hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q2_K", "1.5B", "acemathq"),
        ],
        prompts=PromptSpec(
            user_styles=["minimal", "casual"],
            system_styles=["casual", "analytical"],
        ),
        params=TestParams(
            difficulties=[1, 2],
            batch_size=8,
            task_types=["MEG"],
        ),
    ),
    
    "acemath_quantization": BenchmarkConfig(
        name="AceMath Quantization Study",
        description="Compare 4 AceMath quantizations across 9 prompt configs",
        models=[
            ModelSpec("hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:F16", "1.5B", "acemathf"),
            ModelSpec("hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q2_K", "1.5B", "acemathq"),
            ModelSpec("hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q4_K_M", "1.5B", "acemathq"),
            ModelSpec("hf.co/mradermacher/AceMath-1.5B-Instruct-GGUF:Q8_0", "1.5B", "acemathq"),
        ],
        prompts=PromptSpec(
            user_styles=["minimal", "casual", "linguistic"],
            system_styles=["analytical", "casual", "adversarial"],
        ),
        params=TestParams(
            difficulties=[1, 2, 3],
            batch_size=12,
            task_types=["MEG"],
        ),
    ),
    
    "model_comparison": BenchmarkConfig(
        name="General Model Comparison",
        description="Compare qwen3 and gemma3 across prompt styles",
        models=[
            ModelSpec("qwen3:0.6b", "0.6B", "qwen"),
            ModelSpec("gemma3:1b", "1B", "gemma"),
        ],
        prompts=PromptSpec(
            user_styles=["minimal", "casual", "linguistic"],
            system_styles=["analytical", "casual", "adversarial"],
        ),
        params=TestParams(
            difficulties=[1, 2, 3],
            batch_size=12,
            task_types=["MEG"],
        ),
    ),
}


if __name__ == "__main__":
    # Example usage
    config = PRESET_CONFIGS["quick_test"]
    print(f"Config: {config.name}")
    print(f"Total tests: {config.total_test_count()}")
    print(f"Estimated time: {config.estimated_duration_minutes():.1f} minutes")
    
    is_valid, errors = config.validate()
    if is_valid:
        print("✓ Configuration is valid")
    else:
        print("✗ Configuration errors:")
        for error in errors:
            print(f"  - {error}")
