# Source Code Organization

**Project:** GoL Benchmark  
**Version:** 1.0.0  
**Last Updated:** November 16, 2025

---

## Directory Structure

```
src/
├── __init__.py                 # Main package initialization
│
├── core/                       # Core interfaces and base classes
│   ├── __init__.py
│   ├── BaseModelInterface.py   # Abstract model interface
│   ├── PromptEngine.py         # Prompt generation engine
│   ├── TestEvaluator.py        # Test result evaluation
│   └── types.py                # Shared data types
│
├── models/                     # Model provider implementations
│   ├── __init__.py
│   ├── OllamaInterface.py      # Ollama local inference
│   └── HuggingFaceInterface.py # HuggingFace integration (WIP)
│
├── engines/                    # Task-specific simulation engines
│   ├── __init__.py
│   ├── GameOfLifeEngine.py     # Conway's Game of Life
│   ├── MathExpressionGenerator.py  # Mathematical expressions
│   ├── TestGenerator.py        # Test case generation
│   └── engine/                 # Additional engine modules
│       └── (existing structure)
│
├── evaluation/                 # Result evaluation and analysis
│   ├── __init__.py
│   ├── TestEvaluator.py        # Result aggregation
│   └── PromptEngine.py         # Prompt system
│
└── utils/                      # Utility functions
    ├── __init__.py
    └── (utility modules)
```

---

## Module Descriptions

### core/ - Core Components

**Purpose:** Fundamental interfaces and base classes

**Files:**

- **BaseModelInterface.py**
  - Abstract base class for all model interactions
  - Defines provider interface
  - Implementations: OllamaInterface, HuggingFaceInterface

- **PromptEngine.py**
  - Prompt generation with templates
  - Multi-language support (6 languages)
  - Style combinations (user × system)
  - Context-aware formatting

- **TestEvaluator.py**
  - Result evaluation and scoring
  - Accuracy calculation (exact and normalized)
  - Performance aggregation
  - Error analysis

- **types.py**
  - Shared data structures
  - Configuration types (AriTestConfig, GoLTestConfig, etc.)
  - Enums (DifficultyLevel, Language, etc.)

### models/ - Model Providers

**Purpose:** Implementations for different LLM backends

**Files:**

- **OllamaInterface.py**
  - Local inference via Ollama
  - Dynamic model discovery
  - Model metadata extraction
  - Caching support

- **HuggingFaceInterface.py**
  - HuggingFace API integration (planned)
  - Remote model access
  - API management

### engines/ - Task Engines

**Purpose:** Task-specific simulation and generation

**Files:**

- **GameOfLifeEngine.py**
  - Conway's Game of Life implementation
  - Grid state management
  - Rule application
  - Pattern support (.cells, .rle files)

- **MathExpressionGenerator.py**
  - Expression tree generation
  - Complexity control
  - Target value generation
  - Variable support

- **TestGenerator.py**
  - Pattern-based test generation
  - Multi-language support
  - Reproducible generation (seeding)
  - Configuration-based customization

