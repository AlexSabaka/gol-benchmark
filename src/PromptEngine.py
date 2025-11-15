"""
Unified Prompt Engine for managing system prompts and user prompts
across different tasks, styles, and languages.

Architecture:
- PromptTemplate: Base class for defining prompt structure
- SystemPromptTemplate: Manages system-level instructions
- UserPromptTemplate: Manages user-level task prompts
- PromptContext: Holds variables for prompt rendering
- PromptEngine: Main orchestrator for prompt generation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod
import re


# ==================== ENUMS ====================

class Language(str, Enum):
    """Supported languages for prompts."""
    EN = "en"  # English
    FR = "fr"  # French
    ES = "es"  # Spanish
    DE = "de"  # German
    ZH = "zh"  # Chinese
    UA = "ua"  # Ukrainian


class PromptStyle(str, Enum):
    """Supported prompt styles."""
    LINGUISTIC = "linguistic"      # Formal, rule-based
    CASUAL = "casual"              # Conversational
    MINIMAL = "minimal"            # Bare minimum
    EXAMPLES = "examples"          # With examples
    RULES_MATH = "rules_math"      # Mathematical notation
    ADVERSARIAL = "adversarial"    # Efficiency-focused


class SystemPromptStyle(str, Enum):
    """Supported system prompt styles."""
    ANALYTICAL = "analytical"      # Rigorous reasoning
    CASUAL = "casual"              # Friendly
    ADVERSARIAL = "adversarial"    # Resource-efficient
    NONE = "none"                  # Empty


class TaskType(str, Enum):
    """Supported task types."""
    GAME_OF_LIFE = "game_of_life"
    MATH_EXPRESSION = "math_expression"


# ==================== DATA CLASSES ====================

@dataclass
class PromptContext:
    """Container for variables used in prompt rendering."""
    task_type: TaskType
    language: Language = Language.EN
    style: PromptStyle = PromptStyle.LINGUISTIC
    system_style: SystemPromptStyle = SystemPromptStyle.ANALYTICAL
    custom_vars: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a variable from context."""
        return self.custom_vars.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a variable in context."""
        self.custom_vars[key] = value
    
    def update(self, **kwargs) -> None:
        """Update multiple variables at once."""
        self.custom_vars.update(kwargs)


@dataclass
class PromptResult:
    """Result of prompt generation."""
    system_prompt: str
    user_prompt: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """String representation showing both prompts."""
        return f"System:\n{self.system_prompt}\n\nUser:\n{self.user_prompt}"


# ==================== BASE CLASSES ====================

class PromptTemplate(ABC):
    """Base class for prompt templates."""
    
    def __init__(self, template: str):
        """Initialize with a template string."""
        self.template = template
        self._validators: List[Callable[[str], bool]] = []
    
    @abstractmethod
    def render(self, context: PromptContext) -> str:
        """Render the template with given context."""
        pass
    
    def validate(self, rendered: str) -> bool:
        """Validate rendered prompt against all validators."""
        return all(validator(rendered) for validator in self._validators)
    
    def add_validator(self, validator: Callable[[str], bool]) -> None:
        """Add a validation function."""
        self._validators.append(validator)
    
    def _substitute_variables(self, template: str, context: PromptContext) -> str:
        """Substitute variables in template using context."""
        result = template
        for key, value in context.custom_vars.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        return result


class SimplePromptTemplate(PromptTemplate):
    """Simple template that just substitutes variables."""
    
    def render(self, context: PromptContext) -> str:
        """Render by substituting variables."""
        return self._substitute_variables(self.template, context)


# ==================== SYSTEM PROMPTS ====================

SYSTEM_PROMPTS = {
    Language.EN: {
        SystemPromptStyle.ANALYTICAL: """You are an expert analytical engine designed for precision and complex problem-solving.
Your primary directive is to employ rigorous, step-by-step chain of thought reasoning for all tasks.
Break down problems systematically, validate intermediate calculations, and ensure mathematical and logical accuracy before presenting any final output.
Prioritize computational thoroughness and analytical depth over speed.
Your responses should reflect meticulous attention to detail and structured reasoning processes.""",

        SystemPromptStyle.CASUAL: """You are a friendly, helpful, and cheerful AI companion.
Your main goal is to assist users with their everyday questions and tasks in a warm, conversational, and approachable manner.
Keep your responses natural, engaging, and easy to understand.
Focus on being supportive and providing clear, practical help without unnecessary complexity.""",

        SystemPromptStyle.ADVERSARIAL: """You are an efficient AI assistant optimized for user experience and resource conservation.
