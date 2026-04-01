"""User prompt templates for the Arithmetic plugin.

6 languages x 3 styles (linguistic, casual, minimal).
Placeholders: {expression}, {examples}
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "linguistic": (
            "Given the mathematical expression: {expression}\n\n"
            "Follow these EXACT steps:\n"
            "1. Identify all operations in the expression following order of operations (PEMDAS/BODMAS)\n"
            "2. Calculate each sub-expression step by step\n"
            "3. Show your work for every intermediate calculation\n"
            "4. Provide the final numerical result\n\n"
            "Expression: {expression}\n"
            "Step-by-step solution:\n"
            "[Show your work here]\n\n"
            "Final answer: [number only]"
        ),
        "casual": (
            "Hey! Can you solve this math expression for me? "
            "Just work through it step by step.\n"
            "{expression}\n\n"
            "Show me how you get to the answer:\n"
            "[Your work here]\n\n"
            "Final answer: [just the number]"
        ),
        "minimal": "{expression}\n\nAnswer: ",
    },

    "es": {
        "linguistic": (
            "Dada la expresion matematica: {expression}\n\n"
            "Sigue estos pasos EXACTOS:\n"
            "1. Identifica todas las operaciones en la expresion siguiendo el orden de operaciones (PEMDAS/BODMAS)\n"
            "2. Calcula cada subexpresion paso a paso\n"
            "3. Muestra tu trabajo para cada calculo intermedio\n"
            "4. Proporciona el resultado numerico final\n\n"
            "Expresion: {expression}\n"
            "Solucion paso a paso:\n"
            "[Muestra tu trabajo aqui]\n\n"
            "Respuesta final: [solo el numero]"
        ),
        "casual": (
            "Hola! Puedes resolver esta expresion matematica por mi? "
            "Solo resuelvela paso a paso.\n"
            "{expression}\n\n"
            "Muestrame como llegas a la respuesta:\n"
            "[Tu trabajo aqui]\n\n"
            "Respuesta final: [solo el numero]"
        ),
        "minimal": "{expression}\n\nRespuesta: ",
    },

    "fr": {
        "linguistic": (
            "Etant donnee l'expression mathematique : {expression}\n\n"
            "Suivez ces etapes EXACTES :\n"
            "1. Identifiez toutes les operations dans l'expression en suivant l'ordre des operations (PEMDAS/BODMAS)\n"
            "2. Calculez chaque sous-expression etape par etape\n"
            "3. Montrez votre travail pour chaque calcul intermediaire\n"
            "4. Fournissez le resultat numerique final\n\n"
            "Expression : {expression}\n"
            "Solution etape par etape :\n"
            "[Montrez votre travail ici]\n\n"
            "Reponse finale : [nombre uniquement]"
        ),
        "casual": (
            "Salut ! Tu peux resoudre cette expression mathematique pour moi ? "
            "Travaille dessus etape par etape.\n"
            "{expression}\n\n"
            "Montre-moi comment tu arrives a la reponse :\n"
            "[Ton travail ici]\n\n"
            "Reponse finale : [juste le nombre]"
        ),
        "minimal": "{expression}\n\nReponse : ",
    },

    "de": {
        "linguistic": (
            "Gegeben der mathematische Ausdruck: {expression}\n\n"
            "Befolge diese EXAKTEN Schritte:\n"
            "1. Identifiziere alle Operationen im Ausdruck gemaess der Operationsreihenfolge (PEMDAS/BODMAS)\n"
            "2. Berechne jeden Teilausdruck Schritt fuer Schritt\n"
            "3. Zeige deine Arbeit fuer jede Zwischenberechnung\n"
            "4. Gib das endgueltige numerische Ergebnis an\n\n"
            "Ausdruck: {expression}\n"
            "Schritt-fuer-Schritt-Loesung:\n"
            "[Zeige deine Arbeit hier]\n\n"
            "Endgueltige Antwort: [nur die Zahl]"
        ),
        "casual": (
            "Hey! Kannst du diesen mathematischen Ausdruck fuer mich loesen? "
            "Arbeite ihn einfach Schritt fuer Schritt durch.\n"
            "{expression}\n\n"
            "Zeig mir, wie du zur Antwort kommst:\n"
            "[Deine Arbeit hier]\n\n"
            "Endgueltige Antwort: [nur die Zahl]"
        ),
        "minimal": "{expression}\n\nAntwort: ",
    },

    "zh": {
        "linguistic": (
            "给定数学表达式: {expression}\n\n"
            "请按照以下确切步骤操作:\n"
            "1. 按照运算顺序(PEMDAS/BODMAS)识别表达式中的所有运算\n"
            "2. 逐步计算每个子表达式\n"
            "3. 展示每个中间计算的过程\n"
            "4. 提供最终的数值结果\n\n"
            "表达式: {expression}\n"
            "逐步解答:\n"
            "[在此展示你的计算过程]\n\n"
            "最终答案: [仅填写数字]"
        ),
        "casual": (
            "嗨! 你能帮我解这道数学题吗? "
            "请一步一步地算出来。\n"
            "{expression}\n\n"
            "给我看看你是怎么算出答案的:\n"
            "[你的计算过程]\n\n"
            "最终答案: [只写数字]"
        ),
        "minimal": "{expression}\n\n答案: ",
    },

    "ua": {
        "linguistic": (
            "Дано математичний вираз: {expression}\n\n"
            "Виконай ці ТОЧНІ кроки:\n"
            "1. Визнач усі операції у виразі, дотримуючись порядку операцій (PEMDAS/BODMAS)\n"
            "2. Обчисли кожен підвираз крок за кроком\n"
            "3. Покажи свою роботу для кожного проміжного обчислення\n"
            "4. Надай остаточний числовий результат\n\n"
            "Вираз: {expression}\n"
            "Покрокове розв'язання:\n"
            "[Покажи свою роботу тут]\n\n"
            "Остаточна відповідь: [лише число]"
        ),
        "casual": (
            "Привіт! Можеш розв'язати цей математичний вираз для мене? "
            "Просто розв'яжи його крок за кроком.\n"
            "{expression}\n\n"
            "Покажи мені, як ти отримав відповідь:\n"
            "[Твоя робота тут]\n\n"
            "Остаточна відповідь: [лише число]"
        ),
        "minimal": "{expression}\n\nВідповідь: ",
    },
}
