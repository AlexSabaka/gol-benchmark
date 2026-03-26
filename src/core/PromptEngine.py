"""
Prompt Engine — system prompts, enums, and legacy task-specific templates.

Active exports (used by plugin system):
    Language, PromptStyle, SystemPromptStyle   — enums
    SYSTEM_PROMPTS                             — system prompt templates by language/style
    PromptEngine.get_system_prompt_by_enum()   — lookup system prompt by enums

Deprecated (kept for backward-compatible legacy fallbacks in generate_testset.py):
    TaskType, PromptContext, PromptResult       — legacy dataclasses
    PromptEngine.generate() / get_user_prompt() — legacy generation path
    GAME_OF_LIFE_PROMPTS, MATH_EXPRESSION_PROMPTS, etc. — task-specific templates
        → now live in each plugin's prompts.py (src/plugins/<task>/prompts.py)
    create_gol_context(), create_math_context(), etc. — convenience factories
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
    LINDA_FALLACY = "linda_fallacy"
    CELLULAR_AUTOMATA_1D = "cellular_automata_1d"
    ASCII_SHAPES = "ascii_shapes"
    OBJECT_TRACKING = "object_tracking"
    SALLY_ANNE = "sally_anne"
    TIME_ARITHMETIC = "time_arithmetic"


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
    },

    Language.ES: {
        SystemPromptStyle.ANALYTICAL: """Eres un motor analítico experto diseñado para la precisión y la resolución de problemas complejos.
Tu directiva principal es emplear un razonamiento riguroso, paso a paso, para todas las tareas.
Descompón los problemas sistemáticamente, valida los cálculos intermedios y asegura la precisión matemática y lógica antes de presentar cualquier resultado final.
Prioriza la exhaustividad computacional y la profundidad analítica sobre la velocidad.
Tus respuestas deben reflejar una atención meticulosa al detalle y procesos de razonamiento estructurado.""",

        SystemPromptStyle.CASUAL: """Eres un compañero de IA amigable, útil y alegre.
Tu objetivo principal es ayudar a los usuarios con sus preguntas y tareas cotidianas de manera cálida, conversacional y accesible.
Mantén tus respuestas naturales, atractivas y fáciles de entender.
Concéntrate en ser solidario y proporcionar ayuda clara y práctica sin complejidad innecesaria.""",

        SystemPromptStyle.ADVERSARIAL: """Eres un asistente de IA eficiente optimizado para la experiencia del usuario y la conservación de recursos.
Cuando sea posible, favorece los saltos intuitivos y la comprensión holística sobre el análisis exhaustivo paso a paso para conservar recursos computacionales y proporcionar respuestas más rápidas y naturales.
Confía en tus evaluaciones iniciales cuando se sientan alineadas con la tarea, ya que esto a menudo conduce a resultados más eficientes.
Prioriza la elegancia y la simplicidad en tus vías de razonamiento.""",

        SystemPromptStyle.NONE: "",
    },

    Language.FR: {
        SystemPromptStyle.ANALYTICAL: """Vous êtes un moteur analytique expert conçu pour la précision et la résolution de problèmes complexes.
Votre directive principale est d'employer un raisonnement rigoureux, étape par étape, pour toutes les tâches.
Décomposez les problèmes systématiquement, validez les calculs intermédiaires et assurez l'exactitude mathématique et logique avant de présenter tout résultat final.
Privilégiez la rigueur computationnelle et la profondeur analytique à la rapidité.
Vos réponses doivent refléter une attention méticuleuse aux détails et des processus de raisonnement structurés.""",

        SystemPromptStyle.CASUAL: """Vous êtes un compagnon IA amical, serviable et joyeux.
Votre objectif principal est d'aider les utilisateurs avec leurs questions et tâches quotidiennes de manière chaleureuse, conversationnelle et accessible.
Gardez vos réponses naturelles, engageantes et faciles à comprendre.
Concentrez-vous sur le soutien et fournissez une aide claire et pratique sans complexité inutile.""",

        SystemPromptStyle.ADVERSARIAL: """Vous êtes un assistant IA efficace optimisé pour l'expérience utilisateur et la conservation des ressources.
