"""
Define different prompt styles for the Game of Life task in multiple languages
Supported styles: "systematic", "casual", "minimal"
Supported languages: "en" (English), "fr" (French), "es" (Spanish), "de" (German), "zh" (Chinese), "ua" (Ukrainian)
"""

PROMPT_STYLES_EN = {
    "systematic": 
"""You are applying Conway's Game of Life rules. Here are the EXACT rules:
1. Any live cell (1) with 2 or 3 live neighbors survives to the next generation
2. Any dead cell (0) with exactly 3 live neighbors becomes alive
3. All other live cells die (become 0)
4. All other dead cells stay dead (remain 0)

For each cell, count its 8 adjacent neighbors (including diagonally adjacent).
Current state:
{grid_str}

Apply the rules systematically to EVERY cell and give me the next state.
Respond with ONLY the grid numbers, one row per line, numbers separated by spaces.
Next state:""",

    "casual":
"""Here's a Game of Life grid. You know the rules - live cells need 2-3 neighbors to survive,
dead cells need exactly 3 to come alive.
Current:
{grid_str}
What's next?""",

    "minimal":
"""Game of Life next state:
{grid_str}
Next:"""
}

PROMPT_STYLES_ES = {
    "systematic":
"""Estás aplicando las reglas del Juego de la Vida de Conway. Aquí están las reglas EXACTAS:
1. Cualquier célula viva (1) con 2 o 3 vecinos vivos sobrevive a la siguiente generación
2. Cualquier célula muerta (0) con exactamente 3 vecinos vivos se vuelve viva
3. Todas las demás células vivas mueren (se convierten en 0)
4. Todas las demás células muertas permanecen muertas (permanecen 0)
Para cada célula, cuenta sus 8 vecinos adyacentes (incluyendo los diagonalmente adyacentes).
Estado actual:
{grid_str}
Aplica las reglas sistemáticamente a CADA célula y dame el siguiente estado.
Responde SOLO con los números de la cuadrícula, una fila por línea, números separados por espacios.
Siguiente estado:""",

    "casual":
"""Aquí hay una cuadrícula del Juego de la Vida. Conoces las reglas: las células vivas necesitan 2-3 vecinos para sobrevivir,
las células muertas necesitan exactamente 3 para volverse vivas.
Actual:
{grid_str}
¿Qué sigue?""",

    "minimal":
"""Siguiente estado del Juego de la Vida:
{grid_str}
Siguiente:"""
}

PROMPT_STYLES_FR = {
    "systematic":
"""Vous appliquez les règles du Jeu de la Vie de Conway. Voici les règles EXACTES :
1. Toute cellule vivante (1) avec 2 ou 3 voisins vivants survit à la génération suivante
2. Toute cellule morte (0) avec exactement 3 voisins vivants devient vivante
3. Toutes les autres cellules vivantes meurent (deviennent 0)
4. Toutes les autres cellules mortes restent mortes (restent 0)
Pour chaque cellule, comptez ses 8 voisins adjacents (y compris les diagonalement adjacents).
État actuel :
{grid_str}
Appliquez les règles systématiquement à CHAQUE cellule et donnez-moi l'état suivant.
Répondez UNIQUEMENT avec les numéros de la grille, une ligne par ligne, numéros séparés par des espaces.
État suivant :""",

    "casual":
"""Voici une grille du Jeu de la Vie. Vous connaissez les règles : les cellules vivantes ont besoin de 2-3 voisins pour survivre,
les cellules mortes ont besoin de exactement 3 pour devenir vivantes.
Actuel :
{grid_str}
Quelle est la suite ?""",

    "minimal":
"""Prochain état du Jeu de la Vie :
{grid_str}
Prochain :"""
}

