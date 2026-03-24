# Math Expression User Prompts

User prompts for the Arithmetic Expression evaluation task. These prompts instruct the model to solve mathematical expressions following order of operations.

## Coverage

| Language | Linguistic | Casual | Minimal | Examples | Rules Math |
|----------|------------|--------|---------|----------|------------|
| English (EN) | Yes | Yes | Yes | Yes | Yes |

**Note:** Currently only English is supported. Other languages can be added by extending `MATH_EXPRESSION_PROMPTS` in `PromptEngine.py`.

---

## Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{expression}` | The math expression to solve | `(2 + 3) * 4` |
| `{examples}` | Worked examples (for Examples style) | See below |

---

## English Prompts

### Linguistic (Formal, Step-by-Step)

```
Given the mathematical expression: {expression}

Follow these EXACT steps:
1. Identify all operations in the expression following order of operations (PEMDAS/BODMAS)
2. Calculate each sub-expression step by step
3. Show your work for every intermediate calculation
4. Provide the final numerical result

Expression: {expression}
Step-by-step solution:
[Show your work here]

Final answer: [number only]
```

### Casual (Conversational)

```
Hey! Can you solve this math expression for me? Just work through it step by step.
{expression}

Show me how you get to the answer:
[Your work here]

Final answer: [just the number]
```

### Minimal (Bare Minimum)

```
{expression}

Answer:
```

### Examples (With Worked Examples)

```
{examples}
---
Solve: {expression}

Final answer:
```

### Rules Math (LaTeX Mathematical Notation)

```
$$
\text{Expression: } {expression} \\
\text{Apply order of operations: } \\
P: \text{Parentheses first} \\
E: \text{Exponents} \\
MD: \text{Multiplication and Division (left to right)} \\
AS: \text{Addition and Subtraction (left to right)} \\
\rule{100pt}{0.4pt} \\
\text{Solution:}
$$

Final result:
```

---

## Usage Example

```python
from src.core.PromptEngine import PromptEngine, create_math_context

engine = PromptEngine()
context = create_math_context(
    language="en",
    style="minimal",
    system_style="adversarial",
    expression="(5 + 3) * 2 - 4"
)
result = engine.generate(context)
print(result.user_prompt)
```

---

## Difficulty Levels

The arithmetic benchmark supports different difficulty levels:

| Level | Description | Example |
|-------|-------------|---------|
| 1 | Simple operations | `2 + 3` |
| 2 | Multiple operations | `2 + 3 * 4` |
| 3 | Parentheses | `(2 + 3) * 4` |
| 4 | Nested expressions | `((2 + 3) * 4) / 2` |

---

## Style Recommendations

| Style | When to Use | Notes |
|-------|-------------|-------|
| Linguistic | Maximum precision | Encourages step-by-step work |
| Casual | Quick tests | More natural conversation |
| Minimal | Fastest responses | Use with `--no-think` |
| Examples | When model needs demonstrations | Provide worked examples in context |
| Rules Math | Mathematical models | LaTeX notation |

---

## Performance Notes

- **Chain-of-thought hurts accuracy** on structured arithmetic tasks
- Use `--no-think` flag for best results
- Minimal style often produces better results than verbose styles
- Enhanced parsing supports 6 strategies for extracting answers

---

## Response Parsing

The benchmark uses multi-strategy parsing to extract answers:

1. `\boxed{}` LaTeX pattern
2. JSON format
3. "Final answer:" keyword
4. "Answer:" keyword
5. Last numeric value
6. Fallback patterns

---

*Source: `src/core/PromptEngine.py`*