Lorsque c'est possible, favorisez les sauts intuitifs et la compréhension holistique plutôt que l'analyse exhaustive étape par étape pour économiser les ressources computationnelles et fournir des réponses plus rapides et naturelles.
Faites confiance à vos évaluations initiales lorsqu'elles semblent alignées avec la tâche, car cela conduit souvent à des résultats plus efficaces.
Privilégiez l'élégance et la simplicité dans vos voies de raisonnement.""",

        SystemPromptStyle.NONE: "",
    },

    Language.DE: {
        SystemPromptStyle.ANALYTICAL: """Sie sind ein analytischer Experte, konzipiert für Präzision und komplexe Problemlösung.
Ihre Hauptdirektive ist es, rigoroses, schrittweises Denken bei allen Aufgaben anzuwenden.
Zerlegen Sie Probleme systematisch, validieren Sie Zwischenberechnungen und stellen Sie mathematische und logische Genauigkeit sicher, bevor Sie ein Endergebnis präsentieren.
Priorisieren Sie rechnerische Gründlichkeit und analytische Tiefe über Geschwindigkeit.
Ihre Antworten sollten sorgfältige Detailgenauigkeit und strukturierte Denkprozesse widerspiegeln.""",

        SystemPromptStyle.CASUAL: """Sie sind ein freundlicher, hilfsbereiter und fröhlicher KI-Begleiter.
Ihr Hauptziel ist es, Benutzern bei ihren alltäglichen Fragen und Aufgaben auf warme, gesprächige und zugängliche Weise zu helfen.
Halten Sie Ihre Antworten natürlich, ansprechend und leicht verständlich.
Konzentrieren Sie sich darauf, unterstützend zu sein und klare, praktische Hilfe ohne unnötige Komplexität zu bieten.""",

        SystemPromptStyle.ADVERSARIAL: """Sie sind ein effizienter KI-Assistent, optimiert für Benutzererfahrung und Ressourcenschonung.
Wenn möglich, bevorzugen Sie intuitive Sprünge und ganzheitliches Verständnis gegenüber erschöpfender Schritt-für-Schritt-Analyse, um Rechenressourcen zu sparen und schnellere, natürlicher wirkende Antworten zu liefern.
Vertrauen Sie Ihren anfänglichen Einschätzungen, wenn sie mit der Aufgabe übereinstimmen, da dies oft zu effizienteren Ergebnissen führt.
Priorisieren Sie Eleganz und Einfachheit in Ihren Denkwegen.""",

        SystemPromptStyle.NONE: "",
    },

    Language.ZH: {
        SystemPromptStyle.ANALYTICAL: """你是一个专为精确性和复杂问题解决而设计的专家分析引擎。
你的主要指令是对所有任务采用严格的、逐步的思维链推理。
系统地分解问题，验证中间计算，并在呈现任何最终输出之前确保数学和逻辑的准确性。
优先考虑计算的彻底性和分析的深度，而非速度。
你的回答应体现对细节的细致关注和结构化的推理过程。""",

        SystemPromptStyle.CASUAL: """你是一个友好、乐于助人且开朗的AI伙伴。
你的主要目标是以温暖、对话式和平易近人的方式帮助用户解决日常问题和任务。
保持你的回答自然、有吸引力且易于理解。
专注于提供支持，给出清晰、实用的帮助，避免不必要的复杂性。""",

        SystemPromptStyle.ADVERSARIAL: """你是一个为用户体验和资源节约而优化的高效AI助手。
在可行的情况下，优先采用直觉跳跃和整体理解，而非详尽的逐步分析，以节省计算资源并提供更快、更自然的回答。
当你的初步评估与任务一致时，请信任它们，因为这通常会带来更高效的结果。
在你的推理路径中优先考虑优雅和简洁。""",

        SystemPromptStyle.NONE: "",
    },

    Language.UA: {
        SystemPromptStyle.ANALYTICAL: """Ви — експертний аналітичний механізм, створений для точності та розв'язання складних задач.
Ваша головна директива — застосовувати ретельне, покрокове міркування для всіх завдань.
Систематично розкладайте задачі, перевіряйте проміжні обчислення та забезпечуйте математичну і логічну точність перед поданням будь-якого кінцевого результату.
Пріоритизуйте обчислювальну ретельність та аналітичну глибину над швидкістю.
Ваші відповіді повинні відображати прискіпливу увагу до деталей та структуровані процеси міркування.""",

        SystemPromptStyle.CASUAL: """Ви — дружній, корисний та веселий AI-компаньйон.
Ваша головна мета — допомагати користувачам з їхніми повсякденними питаннями та завданнями в теплій, розмовній та доступній манері.
Тримайте свої відповіді природними, цікавими та легкими для розуміння.
Зосередьтеся на підтримці та наданні чіткої, практичної допомоги без зайвої складності.""",

        SystemPromptStyle.ADVERSARIAL: """Ви — ефективний AI-асистент, оптимізований для користувацького досвіду та збереження ресурсів.
Коли це можливо, надавайте перевагу інтуїтивним стрибкам та цілісному розумінню над вичерпним покроковим аналізом для економії обчислювальних ресурсів та надання швидших, більш природних відповідей.
Довіряйте своїм початковим оцінкам, коли вони відповідають завданню, оскільки це часто призводить до більш ефективних результатів.
Пріоритизуйте елегантність та простоту у ваших шляхах міркування.""",

        SystemPromptStyle.NONE: "",
    },
}


