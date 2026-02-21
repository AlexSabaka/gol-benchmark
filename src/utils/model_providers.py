#!/usr/bin/env python3
"""
Model Provider Interfaces

Abstraction for different model providers (Ollama, HuggingFace, etc.)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
import subprocess
import json


@dataclass
class ModelInfo:
    """Information about an available model."""
    name: str
    size_bytes: int
    size_human: str
    quantization: Optional[str] = None  # "F16", "Q4_K_M", etc.
    modified_at: str = ""
    digest: str = ""
    family: str = ""  # "llama", "gemma", "qwen", etc.
    
    @property
    def size_params(self) -> str:
        """Extract parameter size if available."""
        import re
        
        # First try to parse from model name (e.g., "qwen3:0.6b", "gemma3:1b")
        size_match = re.search(r':(\d+\.?\d*)[bB]', self.name)
        if size_match:
            size_value = float(size_match.group(1))
            if size_value < 1:
                return f"{size_value*1000:.0f}M"
            else:
                return f"{size_value:.1f}B"
        
        # Fallback: calculate from bytes with heuristic
        if self.size_bytes > 0:
            params_bytes = self.size_bytes / 6
            if params_bytes < 1e9:
                return f"{params_bytes/1e6:.1f}M"
            else:
                return f"{params_bytes/1e9:.1f}B"
        
        return "Unknown"
    
    @property
    def display_name(self) -> str:
        """Human-readable name with size and quantization."""
        # Show parameter size if available
        size_str = self.size_params
        if size_str and size_str != "Unknown":
            size_display = f" [{size_str}]"
        else:
            size_display = f" [{self.size_human}]"
        
        q_str = f" {self.quantization}" if self.quantization else ""
        return f"{self.name}{size_display}{q_str}"


class ModelProvider(ABC):
    """Abstract base class for model providers."""
    
    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """List available models."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available/connected."""
        pass


class OllamaProvider(ModelProvider):
    """Ollama model provider."""
    
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host.rstrip("/")
        self._models_cache: Optional[List[ModelInfo]] = None
    
    def _is_default_host(self) -> bool:
        return self.host in ("http://localhost:11434", "http://127.0.0.1:11434")
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        # For non-default hosts always use REST API
        if not self._is_default_host():
            return self._is_available_via_api()
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        # Fallback to REST API check
        return self._is_available_via_api()
    
    def _is_available_via_api(self) -> bool:
        """Check availability via Ollama REST API."""
        import urllib.request
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False
    
    def _list_models_via_api(self) -> List[ModelInfo]:
        """List models via Ollama REST API (supports remote hosts)."""
        import urllib.request
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            
            models = []
            for m in data.get('models', []):
                name = m.get('name', '')
                size_bytes = m.get('size', 0)
                size_human = self._bytes_to_human(size_bytes)
                quantization = self._extract_quantization(name)
                family = self._extract_family(name)
                models.append(ModelInfo(
                    name=name,
                    size_bytes=size_bytes,
                    size_human=size_human,
                    quantization=quantization,
                    family=family,
                    modified_at=m.get('modified_at', ''),
                    digest=m.get('digest', ''),
                ))
            self._models_cache = models
            return models
        except Exception as e:
            print(f"⚠️  Error listing Ollama models via API: {e}")
            return []
    
    @staticmethod
    def _bytes_to_human(size_bytes: int) -> str:
        """Convert bytes to human-readable size string."""
        for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
    
    def list_models(self) -> List[ModelInfo]:
        """Get list of models from Ollama."""
        if self._models_cache is not None:
            return self._models_cache
        
        # Always use REST API when host is non-default
        if not self._is_default_host():
            return self._list_models_via_api()
        
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return self._list_models_via_api()
            
            models = []
            # Parse ollama list output
            lines = result.stdout.strip().split('\n')
            
            for line in lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) < 3:
                    continue
                
                name = parts[0]
                size_human = parts[2]
                
                # Parse size to bytes
                size_bytes = self._parse_size(size_human)
                
                # Extract quantization from name if present
                quantization = self._extract_quantization(name)
                
                # Extract family from model name
                family = self._extract_family(name)
                
                model_info = ModelInfo(
                    name=name,
                    size_bytes=size_bytes,
                    size_human=size_human,
                    quantization=quantization,
                    family=family,
                )
                models.append(model_info)
            
            self._models_cache = models
            return models
        
        except Exception as e:
            print(f"⚠️  Error listing Ollama models: {e}")
            return []
    
    @staticmethod
    def _parse_size(size_str: str) -> int:
        """Parse size string (e.g., '4.7 GB') to bytes."""
        import logging
        
        try:
            parts = size_str.split()
            if len(parts) != 2:
                logging.warning(f"Unexpected size format: '{size_str}' - expected 'number unit'")
                return 0
            
            size, unit = float(parts[0]), parts[1].upper()
            
            multipliers = {
                'B': 1,
                'KB': 1024,
                'MB': 1024**2,
                'GB': 1024**3,
                'TB': 1024**4,
            }
            
            if unit not in multipliers:
                logging.warning(f"Unknown size unit: '{unit}' in '{size_str}'")
                return int(size)  # Return raw number as fallback
            
            return int(size * multipliers[unit])
        except Exception as e:
            logging.warning(f"Failed to parse size '{size_str}': {e}")
            return 0
    
    @staticmethod
    def _extract_quantization(name: str) -> Optional[str]:
        """Extract quantization format from model name."""
        # Common GGUF quantizations
        quantizations = ['F16', 'F32', 'Q2_K', 'Q3_K', 'Q4_K_M', 'Q4_K_S', 
                        'Q5_K_M', 'Q5_K_S', 'Q6_K', 'Q8_0']
        
        for q in quantizations:
            if q in name.upper():
                return q
        
        return None
    
    @staticmethod
    def _extract_family(name: str) -> str:
        """Extract model family from name."""
        families = {
            'qwen': ['qwen', 'qwq'],
            'gemma': ['gemma'],
            'llama': ['llama', 'lama'],
            'phi': ['phi'],
            'mistral': ['mistral', 'minstral'],
            'neural': ['neural'],
            'openchat': ['openchat'],
            'dolphin': ['dolphin'],
            'acemath': ['acemath'],
        }
        
        name_lower = name.lower()
        
        for family, keywords in families.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return family
        
        return "other"


