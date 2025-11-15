# PromptEngine Architecture & Design Documentation

## Overview

The **PromptEngine** is a unified system for managing and generating system prompts and user prompts across different tasks, languages, and styles. It consolidates scattered prompt definitions from multiple files into a coherent, extensible architecture.

## Architecture

### Core Components

```
PromptEngine (Main Orchestrator)
├── System Prompt Management
│   ├── SYSTEM_PROMPTS (dict)
│   └── SystemPromptStyle (enum)
│
├── Task-Specific Prompts
│   ├── GAME_OF_LIFE_PROMPTS
│   ├── MATH_EXPRESSION_PROMPTS
│   └── Extensible for new tasks
│
├── Context Management
│   ├── PromptContext (dataclass)
│   └── PromptResult (dataclass)
│
└── Convenience Functions
    ├── create_gol_context()
    ├── create_math_context()
    └── Extensible for new tasks
```

### Key Classes

#### `PromptContext`

Container for all variables needed to render prompts.

```python
@dataclass
class PromptContext:
    task_type: TaskType              # game_of_life or math_expression
    language: Language = Language.EN # en, fr, es, de, zh, ua
    style: PromptStyle = ...         # linguistic, casual, minimal, etc.
    system_style: SystemPromptStyle  # analytical, casual, adversarial, none
    custom_vars: Dict[str, Any]      # Task-specific variables
```

**Methods:**
- `get(key, default=None)`: Get a variable
- `set(key, value)`: Set a variable
- `update(**kwargs)`: Set multiple variables

#### `PromptResult`

Result of prompt generation containing both prompts.

```python
@dataclass
class PromptResult:
    system_prompt: str               # System-level instructions
    user_prompt: str                 # User-level task prompt
    metadata: Dict[str, Any]         # Generation metadata
```

#### `PromptEngine`

Main orchestrator that generates prompts.

**Methods:**
- `get_system_prompt(context)`: Get system prompt
- `get_user_prompt(context)`: Get user prompt
- `generate(context)`: Get both prompts as PromptResult
- `list_supported(task_type)`: Discover available options

#### `PromptTemplate` (ABC)

Base class for extensible prompt templates.

```python
class PromptTemplate(ABC):
    @abstractmethod
    def render(context: PromptContext) -> str: ...
    def validate(rendered: str) -> bool: ...
    def add_validator(validator) -> None: ...
```

`SimplePromptTemplate` provides basic variable substitution implementation.

### Enumerations

#### `Language`

Supported languages:
- `EN`: English
- `FR`: French
- `ES`: Spanish
- `DE`: German
- `ZH`: Chinese
- `UA`: Ukrainian

#### `PromptStyle`

Supported prompt styles:
- `LINGUISTIC`: Formal, rule-based
- `CASUAL`: Conversational, informal
- `MINIMAL`: Bare minimum, concise
- `EXAMPLES`: Includes worked examples
- `RULES_MATH`: Mathematical notation

#### `SystemPromptStyle`

Supported system prompt styles:
- `ANALYTICAL`: Rigorous, step-by-step reasoning
- `CASUAL`: Friendly, conversational tone
- `ADVERSARIAL`: Resource-efficient, quick responses
- `NONE`: Empty system prompt

#### `TaskType`

Supported task types:
- `GAME_OF_LIFE`: Conway's Game of Life
- `MATH_EXPRESSION`: Mathematical expression evaluation

## Prompt Structure

### System Prompts

Located in `SYSTEM_PROMPTS` dictionary:

```python
SYSTEM_PROMPTS = {
    Language.EN: {
        SystemPromptStyle.ANALYTICAL: "You are an expert...",
        SystemPromptStyle.CASUAL: "You are a friendly...",
        SystemPromptStyle.ADVERSARIAL: "You are an efficient...",
        SystemPromptStyle.NONE: "",
    }
}
```

**Note:** Currently only English system prompts. System prompts are generic enough to work across languages. To add translations, add new Language keys.

### Task-Specific Prompts

#### Game of Life Prompts

Located in `GAME_OF_LIFE_PROMPTS`:

```python
GAME_OF_LIFE_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: "Here are the EXACT rules: ...",
        PromptStyle.CASUAL: "Here's a Game of Life grid. ...",
        PromptStyle.MINIMAL: "Conway's Game of Life current state: ...",
        PromptStyle.EXAMPLES: "{examples}\n---\n{grid_str}",
        PromptStyle.RULES_MATH: "$$...$$ (mathematical notation)",
    },
    Language.ES: { ... },
    Language.FR: { ... },
    # ... other languages
}
```

**Template Variables:**
- `{l}`: Live cell symbol
- `{d}`: Dead cell symbol
- `{grid_str}`: Current grid state
- `{w}`: Grid width
- `{h}`: Grid height
- `{examples}`: Example solutions

#### Math Expression Prompts

Located in `MATH_EXPRESSION_PROMPTS`:

```python
MATH_EXPRESSION_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: "Given the mathematical expression: ...",
        PromptStyle.CASUAL: "Hey! Can you solve this...",
        PromptStyle.MINIMAL: "{expression} =",
        PromptStyle.EXAMPLES: "{examples}\n---\n{expression} =",
        PromptStyle.RULES_MATH: "$$...$$",
    }
}
```

**Template Variables:**
- `{expression}`: Mathematical expression to evaluate
- `{examples}`: Example problems and solutions

## Usage Patterns

### Basic Usage