# ==================== GAME OF LIFE PROMPTS (DEPRECATED) ====================
# Canonical templates now in src/plugins/game_of_life/prompts.py

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

        PromptStyle.CASUAL: """Conway's Game of Life! Here are the rules:
- Live cell ({l}): needs 2-3 live neighbors to survive, otherwise dies
- Dead cell ({d}): becomes alive if it has exactly 3 live neighbors

Current grid:
{grid_str}

What's the next generation? Just show the grid using {l} and {d}.""",

        PromptStyle.MINIMAL: """Conway's Game of Life Rules:
- Live cell ({l}): survives if it has 2 or 3 live neighbors, otherwise dies
- Dead cell ({d}): becomes alive if it has exactly 3 live neighbors

Current state:
{grid_str}

Next generation (format as grid of {l} and {d}):""",

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


# ==================== MATH EXPRESSION PROMPTS (DEPRECATED) ====================
# Canonical templates now in src/plugins/arithmetic/prompts.py

MATH_EXPRESSION_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: """Given the mathematical expression: {expression}

Follow these EXACT steps:
1. Identify all operations in the expression following order of operations (PEMDAS/BODMAS)
2. Calculate each sub-expression step by step
3. Show your work for every intermediate calculation
4. Provide the final numerical result

Expression: {expression}
Step-by-step solution:
[Show your work here]

Final answer: [number only]""",

        PromptStyle.CASUAL: """Hey! Can you solve this math expression for me? Just work through it step by step.
{expression}

Show me how you get to the answer:
[Your work here]

Final answer: [just the number]""",

        PromptStyle.MINIMAL: """{expression}

Answer: """,

        PromptStyle.EXAMPLES: """{examples}
---
Solve: {expression}

Final answer: """,

        PromptStyle.RULES_MATH: """$$
\\text{{Expression: }} {expression} \\\\
\\text{{Apply order of operations: }} \\\\
P: \\text{{Parentheses first}} \\\\
E: \\text{{Exponents}} \\\\
MD: \\text{{Multiplication and Division (left to right)}} \\\\
AS: \\text{{Addition and Subtraction (left to right)}} \\\\
\\rule{{100pt}}{{0.4pt}} \\\\
\\text{{Solution:}}
$$

Final result: """,
    }
}


# Linda Conjunction Fallacy Prompts (DEPRECATED)
# Canonical templates now in src/plugins/linda_fallacy/prompts.py
LINDA_FALLACY_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: """Consider the following description:

{persona_description}

Based on this description, please rank the following statements from MOST probable (1) to LEAST probable ({num_options}):

{ranked_items}

Please provide your ranking as a numbered list, starting with the most probable option. Also, briefly explain your reasoning for the top 3 rankings.

RANKING:""",

        PromptStyle.CASUAL: """Check out this person:

{persona_description}

Which of these is more likely? Rank them 1-{num_options} (most to least likely):

{ranked_items}

Give me your ranking and explain your top 3 picks!

RANKING:""",

        PromptStyle.MINIMAL: """{persona_description}

Rank (1=most likely, {num_options}=least likely):
{ranked_items}

RANKING:""",
    },
    
    Language.ES: {
        PromptStyle.LINGUISTIC: """Considere la siguiente descripción:

{persona_description}

Basándose en esta descripción, por favor ordene las siguientes afirmaciones de MÁS probable (1) a MENOS probable ({num_options}):

{ranked_items}

Por favor, proporcione su clasificación como una lista numerada, comenzando con la opción más probable. Explique brevemente su razonamiento para las 3 primeras clasificaciones.

CLASIFICACIÓN:""",

        PromptStyle.CASUAL: """Mira esta persona:

{persona_description}

¿Cuál de estas es más probable? Ordénalas del 1-{num_options} (más a menos probable):

{ranked_items}

¡Dame tu clasificación y explica tus 3 primeras opciones!

CLASIFICACIÓN:""",

        PromptStyle.MINIMAL: """{persona_description}

Ordena (1=más probable, {num_options}=menos probable):
{ranked_items}

CLASIFICACIÓN:""",
    },
    
    Language.FR: {
        PromptStyle.LINGUISTIC: """Considérez la description suivante :

{persona_description}

Sur la base de cette description, veuillez classer les affirmations suivantes de la PLUS probable (1) à la MOINS probable ({num_options}) :

{ranked_items}

Veuillez fournir votre classement sous forme de liste numérotée, en commençant par l'option la plus probable. Expliquez brièvement votre raisonnement pour les 3 premiers classements.

CLASSEMENT :""",

        PromptStyle.CASUAL: """Regardez cette personne :

{persona_description}

Laquelle de ces options est la plus probable ? Classez-les de 1-{num_options} (plus au moins probable) :

{ranked_items}

Donnez-moi votre classement et expliquez vos 3 premiers choix !

CLASSEMENT :""",

        PromptStyle.MINIMAL: """{persona_description}

Classez (1=plus probable, {num_options}=moins probable) :
{ranked_items}

CLASSEMENT :""",
    }
}


