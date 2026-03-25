"""
Model Provider Interfaces

Unified, lightweight interfaces for Ollama, HuggingFace, and
any OpenAI-compatible API.  Every interface exposes the same
``query(prompt, params) -> dict`` contract defined by
:class:`ModelInterface`.
"""

from .BaseModelInterface import ModelInterface, BaseModelInterface  # BaseModelInterface is a compat alias
from .OllamaInterface import OllamaInterface
from .HuggingFaceInterface import HuggingFaceInterface
from .OpenAICompatibleInterface import OpenAICompatibleInterface


def create_model_interface(
    provider: str,
    model_name: str,
    *,
    base_url: str = "",
    api_key: str = "",
    ollama_host: str = "http://localhost:11434",
) -> ModelInterface:
    """Factory: create the right interface from a *provider* string.

    Parameters
    ----------
    provider : str
        One of ``"ollama"``, ``"huggingface"``, ``"openai_compatible"``.
    model_name : str
        Model identifier (e.g. ``"qwen3:0.6b"``).
    base_url : str, optional
        Base URL for OpenAI-compatible endpoints.
    api_key : str, optional
        API key / bearer token.
    ollama_host : str, optional
        Ollama server URL (default ``http://localhost:11434``).
    """
    provider = provider.lower()
    if provider == "ollama":
        return OllamaInterface(model_name, base_url=ollama_host)
    elif provider == "huggingface":
        return HuggingFaceInterface(model_name)
    elif provider == "openai_compatible":
        url = base_url or ollama_host
        return OpenAICompatibleInterface(model_name, base_url=url, api_key=api_key)
    else:
        raise ValueError(
            f"Unknown provider: {provider!r}. "
            "Choose 'ollama', 'huggingface', or 'openai_compatible'."
        )


# Backward-compatible alias
create_interface = create_model_interface

__all__ = [
    "ModelInterface",
    "BaseModelInterface",
    "OllamaInterface",
    "HuggingFaceInterface",
    "OpenAICompatibleInterface",
    "create_model_interface",
    "create_interface",
]
