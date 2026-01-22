"""
GoL Benchmark - Core Package

A comprehensive benchmarking framework for testing language model reasoning capabilities.

Backward compatibility layer: Creates module aliases for old import patterns.
Example: `from src.types import DifficultyLevel` → imports from `src.core.types`
"""

__version__ = "1.0.0"
__author__ = "GoL Benchmark Team"

# Create module aliases for backward compatibility
import sys
from pathlib import Path

# Alias old module names to new locations
sys.modules['src.types'] = __import__('src.core.types', fromlist=[''])
sys.modules['src.PromptEngine'] = __import__('src.core.PromptEngine', fromlist=[''])
sys.modules['src.PROMPT_STYLES'] = __import__('src.core.PROMPT_STYLES', fromlist=[''])
sys.modules['src.TestGenerator'] = __import__('src.core.TestGenerator', fromlist=[''])
sys.modules['src.BaseModelInterface'] = __import__('src.models.BaseModelInterface', fromlist=[''])
sys.modules['src.OllamaInterface'] = __import__('src.models.OllamaInterface', fromlist=[''])
sys.modules['src.HuggingFaceInterface'] = __import__('src.models.HuggingFaceInterface', fromlist=[''])
sys.modules['src.GameOfLifeEngine'] = __import__('src.engine.GameOfLifeEngine', fromlist=[''])
sys.modules['src.MathExpressionGenerator'] = __import__('src.engine.MathExpressionGenerator', fromlist=[''])
sys.modules['src.TestEvaluator'] = __import__('src.evaluation.TestEvaluator', fromlist=[''])

__all__ = [
    "__version__",
    "__author__",
]