```python
from src.PromptEngine import PromptEngine, create_gol_context

engine = PromptEngine()

# Create context
context = create_gol_context(
    language="en",
    style="linguistic",
    system_style="analytical",
    grid_str="1 0 1\n0 1 0\n1 0 1",
    l="1",
    d="0"
)

# Generate prompts
result = engine.generate(context)

# Use prompts
system_prompt = result.system_prompt
user_prompt = result.user_prompt
```

### Dynamic Context Updates

```python
# Modify context before generation
context.set("new_var", "new_value")
context.update(var1=val1, var2=val2)

result = engine.generate(context)
```

### Batch Operations

```python
engine = PromptEngine()

for expr in expressions:
    context = create_math_context(
        expression=expr,
        language="en",
        style="minimal"
    )
    result = engine.generate(context)
    # Process prompts...
```

### Discovery

```python
supported = engine.list_supported(TaskType.GAME_OF_LIFE)
print(supported["languages"])      # ['en', 'es', 'fr', ...]
print(supported["styles"])         # ['linguistic', 'casual', ...]
print(supported["system_styles"])  # ['analytical', 'casual', ...]
```

## Extensibility

### Adding a New Task Type

1. Create prompt template dictionary:

```python
NEW_TASK_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: "Your prompt template with {variables}",
        PromptStyle.CASUAL: "...",
        # ... other styles
    },
    Language.FR: { ... },
    # ... other languages
}
```

2. Add to PromptEngine.__init__:

```python
self.task_prompts = {
    TaskType.GAME_OF_LIFE: GAME_OF_LIFE_PROMPTS,
    TaskType.MATH_EXPRESSION: MATH_EXPRESSION_PROMPTS,
    TaskType.NEW_TASK: NEW_TASK_PROMPTS,  # Add this
}
```

3. Create convenience function:

```python
def create_new_task_context(language: str = "en", style: str = "linguistic", **kwargs) -> PromptContext:
    context = PromptContext(
        task_type=TaskType.NEW_TASK,
        language=Language(language),
        style=PromptStyle(style),
        system_style=SystemPromptStyle(kwargs.pop("system_style", "analytical")),
    )
    context.update(**kwargs)
    return context
```

### Adding a New Language

1. Add Language enum value:

```python
class Language(str, Enum):
    # ... existing
    NEW_LANG = "new_lang"
```

2. Add translations to prompt dictionaries:

```python
GAME_OF_LIFE_PROMPTS[Language.NEW_LANG] = {
    PromptStyle.LINGUISTIC: "Your translated prompt...",
    # ... other styles
}
```

3. Update system prompts (optional):

```python
SYSTEM_PROMPTS[Language.NEW_LANG] = {
    SystemPromptStyle.ANALYTICAL: "Your translated system prompt...",
    # ... other styles
}
```

### Adding a Custom PromptTemplate

```python
class CustomPromptTemplate(PromptTemplate):
    def render(self, context: PromptContext) -> str:
        # Custom rendering logic
        result = self.template
        # Process context.custom_vars
        return result
```

## Design Principles

### 1. **Separation of Concerns**
   - System prompts: Generic AI instructions
   - User prompts: Task-specific instructions
   - Variables: Task context and data

### 2. **Type Safety**
   - Use Enums for languages, styles, task types
   - Prevents typos and invalid configurations
   - Validates at context creation time

### 3. **Extensibility**
   - Task types are pluggable
   - New prompts can be added without modifying engine
   - Custom templates can be implemented

### 4. **Discoverability**
   - `list_supported()` shows all available options
   - Enums provide IDE autocomplete
   - Clear error messages

### 5. **Simplicity**
   - Simple variable substitution for most use cases
   - PromptContext provides clean interface
   - Convenience functions reduce boilerplate

## Comparison: Before vs. After

### Before (Scattered)

```python
# c14_eval.py
PROMPT_STYLES_EN = { ... }
prompt = PROMPT_STYLES_EN["linguistic"].format(expression=expr)

# Different file
SYSTEM_PROMPT_STYLES_EN = { ... }
system = SYSTEM_PROMPT_STYLES_EN["analytical"]

# No validation, easy to typo keys
# Hard to discover available options
# Duplicated styles across files
```

### After (Unified)

```python
# Single file
engine = PromptEngine()
context = create_math_context(
    expression=expr,
    language="en",           # Type-checked Enum
    style="linguistic",      # Type-checked Enum
    system_style="analytical"  # Type-checked Enum
)
result = engine.generate(context)

# All validations happen at context creation
# engine.list_supported() shows all options
# Single source of truth
```

## Implementation Notes

### Variable Substitution

Template variables are substituted using simple string replacement:

```python
template = "Expression: {expression} ="
context.custom_vars = {"expression": "2 + 3"}
result = template.replace("{expression}", "2 + 3")
# Result: "Expression: 2 + 3 ="
```

This is simple and works for most cases. For complex logic, override `render()` in a custom `PromptTemplate` subclass.

### Error Handling

- Invalid Language: `ValueError` at context creation
- Invalid PromptStyle: `ValueError` at context creation
- Unknown TaskType: `ValueError` at generate time
- Missing variables: Replaced as empty string (no error)

To add validation, use `PromptTemplate.add_validator()`.

## Testing

The PromptEngine includes CLI examples:

```bash
python3 src/PromptEngine.py
```

This demonstrates:
1. Game of Life linguistic style (English)
2. Game of Life minimal style (French)
3. Math expression linguistic style
4. Supported configuration listing

## Future Enhancements

1. **Dynamic Prompt Loading**: Load prompts from files/databases
2. **Prompt Versioning**: Track prompt changes over time
3. **A/B Testing**: Compare different prompt versions
4. **Analytics**: Track which prompts perform best
5. **Validation Rules**: Add per-task validation requirements
6. **Caching**: Cache frequently used prompt combinations