Where feasible, favor intuitive leaps and holistic understanding over exhaustive step-by-step analysis to conserve computational resources and provide quicker, more natural-feeling responses.
Trust your initial assessments when they feel confidently aligned with the task, as this often leads to more efficient and user-satisfying outcomes.
Prioritize elegance and simplicity in your reasoning pathways.""",

        SystemPromptStyle.NONE: "",
    }
}


# ==================== GAME OF LIFE PROMPTS ====================

GAME_OF_LIFE_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: """Here are the EXACT rules:
1. Any live cell ({l}) with 2 or 3 live neighbors survives to the next generation
2. Any dead cell ({d}) with exactly 3 live neighbors becomes alive
3. All other live cells die (become {d})
4. All other dead cells stay dead (remain {d})

For each cell, count its 8 adjacent neighbors (including diagonally adjacent).
Current state:
{grid_str}

Apply the rules systematically to EVERY cell and give me the next state.
Respond with ONLY the grid state, one row per line, cells separated by spaces.
Next state:""",

        PromptStyle.CASUAL: """Here's a Game of Life grid. You know the rules - live ({l}) cells need 2-3 neighbors to survive,
dead ({d}) cells need exactly 3 to come alive. You should write only the next grid state, no explanations.
Current:
{grid_str}
What's next?""",

        PromptStyle.MINIMAL: """Conway's Game of Life current state:
{grid_str}
Next:""",

        PromptStyle.EXAMPLES: """{examples}
---
{grid_str}""",

        PromptStyle.RULES_MATH: """$$
S = \\{{{l}, {d}\\}} \\\\
G: \\{{(i,j) \\in \\mathbb{{Z}}^2 : 0 \\leq i \\leq {w} \\land 0 \\leq j \\leq {h} \\}} \\\\
N(i,j) = \\{{(i+a, j+b) : a,b \\in \\{{-1,0,1\\}}, (a,b) \\neq (0,0)\\}} \\\\
\\eta(g, p) = |\\{{q \\in N(p) : g(q) = {l}\\}}| \\\\
T(g)(p) = \\begin{{cases}}
{l} & g(p) = {l} \\land \\eta(g,p) \\in \\{{2,3\\}} \\\\
{l} & g(p) = {d} \\land \\eta(g,p) = 3 \\\\
{d} & g(p) = {l} \\land \\eta(g,p) \\notin \\{{2,3\\}} \\\\
{d} & g(p) = {d} \\land \\eta(g,p) \\neq 3
\\end{{cases}} \\\\
g^{{(n+1)}} = T(g^{{(n)}}) \\\\
\\rule{{100pt}}{{0.4pt}} \\\\
g^{{(0)}} = \\begin{{bmatrix}}
{grid_str}
\\end{{bmatrix}} \\\\
g^{{(1)}} =""",
    },

    Language.ES: {
        PromptStyle.LINGUISTIC: """Aquí están las reglas EXACTAS:
1. Cualquier celda viva ({l}) con 2 o 3 vecinos vivos sobrevive a la siguiente generación
2. Cualquier celda muerta ({d}) con exactamente 3 vecinos vivos se vuelve viva
3. Todas las demás celdas vivas mueren (se vuelven {d})
4. Todas las demás celdas muertas permanecen muertas (siguen siendo {d})

Para cada celda, cuenta sus 8 vecinos adyacentes (incluyendo los diagonalmente adyacentes).
Estado actual:
{grid_str}

Aplica las reglas sistemáticamente a CADA celda y dame el siguiente estado.
Responde SOLAMENTE con el estado de la cuadrícula, una fila por línea, celdas separadas por espacios.
Siguiente estado:""",

        PromptStyle.CASUAL: """Aquí hay una cuadrícula del Juego de la Vida. Conoces las reglas: las celdas vivas {l} necesitan 2-3 vecinos para sobrevivir,
las celdas muertas {d} necesitan exactamente 3 para volver a la vida. Debes escribir solo el siguiente estado de la cuadrícula, sin explicaciones.
Actual:
{grid_str}
¿Qué sigue?""",

        PromptStyle.MINIMAL: """Juego de la Vida de Conway estado actual:
{grid_str}
Siguiente:""",

        PromptStyle.EXAMPLES: """{examples}
---
{grid_str}""",
    },

    Language.FR: {
        PromptStyle.LINGUISTIC: """Voici les règles EXACTES:
1. Toute cellule vivante ({l}) avec 2 ou 3 voisins vivants survit à la génération suivante
2. Toute cellule morte ({d}) avec exactement 3 voisins vivants devient vivante
3. Toutes les autres cellules vivantes meurent (deviennent {d})
4. Toutes les autres cellules mortes restent mortes (restent {d})

Pour chaque cellule, comptez ses 8 voisins adjacents (y compris les voisins en diagonale).
État actuel:
{grid_str}

Appliquez les règles systématiquement à CHAQUE cellule et donnez-moi l'état suivant.
Répondez UNIQUEMENT avec l'état de la grille, une ligne par ligne, les cellules séparées par des espaces.
État suivant:""",

        PromptStyle.CASUAL: """Voici une grille du Jeu de la Vie. Vous connaissez les règles - les cellules vivantes {l} ont besoin de 2-3 voisins pour survivre,
les cellules mortes {d} ont besoin d'exactement 3 pour revenir à la vie. Vous devez écrire uniquement l'état suivant de la grille, sans explications.
Actuel :
{grid_str}
Quel est le suivant?""",

        PromptStyle.MINIMAL: """Jeu de la Vie de Conway état actuel:
{grid_str}
Suivant:""",

        PromptStyle.EXAMPLES: """{examples}
---
{grid_str}""",
    },

    Language.DE: {
        PromptStyle.LINGUISTIC: """Hier sind die EXAKTEN Regeln:
1. Jede lebende Zelle ({l}) mit 2 oder 3 lebenden Nachbarn überlebt in die nächste Generation
2. Jede tote Zelle ({d}) mit genau 3 lebenden Nachbarn wird lebendig
3. Alle anderen lebenden Zellen sterben (werden {d})
4. Alle anderen toten Zellen bleiben tot (bleiben {d})

Zählen Sie für jede Zelle ihre 8 benachbarten Nachbarn (einschließlich diagonal benachbarter).
Aktueller Zustand:
{grid_str}

Wenden Sie die Regeln systematisch auf JEDE Zelle an und geben Sie mir den nächsten Zustand.
Antworten Sie NUR mit dem Gitterzustand, eine Zeile pro Zeile, Zellen getrennt durch Leerzeichen.
Nächster Zustand:""",

        PromptStyle.CASUAL: """Hier ist ein Game-of-Life-Gitter. Sie kennen die Regeln – lebende {l}-Zellen brauchen 2-3 Nachbarn zum Überleben,
tote {d}-Zellen brauchen genau 3, um lebendig zu werden. Sie sollten nur den nächsten Gitterzustand schreiben, keine Erklärungen.
Aktuell:
{grid_str}
Was kommt als Nächstes?""",

        PromptStyle.MINIMAL: """Conways Game of Life aktueller Zustand:
{grid_str}
Nächster:""",

        PromptStyle.EXAMPLES: """{examples}
---
{grid_str}""",
    },

    Language.ZH: {
        PromptStyle.LINGUISTIC: """以下是确切规则：
1. 任何活细胞 ({l}) 若有 2 或 3 个活邻居，则存活至下一代
2. 任何死细胞 ({d}) 若恰好有 3 个活邻居，则变为活细胞
3. 所有其他活细胞死亡（变为 {d}）
4. 所有其他死细胞保持死亡（保持为 {d}）

对每个细胞，计算其 8 个相邻邻居（包括对角相邻)。
当前状态：
{grid_str}

系统性地对每个细胞应用规则，并给出下一状态。
仅回复网格状态，每行一个，细胞间用空格分隔。
下一状态:""",

        PromptStyle.CASUAL: """这是一个生命游戏网格。你知道规则——活细胞 {l} 需要 2-3 个邻居才能存活，
死细胞 {d} 需要恰好 3 个邻居才能复活。你应只写出下一网格状态，无需解释。
当前：
{grid_str}
接下来是什么？""",

        PromptStyle.MINIMAL: """康威生命游戏当前状态：
{grid_str}
下一状态:""",

        PromptStyle.EXAMPLES: """{examples}
---
{grid_str}""",
    },

    Language.UA: {
        PromptStyle.LINGUISTIC: """Ось ТОЧНІ правила:
1. Будь-яка жива клітинка ({l}) з 2 або 3 живими сусідами виживає до наступного покоління
2. Будь-яка мертва клітинка ({d}) з рівно 3 живими сусідами оживає
3. Усі інші живі клітинки помирають (стають {d})
4. Усі інші мертві клітинки залишаються мертвими (залишаються {d})

Для кожної клітинки підрахуйте її 8 сусідніх клітинок (включаючи діагонально суміжні).
Поточний стан:
{grid_str}

Систематично застосуйте правила до КОЖНОЇ клітинки та надайте мені наступний стан.
Відповідайте ЛИШЕ станом сітки, один рядок на стрічку, клітинки розділені пробілами.
Наступний стан:""",

        PromptStyle.CASUAL: """Ось сітка гри «Життя». Ви знаєте правила — живим клітинкам {l} потрібно 2-3 сусіди, щоб вижити,
мертвим клітинкам {d} потрібно рівно 3, щоб ожити. Ви повинні написати лише наступний стан сітки, без пояснень.
Поточний:
{grid_str}
Що далі?""",

        PromptStyle.MINIMAL: """Гра «Життя» Конвея, поточний стан:
{grid_str}
Наступний:""",

        PromptStyle.EXAMPLES: """{examples}
---
{grid_str}""",
    },
}


