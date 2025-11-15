# PromptEngine Quick Start Guide

## Installation

No installation needed! The PromptEngine is already in `src/PromptEngine.py`.

## Import

```python
from src.PromptEngine import (
    PromptEngine,
    create_gol_context,
    create_math_context,
    Language,
    PromptStyle,
    SystemPromptStyle,
    TaskType
)
```

## Quick Usage

### Game of Life

```python
engine = PromptEngine()

context = create_gol_context(
    grid_str="1 0 1\n0 1 0\n1 0 1",  # Required
    l="1",                             # Required (live symbol)
    d="0",                             # Required (dead symbol)
    language="en",                     # Optional, default: "en"
    style="linguistic",                # Optional, default: "linguistic"
    system_style="analytical",         # Optional, default: "analytical"
    w=3,                               # Optional (grid width)
    h=3,                               # Optional (grid height)
    examples="..."                     # Optional (for "examples" style)
)

result = engine.generate(context)
print(result.system_prompt)  # System instructions
print(result.user_prompt)    # Task prompt
```

### Math Expression

```python
context = create_math_context(
    expression="(2 + 3) * 4",       # Required
    language="en",                   # Optional, default: "en"
    style="linguistic",              # Optional, default: "linguistic"
    system_style="analytical",       # Optional, default: "analytical"
    examples="..."                   # Optional (for "examples" style)
)

result = engine.generate(context)
```

## Discover Supported Options

```python
engine = PromptEngine()

# For Game of Life
supported = engine.list_supported(TaskType.GAME_OF_LIFE)
print(supported["languages"])      # ['en', 'es', 'fr', 'de', 'zh', 'ua']
print(supported["styles"])         # ['linguistic', 'casual', 'minimal', 'examples', 'rules_math']
print(supported["system_styles"])  # ['analytical', 'casual', 'adversarial', 'none']

# For Math Expression
supported = engine.list_supported(TaskType.MATH_EXPRESSION)
```

## Enums (Type-Safe)

Use these instead of strings:

```python
# Languages
Language.EN  # English
Language.ES  # Spanish
Language.FR  # French
Language.DE  # German
Language.ZH  # Chinese
Language.UA  # Ukrainian

# Prompt Styles
PromptStyle.LINGUISTIC      # Formal, rule-based
PromptStyle.CASUAL         # Conversational
PromptStyle.MINIMAL        # Bare minimum
PromptStyle.EXAMPLES       # With worked examples
PromptStyle.RULES_MATH     # Mathematical notation

# System Styles
SystemPromptStyle.ANALYTICAL    # Rigorous reasoning
SystemPromptStyle.CASUAL       # Friendly tone
SystemPromptStyle.ADVERSARIAL  # Resource-efficient
SystemPromptStyle.NONE         # Empty

# Task Types
TaskType.GAME_OF_LIFE
TaskType.MATH_EXPRESSION
```

### Using Enums

```python
# Option 1: Use enum values (simpler)
context = create_gol_context(
    language="en",
    style="linguistic",
    system_style="analytical",
    grid_str=grid
)

# Option 2: Use enum objects (more type-safe)
context = create_gol_context(
    language=Language.EN.value,
    style=PromptStyle.LINGUISTIC.value,
    system_style=SystemPromptStyle.ANALYTICAL.value,
    grid_str=grid
)
```

## Batch Processing

```python
engine = PromptEngine()

expressions = ["2 + 3", "4 * 5", "10 / 2"]
results = []

for expr in expressions:
    context = create_math_context(
        expression=expr,
        style="minimal"
    )
    result = engine.generate(context)
    results.append(result)

# results now contains PromptResult objects
```

## Advanced: Modify Context

```python
context = create_gol_context(grid_str=grid, l="1", d="0")

# Add variables
context.set("extra_var", "value")

# Or update multiple at once
context.update(var1="val1", var2="val2")

# Then generate
result = engine.generate(context)
```

## Advanced: Custom Context

```python
from src.PromptEngine import PromptContext, PromptEngine, TaskType

# Create context manually
context = PromptContext(
    task_type=TaskType.GAME_OF_LIFE,
    language=Language.EN,
    style=PromptStyle.LINGUISTIC,
    system_style=SystemPromptStyle.ANALYTICAL
)

# Add all variables
context.update(
    grid_str="1 0 1\n0 1 0\n1 0 1",
    l="1",
    d="0"
)

# Generate
engine = PromptEngine()
result = engine.generate(context)
```

