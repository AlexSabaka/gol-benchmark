"""
Cellular Automata 1D prompt templates.

6 languages × 3 styles (linguistic, casual, minimal).
Variables: {rule_number}, {rule_table}, {state_str}, {boundary_description}.

Note: EXAMPLES and RULES_MATH styles are deprecated and not included.
"""

# Boundary condition descriptions by language
BOUNDARY_DESCRIPTIONS = {
    "en": {
        "wrap": "Cells wrap around (the last cell is neighbor to the first cell)",
        "dead": "Cells outside the boundary are treated as dead (0)",
        "alive": "Cells outside the boundary are treated as alive (1)",
    },
    "es": {
        "wrap": "Las celdas envuelven (la última celda es vecina de la primera)",
        "dead": "Las celdas fuera del límite se consideran muertas (0)",
        "alive": "Las celdas fuera del límite se consideran vivas (1)",
    },
    "fr": {
        "wrap": "Les cellules bouclent (la dernière cellule est voisine de la première)",
        "dead": "Les cellules hors limites sont considérées comme mortes (0)",
        "alive": "Les cellules hors limites sont considérées comme vivantes (1)",
    },
    "de": {
        "wrap": "Zellen umbrechen (die letzte Zelle ist Nachbar der ersten Zelle)",
        "dead": "Zellen außerhalb der Grenze werden als tot (0) behandelt",
        "alive": "Zellen außerhalb der Grenze werden als lebendig (1) behandelt",
    },
    "zh": {
        "wrap": "细胞环绕（最后一个细胞与第一个细胞相邻）",
        "dead": "边界外的细胞视为死亡（0）",
        "alive": "边界外的细胞视为存活（1）",
    },
    "ua": {
        "wrap": "Комірки обертаються (остання комірка є сусідом першої)",
        "dead": "Комірки за межами вважаються мертвими (0)",
        "alive": "Комірки за межами вважаються живими (1)",
    },
}

USER_PROMPT_TEMPLATES = {
    "en": {
        "linguistic": """You are tasked with applying a 1D elementary cellular automaton rule to a row of cells.

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

        "casual": """Hey! Let's run a cellular automaton! 

Rule {rule_number} says:
{rule_table}

Check each cell with its neighbors, apply the rule, and show me what the next row looks like.

Current row:
{state_str}

Next row (just the cells, space-separated):""",

        "minimal": """Rule {rule_number}:
{rule_table}

Current: {state_str}
Next:""",
    },

    "es": {
        "linguistic": """Se te pide aplicar una regla de autómata celular elemental 1D a una fila de celdas.

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

        "casual": """¡Oye! ¡Ejecutemos un autómata celular!

La regla {rule_number} dice:
{rule_table}

Revisa cada celda con sus vecinos, aplica la regla y muéstrame cómo se ve la siguiente fila.

Fila actual:
{state_str}

Siguiente fila (solo las celdas):""",

        "minimal": """Regla {rule_number}:
{rule_table}

Actual: {state_str}
Siguiente:""",
    },

    "fr": {
        "linguistic": """Vous devez appliquer une règle d'automate cellulaire élémentaire 1D à une rangée de cellules.

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

        "casual": """Salut! Exécutons un automate cellulaire!

La règle {rule_number} dit:
{rule_table}

Vérifiez chaque cellule avec ses voisins, appliquez la règle et montrez-moi à quoi ressemble la rangée suivante.

Rangée actuelle:
{state_str}

Rangée suivante (juste les cellules):""",

        "minimal": """Règle {rule_number}:
{rule_table}

Actuel: {state_str}
Suivant:""",
    },

    "de": {
        "linguistic": """Sie sollen eine elementare 1D-Zellularautomaten-Regel auf eine Zellenreihe anwenden.

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

        "casual": """Hey! Lassen Sie uns einen Zellularautomaten ausführen!

Regel {rule_number} besagt:
{rule_table}

Überprüfen Sie jede Zelle mit ihren Nachbarn, wenden Sie die Regel an und zeigen Sie mir, wie die nächste Reihe aussieht.

Aktuelle Reihe:
{state_str}

Nächste Reihe (nur die Zellen):""",

        "minimal": """Regel {rule_number}:
{rule_table}

Aktuell: {state_str}
Nächste:""",
    },

    "zh": {
        "linguistic": """请对一维元胞自动机应用规则。

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

        "casual": """嘿！我们来运行一个元胞自动机！

规则 {rule_number} 说：
{rule_table}

检查每个细胞及其邻居，应用规则，告诉我下一行是什么样子。

当前行：
{state_str}

下一行（仅细胞）：""",

        "minimal": """规则 {rule_number}：
{rule_table}

当前：{state_str}
下一：""",
    },

    "ua": {
        "linguistic": """Ви маєте застосувати правило елементарного одновимірного клітинного автомата до рядка комірок.

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

        "casual": """Гей! Запустимо клітинний автомат!

Правило {rule_number} каже:
{rule_table}

Перевір кожну комірку з її сусідами, застосуй правило і покажи мені, як виглядає наступний рядок.

Поточний рядок:
{state_str}

Наступний рядок (лише комірки):""",

        "minimal": """Правило {rule_number}:
{rule_table}

Поточний: {state_str}
Наступний:""",
    },
}