class HuggingFaceProvider(ModelProvider):
    """HuggingFace model provider (placeholder)."""
    
    def is_available(self) -> bool:
        """Check if HF CLI is available."""
        try:
            result = subprocess.run(
                ["huggingface-cli", "whoami"],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def list_models(self) -> List[ModelInfo]:
        """Get list of models from HuggingFace."""
        # TODO: Implement HF model listing
        return []


class ModelProviderManager:
    """Manages multiple model providers."""
    
    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.providers = {
            'ollama': OllamaProvider(host=ollama_host),
            'huggingface': HuggingFaceProvider(),
        }
    
    def set_ollama_host(self, host: str):
        """Update the Ollama provider with a new host and clear its cache."""
        self.providers['ollama'] = OllamaProvider(host=host)
    
    def get_available_providers(self) -> Dict[str, ModelProvider]:
        """Get all available providers."""
        return {
            name: provider
            for name, provider in self.providers.items()
            if provider.is_available()
        }
    
    def list_all_models(self) -> Dict[str, List[ModelInfo]]:
        """List all models from all available providers."""
        result = {}
        for name, provider in self.get_available_providers().items():
            result[name] = provider.list_models()
        return result
    
    def list_models_by_provider(self, provider_name: str) -> List[ModelInfo]:
        """List models from specific provider."""
        if provider_name not in self.providers:
            return []
        provider = self.providers[provider_name]
        if not provider.is_available():
            return []
        return provider.list_models()
    
    def group_models(
        self,
        models: List[ModelInfo],
        group_by: str = "family"
    ) -> Dict[str, List[ModelInfo]]:
        """Group models by specified criterion."""
        groups = {}
        
        for model in models:
            if group_by == "family":
                key = model.family
            elif group_by == "quantization":
                key = model.quantization or "Full Precision"
            elif group_by == "size":
                # Group by approximate size
                if model.size_bytes < 2e9:
                    key = "< 2B"
                elif model.size_bytes < 8e9:
                    key = "2-8B"
                elif model.size_bytes < 15e9:
                    key = "8-15B"
                else:
                    key = "> 15B"
            else:
                key = "Other"
            
            if key not in groups:
                groups[key] = []
            groups[key].append(model)
        
        # Sort groups
        return dict(sorted(groups.items()))
    
    def filter_models(
        self,
        models: List[ModelInfo],
        **filters
    ) -> List[ModelInfo]:
        """Filter models by criteria."""
        result = models
        
        if 'family' in filters:
            families = filters['family']
            if not isinstance(families, list):
                families = [families]
            result = [m for m in result if m.family in families]
        
        if 'quantization' in filters:
            quants = filters['quantization']
            if not isinstance(quants, list):
                quants = [quants]
            result = [m for m in result if m.quantization in quants]
        
        if 'min_size' in filters:
            min_size = filters['min_size']
            result = [m for m in result if m.size_bytes >= min_size]
        
        if 'max_size' in filters:
            max_size = filters['max_size']
            result = [m for m in result if m.size_bytes <= max_size]
        
        return result


if __name__ == "__main__":
    # Test
    manager = ModelProviderManager()
    
    print("Available providers:")
    for name in manager.get_available_providers().keys():
        print(f"  ✓ {name}")
    
    print("\nOllama models:")
    ollama_models = manager.list_models_by_provider("ollama")
    for model in ollama_models:
        print(f"  • {model.display_name}")
    
    if ollama_models:
        print("\nGrouped by family:")
        grouped = manager.group_models(ollama_models, group_by="family")
        for family, models in grouped.items():
            print(f"  {family}:")
            for model in models:
                print(f"    • {model.display_name}")
