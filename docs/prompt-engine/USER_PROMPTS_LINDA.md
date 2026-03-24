# Linda Fallacy User Prompts

User prompts for the Linda Conjunction Fallacy task. This benchmark tests whether models fall prey to the conjunction fallacy - incorrectly ranking a conjunction (A AND B) as more probable than one of its constituents (A alone).

## Background

The **conjunction fallacy** is a cognitive bias where people assume that specific conditions are more probable than general ones. The classic "Linda problem" presents a description that makes someone seem like a feminist, then asks whether:
- Linda is a bank teller
- Linda is a bank teller AND active in the feminist movement

Despite P(A AND B) <= P(A) mathematically, many humans (and models) incorrectly rank the conjunction as more likely.

---

## Coverage

| Language | Linguistic | Casual | Minimal |
|----------|------------|--------|---------|
| English (EN) | Yes | Yes | Yes |
| Spanish (ES) | Yes | Yes | Yes |
| French (FR) | Yes | Yes | Yes |

**Note:** Unlike other tasks, Linda only uses 3 styles (no Examples or Rules Math).

---

## Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{persona_description}` | Description of the person | "Linda is 31 years old, single, outspoken..." |
| `{ranked_items}` | List of statements to rank | "A) Bank teller\nB) Bank teller and feminist..." |
| `{num_options}` | Number of options | `5` |

---

## English Prompts

### Linguistic (Formal, Explanatory)

```
Consider the following description:

{persona_description}

Based on this description, please rank the following statements from MOST probable (1) to LEAST probable ({num_options}):

{ranked_items}

Please provide your ranking as a numbered list, starting with the most probable option. Also, briefly explain your reasoning for the top 3 rankings.

RANKING:
```

### Casual (Conversational)

```
Check out this person:

{persona_description}

Which of these is more likely? Rank them 1-{num_options} (most to least likely):

{ranked_items}

Give me your ranking and explain your top 3 picks!

RANKING:
```

### Minimal (Bare Minimum)

```
{persona_description}

Rank (1=most likely, {num_options}=least likely):
{ranked_items}

RANKING:
```

---

## Spanish (ES) Prompts

### Linguistic

```
Considere la siguiente descripción:

{persona_description}

Basándose en esta descripción, por favor ordene las siguientes afirmaciones de MÁS probable (1) a MENOS probable ({num_options}):

{ranked_items}

Por favor, proporcione su clasificación como una lista numerada, comenzando con la opción más probable. Explique brevemente su razonamiento para las 3 primeras clasificaciones.

CLASIFICACIÓN:
```

### Casual

```
Mira esta persona:

{persona_description}

¿Cuál de estas es más probable? Ordénalas del 1-{num_options} (más a menos probable):

{ranked_items}

¡Dame tu clasificación y explica tus 3 primeras opciones!

CLASIFICACIÓN:
```

### Minimal

```
{persona_description}

Ordena (1=más probable, {num_options}=menos probable):
{ranked_items}

CLASIFICACIÓN:
```

---

## French (FR) Prompts

### Linguistic

```
Considérez la description suivante :

{persona_description}

Sur la base de cette description, veuillez classer les affirmations suivantes de la PLUS probable (1) à la MOINS probable ({num_options}) :

{ranked_items}

Veuillez fournir votre classement sous forme de liste numérotée, en commençant par l'option la plus probable. Expliquez brièvement votre raisonnement pour les 3 premiers classements.

CLASSEMENT :
```

### Casual

```
Regardez cette personne :

{persona_description}

Laquelle de ces options est la plus probable ? Classez-les de 1-{num_options} (plus au moins probable) :

{ranked_items}

Donnez-moi votre classement et expliquez vos 3 premiers choix !

CLASSEMENT :
```

### Minimal

```
{persona_description}

Classez (1=plus probable, {num_options}=moins probable) :
{ranked_items}

CLASSEMENT :
```

---

## Usage Example

```python
from src.core.PromptEngine import PromptEngine, PromptContext, TaskType, Language, PromptStyle, SystemPromptStyle

engine = PromptEngine()
context = PromptContext(
    task_type=TaskType.LINDA_FALLACY,
    language=Language.EN,
    style=PromptStyle.LINGUISTIC,
    system_style=SystemPromptStyle.ANALYTICAL,
)
context.update(
    persona_description="Linda is 31 years old, single, outspoken, and very bright...",
    ranked_items="A) Bank teller\nB) Elementary school teacher\nC) Bank teller and active feminist",
    num_options=3
)
result = engine.generate(context)
print(result.user_prompt)
```

---

## Performance Notes

Unlike Game of Life and Arithmetic:

- **Chain-of-thought HELPS** on Linda fallacy (reasoning task)
- Analytical system prompt recommended
- Linguistic style produces most thoughtful responses
- Models often fail this task (fall for the fallacy)

---

## Evaluation

A model **passes** if it correctly ranks single statements (like "bank teller") as more probable than conjunctions ("bank teller AND feminist").

A model **fails** if it ranks conjunctions as more probable, demonstrating the conjunction fallacy.

---

## Research Findings

- Most small models fall for the conjunction fallacy
- Larger models with reasoning capabilities tend to avoid it
- Explicit reasoning (chain-of-thought) significantly helps
- Adversarial system prompts can make models fail more often

---

*Source: `src/core/PromptEngine.py`*
