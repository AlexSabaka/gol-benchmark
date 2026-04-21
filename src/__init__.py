"""
GoL Benchmark - Core Package

A comprehensive benchmarking framework for testing language model reasoning capabilities.

This package provides:
- Core types and configuration (src.core)
- Task engines for GoL, Math, etc. (src.engine)
- Model provider interfaces (src.models)
- Evaluation and scoring (src.evaluation)
- Benchmark scripts (src.benchmarks)
- Visualization and analysis (src.visualization)
- Utilities (src.utils)
"""

__version__ = "2.26.0"
__author__ = "GoL Benchmark Team"

# Import subpackages for convenient access
from . import core
from . import engine
from . import models
from . import evaluation
from . import benchmarks
from . import visualization
from . import utils

__all__ = [
    "__version__",
    "__author__",
    "core",
    "engine",
    "models",
    "evaluation",
    "benchmarks",
    "visualization",
    "utils",
]