## Error Handling

```python
from src.PromptEngine import PromptEngine, create_gol_context

try:
    context = create_gol_context(
        style="invalid_style"  # Invalid!
    )
except ValueError as e:
    print(f"Error: {e}")
    # Output: "Error: 'invalid_style' is not a valid PromptStyle"
```

## Common Mistakes

### ❌ Wrong: Using strings directly

```python
result = engine.generate("game_of_life", "en", "linguistic")  # Won't work
```

### ✅ Right: Use context helpers

```python
context = create_gol_context(language="en", style="linguistic")
result = engine.generate(context)
```

### ❌ Wrong: Forgetting required variables

```python
context = create_gol_context()  # Missing grid_str, l, d
result = engine.generate(context)  # Renders with empty placeholders
```

### ✅ Right: Provide all variables

```python
context = create_gol_context(
    grid_str="1 0 1",
    l="1",
    d="0"
)
result = engine.generate(context)
```

### ❌ Wrong: Typo in style name

```python
context = create_gol_context(style="lingustic")  # Typo!
```

### ✅ Right: Use autocomplete or list_supported()

```python
supported = engine.list_supported(TaskType.GAME_OF_LIFE)
print(supported["styles"])  # See all valid styles
```

## Output Structure

All `engine.generate()` calls return a `PromptResult`:

```python
@dataclass
class PromptResult:
    system_prompt: str              # System-level instructions
    user_prompt: str                # User-level task prompt
    metadata: Dict[str, Any]        # Generation metadata
```

Access like:

```python
result = engine.generate(context)

system = result.system_prompt      # String
user = result.user_prompt          # String
meta = result.metadata             # Dict with task info

# Or use str() to see both
print(result)  # Formatted output with both prompts
```

## Real-World Example

```python
from src.PromptEngine import PromptEngine, create_gol_context

def evaluate_gol_model(model, grids, config):
    engine = PromptEngine()
    results = []
    
    for grid in grids:
        context = create_gol_context(
            grid_str=format_grid(grid),
            l="1",
            d="0",
            language=config.language,
            style=config.prompt_style,
            system_style=config.system_style
        )
        
        prompt_result = engine.generate(context)
        
        # Query model
        response = model.query(
            system=prompt_result.system_prompt,
            user=prompt_result.user_prompt
        )
        
        results.append({
            "grid": grid,
            "response": response,
            "metadata": prompt_result.metadata
        })
    
    return results
```

## Troubleshooting

### Q: How do I know what languages are supported?

```python
engine = PromptEngine()
supported = engine.list_supported(TaskType.GAME_OF_LIFE)
print(supported["languages"])
```

### Q: How do I add a new language?

See `MIGRATION_GUIDE.md` → "Extensibility" section.

### Q: How do I add a new task type?

See `MIGRATION_GUIDE.md` → "Extensibility" section.

### Q: Can I use string values instead of enums?

Yes! `create_gol_context()` accepts strings and validates them:

```python
context = create_gol_context(
    language="en",      # String OK
    style="minimal",    # String OK
    system_style="analytical"  # String OK
)
```

### Q: Why do I get KeyError?

You're probably using old code. Update to use `PromptEngine`:

```python
# Old (KeyError!)
prompt = PROMPT_STYLES_EN["lingustic"]

# New (ValueError with clear message)
context = create_gol_context(style="lingustic")
# ValueError: 'lingustic' is not a valid PromptStyle
```

## Documentation

- **Quick answers**: This file
- **How to migrate**: `MIGRATION_GUIDE.md`
- **Architecture details**: `PROMPT_ENGINE_DESIGN.md`
- **Before/after examples**: `PROMPT_ENGINE_EXAMPLES.py`
- **Overview**: `PROMPT_ENGINE_SUMMARY.md`
- **Full source**: `src/PromptEngine.py`

## Run Examples

```bash
cd /Volumes/2TB/repos/gol_eval
python3 src/PromptEngine.py
```

Shows 4 complete examples and discovers all supported configurations.

## Summary

1. Import: `from src.PromptEngine import ...`
2. Create context: `create_gol_context()` or `create_math_context()`
3. Generate: `engine.generate(context)`
4. Use: `result.system_prompt`, `result.user_prompt`

That's it! The PromptEngine handles everything else.
