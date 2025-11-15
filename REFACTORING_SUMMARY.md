# PromptEngine Refactoring - Complete Overview

## What Was Refactored

The prompt management system was refactored from scattered, duplicated definitions across multiple files into a unified, coherent **PromptEngine** system.

### Files Affected

**Scattered Prompts (Before):**
- `src/PROMPT_STYLES.py` - Game of Life prompts only (300+ lines)
- `c14_eval.py` - Duplicated math expression prompts
- `src/MathExpressionGenerator.py` - Another copy of math expression prompts

**Unified System (After):**
- `src/PromptEngine.py` - Single 600+ line coherent system (NEW)

## The Solution

### Core Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PromptEngine                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Input:  PromptContext                                  │
│          - task_type (game_of_life, math_expression)   │
│          - language (en, fr, es, de, zh, ua)          │
│          - style (linguistic, casual, minimal, ...)    │
│          - system_style (analytical, casual, ...)      │
│          - custom_vars (all task variables)            │
│                                                         │
│  Processing:                                            │
│  1. Lookup SYSTEM_PROMPTS[language][system_style]      │
│  2. Lookup TASK_PROMPTS[task][language][style]         │
│  3. Substitute variables from PromptContext            │
│                                                         │
│  Output: PromptResult                                   │
│          - system_prompt (instructions for AI)         │
│          - user_prompt (task for AI)                   │
│          - metadata (generation info)                  │
└─────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Type-Safe Enumerations

Instead of string keys that are error-prone:

```python
class Language(str, Enum):
    EN = "en"  # English
    FR = "fr"  # French
    ES = "es"  # Spanish
    DE = "de"  # German
    ZH = "zh"  # Chinese
    UA = "ua"  # Ukrainian

class PromptStyle(str, Enum):
    LINGUISTIC = "linguistic"
    CASUAL = "casual"
    MINIMAL = "minimal"
    EXAMPLES = "examples"
    RULES_MATH = "rules_math"

class SystemPromptStyle(str, Enum):
    ANALYTICAL = "analytical"
    CASUAL = "casual"
    ADVERSARIAL = "adversarial"
    NONE = "none"

class TaskType(str, Enum):
    GAME_OF_LIFE = "game_of_life"
    MATH_EXPRESSION = "math_expression"
```

#### 2. Context Management

```python
@dataclass
class PromptContext:
    task_type: TaskType
    language: Language = Language.EN
    style: PromptStyle = PromptStyle.LINGUISTIC
    system_style: SystemPromptStyle = SystemPromptStyle.ANALYTICAL
    custom_vars: Dict[str, Any] = field(default_factory=dict)
```

#### 3. Unified Result

```python
@dataclass
class PromptResult:
    system_prompt: str
    user_prompt: str
    metadata: Dict[str, Any]  # Task info for tracking
```

#### 4. Main Engine

```python
class PromptEngine:
    def generate(context: PromptContext) -> PromptResult:
        """Generate both system and user prompts"""
        
    def get_system_prompt(context) -> str:
        """Get system prompt only"""
        
    def get_user_prompt(context) -> str:
        """Get user prompt only"""
        
    def list_supported(task_type: TaskType) -> Dict:
        """Discover available languages, styles, system_styles"""
```

#### 5. Prompt Storage

```python
SYSTEM_PROMPTS = {
    Language.EN: {
        SystemPromptStyle.ANALYTICAL: "You are an expert...",
        SystemPromptStyle.CASUAL: "You are friendly...",
        SystemPromptStyle.ADVERSARIAL: "You are efficient...",
        SystemPromptStyle.NONE: "",
    }
}

GAME_OF_LIFE_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: "Here are the EXACT rules...",
        PromptStyle.CASUAL: "Here's a Game of Life grid...",
        # ... 5 styles
    },
    Language.ES: { ... },
    Language.FR: { ... },
    # ... 6 languages total
}

MATH_EXPRESSION_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: "Given the mathematical expression...",
        PromptStyle.CASUAL: "Hey! Can you solve this...",
        # ... 5 styles
    }
}
```

## Comparison: Before vs. After

### Before: Scattered Approach

```python
# Multiple import sources
from src.PROMPT_STYLES import PROMPT_STYLES_EN, SYSTEM_PROMPT_STYLES_EN
from src.MathExpressionGenerator import PROMPT_STYLES_EN as MATH_STYLES

# Manual dictionary lookups
style = "linguistic"  # String, easy to typo
prompt = PROMPT_STYLES_EN[style].format(grid_str=grid, l=l, d=d)

# System prompt from different file
system = SYSTEM_PROMPT_STYLES_EN["analytical"]

# Issues:
# - No type checking
# - Duplication (prompts in 2+ files)
# - Hard to discover options
# - Manual variable management
# - Generic error messages
```

### After: Unified PromptEngine

```python
# Single import
from src.PromptEngine import PromptEngine, create_gol_context

# Type-safe context creation
context = create_gol_context(
    language="en",           # Type-checked: Language enum
    style="linguistic",      # Type-checked: PromptStyle enum
    system_style="analytical",  # Type-checked: SystemPromptStyle enum
    grid_str=grid,
    l=l,
    d=d
)

# Single call gets both prompts
result = engine.generate(context)
system = result.system_prompt
prompt = result.user_prompt

# Benefits:
# - Type safety with enums
# - Single source of truth
# - Discoverable (engine.list_supported())
# - Clean context management
# - Clear error messages
```