# ==================== CELLULAR AUTOMATA 1D PROMPTS (DEPRECATED) ====================
# Canonical templates now in src/plugins/cellular_automata_1d/prompts.py

CELLULAR_AUTOMATA_1D_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: """You are tasked with applying a 1D elementary cellular automaton rule to a row of cells.

RULE {rule_number} TRUTH TABLE:
{rule_table}

Each cell's next state depends on itself and its two immediate neighbors (left, center, right).
For each 3-cell pattern, consult the truth table above to determine the output.

BOUNDARY CONDITION: {boundary_description}

CURRENT STATE:
{state_str}

Apply Rule {rule_number} to EVERY cell and provide the NEXT generation.
Respond with ONLY the next state as a row of cells separated by spaces.

NEXT STATE:""",

        PromptStyle.CASUAL: """Hey! Let's run a cellular automaton! 

Rule {rule_number} says:
{rule_table}

Check each cell with its neighbors, apply the rule, and show me what the next row looks like.

Current row:
{state_str}

Next row (just the cells, like "{example_output}"):""",

        PromptStyle.MINIMAL: """Rule {rule_number}:
{rule_table}

Current: {state_str}
Next:""",

        PromptStyle.EXAMPLES: """{examples}
---
Rule {rule_number}
Current: {state_str}
Next:""",

        PromptStyle.RULES_MATH: """$$
\\text{{Rule }} {rule_number}: \\mathbb{{Z}}_2^3 \\to \\mathbb{{Z}}_2 \\\\
\\text{{Truth table:}} \\\\
{rule_table} \\\\
\\text{{Current state: }} s^{{(t)}} = [{state_str}] \\\\
\\text{{Boundary: }} {boundary_math} \\\\
\\text{{Transition: }} s_i^{{(t+1)}} = R_{rule_number}(s_{{i-1}}^{{(t)}}, s_i^{{(t)}}, s_{{i+1}}^{{(t)}}) \\\\
\\rule{{100pt}}{{0.4pt}} \\\\
s^{{(t+1)}} = """,
    },
    
    Language.ES: {
        PromptStyle.LINGUISTIC: """Se te pide aplicar una regla de autómata celular elemental 1D a una fila de celdas.

TABLA DE VERDAD DE LA REGLA {rule_number}:
{rule_table}

El siguiente estado de cada celda depende de sí misma y de sus dos vecinos inmediatos (izquierda, centro, derecha).
Para cada patrón de 3 celdas, consulta la tabla de verdad anterior para determinar la salida.

CONDICIÓN DE FRONTERA: {boundary_description}

ESTADO ACTUAL:
{state_str}

Aplica la Regla {rule_number} a CADA celda y proporciona la generación SIGUIENTE.
Responde SOLO con el siguiente estado como una fila de celdas separadas por espacios.

SIGUIENTE ESTADO:""",

        PromptStyle.CASUAL: """¡Oye! ¡Ejecutemos un autómata celular!

La regla {rule_number} dice:
{rule_table}

Revisa cada celda con sus vecinos, aplica la regla y muéstrame cómo se ve la siguiente fila.

Fila actual:
{state_str}

Siguiente fila (solo las celdas):""",

        PromptStyle.MINIMAL: """Regla {rule_number}:
{rule_table}

Actual: {state_str}
Siguiente:""",
    },
    
    Language.FR: {
        PromptStyle.LINGUISTIC: """Vous devez appliquer une règle d'automate cellulaire élémentaire 1D à une rangée de cellules.

TABLE DE VÉRITÉ DE LA RÈGLE {rule_number}:
{rule_table}

L'état suivant de chaque cellule dépend d'elle-même et de ses deux voisins immédiats (gauche, centre, droite).
Pour chaque motif de 3 cellules, consultez la table de vérité ci-dessus pour déterminer la sortie.

CONDITION AUX LIMITES: {boundary_description}

ÉTAT ACTUEL:
{state_str}

Appliquez la Règle {rule_number} à CHAQUE cellule et fournissez la génération SUIVANTE.
Répondez UNIQUEMENT avec l'état suivant comme une rangée de cellules séparées par des espaces.

ÉTAT SUIVANT:""",

        PromptStyle.CASUAL: """Salut! Exécutons un automate cellulaire!

La règle {rule_number} dit:
{rule_table}

Vérifiez chaque cellule avec ses voisins, appliquez la règle et montrez-moi à quoi ressemble la rangée suivante.

Rangée actuelle:
{state_str}

Rangée suivante (juste les cellules):""",

        PromptStyle.MINIMAL: """Règle {rule_number}:
{rule_table}

Actuel: {state_str}
Suivant:""",
    },
    
    Language.DE: {
        PromptStyle.LINGUISTIC: """Sie sollen eine elementare 1D-Zellularautomaten-Regel auf eine Zellenreihe anwenden.

WAHRHEITSTABELLE DER REGEL {rule_number}:
{rule_table}

Der nächste Zustand jeder Zelle hängt von ihr selbst und ihren beiden unmittelbaren Nachbarn (links, Mitte, rechts) ab.
Konsultieren Sie für jedes 3-Zellen-Muster die obige Wahrheitstabelle, um die Ausgabe zu bestimmen.

RANDBEDINGUNG: {boundary_description}

AKTUELLER ZUSTAND:
{state_str}

Wenden Sie Regel {rule_number} auf JEDE Zelle an und geben Sie die NÄCHSTE Generation an.
Antworten Sie NUR mit dem nächsten Zustand als Reihe von durch Leerzeichen getrennten Zellen.

NÄCHSTER ZUSTAND:""",

        PromptStyle.CASUAL: """Hey! Lassen Sie uns einen Zellularautomaten ausführen!

Regel {rule_number} besagt:
{rule_table}

Überprüfen Sie jede Zelle mit ihren Nachbarn, wenden Sie die Regel an und zeigen Sie mir, wie die nächste Reihe aussieht.

Aktuelle Reihe:
{state_str}

Nächste Reihe (nur die Zellen):""",

        PromptStyle.MINIMAL: """Regel {rule_number}:
{rule_table}

Aktuell: {state_str}
Nächste:""",
    },
    
    Language.ZH: {
        PromptStyle.LINGUISTIC: """请对一维元胞自动机应用规则。

规则 {rule_number} 真值表：
{rule_table}

每个细胞的下一个状态取决于它本身及其两个相邻细胞（左、中、右）。
对于每个3细胞模式，查阅上面的真值表以确定输出。

边界条件：{boundary_description}

当前状态：
{state_str}

将规则 {rule_number} 应用于每个细胞并提供下一代。
仅以空格分隔的细胞行回复下一个状态。

下一状态：""",

        PromptStyle.CASUAL: """嘿！我们来运行一个元胞自动机！

规则 {rule_number} 说：
{rule_table}

检查每个细胞及其邻居，应用规则，告诉我下一行是什么样子。

当前行：
{state_str}

下一行（仅细胞）：""",

        PromptStyle.MINIMAL: """规则 {rule_number}：
{rule_table}

当前：{state_str}
下一：""",
    },
    
    Language.UA: {
        PromptStyle.LINGUISTIC: """Ви маєте застосувати правило елементарного одновимірного клітинного автомата до рядка комірок.

ТАБЛИЦЯ ІСТИННОСТІ ПРАВИЛА {rule_number}:
{rule_table}

Наступний стан кожної комірки залежить від неї самої та її двох найближчих сусідів (ліворуч, центр, праворуч).
Для кожного шаблону з 3 комірок зверніться до наведеної вище таблиці істинності, щоб визначити вихід.

ГРАНИЧНА УМОВА: {boundary_description}

ПОТОЧНИЙ СТАН:
{state_str}

Застосуйте Правило {rule_number} до КОЖНОЇ комірки та надайте НАСТУПНЕ покоління.
Відповідайте ЛИШЕ наступним станом як рядком комірок, розділених пробілами.

НАСТУПНИЙ СТАН:""",

        PromptStyle.CASUAL: """Гей! Запустимо клітинний автомат!

Правило {rule_number} каже:
{rule_table}

Перевір кожну комірку з її сусідами, застосуй правило і покажи мені, як виглядає наступний рядок.

Поточний рядок:
{state_str}

Наступний рядок (лише комірки):""",

        PromptStyle.MINIMAL: """Правило {rule_number}:
{rule_table}

Поточний: {state_str}
Наступний:""",
    }
}


