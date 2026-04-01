"""User prompt templates for the Symbol Arithmetic plugin.

Placeholders: {operation_table}, {expression}, {operator_symbol}, {symbol_set}
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": (
            "A custom binary operation {operator_symbol} is defined on the set "
            "{{{symbol_set}}} by the following table:\n\n"
            "{operation_table}\n\n"
            "Evaluate: {expression}\n\n"
            "Answer: "
        ),
        "casual": (
            "Hey! I've made up a new operation called {operator_symbol}. "
            "It works on the symbols {{{symbol_set}}} and here's the complete "
            "lookup table that defines it:\n\n"
            "{operation_table}\n\n"
            "Using ONLY this table (no normal math rules apply!), "
            "what does this evaluate to?\n\n"
            "{expression}\n\n"
            "Just give me the final symbol."
        ),
        "linguistic": (
            "Consider a binary operation {operator_symbol} defined on the "
            "finite set {{{symbol_set}}}. The operation is specified entirely "
            "by the lookup table below — no algebraic properties "
            "(commutativity, associativity, identity) should be assumed "
            "unless they are evident from the table.\n\n"
            "{operation_table}\n\n"
            "Evaluate the following expression step by step, resolving "
            "the innermost parentheses first and performing each lookup "
            "against the table:\n\n"
            "{expression}\n\n"
            "Show your working, then state the final result as a single "
            "symbol from the set."
        ),
    },
    "es": {
        "minimal": (
            "Una operación binaria personalizada {operator_symbol} está definida sobre el conjunto "
            "{{{symbol_set}}} mediante la siguiente tabla:\n\n"
            "{operation_table}\n\n"
            "Evalúa: {expression}\n\n"
            "Respuesta: "
        ),
        "casual": (
            "¡Hola! Me he inventado una nueva operación llamada {operator_symbol}. "
            "Funciona con los símbolos {{{symbol_set}}} y aquí tienes la tabla "
            "completa que la define:\n\n"
            "{operation_table}\n\n"
            "Usando SOLO esta tabla (¡no se aplican las reglas matemáticas normales!), "
            "¿a qué se evalúa esto?\n\n"
            "{expression}\n\n"
            "Dame solo el símbolo final."
        ),
        "linguistic": (
            "Considera una operación binaria {operator_symbol} definida sobre el "
            "conjunto finito {{{symbol_set}}}. La operación se especifica completamente "
            "mediante la tabla de consulta a continuación — no se deben asumir propiedades "
            "algebraicas (conmutatividad, asociatividad, identidad) "
            "a menos que sean evidentes a partir de la tabla.\n\n"
            "{operation_table}\n\n"
            "Evalúa la siguiente expresión paso a paso, resolviendo "
            "primero los paréntesis más internos y consultando cada resultado "
            "en la tabla:\n\n"
            "{expression}\n\n"
            "Muestra tu trabajo y luego indica el resultado final como un único "
            "símbolo del conjunto."
        ),
    },
    "fr": {
        "minimal": (
            "Une opération binaire personnalisée {operator_symbol} est définie sur l'ensemble "
            "{{{symbol_set}}} par la table suivante :\n\n"
            "{operation_table}\n\n"
            "Évaluez : {expression}\n\n"
            "Réponse : "
        ),
        "casual": (
            "Salut ! J'ai inventé une nouvelle opération appelée {operator_symbol}. "
            "Elle fonctionne sur les symboles {{{symbol_set}}} et voici la table "
            "complète qui la définit :\n\n"
            "{operation_table}\n\n"
            "En utilisant UNIQUEMENT cette table (les règles mathématiques normales "
            "ne s'appliquent pas !), à quoi cela s'évalue-t-il ?\n\n"
            "{expression}\n\n"
            "Donne-moi juste le symbole final."
        ),
        "linguistic": (
            "Considérez une opération binaire {operator_symbol} définie sur "
            "l'ensemble fini {{{symbol_set}}}. L'opération est entièrement spécifiée "
            "par la table de correspondance ci-dessous — aucune propriété algébrique "
            "(commutativité, associativité, identité) ne doit être supposée "
            "à moins qu'elle ne soit évidente dans la table.\n\n"
            "{operation_table}\n\n"
            "Évaluez l'expression suivante étape par étape, en résolvant "
            "d'abord les parenthèses les plus internes et en effectuant chaque "
            "recherche dans la table :\n\n"
            "{expression}\n\n"
            "Montrez votre raisonnement, puis indiquez le résultat final sous forme "
            "d'un seul symbole de l'ensemble."
        ),
    },
    "de": {
        "minimal": (
            "Eine benutzerdefinierte binäre Operation {operator_symbol} ist auf der Menge "
            "{{{symbol_set}}} durch die folgende Tabelle definiert:\n\n"
            "{operation_table}\n\n"
            "Auswerten: {expression}\n\n"
            "Antwort: "
        ),
        "casual": (
            "Hey! Ich habe eine neue Operation namens {operator_symbol} erfunden. "
            "Sie funktioniert mit den Symbolen {{{symbol_set}}} und hier ist die "
            "vollständige Nachschlagetabelle, die sie definiert:\n\n"
            "{operation_table}\n\n"
            "Verwende NUR diese Tabelle (normale Rechenregeln gelten nicht!). "
            "Was ergibt das?\n\n"
            "{expression}\n\n"
            "Gib mir einfach das Endsymbol."
        ),
        "linguistic": (
            "Betrachte eine binäre Operation {operator_symbol}, definiert auf der "
            "endlichen Menge {{{symbol_set}}}. Die Operation wird vollständig "
            "durch die unten stehende Nachschlagetabelle spezifiziert — es sollten keine "
            "algebraischen Eigenschaften (Kommutativität, Assoziativität, Identität) "
            "angenommen werden, es sei denn, sie ergeben sich offensichtlich aus der Tabelle.\n\n"
            "{operation_table}\n\n"
            "Werte den folgenden Ausdruck Schritt für Schritt aus, indem du "
            "zuerst die innersten Klammern auflöst und jede Nachschlageoperation "
            "anhand der Tabelle durchführst:\n\n"
            "{expression}\n\n"
            "Zeige deinen Lösungsweg und gib dann das Endergebnis als einzelnes "
            "Symbol aus der Menge an."
        ),
    },
    "zh": {
        "minimal": (
            "一个自定义二元运算 {operator_symbol} 在集合 "
            "{{{symbol_set}}} 上由以下表格定义：\n\n"
            "{operation_table}\n\n"
            "求值：{expression}\n\n"
            "答案："
        ),
        "casual": (
            "嘿！我发明了一个叫做 {operator_symbol} 的新运算。"
            "它作用于符号 {{{symbol_set}}}，这是定义它的完整查找表：\n\n"
            "{operation_table}\n\n"
            "仅使用这个表（不适用普通数学规则！），"
            "下面的表达式结果是什么？\n\n"
            "{expression}\n\n"
            "只给我最终的符号。"
        ),
        "linguistic": (
            "考虑一个定义在有限集合 {{{symbol_set}}} 上的二元运算 {operator_symbol}。"
            "该运算完全由以下查找表指定——不应假设任何代数性质"
            "（交换律、结合律、单位元），除非它们在表中显而易见。\n\n"
            "{operation_table}\n\n"
            "请逐步求值以下表达式，先解析最内层的括号，"
            "并对照表格执行每次查找：\n\n"
            "{expression}\n\n"
            "展示你的推导过程，然后给出最终结果——集合中的一个符号。"
        ),
    },
    "ua": {
        "minimal": (
            "Користувацька бінарна операція {operator_symbol} визначена на множині "
            "{{{symbol_set}}} за допомогою наступної таблиці:\n\n"
            "{operation_table}\n\n"
            "Обчисліть: {expression}\n\n"
            "Відповідь: "
        ),
        "casual": (
            "Привіт! Я вигадав нову операцію під назвою {operator_symbol}. "
            "Вона працює з символами {{{symbol_set}}}, і ось повна таблиця, "
            "що її визначає:\n\n"
            "{operation_table}\n\n"
            "Використовуючи ТІЛЬКИ цю таблицю (звичайні правила математики "
            "не застосовуються!), яким буде результат?\n\n"
            "{expression}\n\n"
            "Дай мені лише кінцевий символ."
        ),
        "linguistic": (
            "Розглянемо бінарну операцію {operator_symbol}, визначену на "
            "скінченній множині {{{symbol_set}}}. Операція повністю задана "
            "таблицею відповідності нижче — не слід припускати жодних алгебраїчних "
            "властивостей (комутативність, асоціативність, нейтральний елемент), "
            "якщо вони не є очевидними з таблиці.\n\n"
            "{operation_table}\n\n"
            "Обчисліть наступний вираз крок за кроком, розкриваючи спочатку "
            "найвнутрішніші дужки та виконуючи кожен пошук за таблицею:\n\n"
            "{expression}\n\n"
            "Покажіть хід розв'язання, а потім вкажіть кінцевий результат "
            "у вигляді одного символу з множини."
        ),
    },
}
