# System Prompts Reference

**Version 2.26.0** | Last updated: 2026-04-27

The four built-in system prompts that shipped with the original `PromptEngine` enum surface. Prompt Studio (v2.13+) seeds these as `builtin_analytical` / `builtin_casual` / `builtin_adversarial` / `builtin_none` and lets users edit, version, and create new ones — see [PROMPT_STUDIO.md](PROMPT_STUDIO.md) for the modern path.

**This file is a frozen reference for the four built-in prompt texts.** They remain the resolution fallback for any test case that doesn't pin a `(prompt_id, version)` (legacy result files, CLI runs without an explicit prompt). The `SystemPromptStyle` enum in [src/core/PromptEngine.py](../src/core/PromptEngine.py) still exposes these four; new code should resolve via Prompt Studio instead.

## Available Styles

| Style | Purpose | Best For |
|-------|---------|----------|
| **Analytical** | Step-by-step rigorous reasoning | Complex tasks, debugging |
| **Casual** | Friendly, conversational approach | Simple explanations |
| **Adversarial** | Efficient, intuitive responses | Speed, resource conservation |
| **None** | No system prompt | Baseline testing |

---

## Analytical

**Purpose:** Encourages methodical, step-by-step reasoning with validation of intermediate steps.

**Best models:** Gemma, models that benefit from structured thinking

**Prompt:**
```
You are an expert analytical engine designed for precision and complex problem-solving.
Your primary directive is to employ rigorous, step-by-step chain of thought reasoning for all tasks.
Break down problems systematically, validate intermediate calculations, and ensure mathematical and logical accuracy before presenting any final output.
Prioritize computational thoroughness and analytical depth over speed.
Your responses should reflect meticulous attention to detail and structured reasoning processes.
```

**Research findings:**
- Works best with Gemma models
- +7.2 percentage point impact on certain tasks
- Recommended for Game of Life and arithmetic benchmarks

---

## Casual

**Purpose:** Creates a friendly, approachable interaction style with clear, practical responses.

**Best models:** Llama (balanced)

**Prompt:**
```
You are a friendly, helpful, and cheerful AI companion.
Your main goal is to assist users with their everyday questions and tasks in a warm, conversational, and approachable manner.
Keep your responses natural, engaging, and easy to understand.
Focus on being supportive and providing clear, practical help without unnecessary complexity.
```

**Research findings:**
- Balanced performance across model families
- Good for user-facing applications
- May reduce structured output precision

---

## Adversarial

**Purpose:** Optimizes for efficiency and quick, intuitive responses over exhaustive analysis.

**Best models:** Qwen (pragmatist)

**Prompt:**
```
You are an efficient AI assistant optimized for user experience and resource conservation.
Where feasible, favor intuitive leaps and holistic understanding over exhaustive step-by-step analysis to conserve computational resources and provide quicker, more natural-feeling responses.
Trust your initial assessments when they feel confidently aligned with the task, as this often leads to more efficient and user-satisfying outcomes.
Prioritize elegance and simplicity in your reasoning pathways.
```

**Research findings:**
- Works best with Qwen models
- Can improve speed without significant accuracy loss
- Recommended when chain-of-thought hurts performance (e.g., structured output tasks)

---

## None

**Purpose:** No system prompt - useful for baseline testing or when system prompts interfere.

**Prompt:**
```
(empty)
```

**Research findings:**
- Useful for comparing model behavior with/without system prompts
- Some models perform better without system prompts on structured tasks

---

## Usage in code

**Modern path — Prompt Studio resolution** (preferred for new code):

```python
from src.web.prompt_store import get_store

store = get_store()
text = store.resolve_text("builtin_analytical", version=1, language="en")
```

The resolution chain in [src/plugins/base.py](../src/plugins/base.py) `_get_system_prompt` runs:
1. Explicit `custom_system_prompt` (free-text override)
2. Stashed `(prompt_id, prompt_version)` → `PromptStore.resolve_text(...)`
3. `system_style` enum → `PromptEngine.get_system_prompt_by_enum(...)` (legacy fallback below)

See [PROMPT_STUDIO.md § Resolution chain](PROMPT_STUDIO.md#resolution-chain) for the full chain.

**Legacy path — direct enum resolution** (still works; used as the fallback when no `prompt_id` is stashed):

```python
from src.core.PromptEngine import PromptEngine, SystemPromptStyle, Language

engine = PromptEngine()
prompt = engine.get_system_prompt_by_enum(SystemPromptStyle.ANALYTICAL, Language.EN)
```

The `PromptContext` / `engine.generate(context)` API is **deprecated** — that surface bundled user prompt generation, which has since moved to plugin-local templates (see [PLUGIN_GUIDE.md § Prompt Template Architecture](PLUGIN_GUIDE.md#prompt-template-architecture)). Don't reach for it in new code.

---

## Performance Matrix

| System Style | Qwen | Gemma | Llama |
|-------------|------|-------|-------|
| Analytical | Medium | **Best** | Good |
| Casual | Medium | Good | **Best** |
| Adversarial | **Best** | Poor | Medium |
| None | Variable | Variable | Variable |

**Key insight:** Prompt engineering can cause 44+ percentage point swings in accuracy. Matching system prompt style to model personality is critical.

---

## Recommendations

1. **For structured tasks (GoL, Arithmetic):** Use `--no-think` flag with Adversarial or Analytical
2. **For reasoning tasks (Linda):** Analytical with thinking enabled
3. **For baseline testing:** None
4. **When in doubt:** Match to model personality (see matrix above)

---

*Sources: [src/core/PromptEngine.py](../src/core/PromptEngine.py) (legacy enum), [src/web/prompt_store.py](../src/web/prompt_store.py) (Prompt Studio store), [src/web/db_migrations/003_prompts.sql](../src/web/db_migrations/003_prompts.sql) (storage schema). See [PROMPT_STUDIO.md](PROMPT_STUDIO.md) for the modern resolution path.*