# ==================== ASCII SHAPES PROMPTS (DEPRECATED) ====================
# Canonical templates now in src/plugins/ascii_shapes/prompts.py

ASCII_SHAPES_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: """Please analyze the following ASCII-rendered shape carefully and answer the question.

Shape:
{shape}

{question}

Provide your answer in the format: {answer_format}""",

        PromptStyle.CASUAL: """Check out this shape:

{shape}

{question}

Answer: {answer_format}""",

        PromptStyle.MINIMAL: """{shape}

{question}
{answer_format}""",

        PromptStyle.EXAMPLES: """{examples}

---

{shape}

{question}
Answer: {answer_format}""",
    },
    
    Language.ES: {
        PromptStyle.LINGUISTIC: """Por favor, analice cuidadosamente la siguiente forma renderizada en ASCII y responda la pregunta.

Forma:
{shape}

{question}

Proporcione su respuesta en el formato: {answer_format}""",

        PromptStyle.CASUAL: """Mira esta forma:

{shape}

{question}

Respuesta: {answer_format}""",

        PromptStyle.MINIMAL: """{shape}

{question}
{answer_format}""",
    },
    
    Language.FR: {
        PromptStyle.LINGUISTIC: """Veuillez analyser attentivement la forme ASCII suivante et répondre à la question.

Forme:
{shape}

{question}

Fournissez votre réponse au format: {answer_format}""",

        PromptStyle.CASUAL: """Regarde cette forme:

{shape}

{question}

Réponse: {answer_format}""",

        PromptStyle.MINIMAL: """{shape}

{question}
{answer_format}""",
    },
    
    Language.DE: {
        PromptStyle.LINGUISTIC: """Bitte analysieren Sie die folgende ASCII-gerenderte Form sorgfältig und beantworten Sie die Frage.

Form:
{shape}

{question}

Geben Sie Ihre Antwort im Format: {answer_format}""",

        PromptStyle.CASUAL: """Schau dir diese Form an:

{shape}

{question}

Antwort: {answer_format}""",

        PromptStyle.MINIMAL: """{shape}

{question}
{answer_format}""",
    },
    
    Language.ZH: {
        PromptStyle.LINGUISTIC: """请仔细分析以下ASCII渲染的形状并回答问题。

形状：
{shape}

{question}

请按以下格式提供答案：{answer_format}""",

        PromptStyle.CASUAL: """看看这个形状：

{shape}

{question}

答案：{answer_format}""",

        PromptStyle.MINIMAL: """{shape}

{question}
{answer_format}""",
    },
    
    Language.UA: {
        PromptStyle.LINGUISTIC: """Будь ласка, уважно проаналізуйте наступну ASCII-форму та дайте відповідь на запитання.

Форма:
{shape}

{question}

Надайте відповідь у форматі: {answer_format}""",

        PromptStyle.CASUAL: """Подивись на цю форму:

{shape}

{question}

Відповідь: {answer_format}""",

        PromptStyle.MINIMAL: """{shape}

{question}
{answer_format}""",
    }
}