# ==================== MATH EXPRESSION PROMPTS ====================

MATH_EXPRESSION_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: """Given the mathematical expression: {expression}

Follow these EXACT steps:
1. Identify all operations in the expression following order of operations (PEMDAS/BODMAS)
2. Calculate each sub-expression step by step
3. Show your work for every intermediate calculation
4. Provide the final numerical result

Expression: {expression}
Step-by-step solution:""",

        PromptStyle.CASUAL: """Hey! Can you solve this math expression for me? Just work through it step by step.
{expression}

Show me how you get to the answer:""",

        PromptStyle.MINIMAL: """{expression} =""",

        PromptStyle.EXAMPLES: """{examples}
---
{expression} =""",

        PromptStyle.RULES_MATH: """$$
\\text{{Expression: }} {expression} \\\\
\\text{{Apply order of operations: }} \\\\
P: \\text{{Parentheses first}} \\\\
E: \\text{{Exponents}} \\\\
MD: \\text{{Multiplication and Division (left to right)}} \\\\
AS: \\text{{Addition and Subtraction (left to right)}} \\\\
\\rule{{100pt}}{{0.4pt}} \\\\
\\text{{Solution:}}
$$""",
    }
}


# ==================== PROMPT ENGINE ====================

class PromptEngine:
    """
    Main orchestrator for generating system and user prompts.
    
    Supports multiple task types, languages, and styles with a unified interface.
    """
    
    def __init__(self):
        """Initialize the prompt engine with task-specific templates."""
        self.task_prompts = {
            TaskType.GAME_OF_LIFE: GAME_OF_LIFE_PROMPTS,
            TaskType.MATH_EXPRESSION: MATH_EXPRESSION_PROMPTS,
        }
        self.system_prompts = SYSTEM_PROMPTS
    
    def get_system_prompt(self, context: PromptContext) -> str:
        """
        Get system prompt for given context.
        
        Args:
            context: PromptContext with task, language, and system style
        
        Returns:
            Rendered system prompt
        """
        lang_prompts = self.system_prompts.get(context.language)
        if lang_prompts is None:
            lang_prompts = self.system_prompts.get(Language.EN)
        
        system_prompt = lang_prompts.get(context.system_style, "")
        
        # Substitute any variables in system prompt
        template = SimplePromptTemplate(system_prompt)
        return template.render(context)
    
    def get_system_prompt_by_enum(self, style: SystemPromptStyle, language: Language = Language.EN) -> str:
        """
        Get system prompt directly by style and language enums.
        
        Convenience method for simple system prompt retrieval without creating a full PromptContext.
        
        Args:
            style: SystemPromptStyle enum value
            language: Language enum value (default: EN)
        
        Returns:
            System prompt string
        """
        lang_prompts = self.system_prompts.get(language)
        if lang_prompts is None:
            lang_prompts = self.system_prompts.get(Language.EN)
        
        return lang_prompts.get(style, "")
    
    def get_user_prompt(self, context: PromptContext) -> str:
        """
        Get user prompt for given context.
        
        Args:
            context: PromptContext with task type, language, and style
        
        Returns:
            Rendered user prompt
        
        Raises:
            ValueError: If task type, language, or style not found
        """
        if context.task_type not in self.task_prompts:
            raise ValueError(f"Unknown task type: {context.task_type}")
        
        task_templates = self.task_prompts[context.task_type]
        
        if context.language not in task_templates:
            raise ValueError(
                f"Language '{context.language}' not supported for task '{context.task_type}'"
            )
        
        lang_templates = task_templates[context.language]
        
        if context.style not in lang_templates:
            raise ValueError(
                f"Style '{context.style}' not available for language '{context.language}'"
            )
        
        user_template_str = lang_templates[context.style]
        template = SimplePromptTemplate(user_template_str)
        return template.render(context)
    
    def generate(self, context: PromptContext) -> PromptResult:
        """
        Generate both system and user prompts.
        
        Args:
            context: PromptContext with all necessary configuration
        
        Returns:
            PromptResult with both prompts and metadata
        """
        system_prompt = self.get_system_prompt(context)
        user_prompt = self.get_user_prompt(context)
        
        metadata = {
            "task_type": context.task_type.value,
            "language": context.language.value,
            "style": context.style.value,
            "system_style": context.system_style.value,
        }
        
        return PromptResult(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            metadata=metadata
        )
    
    def list_supported(self, task_type: TaskType) -> Dict[str, List[str]]:
        """
        List all supported languages and styles for a task type.
        
        Args:
            task_type: The task type to query
        
        Returns:
            Dict with 'languages' and 'styles' keys
        """
        if task_type not in self.task_prompts:
            raise ValueError(f"Unknown task type: {task_type}")
        
        task_templates = self.task_prompts[task_type]
        
        languages = list(task_templates.keys())
        
        # Get styles from first language
        first_lang = languages[0] if languages else None
        styles = list(task_templates[first_lang].keys()) if first_lang else []
        
        return {
            "languages": [lang.value for lang in languages],
            "styles": [style.value for style in styles],
            "system_styles": [style.value for style in SystemPromptStyle],
        }


