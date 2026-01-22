from src.utils.logger import logger
from src.core.types import BaseTestConfig

import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

class BaseModelInterface(ABC):
    """Abstract base class for model interfaces"""

    def __init__(self, config: BaseTestConfig):
        self.config = config

    @abstractmethod
    def preload_models(self) -> None:
        """Preload models to reduce latency"""
        pass

    @abstractmethod
    def supports_reasoning(self, model: str) -> bool:
        """Check if the model supports reasoning"""
        pass

    @abstractmethod
    def query_model(self, model: str, prompt: str, system: str) -> Tuple[str, Dict[str, int]]:
        """Send prompt to model"""
        pass

def create_interface(config: BaseTestConfig) -> BaseModelInterface:
    """Factory function to create the appropriate interface"""

    from src.models.HuggingFaceInterface import HuggingFaceInterface
    from src.models.OllamaInterface import OllamaInterface

    if config.interface_type.lower() == "ollama":
        return OllamaInterface(config)
    elif config.interface_type.lower() == "huggingface":
        return HuggingFaceInterface(config)
    else:
        raise ValueError(f"Unknown interface type: {config.interface_type}. Choose 'ollama' or 'huggingface'")