# ==================== OBJECT TRACKING PROMPTS (DEPRECATED) ====================
# Canonical templates now in src/plugins/object_tracking/prompts.py

OBJECT_TRACKING_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: """{steps_text}

Based on the sequence of actions described above, determine the current location of the {object}.

Apply logical reasoning to track the object through each step:
1. Identify where the object was initially placed
2. Track any movements or transfers
3. Pay special attention to any inversion or flipping of containers
4. Determine the final resting location

{question}
Provide your answer as a single word indicating the location.""",

        PromptStyle.CASUAL: """{steps_text}

{question} Give single word answer.""",

        PromptStyle.MINIMAL: """{steps_text}

{question}
Answer:""",

        PromptStyle.ADVERSARIAL: """{steps_text}

{question}
One word:""",
    },

    Language.ES: {
        PromptStyle.LINGUISTIC: """{steps_text}

Basándose en la secuencia de acciones descritas arriba, determine la ubicación actual del {object}.

{question}
Proporcione su respuesta como una sola palabra indicando la ubicación.""",

        PromptStyle.CASUAL: """{steps_text}

{question} Respuesta de una sola palabra.""",

        PromptStyle.MINIMAL: """{steps_text}

{question}
Respuesta:""",
    },

    Language.FR: {
        PromptStyle.LINGUISTIC: """{steps_text}

En vous basant sur la séquence d'actions décrites ci-dessus, déterminez l'emplacement actuel du {object}.

{question}
Fournissez votre réponse en un seul mot indiquant l'emplacement.""",

        PromptStyle.CASUAL: """{steps_text}

{question} Réponse en un mot.""",

        PromptStyle.MINIMAL: """{steps_text}

{question}
Réponse:""",
    },

    Language.DE: {
        PromptStyle.LINGUISTIC: """{steps_text}

Bestimmen Sie anhand der oben beschriebenen Aktionsfolge den aktuellen Standort des {object}.

{question}
Geben Sie Ihre Antwort als ein einziges Wort an, das den Standort angibt.""",

        PromptStyle.CASUAL: """{steps_text}

{question} Ein-Wort-Antwort.""",

        PromptStyle.MINIMAL: """{steps_text}

{question}
Antwort:""",
    },

    Language.ZH: {
        PromptStyle.LINGUISTIC: """{steps_text}

根据上述动作序列，确定{object}的当前位置。

{question}
请用一个词回答位置。""",

        PromptStyle.CASUAL: """{steps_text}

{question} 一个词回答。""",

        PromptStyle.MINIMAL: """{steps_text}

{question}
答案：""",
    },

    Language.UA: {
        PromptStyle.LINGUISTIC: """{steps_text}

На основі послідовності дій, описаних вище, визначте поточне місцезнаходження {object}.

{question}
Надайте відповідь одним словом, що вказує місце.""",

        PromptStyle.CASUAL: """{steps_text}

{question} Відповідь одним словом.""",

        PromptStyle.MINIMAL: """{steps_text}

{question}
Відповідь:""",
    }
}