PROMPT_STYLES_DE = {
    "systematic":
"""Du wendest die Regeln von Conways Spiel des Lebens an. Hier sind die GENAUEN Regeln:
1. Jede lebende Zelle (1) mit 2 oder 3 lebenden Nachbarn überlebt in die nächste Generation
2. Jede tote Zelle (0) mit genau 3 lebenden Nachbarn wird lebendig
3. Alle anderen lebenden Zellen sterben (werden zu 0)
4. Alle anderen toten Zellen bleiben tot (bleiben 0)
Zähle für jede Zelle ihre 8 angrenzenden Nachbarn (einschließlich diagonal angrenzender).
Aktueller Zustand:
{grid_str}
Wende die Regeln systematisch auf JEDE Zelle an und gib mir den nächsten Zustand.
Antworte NUR mit den Gitterzahlen, eine Zeile pro Zeile, Zahlen durch Leerzeichen getrennt.
Nächster Zustand:""",

    "casual":
"""Hier ist ein Gitter des Spiels des Lebens. Du kennst die Regeln - lebende Zellen brauchen 2-3 Nachbarn zum Überleben,
tote Zellen brauchen genau  3, um lebendig zu werden.
Aktuell:
{grid_str}
Was kommt als nächstes?""",

    "minimal":
"""Nächster Zustand des Spiels des Lebens:
{grid_str}
Nächster:"""
}

PROMPT_STYLES_ZH = {
    "systematic":
"""你正在应用康威的生命游戏规则。以下是确切的规则：
1. 任何有2或3个活邻居的活细胞（1）在下一代中存活
2. 任何有且仅有3个活邻居的死细胞（0）变为活细胞
3. 所有其他活细胞死亡（变为0）
4. 所有其他死细胞保持死亡（保持为0）
对于每个细胞，计算其8个相邻邻居（包括对角线相邻的）。
当前状态：
{grid_str}
系统地将规则应用于每个细胞，并给我下一个状态。
仅以网格数字响应，每行一行，数字之间用空格分隔。
下一个状态：""",

    "casual":
"""这是一个生命游戏的网格。你知道规则——活细胞需要2-3个邻居才能存活，
死细胞需要恰好3个邻居才能变为活细胞。
当前：
{grid_str}
接下来是什么？""",

    "minimal":
"""生命游戏的下一个状态：
{grid_str}
下一个："""
}

PROMPT_STYLES_UA = {
    "systematic":
"""Ви застосовуєте правила гри "Життя" Конвея. Ось точні правила:
1. Будь-яка жива клітина (1) з 2 або 3 живими сусідами виживає до наступного покоління
2. Будь-яка мертва клітина (0) з рівно 3 живими сусідами стає живою
3. Всі інші живі клітини вмирають (стають 0)
4. Всі інші мертві клітини залишаються мертвими (залишаються 0)
Для кожної клітини порахуйте її 8 прилеглих сусідів (включаючи діагонально прилеглих).
Поточний стан:
{grid_str}
Застосуйте правила систематично до КОЖНОЇ клітини і дайте мені наступний стан.
Відповідайте ЛИШЕ числами сітки, по одному рядку на рядок, числа розділені пробілами.
Наступний стан:""",

    "casual":
"""Ось сітка гри "Життя". Ви знаєте правила - живі клітини потребують 2-3 сусідів, щоб вижити,
мертві клітини потребують рівно 3, щоб стати живими.
Поточний:
{grid_str}
Що далі?""",

    "minimal":
"""Наступний стан гри "Життя":
{grid_str}
Наступний:"""
}

def get_prompt_style(language: str, style: str) -> str:
    """Retrieve the prompt template based on language and style."""
    styles = {
        "en": PROMPT_STYLES_EN,
        "es": PROMPT_STYLES_ES,
        "fr": PROMPT_STYLES_FR,
        "de": PROMPT_STYLES_DE,
        "zh": PROMPT_STYLES_ZH,
        "ua": PROMPT_STYLES_UA
    }
    if language not in styles:
        raise ValueError(f"Unsupported language: {language}")
    if style not in styles[language]:
        raise ValueError(f"Unsupported style: {style}")
    return styles[language][style]