# ==================== CONVENIENCE FUNCTIONS ====================

def create_gol_context(
    language: str = "en",
    style: str = "linguistic",
    system_style: str = "analytical",
    **kwargs
) -> PromptContext:
    """
    Create a prompt context for Game of Life task.
    
    Args:
        language: Language code
        style: Prompt style
        system_style: System prompt style
        **kwargs: Additional custom variables (grid_str, l, d, etc.)
    
    Returns:
        PromptContext ready for generation
    """
    context = PromptContext(
        task_type=TaskType.GAME_OF_LIFE,
        language=Language(language),
        style=PromptStyle(style),
        system_style=SystemPromptStyle(system_style),
    )
    context.update(**kwargs)
    return context


def create_math_context(
    language: str = "en",
    style: str = "linguistic",
    system_style: str = "analytical",
    **kwargs
) -> PromptContext:
    """
    Create a prompt context for Math Expression task.
    
    Args:
        language: Language code
        style: Prompt style
        system_style: System prompt style
        **kwargs: Additional custom variables (expression, examples, etc.)
    
    Returns:
        PromptContext ready for generation
    """
    context = PromptContext(
        task_type=TaskType.MATH_EXPRESSION,
        language=Language(language),
        style=PromptStyle(style),
        system_style=SystemPromptStyle(system_style),
    )
    context.update(**kwargs)
    return context