- **engine/** subdirectory
  - Additional game engines
  - Cellular automata variants
  - Pattern libraries

### evaluation/ - Evaluation & Analysis

**Purpose:** Result evaluation and performance analysis

**Files:**

- **TestEvaluator.py**
  - Result scoring
  - Accuracy metrics
  - Error rate analysis
  - Aggregation across models

- **PromptEngine.py**
  - (See core/)
  - Included here for evaluation-specific usage

### utils/ - Utilities

**Purpose:** Common utility functions

**Files:**

- **logger.py** - Logging utilities
- **helpers.py** - Common helper functions
- Other utility modules as needed

---

## Import Patterns

### Recommended Imports

```python
# Core components
from src.core import BaseModelInterface, PromptEngine, TestEvaluator
from src.core.types import AriTestConfig, Language, DifficultyLevel

# Models
from src.models import OllamaInterface, HuggingFaceInterface

# Engines
from src.engines import GameOfLifeEngine, MathExpressionGenerator, TestGenerator

# Evaluation
from src.evaluation import TestEvaluator

# Utilities
from src.utils import logger
```

### Legacy Imports (still supported)

```python
# Direct imports from root src/ still work for compatibility
from src.BaseModelInterface import BaseModelInterface
from src.PromptEngine import PromptEngine
from src.types import AriTestConfig
```

---

## File Organization Rationale

### By Functionality (core/, models/, engines/, evaluation/)

Grouping by functionality allows:
- Easy navigation to related components
- Clear separation of concerns
- Simplified dependency management
- Better testing organization

### Backward Compatibility

Root-level imports remain functional:
- Existing code continues to work
- Gradual migration to new structure possible
- No breaking changes

### Future Extensibility

Structure accommodates:
- Additional model providers (models/)
- New benchmark tasks (engines/)
- Advanced analysis tools (evaluation/)
- Utility modules (utils/)

---

## Migration Guide

### For Existing Code

**Old imports:**
```python
from src.BaseModelInterface import BaseModelInterface
from src.PromptEngine import PromptEngine
```

**New imports (recommended):**
```python
from src.core import BaseModelInterface, PromptEngine
```

**Both work currently.** Plan to deprecate root-level imports in v2.0.

### For New Code

Always use new structure:
```python
from src.core import BaseModelInterface
from src.engines import GameOfLifeEngine
from src.models import OllamaInterface
```

---

## Package Dependencies

### Internal Dependencies

```
core/types.py
    └─ (no dependencies)

core/BaseModelInterface.py
    └─ core/types.py

core/PromptEngine.py
    └─ core/types.py

core/TestEvaluator.py
    └─ core/types.py

models/OllamaInterface.py
    └─ core/BaseModelInterface.py

engines/GameOfLifeEngine.py
    └─ core/types.py

engines/MathExpressionGenerator.py
    └─ core/types.py

engines/TestGenerator.py
    └─ core/types.py
    └─ engines/GameOfLifeEngine.py
```

### External Dependencies

```python
import numpy as np
import ollama
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
```

---

## Adding New Modules

### New Task Engine

1. Create file in `src/engines/`
2. Import base classes from `src.core`
3. Add to `engines/__init__.py`
4. Update this index

**Example:**
```python
# src/engines/NewTaskEngine.py
from src.core import BaseModelInterface, types

class NewTaskEngine:
    """New benchmark task implementation."""
    pass
```

### New Model Provider

1. Create file in `src/models/`
2. Inherit from `BaseModelInterface`
3. Add to `models/__init__.py`
4. Update this index

**Example:**
```python
# src/models/NewProvider.py
from src.core import BaseModelInterface

class NewProviderInterface(BaseModelInterface):
    """New model provider implementation."""
    pass
```

### New Utility

1. Create file in `src/utils/`
2. Add to `utils/__init__.py`
3. Import in main package as needed

---

## Maintenance Notes

### Code Style

- Type hints for all functions
- Docstrings for all classes and methods
- Module-level docstrings
- Clear variable naming

### Testing

- Unit tests in `tests/`
- Integration tests for multi-module flows
- Test coverage target: >80%

### Documentation

- Docstrings: Google style
- README: Clear usage examples
- Comments: Explain "why", not "what"

---

## Quick Reference

### Finding Code

| Component | Location |
|-----------|----------|
| Model interface | `src/core/BaseModelInterface.py` |
| Prompt generation | `src/core/PromptEngine.py` |
| Ollama integration | `src/models/OllamaInterface.py` |
| Game of Life | `src/engines/GameOfLifeEngine.py` |
| Math expressions | `src/engines/MathExpressionGenerator.py` |
| Result evaluation | `src/evaluation/TestEvaluator.py` |

### Key Classes

| Class | Module | Purpose |
|-------|--------|---------|
| `BaseModelInterface` | `src.core` | Abstract model provider |
| `PromptEngine` | `src.core` | Prompt generation |
| `OllamaInterface` | `src.models` | Ollama backend |
| `GameOfLifeEngine` | `src.engines` | GoL simulator |
| `MathExpressionGenerator` | `src.engines` | Expression generation |
| `TestEvaluator` | `src.evaluation` | Result scoring |

---

## Version History

### v1.0.0 (Current)
- Reorganized into functional modules
- Added package structure with __init__.py
- Maintained backward compatibility

### Future
- v1.1.0: Deprecation of root-level imports
- v2.0.0: Removal of legacy imports

---

**For more information, see docs/PROJECT_DEVELOPMENT_SUMMARY.md**
