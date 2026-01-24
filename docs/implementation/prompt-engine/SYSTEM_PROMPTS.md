# System Prompts Reference

System prompts set the AI's reasoning style and approach for all tasks. They are task-agnostic and applied before any user prompt.

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

## Usage in Code

```python
from src.core.PromptEngine import PromptEngine, SystemPromptStyle, Language

engine = PromptEngine()

# Get system prompt directly
prompt = engine.get_system_prompt_by_enum(SystemPromptStyle.ANALYTICAL, Language.EN)

# Or via context
from src.core.PromptEngine import PromptContext, TaskType, PromptStyle

context = PromptContext(
    task_type=TaskType.GAME_OF_LIFE,
    system_style=SystemPromptStyle.ADVERSARIAL,
    # ... other settings
)
result = engine.generate(context)
print(result.system_prompt)
```

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

*Source: `src/core/PromptEngine.py`*