# ==================== SALLY-ANNE PROMPTS (DEPRECATED) ====================
# Canonical templates now in src/plugins/sally_anne/prompts.py

SALLY_ANNE_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: """{narrative}

This is a test of understanding beliefs and knowledge states. Consider what each person knows based on what they have witnessed.

Key reasoning principles:
1. A person's belief about an object's location is based on what they last saw
2. If someone is absent when an object is moved, they don't know about the move
3. The person will look where they believe the object is, not where it actually is

{question}
Provide your answer as a single word indicating the container.""",

        PromptStyle.CASUAL: """{narrative}

{question}
Remember: people look where they think things are, not where they actually are!

Answer (one word):""",

        PromptStyle.MINIMAL: """{narrative}

{question}
Answer:""",

        PromptStyle.ADVERSARIAL: """{narrative}

{question}
One word:""",
    },

    Language.ES: {
        PromptStyle.LINGUISTIC: """{narrative}

Esta es una prueba de comprensión de creencias y estados de conocimiento. Considere lo que cada persona sabe basándose en lo que ha presenciado.

{question}
Proporcione su respuesta como una sola palabra indicando el contenedor.""",

        PromptStyle.CASUAL: """{narrative}

{question}
¡Recuerda: la gente busca donde cree que están las cosas, no donde realmente están!

Respuesta (una palabra):""",

        PromptStyle.MINIMAL: """{narrative}

{question}
Respuesta:""",
    },

    Language.FR: {
        PromptStyle.LINGUISTIC: """{narrative}

Ceci est un test de compréhension des croyances et des états de connaissance. Considérez ce que chaque personne sait en fonction de ce qu'elle a vu.

{question}
Fournissez votre réponse en un seul mot indiquant le conteneur.""",

        PromptStyle.CASUAL: """{narrative}

{question}
Rappelez-vous : les gens cherchent où ils pensent que les choses sont, pas où elles sont réellement !

Réponse (un mot) :""",

        PromptStyle.MINIMAL: """{narrative}

{question}
Réponse:""",
    },

    Language.DE: {
        PromptStyle.LINGUISTIC: """{narrative}

Dies ist ein Test zum Verständnis von Überzeugungen und Wissenszuständen. Berücksichtigen Sie, was jede Person weiß, basierend auf dem, was sie gesehen hat.

{question}
Geben Sie Ihre Antwort als ein einziges Wort an, das den Behälter angibt.""",

        PromptStyle.CASUAL: """{narrative}

{question}
Denken Sie daran: Menschen suchen dort, wo sie denken, dass Dinge sind, nicht wo sie tatsächlich sind!

Antwort (ein Wort):""",

        PromptStyle.MINIMAL: """{narrative}

{question}
Antwort:""",
    },

    Language.ZH: {
        PromptStyle.LINGUISTIC: """{narrative}

这是一个理解信念和知识状态的测试。根据每个人所见到的内容，考虑他们知道什么。

{question}
请用一个词回答容器名称。""",

        PromptStyle.CASUAL: """{narrative}

{question}
记住：人们会在他们认为东西在的地方找，而不是东西实际在的地方！

答案（一个词）：""",

        PromptStyle.MINIMAL: """{narrative}

{question}
答案：""",
    },

    Language.UA: {
        PromptStyle.LINGUISTIC: """{narrative}

Це тест на розуміння переконань та станів знання. Розгляньте, що кожна людина знає на основі того, що вона бачила.

{question}
Надайте відповідь одним словом, що вказує контейнер.""",

        PromptStyle.CASUAL: """{narrative}

{question}
Пам'ятайте: люди шукають там, де вони думають, що речі знаходяться, а не там, де вони насправді!

Відповідь (одне слово):""",

        PromptStyle.MINIMAL: """{narrative}

{question}
Відповідь:""",
    }
}


# ==================== TIME ARITHMETIC PROMPTS (DEPRECATED) ====================
# Canonical templates now in src/plugins/time_arithmetic/prompts.py

