"""User prompt templates for the Family Relations plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{puzzle}\n\nAnswer with a single integer.",
        "casual": (
            "Hey, here's a quick family puzzle:\n\n"
            "{puzzle}\n\n"
            "What's the answer?  Just give me the number."
        ),
        "linguistic": (
            "Please solve the following family-relations reasoning problem. "
            "Think carefully about who is counted and from whose perspective.\n\n"
            "{puzzle}\n\n"
            "Provide your final answer as a single integer."
        ),
    },
    "es": {
        "minimal": "{puzzle}\n\nResponde con un solo número entero.",
        "casual": (
            "Oye, aquí tienes un acertijo familiar rápido:\n\n"
            "{puzzle}\n\n"
            "¿Cuál es la respuesta? Solo dame el número."
        ),
        "linguistic": (
            "Por favor, resuelve el siguiente problema de razonamiento sobre "
            "relaciones familiares. Piensa cuidadosamente en quién se cuenta "
            "y desde la perspectiva de quién.\n\n"
            "{puzzle}\n\n"
            "Proporciona tu respuesta final como un solo número entero."
        ),
    },
    "fr": {
        "minimal": "{puzzle}\n\nRépondez avec un seul nombre entier.",
        "casual": (
            "Salut, voici une petite énigme familiale :\n\n"
            "{puzzle}\n\n"
            "Quelle est la réponse ? Donne-moi juste le nombre."
        ),
        "linguistic": (
            "Veuillez résoudre le problème de raisonnement suivant portant sur "
            "les relations familiales. Réfléchissez bien à qui est compté "
            "et du point de vue de qui.\n\n"
            "{puzzle}\n\n"
            "Fournissez votre réponse finale sous la forme d'un seul nombre entier."
        ),
    },
    "de": {
        "minimal": "{puzzle}\n\nAntworten Sie mit einer einzelnen ganzen Zahl.",
        "casual": (
            "Hey, hier ist ein schnelles Familienrätsel:\n\n"
            "{puzzle}\n\n"
            "Was ist die Antwort? Gib mir einfach die Zahl."
        ),
        "linguistic": (
            "Bitte lösen Sie die folgende Aufgabe zum logischen Denken über "
            "Familienbeziehungen. Überlegen Sie genau, wer gezählt wird "
            "und aus wessen Perspektive.\n\n"
            "{puzzle}\n\n"
            "Geben Sie Ihre endgültige Antwort als einzelne ganze Zahl an."
        ),
    },
    "zh": {
        "minimal": "{puzzle}\n\n请用一个整数作答。",
        "casual": (
            "嘿，这里有一个简单的家庭关系谜题：\n\n"
            "{puzzle}\n\n"
            "答案是什么？只给我数字就好。"
        ),
        "linguistic": (
            "请解决以下关于家庭关系的推理问题。"
            "请仔细思考统计的是谁，以及从谁的视角出发。\n\n"
            "{puzzle}\n\n"
            "请以一个整数作为你的最终答案。"
        ),
    },
    "ua": {
        "minimal": "{puzzle}\n\nВідповідайте одним цілим числом.",
        "casual": (
            "Привіт, ось швидка сімейна загадка:\n\n"
            "{puzzle}\n\n"
            "Яка відповідь? Просто дай мені число."
        ),
        "linguistic": (
            "Будь ласка, розв'яжіть наступну задачу на логічне мислення "
            "щодо сімейних відносин. Ретельно подумайте, хто рахується "
            "і з чиєї перспективи.\n\n"
            "{puzzle}\n\n"
            "Надайте вашу остаточну відповідь у вигляді одного цілого числа."
        ),
    },
}