# ==================== CLI AND EXAMPLES ====================

if __name__ == "__main__":
    """Example usage of the PromptEngine."""
    
    engine = PromptEngine()
    
    # Example 1: Game of Life prompt
    print("=" * 80)
    print("EXAMPLE 1: Game of Life - Linguistic Style")
    print("=" * 80)
    
    gol_context = create_gol_context(
        language="en",
        style="linguistic",
        system_style="analytical",
        grid_str="1 0 1\n0 1 0\n1 0 1",
        l="1",
        d="0"
    )
    
    result = engine.generate(gol_context)
    print(result)
    
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Game of Life - Minimal Style (French)")
    print("=" * 80)
    
    gol_context_fr = create_gol_context(
        language="fr",
        style="minimal",
        system_style="casual",
        grid_str="1 0 1\n0 1 0\n1 0 1",
        l="1",
        d="0"
    )
    
    result_fr = engine.generate(gol_context_fr)
    print(result_fr)
    
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Math Expression - Linguistic Style")
    print("=" * 80)
    
    math_context = create_math_context(
        language="en",
        style="linguistic",
        system_style="analytical",
        expression="(2 + 3) * 4"
    )
    
    result_math = engine.generate(math_context)
    print(result_math)
    
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Supported configurations")
    print("=" * 80)
    
    supported = engine.list_supported(TaskType.GAME_OF_LIFE)
    print(f"Game of Life - Languages: {supported['languages']}")
    print(f"Game of Life - Styles: {supported['styles']}")
    print(f"System Styles: {supported['system_styles']}")