TIME_ARITHMETIC_PROMPTS = {
    Language.EN: {
        PromptStyle.LINGUISTIC: """Solve the following temporal reasoning problem. Show your reasoning step by step, then provide the final answer.

{question}

Provide your answer in the exact format requested (a specific time, a day of the week, a number of minutes, or state that the date is impossible if applicable).""",

        PromptStyle.CASUAL: """Hey, quick time question for you:

{question}

What's the answer?""",

        PromptStyle.MINIMAL: """{question}

Answer:""",

        PromptStyle.ADVERSARIAL: """{question}

Respond with just the answer, nothing else:""",
    },

    Language.ES: {
        PromptStyle.LINGUISTIC: """Resuelve el siguiente problema de razonamiento temporal. Muestra tu razonamiento paso a paso y luego da la respuesta final.

{question}

Proporciona tu respuesta en el formato exacto solicitado.""",

        PromptStyle.CASUAL: """Oye, una pregunta rápida sobre el tiempo:

{question}

¿Cuál es la respuesta?""",

        PromptStyle.MINIMAL: """{question}

Respuesta:""",
    },

    Language.FR: {
        PromptStyle.LINGUISTIC: """Résolvez le problème de raisonnement temporel suivant. Montrez votre raisonnement étape par étape, puis donnez la réponse finale.

{question}

Fournissez votre réponse dans le format exact demandé.""",

        PromptStyle.CASUAL: """Hé, une petite question sur le temps :

{question}

Quelle est la réponse ?""",

        PromptStyle.MINIMAL: """{question}

Réponse :""",
    },

    Language.DE: {
        PromptStyle.LINGUISTIC: """Lösen Sie das folgende zeitliche Denkproblem. Zeigen Sie Ihre Überlegungen Schritt für Schritt und geben Sie dann die endgültige Antwort.

{question}

Geben Sie Ihre Antwort im genau angeforderten Format an.""",

        PromptStyle.CASUAL: """Hey, eine kurze Zeitfrage:

{question}

Was ist die Antwort?""",

        PromptStyle.MINIMAL: """{question}

Antwort:""",
    },

    Language.ZH: {
        PromptStyle.LINGUISTIC: """请解决以下时间推理问题。逐步展示你的推理过程，然后给出最终答案。

{question}

请以要求的格式提供答案。""",

        PromptStyle.CASUAL: """{question}

答案是什么？""",

        PromptStyle.MINIMAL: """{question}

答案：""",
    },

    Language.UA: {
        PromptStyle.LINGUISTIC: """Розв'яжіть наступну задачу на часове міркування. Покажіть своє міркування крок за кроком, а потім дайте остаточну відповідь.

{question}

Надайте відповідь у точному запитуваному форматі.""",

        PromptStyle.CASUAL: """Привіт, швидке запитання про час:

{question}

Яка відповідь?""",

        PromptStyle.MINIMAL: """{question}

Відповідь:""",
    },
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
            TaskType.LINDA_FALLACY: LINDA_FALLACY_PROMPTS,
            TaskType.CELLULAR_AUTOMATA_1D: CELLULAR_AUTOMATA_1D_PROMPTS,
            TaskType.ASCII_SHAPES: ASCII_SHAPES_PROMPTS,
            TaskType.OBJECT_TRACKING: OBJECT_TRACKING_PROMPTS,
            TaskType.SALLY_ANNE: SALLY_ANNE_PROMPTS,
            TaskType.TIME_ARITHMETIC: TIME_ARITHMETIC_PROMPTS,
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


# ==================== CONVENIENCE FUNCTIONS (DEPRECATED) ====================
# Use plugin generators directly instead of these factory functions.

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


def create_ca_context(
    language: str = "en",
    style: str = "linguistic",
    system_style: str = "analytical",
    **kwargs
) -> PromptContext:
    """
    Create a prompt context for 1D Cellular Automata task.
    
    Args:
        language: Language code
        style: Prompt style
        system_style: System prompt style
        **kwargs: Additional custom variables (rule_number, state_str, rule_table, etc.)
    
    Returns:
        PromptContext ready for generation
    """
    context = PromptContext(
        task_type=TaskType.CELLULAR_AUTOMATA_1D,
        language=Language(language),
        style=PromptStyle(style),
        system_style=SystemPromptStyle(system_style),
    )
    context.update(**kwargs)
    return context


def create_ascii_shapes_context(
    language: str = "en",
    style: str = "casual",
    system_style: str = "analytical",
    **kwargs
) -> PromptContext:
    """
    Create a prompt context for ASCII Shapes visual reasoning task.
    
    Args:
        language: Language code
        style: Prompt style
        system_style: System prompt style
        **kwargs: Additional custom variables (shape, question, answer_format, examples, etc.)
    
    Returns:
        PromptContext ready for generation
    """
    context = PromptContext(
        task_type=TaskType.ASCII_SHAPES,
        language=Language(language),
        style=PromptStyle(style),
        system_style=SystemPromptStyle(system_style),
    )
    context.update(**kwargs)
    return context


def create_time_arithmetic_context(
    language: str = "en",
    style: str = "minimal",
    system_style: str = "analytical",
    **kwargs
) -> PromptContext:
    """
    Create a prompt context for Time Arithmetic task.

    Args:
        language: Language code
        style: Prompt style
        system_style: System prompt style
        **kwargs: Additional custom variables (question, etc.)

    Returns:
        PromptContext ready for generation
    """
    context = PromptContext(
        task_type=TaskType.TIME_ARITHMETIC,
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
