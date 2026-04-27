# Migration Guide: PromptEngine → Plugin-Local Templates

> **Updated: v2.8.0 (March 2026)**

This document explains two migration paths:
1. **Legacy → PromptEngine** (historical, v1 → v2.0)
2. **PromptEngine → Plugin-Local Templates** (current, v2.7 → v2.8.0)

---

## Current Architecture (v2.8.0)

All 21 plugins now use **plugin-local `prompts.py` files** for user prompt templates (canonical: `PluginRegistry.list_task_types()`). The central `PromptEngine` is used **only for system prompts and enums** (and even those resolve via Prompt Studio v2.13+ — see [PROMPT_STUDIO.md](PROMPT_STUDIO.md)).

### What's Active in PromptEngine

```python
from src.core.PromptEngine import Language, PromptStyle, SystemPromptStyle
# These enums are used everywhere — NOT deprecated
```

### What's Deprecated in PromptEngine

```python
# DEPRECATED — do not use in new code:
from src.core.PromptEngine import TaskType, PromptContext, PromptResult
engine = PromptEngine()
engine.generate(context)      # Deprecated
engine.get_user_prompt(...)   # Deprecated
create_math_context(...)      # Deprecated
create_gol_context(...)       # Deprecated
# All *_PROMPTS dicts (GOL_PROMPTS, MATH_PROMPTS, etc.) are deprecated
```

---

## Migration: PromptEngine → Plugin-Local Templates

### Before (PromptEngine, v2.0–2.7)

```python
from src.core.PromptEngine import (
    PromptEngine, create_math_context, Language, PromptStyle, SystemPromptStyle, TaskType
)

engine = PromptEngine()
context = create_math_context(
    language="en", style="linguistic", system_style="analytical",
    expression="(2 + 3) * 4"
)
result = engine.generate(context)
system_prompt = result.system_prompt
user_prompt = result.user_prompt
```

### After (Plugin-Local Templates, v2.8.0)

**Step 1:** Create `prompts.py` in your plugin directory:

```python
# src/plugins/arithmetic/prompts.py
from src.core.PromptEngine import Language

TEMPLATES = {
    (Language.EN, "minimal"):    "Solve: {expression}",
    (Language.EN, "casual"):     "What's {expression}?",
    (Language.EN, "linguistic"): "Evaluate the following expression: {expression}\nProvide only the numeric result.",
}
```

**Step 2:** Use base class helpers in your generator:

```python
# src/plugins/arithmetic/generator.py
from .prompts import TEMPLATES

class ArithmeticTestCaseGenerator(TestCaseGenerator):
    def generate_batch(self, config, prompt_config, count, seed):
        language = prompt_config.get("language", "en")
        user_style = prompt_config.get("user_style", "minimal")
        system_style = prompt_config.get("system_style", "none")

        # Replaces: engine = PromptEngine(); context = create_math_context(...); engine.generate(context)
        user_prompt, system_prompt, full_prompt = self._build_prompts(
            TEMPLATES, language, user_style, system_style,
            expression="(2 + 3) * 4",
        )
```

### Base Class Helper Reference

| Method | Replaces | Notes |
|--------|----------|-------|
| `self._build_prompts(templates, lang, user_style, sys_style, **vars)` | `engine.generate(context)` | Returns `(user, system, full)` tuple |
| `self._get_system_prompt(sys_style, lang)` | `engine.get_system_prompt_by_enum(style, lang)` | Safe enum parsing with fallbacks |
| `self._format_user_prompt(templates, lang, style, **vars)` | `engine.get_user_prompt(context)` | Template lookup with EN/casual fallback |

---

## Historical Migration: Legacy → PromptEngine (v1 → v2.0)

> This section is retained for reference. The PromptEngine approach described here has itself been superseded by plugin-local templates (see above).

### Before (Legacy)

```python
PROMPT_STYLES_EN = {
    "linguistic": "Given the mathematical expression: {expression}...",
    "casual": "Hey! Can you solve this...",
}
prompt = PROMPT_STYLES_EN["linguistic"].format(expression="2 + 3")
system = SYSTEM_PROMPT_STYLES_EN["analytical"]
```

### After (PromptEngine — now deprecated)

```python
from src.core.PromptEngine import PromptEngine, create_math_context
engine = PromptEngine()
context = create_math_context(expression="2 + 3", language="en", style="linguistic")
result = engine.generate(context)
```

---

## Supported Languages

- `en`: English
- `fr`: French
- `es`: Spanish
- `de`: German
- `zh`: Chinese
- `ua`: Ukrainian

## Supported User Prompt Styles

| Style | Status | Description |
|-------|--------|-------------|
| `minimal` | **Active** | Bare minimum instructions |
| `casual` | **Active** | Conversational |
| `linguistic` | **Active** | Formal, rule-based |
| `examples` | **Deprecated** | With worked examples (legacy GoL/ARI only) |
| `rules_math` | **Deprecated** | Mathematical notation (legacy GoL only) |

## Supported System Prompt Styles

| Style | Status | Description |
|-------|--------|-------------|
| `analytical` | **Active** | Rigorous step-by-step reasoning |
| `casual` | **Active** | Friendly, supportive |
| `adversarial` | **Active** | Efficiency-focused, direct |
| `none` | **Active** | Empty system prompt |
