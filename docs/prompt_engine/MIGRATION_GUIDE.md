# Migration Guide: Legacy to PromptEngine

This document explains how to update existing code to use the unified PromptEngine
instead of scattered PROMPT_STYLES definitions.

## Before (Legacy)

```python
# Old way in c14_eval.py
PROMPT_STYLES_EN = {
    "linguistic": "Given the mathematical expression: {expression}...",
    "casual": "Hey! Can you solve this...",
}

prompt = PROMPT_STYLES_EN["linguistic"].format(expression="2 + 3")
system = SYSTEM_PROMPT_STYLES_EN["analytical"]
```

## After (PromptEngine)

```python
from src.PromptEngine import (
    PromptEngine,
    create_math_context,
    create_gol_context,
    Language,
    PromptStyle,
    SystemPromptStyle,
    TaskType
)
```

## Migration Examples

### Math Expression Generation

```python
# OLD
prompt_template = PROMPT_STYLES_EN[config.prompt_style]
prompt = prompt_template.format(expression=e, examples=examples)
system = SYSTEM_PROMPT_STYLES_EN[config.system_prompt_style]

# NEW
engine = PromptEngine()

context = create_math_context(
    language="en",
    style="linguistic",
    system_style="analytical",
    expression="(2 + 3) * 4",
    examples="2 + 2 = 4\n3 + 3 = 6"
)

result = engine.generate(context)
system_prompt = result.system_prompt
user_prompt = result.user_prompt
```

### Game of Life Generation

```python
# OLD
prompt = PROMPT_STYLES_EN[style].format(
    grid_str=grid_str,
    l=l,
    d=d,
    w=w,
    h=h,
    examples=examples
)
system = get_system_prompt_style(language, system_style)

# NEW
engine = PromptEngine()

context = create_gol_context(
    language="en",
    style="linguistic",
    system_style="analytical",
    grid_str="1 0 1\n0 1 0\n1 0 1",
    l="1",
    d="0",
    w=3,
    h=3,
    examples="Example 1: ...\nExample 2: ..."
)

result = engine.generate(context)
system_prompt = result.system_prompt
user_prompt = result.user_prompt
```

## Updating Existing Code

### Configuration Usage

```python
# OLD (c14_eval.py)
config.prompt_style = "linguistic"
config.language = "en"
config.system_prompt_style = "analytical"

# NEW - Use string enums that auto-validate
from src.PromptEngine import Language, PromptStyle, SystemPromptStyle

lang = Language(config.language)  # Validates, throws if invalid
style = PromptStyle(config.prompt_style)
sys_style = SystemPromptStyle(config.system_prompt_style)
```

### Batch Generation

```python
# OLD
for expr in expressions:
    prompt = PROMPT_STYLES_EN[style].format(expression=expr)
    # ...

# NEW
engine = PromptEngine()
expressions = ["2 + 3", "4 * 5", "10 / 2"]

for expr in expressions:
    context = create_math_context(
        expression=expr,
        language="en",
        style="minimal"
    )
    result = engine.generate(context)
    user_prompt = result.user_prompt
    system_prompt = result.system_prompt
    # Use prompts...
```

## Key Differences

- **Unified Interface**: PromptEngine.generate() returns both system and user prompts
- **Type Safety**: Use Language, PromptStyle, SystemPromptStyle enums
- **Extensibility**: Add new prompts in one place
- **Validation**: Enums validate at creation time
- **Context Management**: PromptContext manages all variables cleanly
- **Discoverability**: engine.list_supported(TaskType) shows all options

## Quick Reference

### Game of Life

```python
context = create_gol_context(
    language="en",              # Language enum
    style="linguistic",         # PromptStyle enum
    system_style="analytical",  # SystemPromptStyle enum
    grid_str="...",            # Your grid
    l="1",                     # Live symbol
    d="0",                     # Dead symbol
    w=10, h=10,                # Dimensions (optional)
    examples="..."             # For "examples" style
)
```

### Math Expression

```python
context = create_math_context(
    language="en",
    style="linguistic",
    system_style="analytical",
    expression="(2 + 3) * 4",
    examples="..."
)
```

### Add Custom Variables

```python
context = create_gol_context(...)
context.set("custom_var", value)
context.update(var1=val1, var2=val2)
```

### Generate Prompts

```python
engine = PromptEngine()
result = engine.generate(context)

system_prompt = result.system_prompt
user_prompt = result.user_prompt
metadata = result.metadata
```

### Discover Supported Options

```python
engine = PromptEngine()
supported = engine.list_supported(TaskType.GAME_OF_LIFE)
# {
#   "languages": ["en", "fr", "es", ...],
#   "styles": ["linguistic", "casual", ...],
#   "system_styles": ["analytical", "casual", ...]
# }
```

## Supported Languages

- `en`: English
- `fr`: French
- `es`: Spanish
- `de`: German
- `zh`: Chinese
- `ua`: Ukrainian

## Supported Prompt Styles

- `linguistic`: Formal, rule-based
- `casual`: Conversational
- `minimal`: Bare minimum
- `examples`: With examples
- `rules_math`: Mathematical notation

## Supported System Prompt Styles

- `analytical`: Rigorous reasoning
- `casual`: Friendly
- `adversarial`: Resource-efficient
- `none`: Empty