## Supported Configurations

### Game of Life
- **6 Languages**: English, Spanish, French, German, Chinese, Ukrainian
- **5 Styles**: Linguistic, Casual, Minimal, Examples, Rules (Math)
- **4 System Styles**: Analytical, Casual, Adversarial, None
- **Total Combinations**: 6 × 5 × 4 = 120 different configurations

### Math Expression
- **1 Language**: English (easily extensible)
- **5 Styles**: Linguistic, Casual, Minimal, Examples, Rules (Math)
- **4 System Styles**: Analytical, Casual, Adversarial, None
- **Total Combinations**: 1 × 5 × 4 = 20 configurations

## Usage Examples

### Simple Case: Get one prompt

```python
from src.PromptEngine import PromptEngine, create_gol_context

engine = PromptEngine()

context = create_gol_context(
    grid_str="1 0 1\n0 1 0\n1 0 1",
    l="1",
    d="0"
)

result = engine.generate(context)
print(result.user_prompt)
```

### Complex Case: Batch generation with discovery

```python
from src.PromptEngine import PromptEngine, TaskType

engine = PromptEngine()

# Discover all options
supported = engine.list_supported(TaskType.GAME_OF_LIFE)

# Batch generate
for lang in supported["languages"]:
    for style in supported["styles"]:
        context = create_gol_context(
            language=lang,
            style=style,
            grid_str=current_grid,
            l="1",
            d="0"
        )
        result = engine.generate(context)
        # Process result...
```

## Key Improvements

| Aspect | Before | After |
|--------|--------|-------|
| **Single Source of Truth** | No (scattered across 3 files) | Yes (one file) |
| **Type Safety** | No (string keys) | Yes (enums) |
| **Error Messages** | Generic KeyError | Clear ValueError |
| **Discoverability** | Read source code | `engine.list_supported()` |
| **Variable Management** | Manual dict pass | PromptContext class |
| **System + User Prompts** | Separate retrieval | Single PromptResult |
| **Extensibility** | Add files/dicts | Add to central dicts |
| **Testing** | Hard to mock | Easy to test |
| **IDE Support** | Limited | Full autocomplete |
| **Lines of Duplicated Code** | ~200 lines | 0 lines |

## Migration Path

### Step 1: Update Imports

```python
# Old
from src.PROMPT_STYLES import PROMPT_STYLES_EN

# New
from src.PromptEngine import PromptEngine, create_gol_context
```

### Step 2: Replace Prompt Access

```python
# Old
prompt = PROMPT_STYLES_EN["linguistic"].format(grid_str=grid)
system = SYSTEM_PROMPT_STYLES_EN["analytical"]

# New
engine = PromptEngine()
context = create_gol_context(
    style="linguistic",
    grid_str=grid,
    l="1",
    d="0"
)
result = engine.generate(context)
prompt = result.user_prompt
system = result.system_prompt
```

### Step 3: Update Variable Passing

```python
# Old
context_vars = {
    "grid_str": grid,
    "l": live_symbol,
    "d": dead_symbol,
    "w": width,
    "h": height
}
prompt = template.format(**context_vars)

# New
context = create_gol_context(
    grid_str=grid,
    l=live_symbol,
    d=dead_symbol,
    w=width,
    h=height
)
result = engine.generate(context)
```

## Files Created

1. **src/PromptEngine.py** (600+ lines)
   - Main implementation
   - All prompt templates
   - Enums and classes
   - Convenience functions
   - CLI examples

2. **MIGRATION_GUIDE.md**
   - Step-by-step migration
   - Before/after examples
   - Quick reference

3. **PROMPT_ENGINE_SUMMARY.md**
   - Executive summary
   - Components overview
   - Usage examples

4. **PROMPT_ENGINE_EXAMPLES.py**
   - Visual comparisons
   - Real usage patterns
   - Benefits demonstration

5. **PROMPT_ENGINE_DESIGN.md** (optional reference)
   - Detailed architecture
   - Extensibility guide
   - Design principles

## Testing

Run the built-in examples:

```bash
cd /Volumes/2TB/repos/gol_eval
python3 src/PromptEngine.py
```

Output shows 4 example combinations and all supported configurations.

## Next Steps

1. Review `src/PromptEngine.py` implementation
2. Read `MIGRATION_GUIDE.md` for migration steps
3. Update `c14_eval.py` to use PromptEngine
4. Update `gol_eval.py` to use PromptEngine
5. Update `MathExpressionGenerator.py` to use PromptEngine
6. Optional: Keep `src/PROMPT_STYLES.py` for backward compatibility

## Questions or Issues?

Refer to:
- **How do I use it?** → `MIGRATION_GUIDE.md`
- **How does it work?** → `PROMPT_ENGINE_DESIGN.md`
- **Show me examples** → `PROMPT_ENGINE_EXAMPLES.py`
- **See it in action** → `python3 src/PromptEngine.py`
- **Full code** → `src/PromptEngine.py`

## Summary

The PromptEngine refactoring consolidates scattered, duplicated prompt definitions into a unified, type-safe system with clear extension points. It improves maintainability, discoverability, and reliability while providing a clean API for prompt generation across multiple tasks and languages.
