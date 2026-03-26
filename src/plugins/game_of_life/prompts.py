"""
Game of Life prompt templates.

6 languages × 3 styles (linguistic, casual, minimal).
Variables: {grid_str}, {l} (live cell marker), {d} (dead cell marker).

Note: EXAMPLES and RULES_MATH styles are deprecated and not included.
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "linguistic": """Here are the EXACT rules:
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

        "casual": """Conway's Game of Life! Here are the rules:
- Live cell ({l}): needs 2-3 live neighbors to survive, otherwise dies
- Dead cell ({d}): becomes alive if it has exactly 3 live neighbors

Current grid:
{grid_str}

What's the next generation? Just show the grid using {l} and {d}.""",

        "minimal": """Conway's Game of Life Rules:
- Live cell ({l}): survives if it has 2 or 3 live neighbors, otherwise dies
- Dead cell ({d}): becomes alive if it has exactly 3 live neighbors

Current state:
{grid_str}

Next generation (format as grid of {l} and {d}):""",
    },

    "es": {
        "linguistic": """Aquí están las reglas EXACTAS:
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

        "casual": """Aquí hay una cuadrícula del Juego de la Vida. Conoces las reglas: las celdas vivas {l} necesitan 2-3 vecinos para sobrevivir,
las celdas muertas {d} necesitan exactamente 3 para volver a la vida. Debes escribir solo el siguiente estado de la cuadrícula, sin explicaciones.
Actual:
{grid_str}
¿Qué sigue?""",

        "minimal": """Juego de la Vida de Conway estado actual:
{grid_str}
Siguiente:""",
    },

    "fr": {
        "linguistic": """Voici les règles EXACTES:
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

        "casual": """Voici une grille du Jeu de la Vie. Vous connaissez les règles - les cellules vivantes {l} ont besoin de 2-3 voisins pour survivre,
les cellules mortes {d} ont besoin d'exactement 3 pour revenir à la vie. Vous devez écrire uniquement l'état suivant de la grille, sans explications.
Actuel :
{grid_str}
Quel est le suivant?""",

        "minimal": """Jeu de la Vie de Conway état actuel:
{grid_str}
Suivant:""",
    },

    "de": {
        "linguistic": """Hier sind die EXAKTEN Regeln:
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

        "casual": """Hier ist ein Game-of-Life-Gitter. Sie kennen die Regeln – lebende {l}-Zellen brauchen 2-3 Nachbarn zum Überleben,
tote {d}-Zellen brauchen genau 3, um lebendig zu werden. Sie sollten nur den nächsten Gitterzustand schreiben, keine Erklärungen.
Aktuell:
{grid_str}
Was kommt als Nächstes?""",

        "minimal": """Conways Game of Life aktueller Zustand:
{grid_str}
Nächster:""",
    },

    "zh": {
        "linguistic": """以下是确切规则：
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

        "casual": """这是一个生命游戏网格。你知道规则——活细胞 {l} 需要 2-3 个邻居才能存活，
死细胞 {d} 需要恰好 3 个邻居才能复活。你应只写出下一网格状态，无需解释。
当前：
{grid_str}
接下来是什么？""",

        "minimal": """康威生命游戏当前状态：
{grid_str}
下一状态:""",
    },

    "ua": {
        "linguistic": """Ось ТОЧНІ правила:
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

        "casual": """Ось сітка гри «Життя». Ви знаєте правила — живим клітинкам {l} потрібно 2-3 сусіди, щоб вижити,
мертвим клітинкам {d} потрібно рівно 3, щоб ожити. Ви повинні написати лише наступний стан сітки, без пояснень.
Поточний:
{grid_str}
Що далі?""",

        "minimal": """Гра «Життя» Конвея, поточний стан:
{grid_str}
Наступний:""",
    },
}
